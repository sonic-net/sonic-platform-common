from sonic_platform_base.sonic_xcvr.cpo.cmis import CpoCmisApi

# Imported under a private alias so that pytest does not collect
# and run TestCmis's test cases when executing this file.
from .test_cmis import TestCmis as _TestCmis


class TestCpoCmis(_TestCmis):
    """
    Every test case of TestCmis, run against CpoCmisApi.

    This is intended to catch drift between CpoCmisApi and CmisApi. If a bug-fix
    is added to CmisApi, or a new feature added, then CpoCmisApi should be ideally
    updated with the same feature.
    """

    api = CpoCmisApi(_TestCmis.eeprom)
