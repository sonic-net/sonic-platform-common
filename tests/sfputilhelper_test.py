import os
import sys

import pytest

from sonic_platform_base.sonic_sfp import sfputilhelper
from unittest import mock

PORT_LIST = [
    "Ethernet0",
    "Ethernet4",
    "Ethernet8",
    "Ethernet12",
    "Ethernet16",
    "Ethernet20",
    "Ethernet24",
    "Ethernet28",
    "Ethernet32",
    "Ethernet36",
    "Ethernet40",
    "Ethernet44",
    "Ethernet48"
]

PORT_FILTERED_LIST = [
    "Ethernet0",
    "Ethernet4",
    "Ethernet8",
    "Ethernet12",
    "Ethernet16",
    "Ethernet20",
    "Ethernet24",
    "Ethernet28",
    "Ethernet32",
    "Ethernet36",
    "Ethernet40",
]

LOGICAL_TO_PHYSICAL ={
    'Ethernet0': [1],
    'Ethernet4': [2],
    'Ethernet8': [3],
    'Ethernet12': [4],
    'Ethernet16': [5],
    'Ethernet20': [6],
    'Ethernet24': [7],
    'Ethernet28': [8],
    'Ethernet32': [9],
    'Ethernet36': [10],
    'Ethernet40': [11],
    'Ethernet44': [12],
    'Ethernet48': [13]
}

PHYSICAL_TO_LOGICAL = {
    1: ['Ethernet0'],
    2: ['Ethernet4'],
    3: ['Ethernet8'],
    4: ['Ethernet12'],
    5: ['Ethernet16'],
    6: ['Ethernet20'],
    7: ['Ethernet24'],
    8: ['Ethernet28'],
    9: ['Ethernet32'],
    10: ['Ethernet36'],
    11: ['Ethernet40'],
    12: ['Ethernet44'],
    13: ['Ethernet48']
}

test_dir = os.path.dirname(os.path.realpath(__file__))
hwsku_json_file = os.path.join(test_dir, 'platform_json', 'hwsku.json')
hwsku_role_json_file = os.path.join(test_dir, 'platform_json', 'hwsku_role.json')

@pytest.fixture(scope="class")
def setup_class(request):
    # Configure the setup
    request.cls.port_config_file = os.path.join(test_dir, 'port_config.ini')
    request.cls.platform_dir = os.path.dirname(os.path.realpath(__file__))
    request.cls.platform_json_dir = os.path.join(test_dir, 'platform_json')


@pytest.mark.usefixtures("setup_class")
class TestSfpUtilHelper(object):

    port_config_file = None
    platform_dir = None
    platform_json_dir = None

    def test_read_port_mappings(self):

        sfputil_helper = sfputilhelper.SfpUtilHelper()
        sfputil_helper.read_porttab_mappings(self.port_config_file, 0)

        logical_port_list = sfputil_helper.logical

        assert len(logical_port_list) == len(PORT_LIST)

        for logical_port, port in zip(logical_port_list, PORT_LIST):
            assert logical_port == port


    @mock.patch('portconfig.get_hwsku_file_name', mock.MagicMock(return_value=hwsku_json_file))
    def test_read_all_port_mappings(self):

        sfputil_helper = sfputilhelper.SfpUtilHelper()
        sfputil_helper.logical = []
        sfputil_helper.logical_to_physical = {}
        sfputil_helper.physical_to_logical = {}
        sfputil_helper.read_all_porttab_mappings(self.platform_dir, 2)
        logical_port_list = sfputil_helper.logical

        assert len(logical_port_list) == len(PORT_LIST)

        for logical_port, port in zip(logical_port_list, PORT_LIST):
            assert logical_port == port

        assert sfputil_helper.logical_to_physical == LOGICAL_TO_PHYSICAL
        assert sfputil_helper.physical_to_logical == PHYSICAL_TO_LOGICAL

        # test platform.json case

        sfputil_helper.logical = []
        sfputil_helper.logical_to_physical = {}
        sfputil_helper.physical_to_logical = {}
        sfputil_helper.read_all_porttab_mappings(self.platform_json_dir, 2)
        logical_port_list = sfputil_helper.logical

        assert len(logical_port_list) == len(PORT_LIST)

        for logical_port, port in zip(logical_port_list, PORT_LIST):
            assert logical_port == port

        assert sfputil_helper.logical_to_physical == LOGICAL_TO_PHYSICAL
        assert sfputil_helper.physical_to_logical == PHYSICAL_TO_LOGICAL

    @mock.patch('portconfig.get_hwsku_file_name', mock.MagicMock(return_value=hwsku_role_json_file))
    def test_read_all_port_mappings_role(self):
        sfputil_helper = sfputilhelper.SfpUtilHelper()
        sfputil_helper.logical = []
        sfputil_helper.logical_to_physical = {}
        sfputil_helper.physical_to_logical = {}
        sfputil_helper.read_all_porttab_mappings(self.platform_json_dir, 2)
        logical_port_list = sfputil_helper.logical

        assert len(logical_port_list) == len(PORT_FILTERED_LIST)
