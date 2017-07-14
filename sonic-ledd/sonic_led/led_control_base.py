#!/usr/bin/env python
#
# led_control_base.py
#
# Abstract base class for implementing platform-specific
#  LED control functionality for SONiC
#

try:
    import abc
except ImportError, e:
    raise ImportError (str(e) + " - required module not found")

class LedControlBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def port_link_state_change(self, port, state):
        """
        Called when port link state changes. Update port link state LED here.

        :param port: A string, SONiC port name (e.g., "Ethernet0")
        :param state: A string, the port link state (either "up" or "down")
        """
        return
