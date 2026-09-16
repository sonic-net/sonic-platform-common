#
# SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
# Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""The bodies the generator cannot derive.

Hand-written, and deliberately small: everything here is declared in
`facade.pyi` as an `EscapeHatch` with a reason, so a body that appears without
a matching declaration is a body somebody should have generated.
"""

from typing import Any, Optional


def _call(fn: Any, default: Any = None) -> Any:
    """The same not-implemented handling the generated facade uses.

    Duplicated rather than imported: facade.py imports this module, so taking
    it the other way would be a cycle, and a five-line helper is a smaller
    price than a deferred import in every method here.
    """
    if fn is None:
        return default
    try:
        r = fn()
    except NotImplementedError:
        return default
    if r is None or r is NotImplementedError:
        return default
    return r

# Where a platform's thermal policy lives.  thermalctld:1435 spells the same
# path; it is a platform artefact rather than daemon configuration, which is
# why the facade owns it once instead of each daemon passing it in.
POLICY_FILE: str = '/usr/share/sonic/platform/thermal_policy.json'


# Where a platform declares the sensors it exposes through sysfs rather than
# through a driver object.  sensormond:516 reads the same file.
SENSORS_YAML = 'sensors.yaml'

# The seven status strings ChassisBase.get_change_event documents, named.  A
# value not in here is passed through as-is: vendors are not limited to these,
# and a facade that dropped an eighth would hide the one event somebody needed.
CHANGE_EVENT_KINDS = {
    '0': 'removed',
    '1': 'inserted',
    '2': 'i2c_stuck',
    '3': 'bad_eeprom',
    '4': 'unsupported_cable',
    '5': 'high_temperature',
    '6': 'bad_cable',
}


class EscapeHatches(object):
    """Thermal manager lifecycle, flattened to four argument-less calls.

    `ChassisBase.get_thermal_manager()` returns a *class*, not an instance,
    and all twelve of its methods are `@classmethod` over process-global
    state.  Two of them -- `init_thermal_algorithm` and `run_policy` -- take
    the chassis back as an argument, and the Python policy engine then calls
    back through it into the platform API.

    Holding the chassis here is what keeps that entirely inside Python.  The
    Rust side sees four calls that take nothing and return nothing, so the
    bridge never re-enters Python from Rust from Python, and the thermal
    policy plugin ecosystem stays where it is.
    """

    def __init__(self, chassis: Any) -> None:
        self._chassis = chassis
        self._manager: Any = None
        self._loaded = False
        self._sensors_data: Any = None

    def _get(self) -> Any:
        """The thermal manager class, or None on a platform without one.

        Three ways to not have one, and a platform uses all three: the chassis
        has no such method, the method raises, or it hands back None.
        """
        if self._manager is None:
            fn = getattr(self._chassis, 'get_thermal_manager', None)
            if fn is None:
                return None
            try:
                self._manager = fn()
            except NotImplementedError:
                return None
        return self._manager

    def tm_initialize(self) -> None:
        """Start-up, in the order thermalctld:1477-1482 does it.

        `load()` and `init_thermal_algorithm()` belong with `initialize()`:
        a manager that has been initialised but not loaded has no policies,
        and `run_policy` on it is a no-op that looks like a working one.
        """
        mgr = self._get()
        if mgr is None:
            return
        mgr.initialize()
        mgr.load(POLICY_FILE)
        mgr.init_thermal_algorithm(self._chassis)
        self._loaded = True

    def tm_run_policy(self) -> None:
        """One policy round.

        Skipped rather than raised when nothing was loaded: a platform whose
        fan policy lives in firmware ships a `thermal_policy.json` with no
        policies in it, and that is not an error.
        """
        mgr = self._get()
        if mgr is None or not self._loaded:
            return
        mgr.run_policy(self._chassis)

    def tm_get_interval(self) -> Optional[float]:
        """How often `tm_run_policy` should run, in seconds.

        None when the platform has no manager -- the caller then keeps its own
        polling interval rather than adopting one that does not exist.
        """
        mgr = self._get()
        if mgr is None:
            return None
        try:
            interval = mgr.get_interval()
        except NotImplementedError:
            return None
        # ThermalManagerBase declares this as int; vendors return float. The
        # facade publishes seconds, so it is a float either way.
        return None if interval is None else float(interval)

    def tm_deinitialize(self) -> None:
        """Shutdown.  `stop()` then `deinitialize()`, as thermalctld does at
        :1526 and :1506 respectively."""
        mgr = self._get()
        if mgr is None:
            return
        try:
            mgr.stop()
        except NotImplementedError:
            pass
        mgr.deinitialize()
        self._loaded = False

    # -- sensors.yaml -------------------------------------------------------
    #
    # `SensorFs.factory(sensor_cls, data)` takes a *class* as its first
    # argument, which no declaration can express.  What it produces is an
    # ordinary list of sensor objects, so the stub declares these as flatten
    # sources with a `provider=` and the rows come out with the same columns,
    # in the same order, as every other sensor.

    def _sensors_yaml(self) -> Any:
        """The platform's sensors.yaml, or None.

        Read once. A platform without the file is the common case, not an
        error -- sensormond:512-526 swallows every failure here for exactly
        that reason, and a facade that shouted instead would shout on most
        platforms.
        """
        if self._sensors_data is not None:
            return self._sensors_data
        self._sensors_data = {}
        try:
            import os

            import yaml
            from sonic_py_common import device_info

            platform_path, _hwsku = device_info.get_paths_to_platform_and_hwsku_dirs()
            with open(os.path.join(platform_path, SENSORS_YAML)) as f:
                self._sensors_data = yaml.safe_load(f) or {}
        except Exception:
            pass
        return self._sensors_data

    def _sensors_fs(self, key: str, cls_name: str) -> Any:
        data = self._sensors_yaml().get(key)
        if not data:
            return []
        try:
            from sonic_platform_base import sensor_fs

            cls = getattr(sensor_fs, cls_name)
            # The class is passed to its own factory; that is the signature.
            return cls.factory(cls, data)
        except Exception:
            return []

    def voltage_sensors_from_yaml(self) -> Any:
        return self._sensors_fs('voltage_sensors', 'VoltageSensorFs')

    def current_sensors_from_yaml(self) -> Any:
        return self._sensors_fs('current_sensors', 'CurrentSensorFs')

    # -- change events ------------------------------------------------------

    def get_change_event(self, timeout_ms: int) -> Any:
        """Flatten what `ChassisBase.get_change_event` answered.

        `{'fan': {'0': '0'}, 'sfp': {'11': '0'}}` becomes two rows.  The outer
        key is the device type and the inner key is the device id; the nesting
        carries nothing a row cannot.

        `ok` is carried rather than raised on.  It reads like a success flag
        and is not one -- `ok=False` is how a platform reports a system-level
        event, with the detail under the key the daemon watches for.
        """
        # Imported here rather than at module scope: facade.py imports this
        # module, so naming it at the top would be a cycle.
        from .facade import ChangeEvent, ChangeEventBatch

        fn = getattr(self._chassis, 'get_change_event', None)
        if fn is None:
            raise NotImplementedError('ChassisBase.get_change_event is not implemented')
        answer = fn(timeout_ms)
        try:
            ok, mapping = answer
        except (TypeError, ValueError):
            raise NotImplementedError(
                'ChassisBase.get_change_event did not answer (bool, dict)')

        events = []
        if not hasattr(mapping, 'items'):
            mapping = {}
        for device_type, changes in mapping.items():
            if not hasattr(changes, 'items'):
                # A platform that answered something other than a mapping of
                # device id to status.  Skipped rather than raised: this runs
                # in a polling loop, and one malformed device type should not
                # take the others with it.
                continue
            for device_id, status in changes.items():
                status = str(status)
                events.append(ChangeEvent(
                    device_type=str(device_type),
                    device_id=str(device_id),
                    status=status,
                    kind=CHANGE_EVENT_KINDS.get(status),
                ))
        return ChangeEventBatch(ok=bool(ok), events=events)

    # -- asics --------------------------------------------------------------

    def get_asics(self) -> Any:
        """`ModuleBase.get_all_asics()` answers `[(asic_id, pci_address), ...]`.

        A list of tuples, not of device objects, so a flatten plan has nothing
        to call a getter on.  Short entries read as a missing address rather
        than raising: this runs every cycle.
        """
        from .facade import AsicInfo

        rows = []
        modules = _call(getattr(self._chassis, 'get_all_modules', None)) or ()
        for index, module in enumerate(modules):
            name = _call(getattr(module, 'get_name', None)) or 'Module %d' % (index + 1)
            for entry in _call(getattr(module, 'get_all_asics', None)) or ():
                try:
                    asic_id = str(entry[0])
                except (TypeError, IndexError, KeyError):
                    continue
                try:
                    address = str(entry[1])
                except (TypeError, IndexError, KeyError):
                    address = None
                rows.append(AsicInfo(
                    parent_name=name, asic_id=asic_id, pci_address=address))
        return rows

    # -- bmc commands -------------------------------------------------------

    def _bmc(self) -> Any:
        bmc = _call(getattr(self._chassis, 'get_bmc', None))
        if bmc is None:
            raise NotImplementedError('ChassisBase.get_bmc is not implemented')
        return bmc

    def _bmc_call(self, method: str, *args: Any) -> Any:
        """`(code, payload)` from one BMC command, or NotImplementedError."""
        fn = getattr(self._bmc(), method, None)
        if fn is None:
            raise NotImplementedError('BMCBase.%s is not implemented' % method)
        answer = fn(*args)
        try:
            code, payload = answer
        except (TypeError, ValueError):
            raise NotImplementedError(
                'BMCBase.%s did not answer (code, payload)' % method)
        return int(code), payload

    def _result(self, method: str, *args: Any) -> Any:
        from .facade import BmcResult

        code, payload = self._bmc_call(method, *args)
        return BmcResult(code=code, message=None if payload is None else str(payload))

    def bmc_open_session(self) -> Any:
        """`(code, (message, (session_id, token)))`.

        The credentials are absent on failure, and `config/bmc.py:41` checks
        for that before reading them -- so a row with the code set and the
        credentials None is the shape a caller already handles.
        """
        from .facade import BmcResult

        code, payload = self._bmc_call('open_session')
        message, credentials = None, None
        try:
            message, credentials = payload
        except (TypeError, ValueError):
            message = None if payload is None else str(payload)
        session_id = token = None
        if credentials:
            try:
                session_id, token = str(credentials[0]), str(credentials[1])
            except (TypeError, IndexError, KeyError):
                session_id = token = None
        return BmcResult(
            code=code,
            message=None if message is None else str(message),
            session_id=session_id,
            token=token,
        )

    def bmc_close_session(self, session_id: str) -> Any:
        return self._result('close_session', session_id)

    def bmc_reset_root_password(self) -> Any:
        return self._result('reset_root_password')

    def bmc_reset(self, graceful: bool) -> Any:
        return self._result('request_bmc_reset', graceful)

    def bmc_update_firmware(self, image_path: str) -> Any:
        """`(code, (message, list))`; the list is the components it touched."""
        from .facade import BmcResult

        code, payload = self._bmc_call('update_firmware', image_path)
        message = payload
        try:
            message, _components = payload
        except (TypeError, ValueError):
            pass
        return BmcResult(code=code, message=None if message is None else str(message))

    def bmc_trigger_debug_log_dump(self) -> Any:
        """`(code, (task_id, message))` -- task id first, unlike every other."""
        from .facade import BmcResult

        code, payload = self._bmc_call('trigger_bmc_debug_log_dump')
        task_id, message = None, None
        try:
            task_id, message = payload
        except (TypeError, ValueError):
            message = None if payload is None else str(payload)
        return BmcResult(
            code=code,
            message=None if message is None else str(message),
            task_id=None if task_id is None else str(task_id),
        )

    def bmc_get_debug_log_dump(self, task_id: str, filename: str, path: str) -> Any:
        return self._result('get_bmc_debug_log_dump', task_id, filename, path)
