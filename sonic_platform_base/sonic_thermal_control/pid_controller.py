"""
    pid_controller.py

    Positional-form PID controller for platform thermal control:

        output = setpoint_output + Kp*e + Ki*integral(e dt) + Kd*de/dt

    Depends on nothing outside the standard library, so a platform can use it whether or
    not it drives fans through ThermalPolicy/ThermalManagerBase.

    Several platforms instead implement the incremental (velocity) form, which
    accumulates a change in output. Gains are not portable between the two forms.
"""

import logging


class PIDController(object):
    """Positional-form PID controller with output clamping and anti-windup."""

    # Thermal daemons do not guarantee a fixed period, so a measured dt outside these
    # multiples of the nominal interval is treated as implausible and clamped.
    MIN_DT_FACTOR = 0.25
    MAX_DT_FACTOR = 3.0

    def __init__(self, kp, ki, kd, output_min, output_max, interval,
                 setpoint_output=None, name='', logger=None):
        """
        Args:
            kp, ki, kd: Gains, in output units per error unit, per error-unit-second and
                per error-unit-per-second. Any may be zero, but not all.
            output_min, output_max: Output clamps.
            interval: Nominal seconds between compute() calls; used as the default dt.
            setpoint_output: Output held at zero error, in output units. Defaults to the
                midpoint of the output range.
            name: Label used in log messages.
            logger: Defaults to a module logger.

        Raises:
            ValueError: On a negative gain, all-zero gains, an inverted output range or
                a non-positive interval.
        """
        self._name = name or 'PIDController'
        for gain_name, gain in (('kp', kp), ('ki', ki), ('kd', kd)):
            if gain < 0:
                raise ValueError('{}: {}={} is negative, which inverts the feedback '
                                 'sign'.format(self._name, gain_name, gain))
        if not (kp or ki or kd):
            raise ValueError('{}: all gains are zero'.format(self._name))
        if output_min > output_max:
            raise ValueError('{}: output_min={} exceeds output_max={}'.format(
                self._name, output_min, output_max))
        if interval <= 0:
            raise ValueError('{}: interval={} must be positive'.format(
                self._name, interval))

        self._kp = float(kp)
        self._ki = float(ki)
        self._kd = float(kd)
        self._output_min = float(output_min)
        self._output_max = float(output_max)
        self._interval = float(interval)
        self._logger = logger if logger is not None else logging.getLogger(__name__)
        self._setpoint_output = float(
            (self._output_min + self._output_max) / 2
            if setpoint_output is None else setpoint_output)

        self._integral = 0.0
        self._prev_error = 0.0
        self._have_prev_error = False

    def reset(self, current_output=None):
        """
        Discard accumulated state, for when the loop resumes after a gap long enough
        that the previous samples are meaningless.

        Args:
            current_output: Output currently in effect. When given, the integral is
                back-calculated so the next output starts from it rather than jumping.
        """
        self._have_prev_error = False
        self._prev_error = 0.0
        if current_output is None:
            self._integral = 0.0
        else:
            self._integral = ((float(current_output) - self._setpoint_output) / self._ki
                              if self._ki else 0.0)
            self._clamp_integral()

    def compute(self, error, dt=None):
        """
        Advance the controller by one step and return the new clamped output.

        Args:
            error: Current error, normally (temperature - setpoint) so that a positive
                error raises the output.
            dt: Seconds since the previous call, defaulting to the nominal interval.
                Pass the measured elapsed time when the loop period is not guaranteed,
                since the integral scales with dt and the derivative divides by it.
        """
        dt, stale = self._resolve_dt(dt)

        if self._have_prev_error and not stale and self._kd:
            derivative = (error - self._prev_error) / dt
        else:
            # No usable previous sample, so a cold start or resumed loop cannot kick.
            derivative = 0.0

        candidate_integral = self._integral + error * dt
        output = (self._setpoint_output
                  + self._kp * error
                  + self._ki * candidate_integral
                  + self._kd * derivative)
        clamped = min(max(output, self._output_min), self._output_max)

        # Conditional integration: never accumulate further into a limit already hit.
        winding_up = ((output > self._output_max and error > 0) or
                      (output < self._output_min and error < 0))
        if not winding_up:
            self._integral = candidate_integral
            self._clamp_integral()

        self._prev_error = error
        self._have_prev_error = True

        self._logger.debug(
            '%s: e=%.3f dt=%.3fs P=%.3f I=%.3f D=%.3f -> %.3f%s',
            self._name, error, dt, self._kp * error, self._ki * self._integral,
            self._kd * derivative, clamped,
            ' (clamped)' if clamped != output else '')

        return clamped

    def _resolve_dt(self, dt):
        """Return (dt_to_use, stale), bounding an implausible measured dt."""
        if dt is None:
            return self._interval, False
        if dt <= 0:
            return self._interval, True
        lower = self._interval * self.MIN_DT_FACTOR
        upper = self._interval * self.MAX_DT_FACTOR
        return min(max(dt, lower), upper), dt > upper

    def _clamp_integral(self):
        if not self._ki:
            self._integral = 0.0
            return
        low = (self._output_min - self._setpoint_output) / self._ki
        high = (self._output_max - self._setpoint_output) / self._ki
        self._integral = min(max(self._integral, low), high)
