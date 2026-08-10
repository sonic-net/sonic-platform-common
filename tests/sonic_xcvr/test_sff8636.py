from mock import MagicMock, patch
import pytest
import random
import traceback

from sonic_platform_base.sonic_xcvr.api.public.sff8636 import Sff8636Api
from sonic_platform_base.sonic_xcvr.codes.public.sff8636 import Sff8636Codes
from sonic_platform_base.sonic_xcvr.mem_maps.public.sff8636 import Sff8636MemMap
from sonic_platform_base.sonic_xcvr.xcvr_eeprom import XcvrEeprom
from sonic_platform_base.sonic_xcvr.fields import consts

class TestSff8636(object):
    codes = Sff8636Codes
    mem_map = Sff8636MemMap(codes)
    reader = MagicMock(return_value=None)
    writer = MagicMock()
    eeprom = XcvrEeprom(reader, writer, mem_map)
    api = Sff8636Api(eeprom)

    def test_api(self):
        """
        Verify all api access valid fields
        """
        self.api.get_model()
        self.api.get_serial()
        self.api.get_transceiver_info()
        self.api.get_transceiver_dom_real_value()
        self.api.get_transceiver_threshold_info()
        self.api.get_transceiver_status()
        self.api.get_rx_los()
        self.api.get_tx_fault()
        self.api.get_tx_disable()
        self.api.get_tx_disable_channel()
        self.api.get_module_temperature()
        self.api.get_voltage()
        self.api.get_tx_bias()
        self.api.get_tx_power()
        self.api.get_rx_power()
        self.api.tx_disable(True)
        self.api.tx_disable_channel(0x5, True)
        self.api.get_power_override()
        self.api.get_power_set()
        self.reader.return_value = bytearray([0xFF])
        self.api.set_power_override(True, True)
        self.reader.return_value = None
        self.api.is_flat_memory()
        self.api.get_tx_power_support()
        self.api.get_rx_power_support()
        self.api.is_copper()
        self.api.get_temperature_support()
        self.api.get_voltage_support()
        self.api.get_rx_los_support()
        self.api.get_tx_bias_support()
        self.api.get_tx_fault_support()
        self.api.get_tx_disable_support()
        self.api.get_transceiver_thresholds_support()
        self.api.get_lpmode_support()
        self.api.get_power_override_support()
        self.api.set_lpmode(True)
        self.api.get_lpmode()

    @pytest.mark.parametrize("mock_response, expected", [
        (bytearray([0x0]), "Power Class 1 Module (1.5W max.)"),
        (bytearray([0x40]), "Power Class 2 Module (2.0W max.)"),
        (bytearray([0x80]), "Power Class 3 Module (2.5W max.)"),
        (bytearray([0xC0]), "Power Class 4 Module (3.5W max.)"),
        (bytearray([0xC1]), "Power Class 5 Module (4.0W max.)"),
        (bytearray([0xC2]), "Power Class 6 Module (4.5W max.)"),
        (bytearray([0xC3]), "Power Class 7 Module (5.0W max.)"),
        (bytearray([0x20]), "Power Class 8 Module")
    ])
    def test_power_class(self, mock_response, expected):
        self.api.xcvr_eeprom.reader = MagicMock()
        self.api.xcvr_eeprom.reader.return_value = mock_response
        result = self.api.xcvr_eeprom.read(consts.POWER_CLASS_FIELD)
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected", [
       (bytearray([0x02, 0x0]), "Longwave laser (LC)"),
       (bytearray([0x01, 0x0]), "Electrical inter-enclosure (EN)"),
       (bytearray([0x0, 0x80]), "Electrical intra-enclosure"),
       (bytearray([0x0, 0x40]), "Shortwave laser w/o OFC (SN)"),
       (bytearray([0x0, 0x20]), "Shortwave laser w OFC (SL)"),
       (bytearray([0x0, 0x10]), "Longwave Laser (LL)")
    ])
    def test_fiber_channel_transmitter_tech(self, mock_response, expected):
        self.api.xcvr_eeprom.reader = MagicMock()
        self.api.xcvr_eeprom.reader.return_value = mock_response
        result = self.api.xcvr_eeprom.read(consts.FIBRE_CHANNEL_TRANSMITTER_TECH_FIELD)
        assert result == expected

    def test_is_copper(self):
        with patch.object(self.api, 'xcvr_eeprom') as mock_eeprom:
            mock_eeprom.read = MagicMock()
            mock_eeprom.read.return_value = None
            assert self.api.is_copper() is None
            mock_eeprom.read.return_value = '40GBASE-CR4'
            assert self.api.is_copper()
            self.api._is_copper = None
            mock_eeprom.read.return_value = 'SR'
            assert not self.api.is_copper()

    def test_simulate_copper(self):
        with patch.object(self.api, 'is_copper', return_value=True):
            assert self.api.get_rx_power() == ['N/A'] * self.api.NUM_CHANNELS
            assert self.api.get_tx_bias() == ['N/A'] * self.api.NUM_CHANNELS
            assert self.api.get_rx_los() == ['N/A'] * self.api.NUM_CHANNELS
            assert not self.api.get_tx_power_support()
            assert not self.api.get_rx_power_support()
            assert not self.api.get_tx_bias_support()
            assert not self.api.get_rx_los_support()
            assert not self.api.get_temperature_support()
            assert not self.api.get_voltage_support()

    def test_random_read_fail(self):
        def mock_read_raw(offset, size):
            i = random.randint(0, 1)
            return None if i == 0 else b'0' * size

        self.api.xcvr_eeprom.reader = mock_read_raw

        run_num = 5
        while run_num > 0:
            try:
                self.api.get_transceiver_dom_real_value()
                self.api.get_transceiver_info()
                self.api.get_transceiver_threshold_info()
            except:
                assert 0, traceback.format_exc()
            run_num -= 1

    def test_get_lpmode(self):
        self.api.get_lpmode_support = MagicMock()
        self.api.get_lpmode_support.return_value = True
        self.api.get_power_override_support = MagicMock()
        self.api.get_power_override_support.return_value = True
        self.api.get_power_set = MagicMock()
        self.api.get_power_set.return_value = True
        self.api.get_power_override = MagicMock()
        self.api.get_power_override.return_value = True
        assert self.api.get_lpmode()
        self.api.get_power_set.return_value = False
        self.api.get_power_override.return_value = True
        assert not self.api.get_lpmode()
        self.api.get_lpmode_support.return_value = False
        self.api.get_power_override_support.return_value = False
        assert not self.api.get_lpmode()

    def test_set_lpmode(self):
        self.api.get_lpmode_support = MagicMock()
        self.api.get_lpmode_support.return_value = True
        self.api.get_power_override_support = MagicMock()
        self.api.get_power_override_support.return_value = True
        self.api.set_power_override = MagicMock()
        self.api.set_power_override.return_value = True
        assert self.api.set_lpmode(True)
        assert self.api.set_lpmode(False)
        self.api.get_lpmode_support.return_value = False
        self.api.get_power_override_support.return_value = False
        assert not self.api.set_lpmode(True)

    def test_set_high_power_class(self):
        with patch.object(self.api, 'xcvr_eeprom'):
            # Test low power class
            assert self.api.set_high_power_class(1, True)

            # Test high power class 5-7
            assert self.api.set_high_power_class(5, True)

            # Test high power class 8
            assert self.api.set_high_power_class(8, True)

            # Test high power class disable
            assert self.api.set_high_power_class(8, False)

    def test_get_power_class(self):
        with patch.object(self.api, 'xcvr_eeprom') as mock_eeprom:
            mock_eeprom.read = MagicMock()

            mock_eeprom.read.return_value = "Power Class 1 Module (1.5W max.)"
            assert self.api.get_power_class() == 1

            # Invalid power class
            mock_eeprom.read.return_value = "Power Class 9 Module (555.5W max.)"
            assert self.api.get_power_class() is None

            # Invalid power class string
            mock_eeprom.read.return_value = "XXX Power Class 1 Module (1.5W max.)"
            assert self.api.get_power_class() is None

            mock_eeprom.read.return_value = "XYZ"
            assert self.api.get_power_class() is None

            mock_eeprom.read.return_value = None
            assert self.api.get_power_class() is None

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                0,
                [False, False, False, False]
            ],
            {
                "tx_disabled_channel": 0,
                "tx1disable": False,
                "tx2disable": False,
                "tx3disable": False,
                "tx4disable": False,
            }
        ),
        (
            [
                None,
                None
            ],
            None
        )
    ])
    def test_get_transceiver_status(self, mock_response, expected):
        self.api.get_tx_disable_channel = MagicMock()
        self.api.get_tx_disable_channel.return_value = mock_response[0]
        self.api.get_tx_disable = MagicMock()
        self.api.get_tx_disable.return_value = mock_response[1]
        result = self.api.get_transceiver_status()
        assert result == expected

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                [False, False, False, False],
                [False, False, False, False],
            ],
            {
                'tx1fault': False,
                'tx2fault': False,
                'tx3fault': False,
                'tx4fault': False,
                'rx1los': False,
                'rx2los': False,
                'rx3los': False,
                'rx4los': False,
            }
        ),
        (
            [
                None,
                None
            ],
            None
        )
    ])
    def test_get_transceiver_status_flags(self, mock_response, expected):
        self.api.get_rx_los = MagicMock()
        self.api.get_rx_los.return_value = mock_response[0]
        self.api.get_tx_fault = MagicMock()
        self.api.get_tx_fault.return_value = mock_response[1]
        result = self.api.get_transceiver_status_flags()
        assert result == expected

    # SFF-8636 Rev 2.12 Table 6-6 bit layout, shared by both flag bytes:
    #   bit 7 = L-High Alarm
    #   bit 6 = L-Low Alarm
    #   bit 5 = L-High Warning
    #   bit 4 = L-Low Warning
    # Byte 6 bits 3-2 are reserved and bits 1-0 are TC readiness /
    # initialization complete; byte 7 bits 3-0 are reserved.
    @pytest.mark.parametrize(
        "temp_support, vcc_support, eeprom, expected, expected_reads",
        [
            (
                # both monitors advertised (byte 220 bits 5 and 4 set)
                True, True,
                {
                    consts.TEMP_FLAGS_FIELD: 0b1010_0000,  # high alarm + high warning
                    consts.VCC_FLAGS_FIELD: 0b0101_0000,   # low alarm + low warning
                },
                {
                    "tempHAlarm": True,
                    "tempLAlarm": False,
                    "tempHWarn": True,
                    "tempLWarn": False,
                    "vccHAlarm": False,
                    "vccLAlarm": True,
                    "vccHWarn": False,
                    "vccLWarn": True,
                },
                [consts.TEMP_FLAGS_FIELD, consts.VCC_FLAGS_FIELD],
            ),
            (
                # both monitors advertised, no flags asserted: 0x00 is a real
                # "no excursion" result and must still report all eight keys
                True, True,
                {consts.TEMP_FLAGS_FIELD: 0b0000_0000, consts.VCC_FLAGS_FIELD: 0b0000_0000},
                {
                    "tempHAlarm": False,
                    "tempLAlarm": False,
                    "tempHWarn": False,
                    "tempLWarn": False,
                    "vccHAlarm": False,
                    "vccLAlarm": False,
                    "vccHWarn": False,
                    "vccLWarn": False,
                },
                [consts.TEMP_FLAGS_FIELD, consts.VCC_FLAGS_FIELD],
            ),
            (
                # temperature monitoring not implemented (byte 220 bit 5 clear):
                # the temp flag byte must not be read or reported at all
                False, True,
                {consts.VCC_FLAGS_FIELD: 0b1000_0000},
                {
                    "vccHAlarm": True,
                    "vccLAlarm": False,
                    "vccHWarn": False,
                    "vccLWarn": False,
                },
                [consts.VCC_FLAGS_FIELD],
            ),
            (
                # supply voltage monitoring not implemented (byte 220 bit 4 clear)
                True, False,
                {consts.TEMP_FLAGS_FIELD: 0b0001_0000},
                {
                    "tempHAlarm": False,
                    "tempLAlarm": False,
                    "tempHWarn": False,
                    "tempLWarn": True,
                },
                [consts.TEMP_FLAGS_FIELD],
            ),
            # neither monitor implemented (e.g. a copper cable): nothing is
            # read and nothing is claimed, so xcvrd posts no DOM flags
            (False, False, {}, {}, []),
            # EEPROM read failure of a flag byte drops only that group; the
            # other group is still reported and the absent keys render as N/A
            # rather than as a False that was never measured
            (
                True, True,
                {consts.TEMP_FLAGS_FIELD: None, consts.VCC_FLAGS_FIELD: 0},
                {
                    "vccHAlarm": False,
                    "vccLAlarm": False,
                    "vccHWarn": False,
                    "vccLWarn": False,
                },
                [consts.TEMP_FLAGS_FIELD, consts.VCC_FLAGS_FIELD],
            ),
            (
                True, True,
                {consts.TEMP_FLAGS_FIELD: 0, consts.VCC_FLAGS_FIELD: None},
                {
                    "tempHAlarm": False,
                    "tempLAlarm": False,
                    "tempHWarn": False,
                    "tempLWarn": False,
                },
                [consts.TEMP_FLAGS_FIELD, consts.VCC_FLAGS_FIELD],
            ),
            # read failure of the monitor advertisement itself is treated as
            # "not implemented": that group is skipped, its flag byte is never
            # read, and both cases render as N/A, so an unreadable
            # advertisement cannot be mistaken for a measured in-limits result
            (
                None, True,
                {consts.VCC_FLAGS_FIELD: 0b0000_0000},
                {
                    "vccHAlarm": False,
                    "vccLAlarm": False,
                    "vccHWarn": False,
                    "vccLWarn": False,
                },
                [consts.VCC_FLAGS_FIELD],
            ),
            (
                # a latched temperature alarm survives an unrelated failure of
                # the voltage advertisement: no group is discarded on account
                # of another group's failure
                True, None,
                {consts.TEMP_FLAGS_FIELD: 0b1000_0000},
                {
                    "tempHAlarm": True,
                    "tempLAlarm": False,
                    "tempHWarn": False,
                    "tempLWarn": False,
                },
                [consts.TEMP_FLAGS_FIELD],
            ),
        ],
    )
    def test_get_transceiver_dom_flags(self, temp_support, vcc_support, eeprom,
                                       expected, expected_reads):
        self.api.get_temperature_support = MagicMock(return_value=temp_support)
        self.api.get_voltage_support = MagicMock(return_value=vcc_support)

        # Key the mock on the field name rather than call order, so a swapped
        # or mis-mapped field would fail instead of silently passing. Raw
        # bytes are decoded through the real mem map field so the bitdecode
        # bit positions are exercised, not just the API plumbing.
        def read_field(field):
            raw = eeprom[field]
            if raw is None:
                return None
            return self.mem_map.get_field(field).decode(bytearray([raw]))
        self.api.xcvr_eeprom.read = MagicMock(side_effect=read_field)

        result = self.api.get_transceiver_dom_flags()

        assert result == expected
        # The flag latches clear on read: each advertised byte must be read
        # exactly once per call, in a single whole-byte access, and a byte
        # whose monitor is not advertised must not be read at all.
        assert [c.args[0] for c in self.api.xcvr_eeprom.read.call_args_list] == expected_reads

    def test_dom_flag_fields_map_to_table_6_6_bytes(self):
        """TempFlags/VccFlags must resolve to lower page 00h bytes 6 and 7."""
        assert self.mem_map.get_field(consts.TEMP_FLAGS_FIELD).get_offset() == 6
        assert self.mem_map.get_field(consts.TEMP_FLAGS_FIELD).get_size() == 1
        assert self.mem_map.get_field(consts.VCC_FLAGS_FIELD).get_offset() == 7
        assert self.mem_map.get_field(consts.VCC_FLAGS_FIELD).get_size() == 1

    @pytest.mark.parametrize("mock_response, expected",[
        (
            [
                50,
                3.3,
                [70, 70, 70, 70],
                [0.1, 0.1, 0.1, 0.1],
                [0.1, 0.1, 0.1, 0.1],
                True, True, True, True, True, True
            ],
            {
                'temperature': 50,
                'voltage': 3.3,
                'tx1power': -10.0, 'tx2power': -10.0, 'tx3power': -10.0, 'tx4power': -10.0,
                'rx1power': -10.0, 'rx2power': -10.0, 'rx3power': -10.0, 'rx4power': -10.0,
                'tx1bias': 70, 'tx2bias': 70, 'tx3bias': 70, 'tx4bias': 70,
            }
        )
    ])
    def test_get_transceiver_dom_real_value(self, mock_response, expected):
        self.api.get_module_temperature = MagicMock()
        self.api.get_module_temperature.return_value = mock_response[0]
        self.api.get_voltage = MagicMock()
        self.api.get_voltage.return_value = mock_response[1]
        self.api.get_tx_bias = MagicMock()
        self.api.get_tx_bias.return_value = mock_response[2]
        self.api.get_rx_power = MagicMock()
        self.api.get_rx_power.return_value = mock_response[3]
        self.api.get_tx_power = MagicMock()
        self.api.get_tx_power.return_value = mock_response[4]
        self.api.get_rx_los_support = MagicMock()
        self.api.get_rx_los_support.return_value = mock_response[5]
        self.api.get_tx_fault_support = MagicMock()
        self.api.get_tx_fault_support.return_value = mock_response[6]
        self.api.get_tx_disable_support = MagicMock()
        self.api.get_tx_disable_support.return_value = mock_response[7]
        self.api.get_tx_bias_support = MagicMock()
        self.api.get_tx_bias_support.return_value = mock_response[8]
        self.api.get_tx_power_support = MagicMock()
        self.api.get_tx_power_support.return_value = mock_response[9]
        self.api.get_rx_power_support = MagicMock()
        self.api.get_rx_power_support.return_value = mock_response[10]
        result = self.api.get_transceiver_dom_real_value()
        assert result == expected

