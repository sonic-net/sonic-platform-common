#
# pcie_base.py
#
# Abstract base class for implementing platform-specific
#  PCIE functionality for SONiC
#

try:
    import abc
except ImportError as e:
    raise ImportError (str(e) + " - required module not found")

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
