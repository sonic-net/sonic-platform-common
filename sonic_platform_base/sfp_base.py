#
# sfp_base.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a SFP module in SONiC
#

import sys
from . import device_base


class SfpBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a SFP module
    """

    def get_transceiver_info(self):
        """
        Retrieves transceiver info of this SFP

        Returns:
            A dict which contains following keys/values :
        ========================================================================
        keys                       |Value Format   |Information	
        ---------------------------|---------------|----------------------------
        type                       |1*255VCHAR     |type of SFP
        hardwarerev                |1*255VCHAR     |hardware version of SFP
        serialnum                  |1*255VCHAR     |serial number of the SFP
        manufacturename            |1*255VCHAR     |SFP venndor name
        modelname                  |1*255VCHAR     |SFP model name
        Connector                  |1*255VCHAR     |connector information
        encoding                   |1*255VCHAR     |encoding information
        ext_identifier             |1*255VCHAR     |extend identifier
        ext_rateselect_compliance  |1*255VCHAR     |extended rateSelect compliance
        cable_length               |INT            |cable length in m
        mominal_bit_rate           |INT            |nominal bit rate by 100Mbs
        specification_compliance   |1*255VCHAR     |specification compliance
        vendor_date                |1*255VCHAR     |vendor date
        vendor_oui                 |1*255VCHAR     |vendor OUI
        ========================================================================
        """
        return NotImplementedError

    def get_transceiver_bulk_status(self):
        """
        Retrieves transceiver bulk status of this SFP

        Returns:
            A dict which contains following keys/values :
        ========================================================================
        keys                       |Value Format   |Information	
        ---------------------------|---------------|----------------------------
        RX LOS                     |BOOLEAN        |rx lost-of-signal status,
                                   |               |True if has rx los, False if not.
        TX FAULT                   |BOOLEAN        |tx fault status,
                                   |               |True if has tx fault, False if not.
        Reset status               |BOOLEAN        |reset status,
                                   |               |True if SFP in reset, False if not.
        LP mode                    |BOOLEAN        |low power mode status,
                                   |               |True in lp mode, False if not.
        tx disable                 |BOOLEAN        |tx disable status,
                                   |               |True tx disabled, False if not.
        tx disabled channel        |HEX            |disabled TX channles in hex,
                                   |               |bits 0 to 3 represent channel 0
                                   |               |to channel 3.
        ========================================================================
        """
        return NotImplementedError
                
    def get_reset_status(self):
        """
        Retrieves the reset status of SFP

        Returns:
            A Boolean, True if reset enabled, False if disabled
        """
        return NotImplementedError

    def get_rx_los(self):
        """
        Retrieves the rx los (lost-of-signal) status of SFP

        Returns:
            A Boolean, True if SFP has rx los, False if not.
            Note : rx los status is lached until a call to get_rx_los or a reset.
        """
        return NotImplementedError

    def get_tx_fault(self):
        """
        Retrieves the tx fault status of SFP

        Returns:
            A Boolean, True if SFP has tx-fault, False if not
            Note : tx fault status is lached until a call to get_tx_fault or a reset.
        """
        return NotImplementedError

    def get_tx_disable(self):
        """
        Retrieves the tx-disable status of this SFP

        Returns:
            A Boolean, True if tx-disable is enabled, False if disabled
        """
        return NotImplementedError

    def get_tx_disable_channel(self):
        """
        Retrieves the tx disabled channels in this SFP

        Returns:
            A hex of 4 bits (bit 0 to bit 3 as channel 0 to channel 3) to represent
            tx channels which have been disabled in this SFP.
            As an example, a returned value of 0x5 indicates that channel 0 
            and channel 2 have been disabled.
        """
        return NotImplementedError

    def get_lpmode(self):
        """
        Retrieves the lpmode status of this SFP

        Returns:
            A Boolean, True if lpmode (low power mode) is enabled, False if disabled
        """
        return NotImplementedError

    def get_power_override(self):
        """
        Retrieves the power-override status of this SFP

        Returns:
            A Boolean, True if power-override is enabled, False if disabled
        """
        return NotImplementedError

    def reset(self):
        """
        Reset SFP and return all user module settings to their default srate.

        Returns:
            A boolean, True if successful, False if not
        """
        return NotImplementedError
    
    def tx_disable(self, tx_disable):
        """
        Disable SFP tx for all channels

        Args:
            tx_disable : A Boolean, True to enable tx_disable mode, False to disable
                         tx_disable mode.

        Returns:
            A boolean, True if tx_disable is set successfully, False if not
        """
        return NotImplementedError
    
    def tx_disable_channel(self, channel, disable):
        """
        Sets the tx_disable for specified SFP channels

        Args:
            channel : A hex of 4 bits (bit 0 to bit 3) which represent channel 0 to 3,
                      e.g. 0x5 for channel 0 and channel 2.
            disable : A boolean, Trure to disable tx channels specified in channel,
                      False to enable

        Returns:
            A boolean, True if successful, False if not
        """
        return NotImplementedError
    
    def set_lpmode(self, lpmode):
        """
        Sets the lpmode of SFP

        Args:
            lpmode: A Boolean, True to enable lpmode (low power mode),
                    False to disable it
            Note  : lpmode can be overridden by set_power_override

        Returns:
            A boolean, True if lpmode is set successfully, False if not
        """
        return NotImplementedError
    
    def set_power_override(self, power_override, power_set):
        """
        Sets SFP power level using power_override and power_set

        Args:
            power_override : A Boolean, True to override lpmode and have power_set
                    to control SFP power, False to disable power_override and the
                    control of power_set.
            power_set : A Boolean, True to set power at low power mode, False to set
                    SFP to high power mode.

        Returns:
            A boolean, True if power-override and power_set are set successfully,
            False if not
        """
        return NotImplementedError
