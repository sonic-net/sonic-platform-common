'''
Test LedBase / LedColor module
'''

import pytest

from sonic_platform_base.led_base import LedBase, LedColor


class TestLedColor:
    '''
    Collection of LedColor tests
    '''

    @staticmethod
    def test_color_values():
        '''
        Each color maps to its expected string value.
        '''
        assert LedColor.OFF.value == 'off'
        assert LedColor.GREEN.value == 'green'
        assert LedColor.AMBER.value == 'amber'
        assert LedColor.RED.value == 'red'
        assert LedColor.BLUE.value == 'blue'

    @staticmethod
    def test_yellow_is_alias_of_amber():
        '''
        YELLOW shares AMBER's value, so Python's Enum makes it an alias:
        the two members are the same object.
        '''
        assert LedColor.YELLOW is LedColor.AMBER
        assert LedColor.YELLOW.value == 'amber'


class TestLedBase:
    '''
    Collection of LedBase tests
    '''

    @staticmethod
    def test_unimplemented_methods_raise():
        '''
        All abstract methods raise NotImplementedError by default.
        '''
        led = LedBase()
        not_implemented_methods = [
            (led.get_name,),
            (led.get_color_capabilities,),
            (led.set_color, LedColor.GREEN),
            (led.get_color,),
        ]

        for method in not_implemented_methods:
            func = method[0]
            args = method[1:]
            with pytest.raises(NotImplementedError):
                func(*args)

    @staticmethod
    def test_init_no_args():
        '''
        Default constructor takes no args and does not raise.
        '''
        # Should not raise
        LedBase()
