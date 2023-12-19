from unittest.mock import mock_open
from mock import patch 
from sonic_platform_base.sonic_xcvr.sfp_optoe_base import SfpOptoeBase 

class TestSfpOptoeBase(object): 
 
    sfp_optoe_api = SfpOptoeBase() 
 
    @patch("builtins.open", new_callable=mock_open)
    @patch.object(SfpOptoeBase, 'get_eeprom_path')
    def test_set_optoe_write_timeout_success(self, mock_get_eeprom_path, mock_open):
        mock_get_eeprom_path.return_value = "/sys/bus/i2c/devices/1-0050/eeprom"
        expected_path = "/sys/bus/i2c/devices/1-0050/write_timeout"
        expected_timeout = 1

        self.sfp_optoe_api.set_optoe_write_timeout(expected_timeout)

        mock_open.assert_called_once_with(expected_path, mode='w')
        mock_open().write.assert_called_once_with(str(expected_timeout))

    @patch("builtins.open", new_callable=mock_open)
    @patch.object(SfpOptoeBase, 'get_eeprom_path')
    def test_set_optoe_write_timeout_ioerror(self, mock_get_eeprom_path, mock_open):
        mock_get_eeprom_path.return_value = "/sys/bus/i2c/devices/1-0050/eeprom"
        expected_timeout = 1
        mock_open.side_effect = IOError

        self.sfp_optoe_api.set_optoe_write_timeout(expected_timeout)

        mock_open.assert_called()

    @patch("builtins.open", new_callable=mock_open)
    @patch.object(SfpOptoeBase, 'get_eeprom_path')
    def test_set_optoe_write_timeout_oserror(self, mock_get_eeprom_path, mock_open):
        mock_get_eeprom_path.return_value = "/sys/bus/i2c/devices/1-0050/eeprom"
        expected_timeout = 1
        mock_open.side_effect = OSError

        self.sfp_optoe_api.set_optoe_write_timeout(expected_timeout)

        mock_open.assert_called()
