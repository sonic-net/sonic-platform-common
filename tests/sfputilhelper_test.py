import os
import sys

import pytest

from sonic_platform_base.sonic_sfp import sfputilhelper


@pytest.fixture(scope="class")
def setup_class(request):
    # Configure the setup
    test_dir = os.path.dirname(os.path.realpath(__file__))
    request.cls.port_config_file = os.path.join(test_dir, 'port_config.ini')


@pytest.mark.usefixtures("setup_class")
class TestSfpUtilHelper(object):

    port_config_file = None

    def test_read_port_mappings(self):
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

        sfputil_helper = sfputilhelper.SfpUtilHelper()
        sfputil_helper.read_porttab_mappings(self.port_config_file, 0)

        logical_port_list = sfputil_helper.logical
        assert len(logical_port_list) == len(PORT_LIST)

        for logical_port_name in logical_port_list:
            assert logical_port_name in PORT_LIST
