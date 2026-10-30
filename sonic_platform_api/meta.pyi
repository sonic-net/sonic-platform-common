"""The part of the facade a type alone cannot say.

`facade.pyi` declares what the cross-language platform API looks like.  A type
says a thermal row carries a temperature; it does not say which base-class
method that temperature is read from, in what order rows from four different
places are concatenated, or what a vendor returning the string 'N/A' should
become.  Those are declared here, as arguments to `Annotated[...]` on fields
and to `@platform_method(...)` on methods.

Declarations only: this module has no runtime counterpart and nothing imports
it.  The generator reads `facade.pyi` with `ast` from the standard library --
it never imports the stub and never needs a type checker to run.  The classes
exist so that `mypy --strict` type-checks the metadata itself, which is how a
misspelled base-class path or a malformed flatten plan gets caught.
"""

from dataclasses import dataclass
from typing import Callable, Literal, Optional, TypeVar, Union

# --------------------------------------------------------------------------
# Field-level
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class From:
    """The base-class method this field is read from.

    Written as `Class.method`, e.g. `From("ThermalBase.get_temperature")`.
    The generator emits the call into `facade.py` wrapped in the standard
    not-implemented handling, so a field never needs its own error path.

    `generate.py` holds the path to the base classes: the class, or one it
    derives from, has to define the method, and a call with no arguments has
    to suit its signature.  A path that does not resolve stops the generator.

    A path may name more than one getter: `"LeakageSensorBase.get_leak_profile
    .get_type"` calls each in turn, which is how a column that lives one
    object further down becomes a column here rather than a second row type.
    Any hop answering None makes the whole field absent.

    `at` picks one slot out of a tuple return.  Several base-class getters
    hand back a fixed-arity tuple -- `get_reboot_cause()` is `(cause, detail)`
    -- and the row carries them as separate columns, because a consumer that
    wanted them together would have to know the arity anyway.
    """

    path: str
    at: Optional[int] = ...

@dataclass(frozen=True)
class Parent:
    """This field carries the parent name the flatten plan resolved.

    The thermal that a PSU owns is published under that PSU's name, not the
    thermal's own; `parent_name` is how a consumer tells two identically named
    sensors apart.  There is no base-class call behind it.
    """

@dataclass(frozen=True)
class Key:
    """This field carries the row's `DeviceKey`, built by the traversal.

    Like `Parent()`, there is no base-class call behind it: the key is the
    path the facade walked to reach the device.  Declared as
    `key: Annotated[DeviceKey, Key()]` on every row an action addresses.
    """

@dataclass(frozen=True)
class ParentKey:
    """This field carries the `DeviceKey` of the device's parent.

    None when the parent is the chassis.  It is how a consumer acts on the
    parent of a device it holds -- thermalctld sets a fan's drawer LED -- with
    the same certainty as on the device itself.
    """

@dataclass(frozen=True)
class WithName:
    """This getter takes the device's own name, so the row must pass it.

    `ModuleBase.get_module_state_transition(self, module_name)`
    (`module_base.py:709`) has always required the name -- this is not a vendor
    narrowing, it is a getter the base class declares with an argument, and a
    `From` that names it reads as a zero-argument column unless this says
    otherwise.  Python passes it: `chassisd:1271` is
    `try_get(module.get_module_state_transition, module_name, default=False)`.

    Declared the plain way, the generated call raised
    `TypeError: get_module_state_transition() missing 1 required positional
    argument: 'module_name'`, which on a SmartSwitch NPU cost the whole
    `ModuleInfo` row: chassisd logged "Failed to read the modules" every cycle
    and published no `CHASSIS_MIDPLANE_TABLE` at all.  Measured on a SmartSwitch.

    The name comes from the same `get_name()` the row's `name` column uses, so
    the argument cannot disagree with the key the row is published under.
    """

@dataclass(frozen=True)
class Narrowed:
    """Vendors may narrow this getter's signature, so calling it can TypeError.

    `ChassisBase.get_dpu_id` is declared `get_dpu_id(self, **kwargs)`, which a
    zero-argument call satisfies.  Mellanox overrides it as
    `get_dpu_id(self, name)` (`chassis.py:1764`) -- a *required* positional --
    so on a SmartSwitch NPU the call raises
    `TypeError: get_dpu_id() missing 1 required positional argument: 'name'`.

    `generate.py`'s arity check does not catch this, and cannot: it reads the
    base class's signature, which accepts the call.

    Why it matters more than one column: the facade builds a row eagerly, so
    every field is read on every call.  Without this, one vendor's narrowed
    signature takes down the whole `ChassisInfo` row, and a caller that only
    wanted `is_smartswitch` gets nothing.  Measured on a SmartSwitch: the Rust
    chassisd read `None` for the row, concluded the platform was a fixed
    switch, and exited "not supported" on a SmartSwitch with four live DPUs.

    Python never hits it because it never makes the call on the NPU --
    `chassisd:1748` is inside `DpuStateUpdater`, which runs only on the DPU,
    where the BlueField `sonic_platform` does take no argument.  Declaring the
    quirk gives the same answer on both: absent on the NPU, the id on the DPU.

    A TypeError becomes an absent field, like `NotImplementedError`.  It is
    deliberately not a global rule in `_call`: everywhere else a TypeError is a
    generator bug, and swallowing those would hide them.
    """

@dataclass(frozen=True)
class Truthy:
    """This field is consumed in a boolean context, so normalise it like one.

    `LeakageSensorBase.is_leak` is declared `bool` and Mellanox returns
    `False`, `True`, or the string `'N/A'` when the sysfs read fails
    (`liquid_cooling.py:46-57`).  The Python daemon never compares it to
    anything -- `thermalctld:676` is a bare `if sensor_is_leak:` -- so `'N/A'`,
    a non-empty string, counts as **leaking**.  Reading the sysfs file is the
    only way to know, and a detector that cannot read its sensor must not
    report the tank is dry.

    Declaring it `Observed(sentinels=('N/A',))` would be the natural-looking
    choice and is wrong: that turns the sentinel into None, None is falsy, and
    a switch with a failed leak sensor reports `leaking=No` while `bmcctld`
    waits for a CRITICAL that never comes.  Measured on hardware: Python wrote
    `leaking=Yes` / `device_leak_status=CRITICAL`, the sentinel-to-None port
    wrote `No` / `None`.

    The rule: `None` stays absent -- Python's `if None:` is false too -- and
    anything else becomes `bool(value)`.  A real `bool` is unaffected.
    """

@dataclass(frozen=True)
class Observed:
    """The declared type, and what vendors actually return.

    The base class documents `float`.  Vendors return int, str, numpy scalars,
    and sentinels where there is no reading -- `'N/A'` appears in `pdb_base`,
    `sensor_fs` and `xcvr_api` at positions declared as numbers.

    The normalisation happens once, in the generated Python facade: by the time
    a row crosses into Rust the value is already a number or None.  What this
    declaration buys on the Rust side is the type -- `Option<f64>` rather than
    something looser -- and the guarantee that only one implementation of the
    rule exists to disagree with itself.

    `sentinels` become None.  `coerce_from` names the Python types worth
    attempting a conversion from before giving up.
    """

    sentinels: tuple[object, ...] = ...
    coerce_from: tuple[str, ...] = ...

@dataclass(frozen=True)
class RowError:
    """This column carries what went wrong reading the row's device.

    Only on a row whose snapshot is `Snapshot(per_row_errors=True)`: there a
    getter that raises costs that one row its readings, not the whole call.
    The row is still returned, in its place, with the columns that were not
    read at their absent value, and these three set from the first exception
    -- `error: Annotated[Optional[str], RowError()]` holds `str(exc)`,
    `error_repr: Annotated[Optional[str], RowError(repr=True)]` holds
    `repr(exc)`, because the daemons that log it use one or the other
    (thermalctld:1294 `repr(e)`, sensormond:311 `repr(e)`), and
    `error_column: Annotated[Optional[str], RowError(column=True)]` names the
    column whose getter raised.  All None on a row that was read whole.

    The column is what lets a consumer do what Python had done by the time
    the exception struck.  The guarded columns are read in declaration
    order, and the row declares them in its Python consumer's order: a fan
    whose speed raised had already been published as an entity and taken
    into thermalctld's LED pass (thermalctld:458-479), one whose name raised
    had not.  The columns before it hold what they read.

    A platform that declines to answer -- `NotImplementedError`, None -- has
    not failed, and leaves these None as it always did.
    """

    repr: bool = ...
    column: bool = ...

@dataclass(frozen=True)
class Unguarded:
    """Read outside the row's guard: an exception here fails the whole call.

    On a `per_row_errors` row, for the columns the Python daemon reads outside
    its per-device `try`.  thermalctld asks each thermal for its name and its
    position in `_collect_thermals` (thermalctld:1156-1157), before the `try`
    in `_refresh_temperature_status`, so a thermal whose `get_name()` raises
    fails that cycle there; the facade has to fail the call to say the same
    thing.  Also
    what a `skip`ped row still reads (see `Snapshot.skippable`).
    """

@dataclass(frozen=True)
class ReadIf:
    """Read this column only when `column` -- earlier in the row -- holds a value.

    thermalctld reads a thermal's limits and its recorded extremes only when
    the temperature itself is there (thermalctld:1246-1253): a sensor that
    cannot be read is not asked six more questions it cannot answer either.
    A row that did not read `column` at all, because the caller declined it,
    does not read this one.

    `truthy` makes the test Python's `if column:` rather than "is not None":
    thermalctld asks a fan for its speeds, their verdicts, its status and its
    direction only `if presence:` (thermalctld:471-478), and presence reads
    False, not None, when the fan is not there.

    `when_absorbing=False` lifts the condition from a row read absorbing
    (`Snapshot(absorbable=True)` with `absorb`): the condition is one daemon's
    and the absorbing read another's.  psud reads a PSU's fans gated on the
    PSU's presence, never the fan's (psud:945-950), and does not ask for the
    fan's presence at all.
    """

    column: str
    truthy: bool = ...
    when_absorbing: bool = ...

@dataclass(frozen=True)
class Secret:
    """Never printed.

    A row's Python `repr` and its Rust `Debug` show every column, and both end
    up in log lines.  A BMC session token is a credential; the row says it is
    there, not what it is.
    """

# --------------------------------------------------------------------------
# Flattening: how a row is assembled out of the base-class object tree
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Via:
    """One hop of a flatten plan, when a bare path will not do.

    `single` is for a hop that yields one object rather than a list --
    `ChassisBase.get_liquid_cooling`, `get_watchdog`, `get_bmc`.  Without it
    the generated traversal would iterate the object, which for most of them
    means a TypeError and for a string would mean one row per character.

    A bare string in `via` is this with `single=False`, which is the common
    case and stays readable.
    """

    path: str
    single: bool = ...

@dataclass(frozen=True)
class FlattenSource:
    """One place a row type is collected from.

    Modelled on what the daemons already do, because the generated facade has
    to reproduce their behaviour exactly or the migration is not a migration.
    `thermalctld._collect_thermals` is the worked example for every field
    below (thermalctld:1100-1145).

    from_
        The base-class method yielding the leaf devices, e.g.
        `"PsuBase.get_all_thermals"`.
    mapping
        Instead of `from_`, when the base class answers a mapping rather than
        a list of devices.  `get_system_eeprom_info()` is `{tlv_code: value}`
        and `BMCBase.get_eeprom()` is `{field_name: value}`; both become one
        row per entry, with `sets` naming the columns that take the key and
        the value.  Order is the mapping's own, which on every Python since
        3.7 is insertion order -- the order the platform read them in.
    provider
        Instead of `from_`, when the devices do not come from the base class
        at all: the name of a method on the hand-written `EscapeHatches` that
        yields them.  `sensormond` builds part of its sensor list by handing
        `SensorFs.factory` a *class* and a slab of `sensors.yaml`, which is
        not something a declaration can express -- but the rows it produces
        are ordinary rows, and declaring the source keeps them in the same
        order, with the same columns, as the rest.
    via
        How to walk from the chassis to the owner of `from_`, outermost
        first.  `("ChassisBase.get_all_psus",)` for a PSU's thermals;
        `("ChassisBase.get_all_modules", "ModuleBase.get_all_psus")` for the
        four-hop chassis -> module -> psu -> thermal traversal.
    when
        A predicate called on the innermost `via` object, skipping it when
        false.  `"get_presence"` -- a PSU that is not there has no thermals
        worth publishing.
    when_unsupported
        What a `when` predicate the platform does not answer means.
        `"absent"`, the default, skips the object: thermalctld asks a PSU's
        presence bare (thermalctld:1180), so a None is false there.
        `"present"` keeps it: thermalctld gates PDB thermals with
        `try_get(pdb.get_presence)` (thermalctld:1189), whose 'N/A' for an
        unanswered call is truthy.
    when_chassis
        A predicate on the chassis gating the whole source.  Module thermals
        are collected only on `"is_modular_chassis"`.
    parent
        The getter supplying the parent name, normally `"get_name"`.  None
        when the parent is fixed, as it is for the chassis' own thermals.
    parent_missing
        Answers from `parent` that mean "no name", like None does.  Mellanox's
        virtual fan drawer answers the string 'N/A' (fan_drawer.py:118), and
        thermalctld publishes the fans of a drawer so named under the chassis
        (thermalctld:450-455).
    parent_default
        Used when `parent` is absent or returns nothing.  A format string
        over `{i}`, the 1-based index at that level, and `{parent}`, the
        enclosing level's already-resolved name.  One per `via` level,
        innermost last, so that the four-hop traversal can spell the module's
        fallback and the PSU's separately -- `("Module {i}", "{parent} PSU
        {i}")` is what reproduces thermalctld's nested naming.  A bare string
        is shorthand for a single level, and for a source with no `via` it is
        the fixed parent name -- with `{i}` resolved against the row's own
        position, so that the PSUs at the top of the tree are `PSU 1`, `PSU 2`.
    index_from_previous
        The row's `{i}` carries on from the source declared just before it
        instead of starting again at 1.  sensormond numbers the sensors of
        sensors.yaml and the chassis' own as one list
        (`self.fs_sensors + self.chassis.get_all_voltage_sensors()`,
        sensormond:209), so an unnamed chassis sensor after two yaml ones is
        `chassis 1 voltage_sensor 3`.  Only between two sources that share
        one fixed parent: neither has `via`, `mapping` or `single`, and both
        declare the same `parent_default`.  The key is not affected; it is
        the path to the device.
    single
        The leaf yields one object rather than a list -- `get_watchdog` does.
        The row list is then of length at most one, which is the honest shape:
        a platform without a watchdog has no row, not a row full of None.
    optional
        The whole source is wrapped in the not-implemented handling rather
        than each call within it.  Set for sources a platform may not have at
        all, such as PDBs on a PSU-based platform.
    reaches
        For a `provider=` source, the base-class methods the hand-written
        provider calls.  Same reason as `EscapeHatch.reaches`.
    sets
        Field values this source fixes, for the fields that say where a row
        came from rather than what a device reported -- `FanInfo.kind`, and
        `PsuInfo.kind` distinguishing a PDB from a PSU.  The value `"@parent"`
        means the parent name this source resolved; `"@parent_raw"` is what
        the parent answered before any fallback, 'N/A' when it answered
        nothing -- thermalctld's `str(try_get(parent.get_name))`, which is a
        drawer fan's `drawer_name` (thermalctld:450).  `"@key"` and `"@value"`
        are the two halves of a `mapping=` entry.
    """

    from_: str = ...
    mapping: Optional[str] = ...
    provider: Optional[str] = ...
    via: tuple[Union[str, Via], ...] = ...
    when: Optional[str] = ...
    when_unsupported: Literal["absent", "present"] = ...
    when_chassis: Optional[str] = ...
    parent: Optional[str] = ...
    parent_missing: tuple[str, ...] = ...
    parent_default: Union[str, tuple[str, ...]] = ...
    index_from_previous: bool = ...
    optional: bool = ...
    single: bool = ...
    reaches: tuple[str, ...] = ...
    sets: tuple[tuple[str, object], ...] = ...

@dataclass(frozen=True)
class Flatten:
    """The ordered set of sources a row type is collected from.

    Order is part of the contract: consumers index published rows positionally
    in places, and a native implementation is tested against this one row for
    row.  Within one source the order is the platform's; across sources it is
    the order they are declared in, whole source after whole source.
    """

    sources: tuple[FlattenSource, ...]

# --------------------------------------------------------------------------
# Method-level
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Unsupported:
    """What a facade field does when the base class cannot answer.

    On a field, `default` may be a format string over `{i}` and `{parent}`,
    which is how a row whose device has no name still gets the key its
    consumers already publish it under -- `"{parent} Thermal {i}"`.  It may
    also name a field every source fixes with `sets`: sensormond's fallback
    says which kind of sensor it is (sensormond:246, 394), and
    `"{parent} {kind}_sensor {i}"` spells both from one declaration.

    `NotImplementedError` and a `None` return are the same event -- every
    daemon's `try_get()` already treats them alike, and five base-class
    methods muddy it further by writing `return NotImplementedError`, which
    hands back a truthy class object rather than raising.  The facade collapses
    all three into one declared outcome.

    none    -- the field becomes None; the ordinary case
    default -- substitute `default`, for the methods whose base-class body is
               already a constant

    Fields only.  An action does not need one: it always raises
    `NotImplementedError` for a method the platform lacks and passes on
    whatever else the method raises (see `Calls`).
    """

    on: Literal["none", "default"] = ...
    default: object = ...

@dataclass(frozen=True)
class On:
    """The row an action addresses, when its first parameter is a row's key.

    With EscapeHatch, the generated facade resolves that key and passes the
    device to the hand-written body instead. Key validation and traversal stay
    identical to generated actions; no Python object crosses to the caller.

    `set_fan_led("fan_drawers[0]/fans[2]", "amber")` has to reach the device
    that row was read from, which means following the getters of the source
    that made the key.  Naming the row here is what lets the generator derive
    that path from the row's sources instead of a lookup written by hand.

    Absent for an action on the chassis itself.

    `pass_key` is for the handful of base-class methods that take the device's
    own name as their first argument -- `ModuleBase.set_module_state_transition`
    is called on a module *and* handed that module's name.  The key is
    consumed by the lookup, and the device's own `get_name()` goes out in its
    place, as Python's consumers pass it.
    """

    row: str
    pass_key: bool = ...

@dataclass(frozen=True)
class Calls:
    """The base-class method an action invokes.

    Written as `Class.method`, like `From`, and like `From` it may name more
    than one hop: `"ChassisBase.get_watchdog.arm"` reaches the watchdog and
    arms it.  Without it an action is a signature with no body and the
    generator has nothing to emit -- which is the difference between an action
    and an `EscapeHatch`.

    `at` picks one slot out of a tuple return, exactly as it does on `From`.
    `ModuleBase.get_reboot_cause()` answers `(cause, detail)` and the caller
    wants the cause.

    `ints` names `bool` parameters the platform is handed as the ints 1 and
    0, because that is what the Python caller hands it: chassisd passes its
    MODULE_ADMIN_UP / MODULE_ADMIN_DOWN, 1 and 0, to `set_admin_state`
    (chassisd:103-104, 333, 377), and a platform that prints the argument or
    compares it with `is` sees the difference.

    One behaviour for every action: a method the platform does not have
    raises `NotImplementedError`, which a Rust caller sees as
    `PlatformError::NotSupported`; anything the method raises is passed on as
    it is; and what it answers is the action's answer.  A key that leads to
    no device raises `DeviceNotFound`.
    """

    path: str
    at: Optional[int] = ...
    ints: tuple[str, ...] = ...

@dataclass(frozen=True)
class Snapshot:
    """A method answering rows: every one, read when it is called.

    A method returning a bare row rather than `list[...]` is a singleton: the
    chassis is the device, so there is nothing to flatten and the row carries
    no `ORDER`.  Nothing is cached between calls; a caller polls by calling.

    `projected` gives the caller a say in which columns are read.

    One call carries every row, instead of one crossing per field per device.
    Filling every *column* is a separate choice, and it is not free -- the
    getters run inside the
    facade, at the same cost the object tree paid, for columns the caller may
    throw away.  Measured on a Mellanox switch: psud reads four of FanInfo's
    sixteen columns, but asking for the snapshot ran `is_under_speed`, whose
    Mellanox implementation reads `psu{n}_fan_min`; with the PSU switched off
    that file is readable and empty, so the read logged a ValueError at ERR
    under psud -- a pairing Python cannot produce, because Python's psud never
    makes that call.  psud polls at 3s and thermalctld at 60s, so the port hit
    a pre-existing race twenty times as often, under the wrong identifier.

    A projected snapshot takes a column set and reads only what is in it.
    **Columns outside the set are unspecified, not guaranteed absent**: an
    implementation with no notion of columns -- a native one reading sysfs
    directly -- may fill them anyway and still be correct.  That keeps the
    parameter a hint rather than an obligation, which is what lets the trait
    outlive this Python implementation.

    `skippable` adds a `skip` list of keys: those rows read only their
    `Unguarded()` columns, and the rest of the row is left absent.  It is how
    thermalctld keeps platform.json's `polling_interval`: Python reads a
    thermal that is not due only for its name and position, and its
    readings only when due (thermalctld:1126-1158).  A key not in the list --
    one seen for the first time included -- is read in full, as Python reads
    a name it has no last-update time for.

    `per_row_errors` confines a getter's exception to the row it was reading
    (see `RowError`), for the snapshots whose Python consumer isolates each
    device: thermals and fans in thermalctld (thermalctld:1221-1294, 378-384),
    sensors in sensormond (sensormond:237-311, 385-459).  Everywhere else --
    but where a snapshot absorbs, below -- an exception fails the call, as it
    fails the Python loop.

    `absorbs` is psud's way instead: every getter in a `try` of its own, an
    exception leaving that column absent and the rest of the row read, which
    is what `psud:try_get` does with any exception (psud:271-292).  No row
    error is set; Python logs nothing either.  `absorbable` lets the caller
    choose, per call, on a snapshot two daemons share: `get_fans` is
    thermalctld's, per row (thermalctld:378-384), and psud's for a PSU's
    fans, per column (psud:943-960), so it takes an `absorb` flag.
    """

    projected: bool = ...
    skippable: bool = ...
    per_row_errors: bool = ...
    absorbs: bool = ...
    absorbable: bool = ...

@dataclass(frozen=True)
class EscapeHatch:
    """This method's body is hand-written in `_escape_hatch.py`.

    Four things in the surface resist mechanical generation and are declared
    rather than derived:

    - `get_thermal_manager()` returns a class, not an instance, whose twelve
      methods are all `@classmethod` over process-global state, and which
      takes the chassis back as an argument.  The facade holds the chassis and
      passes it, so the Rust side sees four argument-less calls and no
      re-entrancy.
    - `get_xcvr_api()` returns common code with 161 public methods on it, and
      seven sites dispatch on its Python type.
    - `SensorFs.factory(sensor_cls, ...)` takes a class as a parameter.
    - `get_change_event()` returns a two-level mapping whose leaf is a
      stringly-typed enumeration documented only in prose.

    `reason` is required: an escape hatch that nobody justified is a method
    somebody gave up on generating.

    `reaches` names the base-class methods the hand-written body calls.  A
    generated body declares what it touches by construction; a hand-written
    one has to say, or `api_coverage.py` cannot count what it reaches and
    reports it unfinished forever.
    """

    reason: str
    reaches: tuple[str, ...] = ...

@dataclass(frozen=True)
class Rust:
    """The Rust spelling, where the mechanical mapping is not the right one."""

    name: str

F = TypeVar("F", bound=Callable[..., object])

def platform_method(*spec: object) -> Callable[[F], F]:
    """Attach method-level metadata.

    Variadic so that the metadata composes -- an action carries an `On` and
    a `Calls` -- without a combining type per pairing.
    """
