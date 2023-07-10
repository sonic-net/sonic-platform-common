'''
Test FanBase module
'''

from unittest import mock
from sonic_platform_base.fan_base import FanBase

class TestFanBase:
    '''
    Collection of FanBase test methods
    '''

    @staticmethod
    def test_is_under_speed():
        '''
        Test fan.is_under_speed default implementation
        '''
        fan = FanBase()
        fan.get_speed = mock.MagicMock(return_value=100)
        fan.get_target_speed = mock.MagicMock(return_value=50)
        fan.get_speed_tolerance = mock.MagicMock(return_value=10)

        for func in (fan.get_speed, fan.get_target_speed, fan.get_speed_tolerance):
            return_val = func()

            # Check type and bounds errors
            for value, exc_type in ((None, TypeError), (-1, ValueError), (101, ValueError)):
                func.return_value = value
                expected_exception = False
                try:
                    fan.is_under_speed()
                except Exception as exc:
                    expected_exception = isinstance(exc, exc_type)
                assert expected_exception

            # Reset function return value
            func.return_value = return_val

        # speed=100, minimum tolerated speed=45, not under speed
        assert not fan.is_under_speed()

        # speed=46, minimum tolerated speed=45, not under speed
        fan.get_speed.return_value = 46
        assert not fan.is_under_speed()

        # speed=45, minimum tolerated speed=45, not under speed
        fan.get_speed.return_value = 45
        assert not fan.is_under_speed()

        # speed=44, minimum tolerated speed=45, under speed
        fan.get_speed.return_value = 44
        assert fan.is_under_speed()

        # speed=44, minimum tolerated speed=40, not under speed
        fan.get_speed_tolerance.return_value = 20
        assert not fan.is_under_speed()

        # speed=41, minimum tolerated speed=40, not under speed
        fan.get_speed.return_value = 41
        assert not fan.is_under_speed()

        # speed=40, minimum tolerated speed=40, not under speed
        fan.get_speed.return_value = 40
        assert not fan.is_under_speed()

        # speed=39, minimum tolerated speed=40, under speed
        fan.get_speed.return_value = 39
        assert fan.is_under_speed()

        # speed=1, minimum tolerated speed=40, under speed
        fan.get_speed.return_value = 1
        assert fan.is_under_speed()

    @staticmethod
    def test_is_over_speed():
        '''
        test fan.is_over_speed default implementation
        '''
        fan = FanBase()
        fan.get_speed = mock.MagicMock(return_value=1)
        fan.get_target_speed = mock.MagicMock(return_value=50)
        fan.get_speed_tolerance = mock.MagicMock(return_value=10)

        for func in (fan.get_speed, fan.get_target_speed, fan.get_speed_tolerance):
            return_val = func()

            # Check type and bounds errors
            for value, exc_type in ((None, TypeError), (-1, ValueError), (101, ValueError)):
                func.return_value = value
                expected_exception = False
                try:
                    fan.is_under_speed()
                except Exception as exc:
                    expected_exception = isinstance(exc, exc_type)
                assert expected_exception

            # Reset function return value
            func.return_value = return_val

        # speed=1, maximum tolerated speed=55, not over speed
        assert not fan.is_over_speed()

        # speed=54, maximum tolerated speed=55, not over speed
        fan.get_speed.return_value = 54
        assert not fan.is_over_speed()

        # speed=55, maximum tolerated speed=55, not over speed
        fan.get_speed.return_value = 55
        assert not fan.is_over_speed()

        # speed=56, maximum tolerated speed=55, over speed
        fan.get_speed.return_value = 56
        assert fan.is_over_speed()

        # speed=56, maximum tolerated speed=60, not over speed
        fan.get_speed_tolerance.return_value = 20
        assert not fan.is_over_speed()

        # speed=59, maximum tolerated speed=60, not over speed
        fan.get_speed.return_value = 59
        assert not fan.is_over_speed()

        # speed=60, maximum tolerated speed=60, not over speed
        fan.get_speed.return_value = 60
        assert not fan.is_over_speed()

        # speed=61, maximum tolerated speed=60, over speed
        fan.get_speed.return_value = 61
        assert fan.is_over_speed()

        # speed=100, maximum tolerated speed=60, over speed
        fan.get_speed.return_value = 100
        assert fan.is_over_speed()

    @staticmethod
    def test_fan_base():
        '''
        Verify unimplemented methods
        '''
        fan = FanBase()
        not_implemented_methods = [
            (fan.get_direction,),
            (fan.get_speed,),
            (fan.get_target_speed,),
            (fan.get_speed_tolerance,),
            (fan.set_speed, 50),
            (fan.set_status_led, 'green'),
            (fan.get_status_led,)]

        for method in not_implemented_methods:
            expected_exception = False
            try:
                func = method[0]
                args = method[1:]
                func(*args)
            except Exception as exc:
                expected_exception = isinstance(exc, NotImplementedError)
            assert expected_exception
