"""Unit tests for sonic_platform_base.sonic_thermal_control.pid_controller."""

import pytest

from sonic_platform_base.sonic_thermal_control.pid_controller import PIDController


def make_controller(**kwargs):
    """A proportional-only controller over 0-100 with a 50 operating point."""
    params = dict(kp=2.0, ki=0.0, kd=0.0, output_min=0.0, output_max=100.0,
                  interval=5.0, setpoint_output=50.0)
    params.update(kwargs)
    return PIDController(**params)


@pytest.mark.parametrize("bad", [{'kp': -1.0}, {'ki': -0.1}, {'kd': -0.5}])
def test_rejects_negative_gain(bad):
    # Given a set of gains where one is negative
    # When a controller is built with it
    # Then it is rejected
    with pytest.raises(ValueError):
        make_controller(**bad)


def test_rejects_all_zero_gains():
    # Given gains that are all zero
    # When a controller is built with them
    # Then it is rejected
    with pytest.raises(ValueError):
        make_controller(kp=0.0, ki=0.0, kd=0.0)


def test_rejects_inverted_output_range():
    # Given an output range whose minimum is above its maximum
    # When a controller is built with it
    # Then it is rejected
    with pytest.raises(ValueError):
        make_controller(output_min=90.0, output_max=10.0)


def test_rejects_non_positive_interval():
    # Given a zero control interval
    # When a controller is built with it
    # Then it is rejected
    with pytest.raises(ValueError):
        make_controller(interval=0.0)


def test_zero_integral_gain_is_supported():
    """Ki=0 must not raise; a P-only controller is a legitimate configuration."""
    # Given a controller with no integral gain
    controller = make_controller(ki=0.0)

    # When it is fed no error and then a positive error
    at_zero = controller.compute(0.0)
    at_ten = controller.compute(10.0)

    # Then it behaves as a plain proportional controller
    assert at_zero == 50.0
    assert at_ten == 70.0


def test_zero_error_holds_the_operating_point():
    # Given a proportional-only controller
    controller = make_controller()

    # When there is no error
    output = controller.compute(0.0)

    # Then it outputs its operating point
    assert output == 50.0


def test_output_follows_error_sign():
    # Given two fresh proportional-only controllers
    # When one sees a positive error and the other a negative one
    above = make_controller().compute(10.0)
    below = make_controller().compute(-10.0)

    # Then the output moves above and below the operating point accordingly
    assert above == 70.0
    assert below == 30.0


def test_output_is_clamped():
    # Given two fresh controllers over 0-100
    # When each sees a huge positive or negative error
    high = make_controller().compute(1000.0)
    low = make_controller().compute(-1000.0)

    # Then the output is held at the range limits
    assert high == 100.0
    assert low == 0.0


def test_integral_accumulates_with_dt():
    # Given a PI controller starting from zero output
    controller = make_controller(kp=1.0, ki=0.5, setpoint_output=0.0, output_min=0.0)

    # When the same error persists over two 2s steps
    first = controller.compute(10.0, dt=2.0)
    second = controller.compute(10.0, dt=2.0)

    # Then the integral term grows by error * dt on each step
    assert first == 20.0     # 1*10 + 0.5*(10*2)
    assert second == 30.0    # 1*10 + 0.5*(20+20)


def test_dt_defaults_to_nominal_interval():
    # Given an integral-only controller with a 4s interval
    controller = make_controller(kp=0.0, ki=1.0, setpoint_output=0.0, interval=4.0)

    # When it is called without a dt
    output = controller.compute(2.0)

    # Then the step is taken to be the nominal interval
    assert output == 8.0                 # 2 * 4s


def test_integral_freezes_while_saturated_then_unwinds():
    # Given a PI controller with a low output ceiling
    controller = make_controller(kp=1.0, ki=1.0, kd=0.0, output_min=0.0,
                                 output_max=10.0, interval=1.0, setpoint_output=0.0)

    # When it is driven into the ceiling
    # Then the output saturates
    assert controller.compute(5.0, dt=1.0) == 10.0
    frozen = controller._integral

    # When it stays against the ceiling
    # Then the integral does not keep growing
    assert controller.compute(5.0, dt=1.0) == 10.0
    assert controller._integral == frozen

    # When the error turns negative
    # Then the integral unwinds promptly rather than after a long delay
    assert controller.compute(-2.0, dt=1.0) == 1.0
    assert controller._integral < frozen


def test_derivative_suppressed_on_first_call():
    """A cold start has no previous sample, so it must not produce a derivative kick."""
    # Given a derivative-only controller with no previous sample
    controller = make_controller(kp=0.0, ki=0.0, kd=10.0, interval=1.0)

    # When it sees its first error
    output = controller.compute(7.0, dt=1.0)

    # Then it stays at the operating point
    assert output == 50.0


def test_derivative_responds_to_change():
    # Given a derivative-only controller that has seen a zero error
    controller = make_controller(kp=0.0, ki=0.0, kd=10.0, interval=1.0)
    controller.compute(0.0, dt=1.0)

    # When the error rises
    output = controller.compute(3.0, dt=1.0)

    # Then the output moves by the rate of change
    assert output == 80.0                # 10 * (3 / 1s)


def test_implausibly_large_dt_is_clamped_and_suppresses_derivative():
    # Given an integral and derivative controller that has taken one normal step
    controller = make_controller(kp=0.0, ki=1.0, kd=10.0, setpoint_output=0.0,
                                 output_min=-1000.0, output_max=1000.0, interval=5.0)
    controller.compute(1.0, dt=5.0)
    before = controller._integral

    # When the next sample arrives after a 600s gap
    controller.compute(1.0, dt=600.0)

    # Then the integral advances by the clamped bound (3 * 5s), and the stale sample does
    # not generate a derivative term
    assert controller._integral == pytest.approx(before + 15.0)


def test_implausibly_small_dt_is_clamped():
    # Given a derivative-only controller that has seen a zero error
    controller = make_controller(kp=0.0, ki=0.0, kd=10.0, interval=5.0)
    controller.compute(0.0, dt=5.0)

    # When the next sample arrives after only 0.01s
    output = controller.compute(3.0, dt=0.01)

    # Then dt is floored at 0.25 * 5s, so D = 10 * (3 / 1.25s), not 10 * (3 / 0.01s)
    assert output == pytest.approx(74.0)


def test_non_positive_dt_falls_back_to_interval():
    # Given an integral-only controller with a 5s interval
    controller = make_controller(kp=0.0, ki=1.0, setpoint_output=0.0, interval=5.0)

    # When it is given a zero and then a negative dt
    with_zero = controller.compute(2.0, dt=0.0)
    with_negative = controller.compute(2.0, dt=-3.0)

    # Then each step uses the nominal interval instead
    assert with_zero == 10.0
    assert with_negative == 20.0


def test_reset_with_current_output_is_bumpless():
    # Given a PI controller that has accumulated some integral
    controller = make_controller(kp=1.0, ki=0.5)
    controller.compute(20.0)

    # When it is reset to the current fan output
    controller.reset(current_output=80.0)
    output = controller.compute(0.0)

    # Then it carries on from that output without a jump
    assert output == pytest.approx(80.0)


def test_reset_without_output_clears_integral():
    # Given a PI controller that has accumulated some integral
    controller = make_controller(kp=1.0, ki=0.5)
    controller.compute(20.0)

    # When it is reset without an output
    controller.reset()
    output = controller.compute(0.0)

    # Then it returns to its operating point
    assert output == 50.0
