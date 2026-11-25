# Example thermal policy and config

A platform that uses the common thermal policy types ships these two files in its device
directory (`/usr/share/sonic/platform` at runtime).

`thermal_policy.json` says what to do when. With two or fewer fan drawers present the fans run
at full speed. Otherwise a PID controller picks the speed, and its `max_speed` keeps it at or
below 75%. The two policies must not overlap, because every policy whose conditions match runs.

`thermal_config.json` holds the tuning. Fans stay between 30% and 100%. Sensors whose
`get_pid_domain()` is `asic` share one PID loop, and `board` sensors share another with gentler
gains. `board` sensors all target 70 C; `asic` sensors use the target from
`get_pid_setpoint()`. The group needing the most cooling sets the fan speed.

`tests/common_policy_load_test.py` loads both files, so they stay valid as the code changes.
