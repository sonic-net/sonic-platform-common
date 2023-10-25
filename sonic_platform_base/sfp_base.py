"""
    sfp_base.py

    Abstract base class for implementing a platform-specific class with which
    to interact with a SFP module in SONiC
"""

import sys
from . import device_base

from .sonic_xcvr.xcvr_api_factory import XcvrApiFactory

class SfpBase(device_base.DeviceBase):
    """
    Abstract base class for interfacing with a SFP module
    """
    # Device type definition. Note, this is a constant.
    DEVICE_TYPE = "sfp"

    # Generic error types definition
    SFP_STATUS_INITIALIZING                         = 'Initializing'
    SFP_STATUS_OK                                   = 'OK'
    SFP_STATUS_UNPLUGGED                            = 'Unplugged'
    SFP_STATUS_DISABLED                             = 'Disabled'
    SFP_ERROR_DESCRIPTION_BLOCKING                  = 'Blocking EEPROM from being read'
    SFP_ERROR_DESCRIPTION_POWER_BUDGET_EXCEEDED     = 'Power budget exceeded'
    SFP_ERROR_DESCRIPTION_I2C_STUCK                 = 'Bus stuck (I2C data or clock shorted)'
    SFP_ERROR_DESCRIPTION_BAD_EEPROM                = 'Bad or unsupported EEPROM'
    SFP_ERROR_DESCRIPTION_UNSUPPORTED_CABLE         = 'Unsupported cable'
    SFP_ERROR_DESCRIPTION_HIGH_TEMP                 = 'High temperature'
    SFP_ERROR_DESCRIPTION_BAD_CABLE                 = 'Bad cable (module/cable is shorted)'

    # SFP status
    SFP_STATUS_BIT_REMOVED                = 0x00000000
    SFP_STATUS_BIT_INSERTED               = 0x00000001
    # SFP error status
    SFP_ERROR_BIT_BLOCKING                = 0x00000002
    SFP_ERROR_BIT_POWER_BUDGET_EXCEEDED   = 0x00000004
    SFP_ERROR_BIT_I2C_STUCK               = 0x00000008
    SFP_ERROR_BIT_BAD_EEPROM              = 0x00000010
    SFP_ERROR_BIT_UNSUPPORTED_CABLE       = 0x00000020
    SFP_ERROR_BIT_HIGH_TEMP               = 0x00000040
    SFP_ERROR_BIT_BAD_CABLE               = 0x00000080

    SFP_ERROR_BIT_TO_DESCRIPTION_DICT = {
        SFP_ERROR_BIT_BLOCKING:                SFP_ERROR_DESCRIPTION_BLOCKING,
        SFP_ERROR_BIT_POWER_BUDGET_EXCEEDED:   SFP_ERROR_DESCRIPTION_POWER_BUDGET_EXCEEDED,
        SFP_ERROR_BIT_I2C_STUCK:               SFP_ERROR_DESCRIPTION_I2C_STUCK,
        SFP_ERROR_BIT_BAD_EEPROM:              SFP_ERROR_DESCRIPTION_BAD_EEPROM,
        SFP_ERROR_BIT_UNSUPPORTED_CABLE:       SFP_ERROR_DESCRIPTION_UNSUPPORTED_CABLE,
        SFP_ERROR_BIT_HIGH_TEMP:               SFP_ERROR_DESCRIPTION_HIGH_TEMP,
        SFP_ERROR_BIT_BAD_CABLE:               SFP_ERROR_DESCRIPTION_BAD_CABLE
    }

    # Port types that are used by the chassis API ChassisBase.get_port_or_cage_type()
    # It's possible that multiple types are supported on one port.
    # In that case, the result will be logical OR of all the supported types
    # Check example in ChassisBase.get_port_or_cage_type()
    SFP_PORT_TYPE_BIT_RJ45                = 0x00000001
    SFP_PORT_TYPE_BIT_SFP                 = 0x00000002
    SFP_PORT_TYPE_BIT_XFP                 = 0x00000004
    SFP_PORT_TYPE_BIT_SFP_PLUS            = 0x00000008
    SFP_PORT_TYPE_BIT_QSFP                = 0x00000010
    SFP_PORT_TYPE_BIT_CFP                 = 0x00000020
    SFP_PORT_TYPE_BIT_QSFP_PLUS           = 0x00000040
    SFP_PORT_TYPE_BIT_QSFP28              = 0x00000080
    SFP_PORT_TYPE_BIT_SFP28               = 0x00000100
    SFP_PORT_TYPE_BIT_CFP2                = 0x00000200
    SFP_PORT_TYPE_BIT_QSFP56              = 0x00000400
    SFP_PORT_TYPE_BIT_QSFPDD              = 0x00000800
    SFP_PORT_TYPE_BIT_OSFP                = 0x00001000
    SFP_PORT_TYPE_BIT_SFP_DD              = 0x00002000

    def __init__(self):
        # List of ThermalBase-derived objects representing all thermals
        # available on the SFP
        self._thermal_list = []
        self._xcvr_api_factory = XcvrApiFactory(self.read_eeprom, self.write_eeprom)
        self._xcvr_api = None

    def get_num_thermals(self):
        """
        Retrieves the number of thermals available on this SFP

        Returns:
            An integer, the number of thermals available on this SFP
        """
        return len(self._thermal_list)

    def get_all_thermals(self):
        """
        Retrieves all thermals available on this SFP

        Returns:
            A list of objects derived from ThermalBase representing all thermals
            available on this SFP
        """
        return self._thermal_list

    def get_thermal(self, index):
        """
        Retrieves thermal unit represented by (0-based) index <index>

        Args:
            index: An integer, the index (0-based) of the thermal to
            retrieve

        Returns:
            An object derived from ThermalBase representing the specified thermal
        """
        thermal = None

        try:
            thermal = self._thermal_list[index]
        except IndexError:
            sys.stderr.write("THERMAL index {} out of range (0-{})\n".format(
                             index, len(self._thermal_list)-1))

        return thermal

    def get_transceiver_info(self):
        """
        Retrieves transceiver info of this SFP

        Returns:
            A dict which contains following keys/values :
        ================================================================================
        keys                       |Value Format   |Information
        ---------------------------|---------------|----------------------------
        type                       |1*255VCHAR     |type of SFP
        type_abbrv_name            |1*255VCHAR     |type of SFP, abbreviated
        hardware_rev               |1*255VCHAR     |hardware version of SFP
        vendor_rev                 |1*255VCHAR     |vendor revision of SFP
        serial                     |1*255VCHAR     |serial number of the SFP
        manufacturer               |1*255VCHAR     |SFP vendor name
        model                      |1*255VCHAR     |SFP model name
        connector                  |1*255VCHAR     |connector information
        encoding                   |1*255VCHAR     |encoding information
        ext_identifier             |1*255VCHAR     |extend identifier
        ext_rateselect_compliance  |1*255VCHAR     |extended rateSelect compliance
        cable_length               |INT            |cable length in m
        nominal_bit_rate           |INT            |nominal bit rate by 100Mbs
        specification_compliance   |1*255VCHAR     |specification compliance
        vendor_date                |1*255VCHAR     |vendor date
        vendor_oui                 |1*255VCHAR     |vendor OUI
        application_advertisement  |1*255VCHAR     |supported applications advertisement
        ================================================================================
        """
        raise NotImplementedError

    def get_transceiver_bulk_status(self):
        """
        Retrieves transceiver bulk status of this SFP

        Returns:
            A dict which contains following keys/values :
        ========================================================================
        keys                       |Value Format   |Information
        ---------------------------|---------------|----------------------------
        rx_los                     |BOOLEAN        |RX loss-of-signal status, True if has RX los, False if not.
        tx_fault                   |BOOLEAN        |TX fault status, True if has TX fault, False if not.
        reset_status               |BOOLEAN        |reset status, True if SFP in reset, False if not.
        lp_mode                    |BOOLEAN        |low power mode status, True in lp mode, False if not.
        temperature                |INT            |module temperature in Celsius
        voltage                    |INT            |supply voltage in mV
        tx<n>bias                  |INT            |TX Bias Current in mA, n is the channel number,
                                   |               |for example, tx2bias stands for tx bias of channel 2.
        rx<n>power                 |INT            |received optical power in mW, n is the channel number,
                                   |               |for example, rx2power stands for rx power of channel 2.
        tx<n>power                 |INT            |TX output power in mW, n is the channel number,
                                   |               |for example, tx2power stands for tx power of channel 2.
        ========================================================================
        """
        raise NotImplementedError

    def get_transceiver_threshold_info(self):
        """
        Retrieves transceiver threshold info of this SFP

        Returns:
            A dict which contains following keys/values :
        ========================================================================
        keys                       |Value Format   |Information
        ---------------------------|---------------|----------------------------
        temphighalarm              |FLOAT          |High Alarm Threshold value of temperature in Celsius.
        templowalarm               |FLOAT          |Low Alarm Threshold value of temperature in Celsius.
        temphighwarning            |FLOAT          |High Warning Threshold value of temperature in Celsius.
        templowwarning             |FLOAT          |Low Warning Threshold value of temperature in Celsius.
        vcchighalarm               |FLOAT          |High Alarm Threshold value of supply voltage in mV.
        vcclowalarm                |FLOAT          |Low Alarm Threshold value of supply voltage in mV.
        vcchighwarning             |FLOAT          |High Warning Threshold value of supply voltage in mV.
        vcclowwarning              |FLOAT          |Low Warning Threshold value of supply voltage in mV.
        rxpowerhighalarm           |FLOAT          |High Alarm Threshold value of received power in dBm.
        rxpowerlowalarm            |FLOAT          |Low Alarm Threshold value of received power in dBm.
        rxpowerhighwarning         |FLOAT          |High Warning Threshold value of received power in dBm.
        rxpowerlowwarning          |FLOAT          |Low Warning Threshold value of received power in dBm.
        txpowerhighalarm           |FLOAT          |High Alarm Threshold value of transmit power in dBm.
        txpowerlowalarm            |FLOAT          |Low Alarm Threshold value of transmit power in dBm.
        txpowerhighwarning         |FLOAT          |High Warning Threshold value of transmit power in dBm.
        txpowerlowwarning          |FLOAT          |Low Warning Threshold value of transmit power in dBm.
        txbiashighalarm            |FLOAT          |High Alarm Threshold value of tx Bias Current in mA.
        txbiaslowalarm             |FLOAT          |Low Alarm Threshold value of tx Bias Current in mA.
        txbiashighwarning          |FLOAT          |High Warning Threshold value of tx Bias Current in mA.
        txbiaslowwarning           |FLOAT          |Low Warning Threshold value of tx Bias Current in mA.
        ========================================================================
        """
        raise NotImplementedError

    def get_reset_status(self):
        """
        Retrieves the reset status of SFP

        Returns:
            A Boolean, True if reset enabled, False if disabled
        """
        raise NotImplementedError

    def get_rx_los(self):
        """
        Retrieves the RX LOS (loss-of-signal) status of SFP

        Returns:
            A list of boolean values, representing the RX LOS status
            of each available channel, value is True if SFP channel
            has RX LOS, False if not.
            E.g., for a tranceiver with four channels: [False, False, True, False]
            Note : RX LOS status is latched until a call to get_rx_los or a reset.
        """
        raise NotImplementedError

    def get_tx_fault(self):
        """
        Retrieves the TX fault status of SFP

        Returns:
            A list of boolean values, representing the TX fault status
            of each available channel, value is True if SFP channel
            has TX fault, False if not.
            E.g., for a tranceiver with four channels: [False, False, True, False]
            Note : TX fault status is lached until a call to get_tx_fault or a reset.
        """
        raise NotImplementedError

    def get_tx_disable(self):
        """
        Retrieves the tx_disable status of this SFP

        Returns:
            A list of boolean values, representing the TX disable status
            of each available channel, value is True if SFP channel
            is TX disabled, False if not.
            E.g., for a tranceiver with four channels: [False, False, True, False]
        """
        raise NotImplementedError

    def get_tx_disable_channel(self):
        """
        Retrieves the TX disabled channels in this SFP

        Returns:
            A hex of 4 bits (bit 0 to bit 3 as channel 0 to channel 3) to represent
            TX channels which have been disabled in this SFP.
            As an example, a returned value of 0x5 indicates that channel 0
            and channel 2 have been disabled.
        """
        raise NotImplementedError

    def get_lpmode(self):
        """
        Retrieves the lpmode (low power mode) status of this SFP

        Returns:
            A Boolean, True if lpmode is enabled, False if disabled
        """
        raise NotImplementedError

    def get_power_override(self):
        """
        Retrieves the power-override status of this SFP

        Returns:
            A Boolean, True if power-override is enabled, False if disabled
        """
        raise NotImplementedError

    def get_temperature(self):
        """
        Retrieves the temperature of this SFP

        Returns:
            A float representing the current temperature in Celsius
        """
        raise NotImplementedError


    def get_voltage(self):
        """
        Retrieves the supply voltage of this SFP

        Returns:
            A float representing the supply voltage in mV
        """
        raise NotImplementedError

    def get_tx_bias(self):
        """
        Retrieves the TX bias current of all SFP channels

        Returns:
            A list of floats, representing TX bias in mA
            for each available channel
            E.g., for a tranceiver with four channels: ['110.09', '111.12', '108.21', '112.09']
        """
        raise NotImplementedError

    def get_rx_power(self):
        """
        Retrieves the received optical power of all SFP channels

        Returns:
            A list of floats, representing received optical
            power in mW for each available channel
            E.g., for a tranceiver with four channels: ['1.77', '1.71', '1.68', '1.70']
        """
        raise NotImplementedError

    def get_tx_power(self):
        """
        Retrieves the TX power of all SFP channels

        Returns:
            A list of floats, representing TX power in mW
            for each available channel
            E.g., for a tranceiver with four channels: ['1.86', '1.86', '1.86', '1.86']
        """
        raise NotImplementedError

    def reset(self):
        """
        Reset SFP and return all user module settings to their default srate.

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError

    def tx_disable(self, tx_disable):
        """
        Disable SFP TX for all channels

        Args:
            tx_disable : A Boolean, True to enable tx_disable mode, False to disable
                         tx_disable mode.

        Returns:
            A boolean, True if tx_disable is set successfully, False if not
        """
        raise NotImplementedError

    def tx_disable_channel(self, channel, disable):
        """
        Sets the tx_disable for specified SFP channels

        Args:
            channel : A hex of 4 bits (bit 0 to bit 3) which represent channel 0 to 3,
                      e.g. 0x5 for channel 0 and channel 2.
            disable : A boolean, True to disable TX channels specified in channel,
                      False to enable

        Returns:
            A boolean, True if successful, False if not
        """
        raise NotImplementedError

    def set_lpmode(self, lpmode):
        """
        Sets the lpmode (low power mode) of SFP

        Args:
            lpmode: A Boolean, True to enable lpmode, False to disable it
            Note  : lpmode can be overridden by set_power_override

        Returns:
            A boolean, True if lpmode is set successfully, False if not
        """
        raise NotImplementedError

    def set_power_override(self, power_override, power_set):
        """
        Sets SFP power level using power_override and power_set

        Args:
            power_override :
                    A Boolean, True to override set_lpmode and use power_set
                    to control SFP power, False to disable SFP power control
                    through power_override/power_set and use set_lpmode
                    to control SFP power.
            power_set :
                    Only valid when power_override is True.
                    A Boolean, True to set SFP to low power mode, False to set
                    SFP to high power mode.

        Returns:
            A boolean, True if power-override and power_set are set successfully,
            False if not
        """
        raise NotImplementedError

    def read_eeprom(self, offset, num_bytes):
        """
        read eeprom specfic bytes beginning from a random offset with size as num_bytes

        Args:
             offset :
                     Integer, the offset from which the read transaction will start
             num_bytes:
                     Integer, the number of bytes to be read

        Returns:
            bytearray, if raw sequence of bytes are read correctly from the offset of size num_bytes
            None, if the read_eeprom fails
        """
        raise NotImplementedError

    def read_eeprom_by_page(self, page, offset, size, wire_addr=None):
        """
        Read EEPROM by page

        Args:
            page: EEPROM page number. Raise ValueError for invalid page.
            offset: EEPROM page offset. Raise ValueError for invalid offset.
            size: Number of bytes to be read. Raise ValueError for invalid size.
            wire_addr: Wire address. Only valid for sff8472. Raise ValueError for invalid wire address.

        Returns:
            A string contains the hex format EEPROM data.
        """
        raise NotImplementedError

    def write_eeprom(self, offset, num_bytes, write_buffer):
        """
        write eeprom specific bytes beginning from a random offset with size as num_bytes
        and write_buffer as the required bytes

        Args:
             offset :
                     Integer, the offset from which the read transaction will start
             num_bytes:
                     Integer, the number of bytes to be written
             write_buffer:
                     bytearray, raw bytes buffer which is to be written beginning at the offset

        Returns:
            a Boolean, true if the write succeeded and false if it did not succeed.
        """
        raise NotImplementedError

    def write_eeprom_by_page(self, page, offset, data, wire_addr=None):
        """
        Write EEPROM by page

        Args:
            page: EEPROM page number. Raise ValueError for invalid page.
            offset: EEPROM page offset. Raise ValueError for invalid offset.
            data: bytearray EEPROM data.
            wire_addr: Wire address. Only valid for sff8472. Raise ValueError for invalid wire address.

        Returns:
            True if write successfully else False
        """
        raise NotImplementedError

    def get_error_description(self):
        """
        Retrives the error descriptions of the SFP module

        Returns:
            String that represents the current error descriptions of vendor specific errors
            In case there are multiple errors, they should be joined by '|',
            like: "Bad EEPROM|Unsupported cable"
        """
        raise NotImplementedError

    def refresh_xcvr_api(self):
        """
        Updates the XcvrApi associated with this SFP
        """
        self._xcvr_api = self._xcvr_api_factory.create_xcvr_api()

    def get_xcvr_api(self):
        """
        Retrieves the XcvrApi associated with this SFP

        Returns:
            An object derived from XcvrApi that corresponds to the SFP
        """
        if self._xcvr_api is None:
            self.refresh_xcvr_api()
        return self._xcvr_api
