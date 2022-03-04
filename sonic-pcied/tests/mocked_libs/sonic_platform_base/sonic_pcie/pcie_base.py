#
# pcie_base.py
#
# Abstract base class for implementing platform-specific
#  PCIE functionality for SONiC
#

try:
    import abc
except ImportError as e:
    raise ImportError(str(e) + " - required module not found")


class PcieBase(object):
    def __init__(self, path):
        """
         Constructor

         Args:
           pcieutil file and config file path
        """

    @abc.abstractmethod
    def get_pcie_device(self):
        """
         get current device pcie info

          Returns:
            A list including pcie device info
        """
        return []

    @abc.abstractmethod
    def get_pcie_check(self):
        """
         Check Pcie device with config file

         Returns:
            A list including pcie device and test result info
        """
        return []

    @abc.abstractmethod
    def get_pcie_aer_stats(self, domain, bus, dev, fn):
        """
        Returns a nested dictionary containing the AER stats belonging to a
        PCIe device

        Args:
            domain, bus, dev, fn: Domain, bus, device, function of the PCIe
            device respectively

        Returns:
            A nested dictionary where key is severity 'correctable', 'fatal' or
            'non_fatal', value is a dictionary of key, value pairs in the format:
                {'AER Error type': Error count}

            Ex. {'correctable': {'BadDLLP': 0, 'BadTLP': 0},
                 'fatal': {'RxOF': 0, 'MalfTLP': 0},
                 'non_fatal': {'RxOF': 0, 'MalfTLP': 0}}

            For PCIe devices that do not support AER, the value for each
            severity key is an empty dictionary.
        """
        return {}
