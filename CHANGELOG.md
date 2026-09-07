# Changelog

## [0.2.1](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/compare/0.2.0...0.2.1) (2026-09-07)


### Bug Fixes

* **deps:** update ruff requirement from ~=0.16.3 to ~=0.16.6 ([#3](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/issues/3)) ([ab8a9e2](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/ab8a9e206fd30d37f9e3945457bf528bddccb830))


### Documentation

* HACS-Button ergänzen und Lizenz auf GPLv3 korrigieren ([#4](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/issues/4)) ([7f30381](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/7f3038123cbba64e819446fc2b72363b176369f7))

## [0.2.0](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/compare/0.1.0...0.2.0) (2026-09-07)


### Features

* **api:** derive the alarm group inventory from list responses ([558a1d3](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/558a1d3f5bd7fa94e4b03f3c5157d8fbcc1f379c))
* **api:** let list_alarms return only the newest n alarms ([77e75e3](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/77e75e3e3342375a3d47fdb5a2fbae88983e903d))
* blaulichtSMS Alarm Integration ([ba74fc3](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/ba74fc32262f1644497067ad6c5ec4b11c983dfc))
* **config_flow:** pick the alarm groups from a list instead of typing them ([f722b9a](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/f722b9a6b321a636c8ab9143d239de3bd9f99a07))
* deutsche und englische Texte für Wizard, Services und Fehler ([b58960c](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/b58960cd3614e48d50bf3116cc362288f726ab46))
* Einrichtungs-Wizard mit Zugangsdaten- und Gruppen-Schritt ([47f5d5e](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/47f5d5e4f5aa0531297216b135512aca9616be80))
* Exception-Hierarchie für den Alarm API Client ([8433e14](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/8433e144bedddbc504a74b1d62a2e7aa7c1e3be4))
* Felddefinitionen für die Service-Oberfläche ([dc4df00](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/dc4df001461f78b4ab73c79f7096666d8ecf1b1f))
* HTTP-Client für trigger, query und list ([ee08eb7](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/ee08eb72d95142f05f32bf331d4a3e9abc0a5055))
* Payload-Builder für den Alarm API Trigger-Endpunkt ([da3ae5e](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/da3ae5ea95ef4a5e80a902882dfe35dd97d3fbf3))
* Schemas und Helfer für den Einrichtungs-Wizard ([273213f](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/273213f4e67b23ad1d8a3fc2acdf6cebc70a505f))
* Sensor für den zuletzt ausgelösten Alarm ([494a000](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/494a0001936eff38780c0bd2d5ae0fc5d4ea7272))
* Services zum Auslösen und Abfragen von Alarmen ([c0a7f14](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/c0a7f149fc4b76fda6fa95bc3d56b0343d505253))
* **services:** add a limit field to list_alarms ([aaf6268](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/aaf62687a505e07d7d1c33b2b88a2c9b6a3aa4be))
* Setup des Config Entry mit Zugangsdaten-Prüfung ([596b647](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/596b647d430a384f019d94cd9fd11ab1ccfd03f8))
* strikte Durchsetzung des Alarmgruppen-Filters ([718540d](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/718540d396d28bf18ee42306f3bec8cbb6e10874))
* **wizard:** say that the alarm api needs its own alarm trigger user ([dff0fb7](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/dff0fb781ef2bfa09af8580d858bcffcd7d7d705))


### Documentation

* Design für blaulichtSMS Alarm Integration ([7206dab](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/7206dab311eab3561abee66b2343b2691d104e5f))
* document the limit field of list_alarms ([77f1a0b](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/77f1a0bd285d62de533c98aa3bf2aa7a2aae34f3))
* explain the alarm trigger user and the group suggestions ([7bdb762](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/7bdb7629b12ad4dfcfc36ece5697f70ff23c4c18))
* Implementierungsplan für die blaulichtSMS Alarm Integration ([2b99699](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/2b996998c1324161b642319ebfb85e756f1ebf18))
* README und Projektleitfaden ([73de759](https://github.com/r00tat/homeassistant-blaulichtsms-alarm/commit/73de7596781de6400369d5e94ce81df8b304bb42))
