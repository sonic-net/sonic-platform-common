import os
import sys
from imp import load_source

from mock import Mock, MagicMock, patch
from sonic_py_common import daemon_base

from .mock_platform import MockChassis, MockModule
from .mock_module_base import ModuleBase

SYSLOG_IDENTIFIER = 'chassis_db_init_test'
NOT_AVAILABLE = 'N/A'

daemon_base.db_connect = MagicMock()

test_path = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.dirname(test_path)
scripts_path = os.path.join(modules_path, "scripts")
sys.path.insert(0, modules_path)

os.environ["CHASSIS_DB_INIT_UNIT_TESTING"] = "1"
load_source('chassis_db_init', scripts_path + '/chassis_db_init')
from chassis_db_init import *


def test_provision_db():
    chassis = MockChassis()
    log = MagicMock()
    serial = "Serial No"
    model = "Model A"
    revision = "Rev C"

    chassis_table = provision_db(chassis, log)

    fvs = chassis_table.get(CHASSIS_INFO_KEY_TEMPLATE.format(1))
    if isinstance(fvs, list):
        fvs = dict(fvs[-1])
    assert serial == fvs[CHASSIS_INFO_SERIAL_FIELD]
    assert model == fvs[CHASSIS_INFO_MODEL_FIELD]
    assert revision == fvs[CHASSIS_INFO_REV_FIELD]
