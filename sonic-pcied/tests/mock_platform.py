
"""
    Mock implementation of sonic_platform package for unit testing
"""

# TODO: Clean this up once we no longer need to support Python 2
import sys
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock



pcie_device_list = \
"""
[{'bus': '00', 'dev': '01', 'fn': '0', 'id': '1f10', 'name': 'PCI A'}]
"""

pcie_check_result = \
"""
[{'bus': '00', 'dev': '01', 'fn': '0', 'id': '1f10', 'name': 'PCI A', 'result': 'Passed'}]
"""

pcie_aer_stats = \
"""
{'correctable': {}, 'fatal': {}, 'non_fatal': {}}
"""

#class MockPcieUtil(PcieUtil):
class MockPcieUtil():
    def __init__(self, 
                 pciList=pcie_device_list,
                 result=pcie_check_result, 
                 aer_stats=pcie_aer_stats):
        super(MockPcieUtil, self).__init__()
        self._pciList = pciList
        self._result = result
        self._aer_stats = aer_stats

    def get_pcie_device(self):
        return self._pciList

    def get_pcie_check(self):
        return self._result

    def get_pcie_aer_stats(self, domain, bus, dev, fn):
        return self._aer_stats
