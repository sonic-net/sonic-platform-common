'''
Test SfpBase LED-related methods
'''

import pytest
from unittest import mock

from sonic_platform_base.sfp_base import SfpBase
from sonic_platform_base.led_base import LedBase

def _make_led(name='led0'):
    led = mock.MagicMock(spec=LedBase)
    led.get_name.return_value = name
    return led

class TestSfpBaseLeds:
    '''
    Coverage for the LED accessors added by the platform LED policy V2 patch.
    '''

    @staticmethod
    def test_led_list_initialized_empty():
        '''
        SfpBase.__init__ must initialize self._led_list to an empty list so
        that platforms inheriting the default get_num_leds() / get_led()
        behavior do not blow up before they populate it.
        '''
        sfp = SfpBase()
        assert sfp._led_list == []
        assert sfp.get_num_leds() == 0

    @staticmethod
    def test_leds_with_populated_list():
        '''
        Returns the correct count and get_led(index) returns the matching LED
        '''
        sfp = SfpBase()
        leds = [_make_led('a'), _make_led('b'), _make_led('c')]
        sfp._led_list = leds

        assert sfp.get_num_leds() == 3
        assert sfp.get_led(0) is leds[0]
        assert sfp.get_led(1) is leds[1]
        assert sfp.get_led(2) is leds[2]

    @staticmethod
    def test_get_all_leds_raises_by_default():
        '''
        get_all_leds() raises NotImplementedError on the base class. This is
        the platform's opt-in to LED policy V2
        '''
        sfp = SfpBase()
        with pytest.raises(NotImplementedError):
            sfp.get_all_leds()

    @staticmethod
    def test_get_led_out_of_range_returns_none(capsys):
        '''
        Out-of-range indexes return None and write a diagnostic to stderr
        (matching the get_thermal() pattern).
        '''
        sfp = SfpBase()
        sfp._led_list = [_make_led('a')]

        assert sfp.get_led(5) is None
        captured = capsys.readouterr()
        assert 'LED index 5 out of range' in captured.err

    @staticmethod
    def test_get_led_empty_list_returns_none(capsys):
        '''
        With no LEDs registered, any index is out of range.
        '''
        sfp = SfpBase()

        assert sfp.get_led(0) is None
        captured = capsys.readouterr()
        assert 'LED index 0 out of range' in captured.err
