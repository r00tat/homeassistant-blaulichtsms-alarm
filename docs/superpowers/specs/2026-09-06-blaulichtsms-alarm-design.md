# blaulichtSMS Alarm — Home Assistant Integration

Design-Dokument, 2026-09-06

## Ziel

Eine Home-Assistant-Custom-Integration, mit der aus Automatisierungen heraus
blaulichtSMS-Alarme, -Infos und -Termine **ausgelöst** werden können. Sie ist das
Gegenstück zur bestehenden Integration
[`blaulichtsms`](https://github.com/r00tat/hassio_blaulichtsms), die Alarme nur
*abruft*.

Grundlage ist die
[blaulichtSMS Alarm API v1](https://github.com/blaulichtSMS/docs/blob/master/alarm_api_v1.md).
Sie ist von der Dashboard-API getrennt und benötigt eigene Zugangsdaten
("automatischer Alarmauslöser", pro `customerId` freizuschalten).

Verteilung über HACS, wie beim bestehenden Plugin.

## Abgrenzung

Die Alarm-API kennt nur drei Endpunkte: `trigger`, `query` und `list`. Einen
eigenen Termin-Endpunkt gibt es nicht. Die Begriffe bilden sich so ab:

| Begriff | `type` | `startDate` |
| --- | --- | --- |
| Alarm | `alarm` | nicht gesetzt (sofort) |
| Info | `info` | nicht gesetzt (sofort) |
| Termin | `info` | Zeitpunkt in der Zukunft |

Nicht Teil dieser Integration: Abrufen laufender Alarme zur Anzeige
(macht `blaulichtsms`), Lovelace-Karten, Rückmeldungs-Auswertung.

## Architektur

Eigenständige Integration mit der Domain `blaulichtsms_alarm`. Die Domain
unterscheidet sich bewusst von `blaulichtsms`, damit beide Integrationen
gleichzeitig installiert sein können.

```
custom_components/blaulichtsms_alarm/
  __init__.py          Setup/Teardown des Config Entry, Service-Registrierung
  api.py               AlarmApiClient — HTTP-Client, keine HA-Abhängigkeiten
  errors.py            Exception-Hierarchie des Clients
  group_filter.py      Reine Funktion: Durchsetzung des Gruppen-Filters
  services.py          Service-Handler, Mapping HA-Felder -> API-Payload
  services.yaml        Feld-Definitionen für die HA-Service-UI
  config_flow.py       Einrichtungs-Wizard, Options-, Reauth-, Reconfigure-Flow
  schema.py            voluptuous-Schemas der Flows
  sensor.py            Sensor "letzter ausgelöster Alarm"
  const.py             DOMAIN, CONF_*, DEFAULT_*, VERSION
  manifest.json  strings.json  translations/{de,en}.json
  test_*.py            unittest, im Komponenten-Verzeichnis
```

Jede Einheit hat eine Aufgabe und ist für sich testbar: `api.py` kennt Home
Assistant nicht, `group_filter.py` ist eine reine Funktion ohne I/O,
`services.py` übersetzt zwischen beidem.

### Datenfluss

```
Automatisierung
  -> Service-Handler (services.py)
     -> Config Entry auflösen
     -> group_filter.resolve_group_codes(angefragt, erlaubt)
     -> AlarmApiClient.trigger(...)
        -> POST /api/alarm/v1/trigger
     -> RuntimeData.last_alarm aktualisieren + Dispatcher-Signal
        -> Sensor schreibt neuen State
     -> ServiceResponse an die Automatisierung
```

`entry.runtime_data` hält ein `BlaulichtSmsAlarmRuntimeData`-Dataclass mit dem
Client, dem Gruppen-Filter und dem zuletzt ausgelösten Alarm. In `hass.data`
wird nichts abgelegt.

## API-Client (`api.py`)

`AlarmApiClient(customer_id, username, password, base_url, session)`.

Die Alarm-API kennt **keinen** Login- oder Session-Mechanismus: Benutzername,
Passwort und `customerId` werden bei jedem Request im JSON-Body mitgeschickt.

Methoden:

- `async trigger(**felder) -> dict` — POST `/api/alarm/v1/trigger`
- `async query(alarm_id) -> dict` — POST `/api/alarm/v1/query`
- `async list_alarms(start_date=None, end_date=None) -> list[dict]` —
  POST `/api/alarm/v1/list`, `customerIds` ist `[customer_id]`

Base-URLs:

- Live: `https://api.blaulichtsms.net/blaulicht`
- Test: `https://api-staging.blaulichtsms.net/blaulicht`

### Payload-Aufbau

Nur gesetzte Felder werden in den Payload übernommen; `None` wird
weggelassen, damit die API-Defaults greifen. `startDate` wird nach UTC
konvertiert und als `2026-10-01T16:00:00.000Z` serialisiert.

Standort: entweder `coordinates: {lat, lon}` **oder**
`geolocation: {address: "..."}`. Werden beide angegeben, gewinnen die
Koordinaten und die Adresse wird verworfen (mit Log-Warnung).

### Fehlerbehandlung

Die API antwortet mit HTTP 200 und einem `result`-Feld. Der Client wertet
dieses aus:

- `OK` -> Rückgabe des geparsten Bodys
- `UNKNOWN_USER`, `NOT_AUTHORIZED`, `NOT_CONFIGURED_FOR_CUSTOMER`,
  `INVALID_CUSTOMER_ID`, `DEACTIVATED` -> `BlaulichtSmsAuthError`
- alles andere (`INVALID_GROUP`, `INVALID_TEMPLATE`, `NOT_FOUND`,
  `MISSING_*`, `UNKNOWN_ERROR`, unbekannte Codes) ->
  `BlaulichtSmsApiError(result, description)`

HTTP-Fehler und Netzwerkprobleme schlagen als `aiohttp.ClientError` durch.
Das Passwort wird in allen Log-Ausgaben durch `***` ersetzt.

## Gruppen-Filter (`group_filter.py`)

Der optionale Filter ist eine Liste erlaubter `groupCodes`. Ist er gesetzt,
gilt **strikt und immer explizit**:

```python
def resolve_group_codes(
    requested: list[str] | None,
    allowed: list[str] | None,
) -> list[str] | None:
    ...
```

| erlaubt | angefragt | Ergebnis |
| --- | --- | --- |
| leer / nicht gesetzt | beliebig | unverändert durchgereicht |
| `[G1, G2]` | `[G1]` | `[G1]` |
| `[G1, G2]` | `[G1, G3]` | `GroupNotAllowedError(["G3"])` |
| `[G1, G2]` | leer / nicht gesetzt | `GroupsRequiredError` |

Ein Fehler bedeutet: es wird **nichts** ausgelöst, der API-Aufruf unterbleibt.
Der Vergleich ist case-sensitiv, Leerzeichen um die Codes werden auf beiden
Seiten getrimmt.

**`additional_msisdns` ist gesperrt, solange ein Gruppen-Filter gesetzt ist.**
Ohne diese Sperre ließe sich die Gruppenbeschränkung umgehen, indem einzelne
Rufnummern direkt alarmiert werden.

## Services

Registriert in `async_setup`, also einmalig und unabhängig von der Zahl der
Config Entries.

### Zielauswahl

Jeder Service hat ein optionales Feld `config_entry` (`ConfigEntrySelector`).
Ist genau ein Eintrag konfiguriert, darf es entfallen und wird automatisch
aufgelöst. Bei mehreren Einträgen ohne Angabe: `ServiceValidationError`.

### Auslösende Services

| Service | `type` | `startDate` |
| --- | --- | --- |
| `blaulichtsms_alarm.trigger_alarm` | `alarm` | — |
| `blaulichtsms_alarm.send_info` | `info` | — |
| `blaulichtsms_alarm.create_appointment` | `info` | Pflichtfeld `start_date` |

Gemeinsame Felder:

| Feld | Typ | Anmerkung |
| --- | --- | --- |
| `config_entry` | Config Entry | optional bei genau einem Eintrag |
| `alarm_text` | Text | |
| `group_codes` | Liste Text | Pflicht, wenn ein Filter gesetzt ist |
| `needs_acknowledgement` | Boolean | Default `true` |
| `duration` | Integer | Rückmeldefenster, 1:1 an die API |
| `template` | Text | z.B. `A1` |
| `index_number` | Integer | gleicher Wert aktualisiert einen Alarm |
| `additional_msisdns` | Liste Text | gesperrt bei gesetztem Filter |
| `hide_trigger_details` | Boolean | |
| `recipient_confirmation` | Boolean | kostenpflichtig |
| `recipient_confirmation_target` | Text | Rufnummer |
| `location` | Standort (lat/lon) | alternativ zu `address` |
| `address` | Text | wird von der API geocodiert |

`create_appointment` hat zusätzlich `start_date` (Datum + Uhrzeit, Pflicht).

Rückgabe (`SupportsResponse.OPTIONAL`):

```yaml
alarm_id: "dakldjsfal-2343232-afsdaddfa-234"
result: "OK"
alarm_data: {...}
```

### Abfragende Services

- `blaulichtsms_alarm.query_alarm` — Felder `config_entry`, `alarm_id`
  (Pflicht). Gibt `alarm_data` zurück. `SupportsResponse.ONLY`.
- `blaulichtsms_alarm.list_alarms` — Felder `config_entry`, `start_date`,
  `end_date` (beide optional). Gibt `alarms` (Liste) zurück.
  `SupportsResponse.ONLY`.

### Fehler in Services

- `ServiceValidationError` (mit `translation_key`) für Nutzerfehler:
  unbekannter/mehrdeutiger Config Entry, unerlaubte Gruppe, fehlende Gruppen,
  gesperrte `additional_msisdns`.
- `HomeAssistantError` für API- und Netzwerkfehler, mit `result` und
  `description` der API im Text.
- Bei `BlaulichtSmsAuthError` wird zusätzlich `entry.async_start_reauth(hass)`
  ausgelöst, damit die Zugangsdaten in der UI korrigiert werden können.

## Einrichtungs-Wizard (`config_flow.py`)

Zwei Schritte:

1. **`user` — Zugangsdaten:** `customer_id`, `username`, `password`,
   `use_staging` (Boolean, Default `false`).
2. **`groups` — Alarmierungs-Filter:** `group_filter` (Text, kommagetrennt,
   optional). Leer bedeutet: alle Gruppen dürfen alarmiert werden.

Die Zugangsdaten werden nach Schritt 1 mit einem Aufruf von
`/api/alarm/v1/list` geprüft. Der Aufruf ist **lesend und löst keinen Alarm
aus**. Fehlerzuordnung: `BlaulichtSmsAuthError` -> `invalid_auth`,
`aiohttp.ClientError` -> `cannot_connect`, sonstige `BlaulichtSmsApiError` ->
`unknown` (mit `description` im Log).

`unique_id` ist `live-<customerId>` bzw. `staging-<customerId>`. So können
Test- und Live-Zugang parallel eingerichtet werden.
Titel des Eintrags: `blaulichtSMS Alarm <customerId>`, bei Staging mit dem
Zusatz `(Test)`.

Zusätzlich:

- **Options-Flow:** `group_filter` nachträglich ändern.
- **Reauth-Flow:** `username` + `password` neu erfassen, ausgelöst durch
  Auth-Fehler beim Setup oder in einem Service.
- **Reconfigure-Flow:** `username`, `password` und `use_staging` ändern.

Die effektive Konfiguration ist stets `{**entry.data, **entry.options}`. Eine
Änderung an Daten oder Optionen lädt den Eintrag über einen Update-Listener neu.

## Setup (`__init__.py`)

`async_setup` registriert die Services.

`async_setup_entry`:

1. `AlarmApiClient` mit der `aiohttp`-Session von Home Assistant bauen.
2. Zugangsdaten mit einem `list`-Aufruf verifizieren.
   `BlaulichtSmsAuthError` -> `ConfigEntryAuthFailed`,
   `aiohttp.ClientError` -> `ConfigEntryNotReady`.
3. `entry.runtime_data` setzen, Plattform `sensor` weiterleiten,
   Update-Listener registrieren.

Reine Config-Entry-Integration: kein YAML-Setup, kein `PLATFORM_SCHEMA`.

## Sensor (`sensor.py`)

Eine Entity: `BlaulichtSmsLastTriggeredSensor`.

- `device_class: timestamp`, State ist der Zeitpunkt der letzten erfolgreichen
  Auslösung über diese Integration.
- Attribute: `alarm_id`, `alarm_text`, `type`, `group_codes`, `result`.
- `RestoreEntity`, damit der letzte Stand einen Neustart übersteht.
- Kein Polling (`should_poll = False`). Aktualisierung über ein
  Dispatcher-Signal, das die Service-Handler nach jedem erfolgreichen
  `trigger` senden.
- Vor der ersten Auslösung (und ohne wiederhergestellten Stand) ist der State
  `unknown`.

## Tests

`unittest`, Testdateien liegen neben dem Code (Konvention aus dem bestehenden
Plugin). Kein Test benötigt Netzwerkzugriff.

- `test_api.py` — Payload-Aufbau (Weglassen von `None`, `startDate`-Format,
  Koordinaten vs. Adresse), Zuordnung der `result`-Codes zu Exceptions,
  Live-/Staging-URL, Passwort-Maskierung im Log.
- `test_group_filter.py` — die vollständige Matrix aus dem Abschnitt oben,
  inklusive Trimmen und Case-Sensitivität.
- `test_services.py` — mit einem Fake-Client: korrektes `type`/`startDate`
  je Service, Durchsetzung des Filters (kein API-Aufruf im Fehlerfall),
  Sperre für `additional_msisdns`, Auflösung des Config Entry,
  Form der Rückgabewerte, Fehlerübersetzung.
- `test_sensor.py` — Zustand nach Auslösung, Wiederherstellung nach Neustart,
  Attribute.
- `test_config_flow.py` — beide Wizard-Schritte, Auth- und Verbindungsfehler,
  `unique_id`-Vergabe live/staging, Options-, Reauth- und Reconfigure-Flow.

Entwickelt wird testgetrieben: pro Einheit erst der fehlschlagende Test,
dann die Implementierung.

## Werkzeuge und Auslieferung

- venv über `uv`, Aufrufe als `uv run python -m ...`.
- Ruff-Konfiguration aus dem bestehenden Plugin übernommen (Ziel `py310`,
  Zeilenlänge 88, HA-Regelsatz). Vor jedem Commit lauffähig und warnungsfrei.
- `dev.sh` synchronisiert die Komponente in eine lokale HA-Instanz und startet
  sie im Container.
- `hacs.json` mit `"iot_class": "cloud_push"`, `manifest.json` als einzige
  Quelle der Versionsnummer.
- Release über release-please; ein Workflow zippt bei einem Release
  `custom_components/blaulichtsms_alarm/` und hängt das Archiv an, damit HACS
  es laden kann.
- Commits nach Conventional Commits.

## Festgelegte Annahmen

1. Die Einheit von `duration` ist in der API-Dokumentation nicht angegeben.
   Der Wert wird unverändert durchgereicht und in `services.yaml` als
   "laut blaulichtSMS-Dokumentation Minuten" beschrieben.
2. `needs_acknowledgement` ist bei allen drei auslösenden Services
   standardmäßig `true`, auch beim Termin (Rückmeldung, wer kommt).
3. `additional_msisdns` ist gesperrt, sobald ein Gruppen-Filter gesetzt ist.
