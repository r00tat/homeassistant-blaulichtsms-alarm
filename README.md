# blaulichtSMS Alarm für Home Assistant

Home-Assistant-Integration, mit der aus Automatisierungen heraus
[blaulichtSMS](https://blaulichtsms.net/) Alarme, Infos und Termine **ausgelöst**
werden können.

Sie ist das Gegenstück zu
[hassio_blaulichtsms](https://github.com/r00tat/hassio_blaulichtsms), das Alarme
nur abruft. Beide Integrationen können parallel installiert sein.

Grundlage ist die
[blaulichtSMS Alarm API v1](https://github.com/blaulichtSMS/docs/blob/master/alarm_api_v1.md).

## Voraussetzungen

Für die Kundennummer muss bei blaulichtSMS ein **automatischer Alarmauslöser**
mit Benutzername und Passwort eingerichtet sein. Das sind andere Zugangsdaten
als die des Einsatzmonitors.

## Installation

1. HACS öffnen, 3 Punkte, "Benutzerdefinierte Repositories"
2. `https://github.com/r00tat/homeassistant-blaulichtsms-alarm` als Repository,
   Kategorie `Integration`
3. "blaulichtSMS Alarm" installieren und Home Assistant neu starten
4. Integration hinzufügen und dem Wizard folgen

## Einrichtung

Der Wizard hat zwei Schritte:

1. **Zugangsdaten** — Kundennummer, Benutzername, Passwort. Optional kann die
   Test-API verwendet werden, um Automatisierungen gefahrlos zu erproben. Die
   Prüfung erfolgt über eine reine Leseabfrage, es wird kein Alarm ausgelöst.
2. **Alarmgruppen-Filter** — optionale, kommagetrennte Liste der Gruppencodes,
   die alarmiert werden dürfen.

Der Filter lässt sich später über "Konfigurieren" ändern.

### Wirkung des Filters

Ist ein Filter gesetzt, gilt strikt:

| Filter | `group_codes` im Aufruf | Ergebnis |
| --- | --- | --- |
| `G1,G2` | `G1` | wird alarmiert |
| `G1,G2` | `G1,G3` | Fehler, es wird nichts ausgelöst |
| `G1,G2` | nicht angegeben | Fehler, Gruppen müssen genannt werden |
| leer | beliebig | alles erlaubt |

Solange ein Filter gesetzt ist, ist `additional_msisdns` gesperrt — einzelne
Rufnummern würden den Filter sonst umgehen.

## Services

| Service | Wirkung |
| --- | --- |
| `blaulichtsms_alarm.trigger_alarm` | Alarm sofort auslösen |
| `blaulichtsms_alarm.send_info` | Info sofort senden |
| `blaulichtsms_alarm.create_appointment` | Termin für einen späteren Zeitpunkt |
| `blaulichtsms_alarm.query_alarm` | Daten eines Alarms samt Rückmeldungen |
| `blaulichtsms_alarm.list_alarms` | Alarme der Kundennummer auflisten |

### Beispiele

```yaml
action: blaulichtsms_alarm.trigger_alarm
data:
  alarm_text: "Brand B2, Hauptstraße 1"
  group_codes: ["G1", "G2"]
  needs_acknowledgement: true
  duration: 60
  address: "Hauptstraße 1, 7000 Eisenstadt"
```

```yaml
action: blaulichtsms_alarm.create_appointment
data:
  alarm_text: "Monatsschulung im Rüsthaus"
  start_date: "2026-10-01 18:00:00"
  group_codes: ["G1"]
```

Die auslösenden Services geben `alarm_id`, `result` und `alarm_data` zurück:

```yaml
actions:
  - action: blaulichtsms_alarm.trigger_alarm
    data:
      alarm_text: "Übung"
      group_codes: ["G1"]
    response_variable: alarm
  - action: persistent_notification.create
    data:
      message: "Alarm {{ alarm.alarm_id }} ausgelöst"
```

## Entität

`sensor.blaulichtsms_alarm_zuletzt_ausgeloester_alarm` zeigt den Zeitpunkt der
letzten Auslösung über diese Integration. Attribute: `alarm_id`, `alarm_text`,
`type`, `group_codes`, `result`. Der Wert übersteht einen Neustart.

## Entwicklung

`./dev.sh` legt die venv an, synchronisiert die Komponente nach `config/` und
startet Home Assistant im Container auf Port 8123.

```bash
uv run python -m ruff check            # Lint
uv run python -m unittest discover -v  # Tests
```

## Lizenz

Diese Software steht in keiner Verbindung zu blaulichtSMS. Lizenziert unter
[Apache License 2.0](LICENSE).
