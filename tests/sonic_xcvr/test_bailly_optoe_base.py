import os
import json
import pytest
from unittest.mock import mock_open, patch, MagicMock
from sonic_platform_base.sonic_xcvr.bailly_optoe_base import (
    CpoOptoeBase,
    get_cpo_json_data
)

# Mock CPO JSON data for testing
MOCK_CPO_JSON = {
    "oes": {
        "oe0": {
            "oe_cmis_path": "/sys/bus/i2c/devices/0-0050/"
        }
    },
    "elss": {
        "els0": {
            "index": "0",
            "els_presence": {
                "presence_file": "/sys/class/gpio/gpio123/value",
                "presence_offset": "0x00",
                "presence_len": 1,
                "presence_bit": 0,
                "presence_value": 1
            }
        }
    }
}

@pytest.fixture
def cpo_instance():
    """Fixture to create a CpoOptoeBase instance with test attributes"""
    instance = CpoOptoeBase()
    instance._oe_id = 0
    instance._els_id = 0
    instance._port_id = 0
    return instance

@pytest.fixture
def mock_platform_info():
    """Fixture to mock platform info retrieval"""
    with patch("sonic_platform_base.sonic_xcvr.bailly_optoe_base.get_platform") as mock_get_platform:
        with patch("sonic_platform_base.sonic_xcvr.bailly_optoe_base.get_path_to_platform_dir") as mock_get_path:
            mock_get_platform.return_value = "test_platform"
            mock_get_path.return_value = "/usr/share/sonic/device/test_platform"
            yield

class TestCpoOptoeBase:
    def test_get_cpo_json_data_success(self, mock_platform_info):
        """Test successful retrieval of CPO JSON data"""
        mock_json_path = os.path.join("/usr/share/sonic/device/test_platform", "cpo.json")
        
        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(MOCK_CPO_JSON))):
                result = get_cpo_json_data()
                assert result == MOCK_CPO_JSON
                open.assert_called_once_with(mock_json_path, 'r')

    def test_get_cpo_json_data_platform_none(self):
        """Test get_cpo_json_data when platform is None"""
        with patch("sonic_platform_base.sonic_xcvr.bailly_optoe_base.get_platform", return_value=None):
            assert get_cpo_json_data() is None

    def test_get_cpo_json_data_path_none(self):
        """Test get_cpo_json_data when platform path is None"""
        with patch("sonic_platform_base.sonic_xcvr.bailly_optoe_base.get_platform", return_value="test_platform"):
            with patch("sonic_platform_base.sonic_xcvr.bailly_optoe_base.get_path_to_platform_dir", return_value=None):
                assert get_cpo_json_data() is None

    def test_get_cpo_json_data_file_not_exists(self, mock_platform_info):
        """Test get_cpo_json_data when JSON file doesn't exist"""
        with patch("os.path.isfile", return_value=False):
            assert get_cpo_json_data() is None

    def test_get_cpo_json_data_invalid_json(self, mock_platform_info):
        """Test get_cpo_json_data with invalid JSON content"""
        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", mock_open(read_data="invalid json")):
                assert get_cpo_json_data() is None

    def test_get_oe_eeprom_path(self, cpo_instance, mock_platform_info):
        """Test EEPROM path generation"""
        with patch("sonic_platform_base.sonic_xcvr.bailly_optoe_base.get_cpo_json_data", return_value=MOCK_CPO_JSON):
            assert cpo_instance.get_oe_eeprom_path() == "/sys/bus/i2c/devices/0-0050/eeprom"

    def test_get_oe_eeprom_path_none(self, cpo_instance, mock_platform_info):
        """Test EEPROM path when config is missing"""
        mock_empty_json = {"oes": {"oe0": {}}}
        with patch("sonic_platform_base.sonic_xcvr.bailly_optoe_base.get_cpo_json_data", return_value=mock_empty_json):
            assert cpo_instance.get_oe_eeprom_path() is None

    def test_read_eeprom_success(self, cpo_instance, mock_platform_info):
        """Test successful EEPROM read operation"""
        mock_data = b'\x01\x02\x03'
        with patch.object(cpo_instance, "get_eeprom_path", return_value="/fake/eeprom"):
            with patch("builtins.open", mock_open(read_data=mock_data)) as mock_file:
                result = cpo_instance.read_eeprom(0, 3)
                assert result == bytearray(mock_data)
                mock_file.assert_called_once_with("/fake/eeprom", mode='rb', buffering=0)
                mock_file.return_value.seek.assert_called_once_with(0)
                mock_file.return_value.read.assert_called_once_with(3)

    def test_read_eeprom_error(self, cpo_instance, mock_platform_info):
        """Test EEPROM read operation with IO error"""
        with patch.object(cpo_instance, "get_eeprom_path", return_value="/fake/eeprom"):
            with patch("builtins.open", side_effect=OSError("Read error")):
                result = cpo_instance.read_eeprom(0, 3)
                assert result is None

    def test_write_eeprom_success(self, cpo_instance, mock_platform_info):
        """Test successful EEPROM write operation"""
        write_buffer = bytearray([0x01, 0x02, 0x03])
        with patch.object(cpo_instance, "get_eeprom_path", return_value="/fake/eeprom"):
            with patch("builtins.open", mock_open()) as mock_file:
                result = cpo_instance.write_eeprom(0, 3, write_buffer)
                assert result is True
                mock_file.assert_called_once_with("/fake/eeprom", mode='r+b', buffering=0)
                mock_file.return_value.seek.assert_called_once_with(0)
                mock_file.return_value.write.assert_called_once_with(write_buffer[0:3])

    def test_write_eeprom_error(self, cpo_instance, mock_platform_info):
        """Test EEPROM write operation with IO error"""
        write_buffer = bytearray([0x01, 0x02, 0x03])
        with patch.object(cpo_instance, "get_eeprom_path", return_value="/fake/eeprom"):
            with patch("builtins.open", side_effect=OSError("Write error")):
                result = cpo_instance.write_eeprom(0, 3, write_buffer)
                assert result is False

    def test_get_els_presence_success(self, cpo_instance, mock_platform_info):
        """Test ELS presence detection with valid data"""
        with patch("sonic_platform_base.sonic_xcvr.bailly_optoe_base.get_cpo_json_data", return_value=MOCK_CPO_JSON):
            with patch("builtins.open", mock_open(read_data=b'\x01')) as mock_file:
                result = cpo_instance.get_els_presence()
                assert result is True
                mock_file.assert_called_once_with("/sys/class/gpio/gpio123/value", mode='rb', buffering=0)
                mock_file.return_value.seek.assert_called_once_with(0)

    def test_get_els_presence_mismatch(self, cpo_instance, mock_platform_info):
        """Test ELS presence detection with mismatched bit value"""
        with patch("sonic_platform_base.sonic_xcvr.bailly_optoe_base.get_cpo_json_data", return_value=MOCK_CPO_JSON):
            with patch("builtins.open", mock_open(read_data=b'\x00')) as mock_file:
                result = cpo_instance.get_els_presence()
                assert result is False

    def test_get_els_presence_error(self, cpo_instance, mock_platform_info):
        """Test ELS presence detection with IO error"""
        with patch("sonic_platform_base.sonic_xcvr.bailly_optoe_base.get_cpo_json_data", return_value=MOCK_CPO_JSON):
            with patch("builtins.open", side_effect=OSError("Read error")):
                result = cpo_instance.get_els_presence()
                assert result is False

    def test_get_els_base_page_invalid_type(self, cpo_instance, mock_platform_info):
        """Test get_els_base_page with non-int/non-string invalid type"""
        with pytest.raises(TypeError):
            mock_get_elss = lambda: {"base_page": [1, 2, 3]}
            cpo_instance.get_elss_config = mock_get_elss
            cpo_instance.get_els_base_page()

    def test_getter_methods(self, cpo_instance):
        """Test all getter methods return correct values"""
        cpo_instance._oe_bank_id = 1
        cpo_instance._oe_id = 2
        cpo_instance._els_bank_id = 3
        cpo_instance._els_id = 4
        
        assert cpo_instance.get_oe_bank_id() == 1
        assert cpo_instance.get_oe_id() == 2
        assert cpo_instance.get_els_bank_id() == 3
        assert cpo_instance.get_els_id() == 4

    def test_get_presence(self, cpo_instance, mock_platform_info):
        """Test presence method delegates to els presence"""
        with patch.object(cpo_instance, "get_els_presence", return_value=True):
            assert cpo_instance.get_presence() is True
        
        with patch.object(cpo_instance, "get_els_presence", return_value=False):
            assert cpo_instance.get_presence() is False

class TestCpoOptoeBaseAbstractMethods:
    """
    Unit tests for abstract methods in CpoOptoeBase class
    Follows SONiC community testing standards
    """
    def test_abstract_methods_raise_not_implemented(self):
        """Test that unimplemented abstract methods raise NotImplementedError"""
        # Create a minimal subclass that implements all abstract methods
        class MinimalCpoImpl(CpoOptoeBase):
            def check_fiber_dirty(self):
                return super().check_fiber_dirty()
            
            def check_calibration(self):
                return super().check_calibration()
            
            def is_els_power_sufficient(self):
                return super().is_els_power_sufficient()
            
            def is_calibration_checked(self):
                return super().is_calibration_checked()
            
            def is_fiber_checked(self):
                return super().is_fiber_checked()
            
            def is_els_tx_on(self):
                return super().is_els_tx_on()
            
            def is_els_tx_enabled(self):
                return super().is_els_tx_enabled()

        # Instantiate the subclass
        instance = MinimalCpoImpl()
        instance._oe_id = 0
        instance._els_id = 0
        instance._port_id = 0

        # Test each abstract method raises NotImplementedError
        with pytest.raises(NotImplementedError):
            instance.check_fiber_dirty()

        with pytest.raises(NotImplementedError):
            instance.check_calibration()

        with pytest.raises(NotImplementedError):
            instance.is_els_power_sufficient()

        with pytest.raises(NotImplementedError):
            instance.is_calibration_checked()

        with pytest.raises(NotImplementedError):
            instance.is_fiber_checked()

        with pytest.raises(NotImplementedError):
            instance.is_els_tx_on()

        with pytest.raises(NotImplementedError):
            instance.is_els_tx_enabled()

    def test_valid_subclass_implementation(self):
        """Test that a subclass with all abstract methods implemented works correctly"""
        class ValidCpoImpl(CpoOptoeBase):
            def __init__(self):
                super().__init__()
                self._oe_id = 0
                self._els_id = 0
                self._port_id = 0

            def check_fiber_dirty(self):
                return True
            
            def check_calibration(self):
                return True
            
            def is_els_power_sufficient(self):
                return True
            
            def is_calibration_checked(self):
                return True
            
            def is_fiber_checked(self):
                return True
            
            def is_els_tx_on(self):
                return True
            
            def is_els_tx_enabled(self):
                return True

        # Should instantiate without error
        instance = ValidCpoImpl()
        assert isinstance(instance, CpoOptoeBase)
        
        # All methods should return implemented values
        assert instance.check_fiber_dirty() is True
        assert instance.check_calibration() is True
        assert instance.is_els_power_sufficient() is True
        assert instance.is_calibration_checked() is True
        assert instance.is_fiber_checked() is True
        assert instance.is_els_tx_on() is True
        assert instance.is_els_tx_enabled() is True
