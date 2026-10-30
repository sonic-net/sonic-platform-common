"""Units, so that a reader of the facade knows what a bare number means.

These are aliases, not new types: the base classes return plain numbers and
the facade does not wrap them.  What the alias buys is that `get_voltage`
returning `Volt` and `get_speed` returning `Percent` no longer read alike, and
that the generator has a name to hang a Rust type on.

Optionality is deliberately NOT folded into these aliases.  Almost every
facade field is `Optional[...]`, because every daemon's `try_get()` treats a
`None` return from the base class as "not implemented" exactly as it treats
`NotImplementedError` (thermalctld:104, psud:272, chassisd:183,
sensormond:36, bmcctld:297).  Writing that `Optional` out at each field keeps
the stub honest about what the generated code returns -- if the alias hid it,
`stubtest` would be comparing against a type nobody wrote down.
"""

from typing import Union

# A reading or a limit, as the platform answered it.  Vendors return int as
# often as float, and the daemons publish what they got with `str()`
# (thermalctld:1272-1281, psud:880-900, sensormond:294-303): a temperature of
# 3 is "3" in STATE_DB and 3.0 is "3.0".  The union keeps the difference --
# Rust carries it as `Number` -- where a float would rewrite every int.  The
# difference is outside what `stubtest` can check; it verifies shape, not
# types.  The aliases below say what a number measures.
Number = Union[int, float]

# JSON-encoded transceiver data. Keys depend on module type, lane count and
# vendor extensions, so they cannot be enumerated as fixed row columns.
# Non-finite readings use Python's strings ("-inf", "inf", "nan"); None is
# JSON null. Keeping the wire type a string leaves the native trait independent
# of a particular JSON library.
Json = str

# Temperature, in degrees Celsius.
Celsius = Number

# A temperature, voltage or power limit.
Threshold = Number

# Fan speed as a percentage of maximum, 0-100.
Percent = Number

# Fan speed in revolutions per minute.
Rpm = int

Watt = Number
Volt = Number
Ampere = Number

# 1-based position of a device within its parent; -1 when unknown.
PositionInParent = int

# 0-based selector accepted by the indexed base-class accessors.  The facade
# addresses rows by name instead, so this appears only in the ABC mirror --
# where the parameter must keep the name `index`, because the conformance
# suite's server dispatches on that name through inspect.signature().
Index = int

Count = int

# Where a device sits in the object tree, as the facade walked to it: the
# collections from the chassis down, each with the position in its list.
# "fan_drawers[1]/fans[0]" is `chassis.get_all_fan_drawers()[1]
# .get_all_fans()[0]`.  Every addressed row carries one, and every action takes
# one, because names are not unique: two line cards each have a "BIOS".  The
# positions are list positions, 0-based throughout, not the indexed accessors'
# mixed conventions.  Treat it as opaque; build it from a row or from
# `get_module_key` / `get_component_key`, never by hand.
DeviceKey = str
