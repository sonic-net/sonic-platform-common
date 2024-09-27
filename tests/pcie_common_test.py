import os
import sys
import yaml
from sonic_platform_base.sonic_pcie.pcie_common import PcieUtil

if sys.version_info.major == 3:
    from unittest import mock
    BUILTINS = 'builtins'
else:
    import mock
    BUILTINS = '__builtin__'

tests_dir = os.path.dirname(os.path.abspath(__file__))
pcie_config_file = os.path.join(tests_dir, 'pcie.yaml')

lspci_output = '''\
00:01.0 PCI A
00:02.0 PCI B
00:02.1 PCI C
01:00.0 PCI D
'''

lspci_ID_output = '''\
00:01.0 0001: 0000:000a
00:02.0 0002: 0000:000b
00:02.1 0003: 0000:000c
01:00.0 0004: 0000:000d
'''

pci_sysfs_paths = [
    '/sys/bus/pci/devices/0000:00:01.0',
    '/sys/bus/pci/devices/0000:00:02.0',
    '/sys/bus/pci/devices/0000:00:02.1',
    '/sys/bus/pci/devices/0000:01:00.0'
]

pcie_device_list = [
    {'bus': '00', 'dev': '01', 'fn': '0', 'id': '000a', 'name': 'PCI A'},
    {'bus': '00', 'dev': '02', 'fn': '0', 'id': '000b', 'name': 'PCI B'},
    {'bus': '00', 'dev': '02', 'fn': '1', 'id': '000c', 'name': 'PCI C'},
    {'bus': '01', 'dev': '00', 'fn': '0', 'id': '000d', 'name': 'PCI D'},
]

pcie_check_output = [
    {'bus': '00', 'dev': '01', 'fn': '0', 'id': '000a', 'name': 'PCI A', 'result': 'Passed'},
    {'bus': '00', 'dev': '02', 'fn': '0', 'id': '000b', 'name': 'PCI B', 'result': 'Passed'},
    {'bus': '00', 'dev': '02', 'fn': '1', 'id': '000c', 'name': 'PCI C', 'result': 'Passed'},
    {'bus': '01', 'dev': '00', 'fn': '0', 'id': '000d', 'name': 'PCI D', 'result': 'Passed'}
]

pcie_aer_correctable_content = '''\
RxErr 0
BadTLP 1
BadDLLP 2
Rollover 3
Timeout 4
NonFatalErr 5
CorrIntErr 6
HeaderOF 7
TOTAL_ERR_COR 28
'''

pcie_aer_fatal_content = '''\
Undefined 0
DLP 1
SDES 2
TLP 3
FCP 4
CmpltTO 5
CmpltAbrt 6
UnxCmplt 7
RxOF 8
MalfTLP 9
ECRC 0
UnsupReq 1
ACSViol 2
UncorrIntErr 3
BlockedTLP 4
AtomicOpBlocked 5
TLPBlockedErr 6
TOTAL_ERR_FATAL 66
'''

pcie_aer_nonfatal_content = '''\
Undefined 0
DLP 1
SDES 2
TLP 3
FCP 4
CmpltTO 5
CmpltAbrt 6
UnxCmplt 7
RxOF 8
MalfTLP 9
ECRC 0
UnsupReq 1
ACSViol 2
UncorrIntErr 3
BlockedTLP 4
AtomicOpBlocked 5
TLPBlockedErr 6
TOTAL_ERR_NONFATAL 66
'''

pcie_aer_stats = {
    'correctable': {
        'RxErr': '0', 'BadTLP': '1', 'BadDLLP': '2', 'Rollover': '3',
        'Timeout': '4', 'NonFatalErr': '5', 'CorrIntErr': '6', 'HeaderOF': '7',
        'TOTAL_ERR_COR': '28'
    },
    'fatal': {
        'Undefined': '0', 'DLP': '1', 'SDES': '2', 'TLP': '3', 'FCP': '4',
        'CmpltTO': '5', 'CmpltAbrt': '6', 'UnxCmplt': '7', 'RxOF': '8',
        'MalfTLP': '9', 'ECRC': '0', 'UnsupReq': '1', 'ACSViol': '2',
        'UncorrIntErr': '3', 'BlockedTLP': '4', 'AtomicOpBlocked': '5',
        'TLPBlockedErr': '6', 'TOTAL_ERR_FATAL': '66'
    },
    'non_fatal': {
        'Undefined': '0', 'DLP': '1', 'SDES': '2', 'TLP': '3', 'FCP': '4',
        'CmpltTO': '5', 'CmpltAbrt': '6', 'UnxCmplt': '7', 'RxOF': '8',
        'MalfTLP': '9', 'ECRC': '0', 'UnsupReq': '1', 'ACSViol': '2',
        'UncorrIntErr': '3', 'BlockedTLP': '4', 'AtomicOpBlocked': '5',
        'TLPBlockedErr': '6', 'TOTAL_ERR_NONFATAL': '66'
    },
}


class TestPcieCommon:

    @mock.patch('subprocess.Popen')
    def test_get_pcie_devices(self, subprocess_popen_mock):

        def subprocess_popen_side_effect(*args, **kwargs):
            if args[0] == ['sudo', 'lspci']:
                output = lspci_output.splitlines()
            elif args[0] == ['sudo', 'lspci', '-n']:
                output = lspci_ID_output.splitlines()

            popen_mock = mock.Mock()
            popen_attributes = {
                'returncode': 0,
                'communicate.return_value': ('', ''),
                'stdout.readlines.return_value': output
            }
            popen_mock.configure_mock(**popen_attributes)
            return popen_mock

        subprocess_popen_mock.side_effect = subprocess_popen_side_effect
        pcieutil = PcieUtil(tests_dir)
        result = pcieutil.get_pcie_device()
        assert result == pcie_device_list

    @mock.patch('subprocess.check_output')
    def test_check_pcie_deviceid(self, subprocess_check_output_mock):
        bus = "00"
        dev = "01"
        fn  = "1"
        id  = "0001"
        test_binary_file = b'\x01\x00\x00\x00'

        def subprocess_check_output_side_effect(*args, **kwargs):
            return ("0001".encode("utf-8"))

        subprocess_check_output_mock.side_effect = subprocess_check_output_side_effect

        pcieutil = PcieUtil(tests_dir)
        with mock.patch('builtins.open', new_callable=mock.mock_open, read_data=test_binary_file) as mock_fd:
            result = pcieutil.check_pcie_deviceid(bus, dev, fn, id)
            assert result == True

    def test_check_pcie_deviceid_mismatch(self):
        bus = "00"
        dev = "01"
        fn  = "1"
        id  = "0001"
        test_binary_file = b'\x02\x03\x00\x00'
        pcieutil = PcieUtil(tests_dir)
        with mock.patch('builtins.open', new_callable=mock.mock_open, read_data=test_binary_file) as mock_fd:
            result = pcieutil.check_pcie_deviceid(bus, dev, fn, id)
            assert result == False

    @mock.patch('os.path.exists')
    def test_get_pcie_check(self, os_path_exists_mock):

        def os_path_exists_side_effect(*args):
            return bool(args[0] in pci_sysfs_paths)

        os_path_exists_mock.side_effect = os_path_exists_side_effect
        pcieutil = PcieUtil(tests_dir)
        sample_pcie_config = yaml.dump(pcie_device_list)
        pcieutil.check_pcie_deviceid = mock.MagicMock()

        open_mock = mock.mock_open(read_data=sample_pcie_config)
        with mock.patch('{}.open'.format(BUILTINS), open_mock):
            result = pcieutil.get_pcie_check()
            open_mock.assert_called_once_with(pcie_config_file)
            assert result == pcie_check_output

    @mock.patch('os.path.isfile', mock.MagicMock(return_value=True))
    @mock.patch('{}.open'.format(BUILTINS))
    def test_get_pcie_aer_stats(self, open_mock):

        def open_mock_side_effect(*args):
            file_content = ''
            if os.path.dirname(args[0]) == pci_sysfs_paths[0]:
                file_name = os.path.basename(args[0])
                if file_name == 'aer_dev_correctable':
                    file_content = pcie_aer_correctable_content
                elif file_name == 'aer_dev_fatal':
                    file_content = pcie_aer_fatal_content
                elif file_name == 'aer_dev_nonfatal':
                    file_content = pcie_aer_nonfatal_content

            return mock.mock_open(read_data=file_content).return_value

        open_mock.side_effect = open_mock_side_effect
        pcieutil = PcieUtil(tests_dir)
        test_device = pcie_device_list[0]
        result = pcieutil.get_pcie_aer_stats(bus=int(test_device['bus']),
                                             dev=int(test_device['dev']),
                                             func=int(test_device['fn']))
        assert result == pcie_aer_stats

    @mock.patch('sonic_platform_base.sonic_pcie.pcie_common.PcieUtil.get_pcie_device', mock.MagicMock(return_value=pcie_device_list))
    def test_dump_conf_yaml(self):
        pcieutil = PcieUtil(tests_dir)

        # Verify pcie config path before writing to file
        open_mock = mock.mock_open()
        with mock.patch('{}.open'.format(BUILTINS), open_mock):
            pcieutil.dump_conf_yaml()
            open_mock.assert_called_once_with(pcie_config_file, 'w')

        pcieutil.dump_conf_yaml()
        with open(pcie_config_file) as fd:
            result = yaml.safe_load(fd)

        assert result == pcie_device_list

    @classmethod
    def teardown_class(cls):
        # Cleanup generated config
        if os.path.isfile(pcie_config_file):
            os.remove(pcie_config_file)
