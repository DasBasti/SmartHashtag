# Smart #1, #3 and #5 Integration

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)
[![CodeQL Validation][codeql-shield]][codeql]
[![Dependency Validation][tests-shield]][tests]

## Installation

### Using HACS (Recommended)

1. Search for and install "Smart #1/#3/#5 Integration" in HACS.
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

## Preconditioning, Seat Heating and Defrost

All climate commands are sent to the car through the Smart cloud. The car takes a while to report a new state. The heating and defrost switches therefore show the requested state for up to two minutes, and the integration polls faster until the car confirms it.

### Entities

| Entity                                           | Type    | What it does                                                                |
| ------------------------------------------------ | ------- | --------------------------------------------------------------------------- |
| `climate.smart_<vin>_conditioning`               | Climate | Starts / stops preconditioning (air conditioning to the target temperature) |
| `select.smart_<vin>_conditioning_driver_seat`    | Select  | Heating level `Off` / `Low` / `Mid` / `High` for the driver seat            |
| `select.smart_<vin>_conditioning_passenger_seat` | Select  | Heating level for the passenger seat                                        |
| `select.smart_<vin>_conditioning_steering_wheel` | Select  | Heating level for the steering wheel                                        |
| Seat heating                                     | Switch  | Turns on the front seat heating without preconditioning                     |
| Steering wheel heating                           | Switch  | Turns on the steering wheel heating without preconditioning                 |
| Front defrost                                    | Switch  | Starts / stops the front windscreen defrost                                 |

### Preconditioning

Turning on the climate entity (HVAC mode `heat_cool`) starts preconditioning at the target temperature. The default target temperature is set in the integration options ("Target temperature preconditioning"). Changing the temperature on the climate entity applies to the next start.

Preconditioning also turns on the seat and steering wheel heating at the levels chosen in the heating selects. Locations set to `Off` are not heated. Turning the climate entity off stops preconditioning.

### Heating Levels (Selects)

The selects only store the heating level. Changing a select does **not** send anything to the car. The stored level is used the next time preconditioning or one of the heating switches is turned on, and is kept across restarts.

### Seat and Steering Wheel Heating Switches

The switches turn on heating **without** starting the air conditioning:

- **Seat heating** heats the driver and passenger seat at the levels from their selects. A seat whose select is `Off` is skipped. If both are `Off`, both seats are heated at `High`.
- **Steering wheel heating** heats the steering wheel at the level from its select, or at `High` if the select is `Off`.

Turning a switch off stops the heating for its locations. The switch state follows the heating status the car reports; the seat heating switch is on while either front seat is heating.

> [!NOTE]
> Smart #5: the cloud accepts the seat heating command, but the car does not heat the seats yet. Steering wheel heating works. See [#478](https://github.com/DasBasti/SmartHashtag/issues/478).

### Front Defrost

The front defrost switch starts the windscreen defrost and stops it when turned off. Its state follows the "Defrosting active" status reported by the car.

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
conditions:
  - condition: template
    value_template: "{{ states('sensor.smart_last_update') not in ['unavailable', 'unknown'] }}"
actions:
  - action: rest_command.abrp
    data:
      token: 99999999-aaaa-aaaa-bbbb-eeeeeeeeee # generated for each car in ABRP app
      api_key: 8888888-2222-44444-bbbb-333333333 # obtained from contact@iternio.com , see https://documenter.getpostman.com/view/7396339/SWTK5a8w
      utc: >-
        {{ as_timestamp(states('sensor.smart_last_update')) | int }}
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
      lat: >-
        {{ state_attr('device_tracker.smart_none', 'latitude') |
        default('null') }}
      lon: >-
        {{ state_attr('device_tracker.smart_none', 'longitude') |
        default('null') }}
      elevation: >-
        {{ state_attr('device_tracker.smart_none', 'altitude').value |
        default('null') }}
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
      is_parked: |
        {% if states('binary_sensor.smart_electric_park_brake_status') == 'off' %}
            1
        {% else %}
            0
        {% endif %}
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
  abrp: # As documented in https://documenter.getpostman.com/view/7396339/SWTK5a8w#fdb20525-51da-4195-8138-54deabe907d5
    url: https://api.iternio.com/1/tlm/send?token={{ token }}&tlm={"utc":{{ utc }},"soc":{{ soc }},"soh":{{ soh }},"power":{{ power }},"lat":{{ lat }},"lon":{{ lon }},"is_charging":{{ is_charging }},"is_dcfc":{{ is_dcfc }},"is_parked":{{ is_parked }},"elevation":{{ elevation }},"ext_temp":{{ ext_temp }},"odometer":{{ odometer }},"est_battery_range":{{ est_battery_range }}}
    method: post
    headers:
      Authorization: "APIKEY {{ api_key }}"
```

## Connect to EVCC

[EVCC](https://github.com/evcc-io/evcc) is an extensible EV Charge Controller and home energy management system.

```yaml
vehicles:
  - name: smart
    title: "Smart #1"
    type: homeassistant
    uri: http://homeassistant.local:8123
    token: "eyJ0e..." # HA-Token

    sensors:
      soc: sensor.smart_batterie # MANDATORY: SoC in %
      range: sensor.smart_reichweite # OPTIONAL: Range in km
      status: sensor.smart_ladezustand # OPTIONAL: Charging state
      limitSoc: number.smart_ladeziel # OPTIONAL: Charging limit in %
      odometer: sensor.smart_kilometerstand # OPTIONAL: Odometer in km
      climater: climate.smart_vorklimatisierung_aktiv # OPTIONAL: Aircon
      finishTime: sensor.smart_verbleibende_ladezeit # OPTIONAL: Chraing time remaining

    capacity: 62 # Capacity of the battery in kWh
```

The sensor finishTime should be a point in time, but it seems the time span of the sensor works as well.

## Create Debug Logs

To create logs for debugging, add this to your `configuration.yaml` file

```
logger:
  default: error
  logs:
    custom_components.smarthashtag: debug
    pysmarthashtag: debug
```

## Install a Test Version in HACS

You can use the yaml input of the developer tools to install a specific version/branch/commit using the development tools-

```
action: update.install
data:
  version: 552b43c
target:
  entity_id: update.smart_1_3_integration_update
```

## AI-Assisted Development

This project uses AI tools to assist with development, including GitHub Copilot for code suggestions and commit message generation.

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
