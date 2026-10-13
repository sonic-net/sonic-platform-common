"""The cross-language platform API.

`facade.pyi` is the source of truth; `facade.py` is generated from it, as are
the Rust trait and the PyO3 bridge a Rust daemon reaches this through.
"""

from .facade import PlatformApi  # noqa: F401
