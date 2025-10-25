# Smart #1 and #3 Integration

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![CodeQL Validation][codeql-shield]][codeql]
[![Dependency Validation][tests-shield]][tests]

## Installation

### Using HACS (Recommended)

1. Search for and install "Smart #1/#3 Integration" in HACS.
1. Restart Home Assistant.
1. In the Home Assistant UI go to "Configuration" -> "Integrations" click "+" and search for "Smart"

### Manually Copy Files

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `smarthashtag`.
1. Download _all_ the files from the `custom_components/smarthashtag/` directory (folder) in this repository. You can download from the current [Release](https://github.com/DasBasti/SmartHashtag/releases)
1. Extract the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the Home Assistant UI go to "Configuration" -> "Integrations" click "+" and search for "Smart"

### Finally

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=smarthashtag)

## Connect to ABRP

[@chriscatuk](https://github.com/chriscatuk) integrated [A Better Route Planner](https://abetterrouteplanner.com/) with data from this component. To automatically send the information everytime the component updates, add this to your automations.

```yaml
# based on https://documenter.getpostman.com/view/7396339/SWTK5a8w
alias: ABRP update
description: ""
triggers:
  - entity_id:
      - sensor.smart_last_update
    trigger: state
conditions: []
actions:
  - action: rest_command.abrp
    data:
      token: 99999999-aaaa-aaaa-bbbb-eeeeeeeeee # generated for each car in ABRP app
      api_key: 8888888-2222-44444-bbbb-333333333 # obtained from contact@iternio.com , see https://documenter.getpostman.com/view/7396339/SWTK5a8w
      utc: "{{ as_timestamp(states('sensor.smart_last_update')) | int }}"
      soc: >-
        {{ states('sensor.smart_battery', rounded=False, with_unit=False) |
        default('') }}
      soh: 100
      power: >
        {% if states('sensor.smart_charging_power', rounded=False,
        with_unit=False) | default(0) | float > 0 %}
            -{{ states('sensor.smart_charging_power', rounded=False, with_unit=False) | int / 1000 }}
        {% else %}
        0
        {% endif %}
      speed: ""
      lat: "{{ state_attr('device_tracker.smart_none', 'latitude') | default('') }}"
      lon: "{{ state_attr('device_tracker.smart_none', 'longitude') | default('') }}"
      elevation: >-
        {{ state_attr('device_tracker.smart_none', 'altitude').value |
        default('') }}
      is_charging: >
        {% if states('sensor.smart_charging_status') == 'charging' or
        states('sensor.smart_charging_status') == 'DC charging' %}
            1
        {% else %}
            0
        {% endif %}
      is_dcfc: |
        {% if states('sensor.smart_charging_status') == 'DC charging' %}
            1
        {% else %}
            0
        {% endif %}
      is_parked: "{{ states('binary_sensor.smart_electric_park_brake_status') | default(0) }}"
      ext_temp: >-
        {{ states('sensor.smart_exterior_temperature', rounded=False,
        with_unit=False) | default('') }}
      odometer: >-
        {{ states('sensor.smart_odometer', rounded=False, with_unit=False) |
        default('') }}
      est_battery_range: >-
        {{ states('sensor.smart_range', rounded=False, with_unit=False) |
        default('') }}
mode: single
```

And this to your `configuration.yaml` to create the `rest_command`.

```yaml
rest_command:
  abrp:
    url: https://api.iternio.com/1/tlm/send
    method: post
    headers:
      Authorization: "APIKEY {{ api_key }}"
    payload: {"data":[{"token":"{{ token }}",{"tlm":{"utc":{{utc}},"soc":{{soc}},"soh":{{soh}},"power":{{power}},"speed":{{speed}},"lat":{{lat}},"lon":{{lon}},"is_charging":{{is_charging}},"is_dcfc":{{is_dcfc}},"is_parked":{{is_parked}},"elevation":{{elevation}},"ext_temp":{{ext_temp}},"odometer":{{odometer}},"est_battery_range":{{est_battery_range}}}]}
```

## Connect to EVCC

[EVCC](https://github.com/evcc-io/evcc) is an extensible EV Charge Controller and home energy management system.
```yaml
vehicles:
  - name: smart
    title: "Smart #1"
    type: homeassistant
    uri: http://homeassistant.local:8123
    token: "eyJ0e..."  # HA-Token
    
    sensors:
      soc: sensor.smart_batterie                    # MANDATORY: SoC in %
      range: sensor.smart_reichweite                # OPTIONAL: Range in km
      status: sensor.smart_ladezustand              # OPTIONAL: Charging state
      limitSoc: number.smart_ladeziel               # OPTIONAL: Charging limit in %
      odometer: sensor.smart_kilometerstand         # OPTIONAL: Odometer in km
      climater: climate.smart_vorklimatisierung_aktiv # OPTIONAL: Aircon
      finishTime: sensor.smart_verbleibende_ladezeit  # OPTIONAL: Chraing time remaining
    
    capacity: 62  # Capacity of the battery in kWh
```
The sensor finishTime should be a point in time, but it seems the time span of the sensor works as well.

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
