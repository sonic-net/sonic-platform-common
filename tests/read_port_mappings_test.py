import os
import sys

try:

    import sonic_platform_base.sonic_sfp.sfputilhelper 
except Exception as e:
    print("Failed to load chassis due to {}".format(repr(e)))


class TestPortMappingsRead(object):

    self.platform_sfputil = None
    self.test_dir = None
    self.port_config = None

    @classmethod
    def setup_class(cls):
        print("SETUP")
        self.test_dir = os.path.dirname(os.path.realpath(__file__))
        self.port_config = os.path.join(self.test_dir, 't0-sample-port-config.ini')

        self.platform_sfputil = sonic_platform_base.sonic_sfp.sfputilhelper.SfpUtilHelper()
        try:
            platform_sfputil.read_porttab_mappings(self.port_config, 0)
        except Exception as e:
            print("Failed to read port tab mappings to {}".format(repr(e)))


    def test_port_names(self): 

        PORT_LIST  = [ "Ethernet0",
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
                for logical_port_name in logical_port_list:
                    assert logical_port_name in self.port_list
        else:
            print("platform_sfputil is None, cannot read Ports")

