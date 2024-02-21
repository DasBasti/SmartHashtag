# Smart #1 and #3 Integration

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![CodeQL Validation][codeql-shield]][codeql]
[![Dependency Validation][tests-shield]][tests]

**This integration will set up the following platforms.**

| Sensor Name                  | Sensor Type                       | Unit of Measurement | Attributes | Notes                                    |
| ---------------------------- | --------------------------------- | ------------------- | ---------- | ---------------------------------------- |
| `Last Update`                | Last data update                  | Timestamp           |            | Data age in Web API                      |
| `Engine State`               | Boolean                           |                     |            | If in 'D' True else False                |
| `Odometer`                   | Total distance traveled           | km                  |            |                                          |
| `Days to next service`       | Duration                          | d                   |            |                                          |
| `Distance to next service`   | Distance                          | km                  |            |                                          |
| `Remaining Range`            | Distance                          | km                  |            |                                          |
| `Range at full battery`      | Distance                          | km                  |            |                                          |
| `Remaining Battery Charge`   | Percent                           | %                   |            |                                          |
| `Charger Connection Status`  | Number                            | ?                   |            | Need to determine what number means what |
| `Is Charger Connected`       | Boolen                            | True, False         |            |                                          |
| `Charging Voltage`           | Volts at Charging Port            | V                   |            |                                          |
| `Charging Current`           | Ampere at Charging Port           | A                   |            |                                          |
| `Charging Power`             | Power going to Battery            | W                   |            |                                          |
| `Charging Time remaining`    | Duration                          | min                 |            |                                          |
| `Charging Target Percent`    | Percent State of Charge           | %                   |            | Not yet available                        |
| `Tire Temperature`           | Temperature                       | °C                  |            |                                          |
| `Tire Pressure`              | Pressure                          | kPa                 |            |                                          |
| `12V Battery State`          | State, Voltage, Energy Level      | V, %                |            | Determine what some of the values mean   |
| `Fluid States`               | Numerical                         |                     |            | Determine what each number means         |
| `Light states`               | Boolean                           |                     |            | Check names of sensors                   |
| `Trim Meter`                 | Distance                          | km                  |            | 2 different trip counter                 |
| `Climate Sensors`            | Blower and Heating States         |                     |            | Test what the different numbers mean     |
| `Window Status and Position` | Numerical                         |                     |            | Test what the different numbers mean     |
| `Temperatur Sensor`          | Inner and Surrounding Temperature | °C                  |            |                                          |

| Climate Name       | Climate Type | Unit of Measurement | Attributes | Notes                                   |
| ------------------ | ------------ | ------------------- | ---------- | --------------------------------------- |
| `Pre Conditioning` | Temperature  | °C                  |            | Works not very stable, work in progress |

| Device Tracker     | Type     | Unit of Measurement | Attributes | Notes |
| ------------------ | -------- | ------------------- | ---------- | ----- |
| `Pre Conditioning` | Position | Geoposition         |            |       |

## Installation

### Using HACS (Recommended)

1. Add this repository to your custom repositories
1. Search for and install "Smart #1/#3 Integration" in HACS.
1. Restart Home Assistant.
1. In the Home Assistant UI go to "Configuration" -> "Integrations" click "+" and search for "Smart"

### Manually Copy Files

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `smarthashtag`.
1. Download _all_ the files from the `custom_components/smarthashtag/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the Home Assistant UI go to "Configuration" -> "Integrations" click "+" and search for "Smart"

### Finally

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=smarthashtag)

## Contributions are welcome!

We need to add more sensor values from the JSON aquired form the Web API. Please have a look at [pySmartHashtag](https://github.com/DasBasti/pySmartHashtag).
If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

---

[![Project Maintenance][maintenance-shield]](https://platinenmacher.tech)

[commits-shield]: https://img.shields.io/github/commit-activity/y/DasBasti/smarthashtag.svg
[commits]: https://github.com/DasBasti/smarthashtag/commits/main
[license-shield]: https://img.shields.io/github/license/DasBasti/smarthashtag.svg
[maintenance-shield]: https://img.shields.io/badge/maintainer-Bastian%20Neumann%20%40DasBasti-blue.svg
[releases-shield]: https://img.shields.io/github/v/release/DasBasti/smarthashtag.svg
[releases]: https://github.com/DasBasti/smarthashtag/releases
[codeql-shield]: https://github.com/DasBasti/smarthashtag/actions/workflows/codeql-analysis.yml/badge.svg
[codeql]: https://github.com/DasBasti/smarthashtag/actions/workflows/codeql-analysis.yml
[tests-shield]: https://github.com/DasBasti/SmartHashtag/actions/workflows/tests.yml/badge.svg
[tests]: https://github.com/DasBasti/SmartHashtag/actions/workflows/tests.yml
