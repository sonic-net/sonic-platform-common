#!/usr/bin/env python
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
    __metaclass__ = abc.ABCMeta
    
    @abc.abstractmethod
    def get_pcie_speed(self,device):
         """
        Retrieves PCIE speed for the given device
        
         Returns:
            A string holding PCIE speed with specific device
        """  
      
        raise NotImplementedError
    
    
    
    def get_pcie_id(self,device):
        
          """
        Retrieves PCIE id for the given device
        
         Returns:
            A string holding PCIE id with specific device
        """  
        raise NotImplementedError