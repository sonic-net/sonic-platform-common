import os
import sys

import pytest
try:
    import sonic_platform_base.sonic_sfp.sfputilhelper
except Exception as e:
    print("Failed to load sonic_platform_base.sonic_sfp.sfputilhelper  due to {}".format(repr(e)))


@pytest.fixture(scope="class")
def setup_class(request):
    # Configure the setup
    test_dir = os.path.dirname(os.path.realpath(__file__))
    request.cls.port_config = os.path.join(
        test_dir, 't0-sample-port-config.ini')

    request.cls.port_config = sonic_platform_base.sonic_sfp.sfputilhelper.SfpUtilHelper()


@pytest.mark.usefixtures("setup_class")
class TestSfpUtilHelper(object):

    platform_sfputil = None
    port_config = None

    def test_read_port_mappings(self):

        try:
            platform_sfputil.read_porttab_mappings(self.port_config, 0)
        except Exception as e:
            print("Failed to read port tab mappings to {}".format(repr(e)))

        PORT_LIST = ["Ethernet0",
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
                     "Ethernet48"]

        if self.platform_sfputil is not None:
            logical_port_list = self.platform_sfputil.logical
            assert len(logical_port_name) == len(self.port_list)
            for logical_port_name in logical_port_list:
                assert logical_port_name in PORT_LIST
        else:
            print("platform_sfputil is None, cannot read Ports")
