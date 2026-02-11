# Copilot Instructions for sonic-platform-common

## Project Overview

sonic-platform-common provides a collection of Python packages that define the common abstract interface for platform-specific hardware peripherals in SONiC. It includes base classes for fans, PSUs, thermal sensors, LEDs, transceivers (SFP/QSFP), and Y-cable management. Vendor platform plugins inherit from these base classes to provide hardware-specific implementations.

## Architecture

```
sonic-platform-common/
├── sonic_platform_base/   # Abstract base classes for all platform APIs
│   ├── chassis_base.py    # Chassis abstraction (root platform object)
│   ├── module_base.py     # Module/linecard abstraction
│   ├── fan_base.py        # Fan control and monitoring
│   ├── fan_drawer_base.py # Fan drawer abstraction
│   ├── psu_base.py        # Power Supply Unit
│   ├── thermal_base.py    # Thermal sensor monitoring
│   ├── sfp_base.py        # SFP/QSFP transceiver abstraction
│   ├── watchdog_base.py   # Hardware watchdog
│   ├── component_base.py  # Firmware components (BIOS, CPLD, FPGA)
│   └── ...
├── sonic_fan/             # Legacy fan platform API
├── sonic_psu/             # Legacy PSU platform API
├── sonic_thermal/         # Legacy thermal platform API
├── sonic_led/             # LED control API
├── sonic_y_cable/         # Y-cable (dual-ToR) management
├── tests/                 # pytest unit tests
├── setup.py               # Package setup
└── .github/               # GitHub configuration
```

### Key Concepts
- **Platform abstraction**: Base classes define APIs; vendors implement them
- **Chassis model**: `ChassisBase` is the root — contains modules, fans, PSUs, SFPs, thermals
- **Plugin architecture**: Platform-specific code lives in `device/<vendor>/` in sonic-buildimage
- **PDDF**: Platform Driver Development Framework — generic driver-based alternative

## Language & Style

- **Primary language**: Python 3
- **Indentation**: 4 spaces
- **Naming conventions**:
  - Classes: `PascalCase` (e.g., `ChassisBase`, `FanBase`)
  - Methods: `snake_case` (e.g., `get_name()`, `get_status()`)
  - Abstract methods: Raise `NotImplementedError` in base class
  - Constants: `UPPER_CASE`
- **Docstrings**: Required for all public methods — describe return types and values
- **Type hints**: Encouraged for new code

## Build Instructions

```bash
# Install for development
pip3 install -e .

# Build wheel
python3 setup.py bdist_wheel

# Install
pip3 install sonic_platform_common
```

## Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=sonic_platform_base --cov-report=term-missing
```

- Tests use **pytest**
- Tests verify abstract interface contracts
- Mock-based testing for platform base classes

## PR Guidelines

- **Commit format**: `[component]: Description`
- **Signed-off-by**: REQUIRED (`git commit -s`)
- **CLA**: Sign Linux Foundation EasyCLA
- **Backwards compatibility**: CRITICAL — don't break existing vendor implementations
- **Abstract methods**: New abstract methods must have default implementations to avoid breaking subclasses
- **Documentation**: All new API methods need docstrings

## Common Patterns

### Adding a New Platform API
```python
class NewFeatureBase:
    """Base class for new feature abstraction"""
    
    def get_name(self):
        """Get the name of the feature component
        Returns:
            string: Name of the component
        """
        raise NotImplementedError
    
    def get_status(self):
        """Get operational status
        Returns:
            bool: True if operational
        """
        raise NotImplementedError
```

### Extending Existing Base Classes
```python
# Always add default implementation to avoid breaking vendors
def get_new_attribute(self):
    """Get new attribute (added in version X.Y)
    Returns:
        string: Value or 'N/A' if not supported
    """
    return 'N/A'  # Default — vendors override as needed
```

## Dependencies

- **Python 3**: Standard library primarily
- **sonic-py-common**: Common SONiC Python utilities
- Minimal external dependencies by design (this is a base library)

## Gotchas

- **Never break the API contract**: Dozens of vendor plugins inherit from these classes
- **Default implementations**: New methods MUST have safe defaults (return None, 'N/A', False, etc.)
- **No hardware access**: Base classes must never import platform-specific libraries
- **Testing on real hardware**: Unit tests cover interface contracts; real testing needs vendor hardware
- **Version compatibility**: Changes here propagate to all platforms — be conservative
- **Legacy APIs**: `sonic_fan/`, `sonic_psu/`, `sonic_thermal/` are legacy; prefer `sonic_platform_base/`
- **Y-cable complexity**: `sonic_y_cable/` has multiple vendor implementations — test carefully
