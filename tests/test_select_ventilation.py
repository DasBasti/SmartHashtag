"""Tests for the Smart #5 seat ventilation selects."""

from pysmarthashtag.control.climate import HeatingLocation, VentilationLocation

from custom_components.smarthashtag.select import VENTILATION_KEY_PREFIX


def test_ventilation_keys_do_not_clash_with_heating():
    """Ventilation is saved under its own prefix so it never overwrites heating."""
    for v in VentilationLocation:
        assert VENTILATION_KEY_PREFIX + v.value not in {h.value for h in HeatingLocation}


def test_rear_heating_keys_do_not_clash():
    """Rear seat heating is saved under keys distinct from front heating and ventilation."""
    from pysmarthashtag.control.climate import RearHeatingLocation

    taken = {h.value for h in HeatingLocation} | {VENTILATION_KEY_PREFIX + v.value for v in VentilationLocation}
    assert not {r.value for r in RearHeatingLocation} & taken
