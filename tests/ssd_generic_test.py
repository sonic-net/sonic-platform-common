
import sys
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

from sonic_platform_base.sonic_ssd.ssd_generic import SsdUtil

output_ssd = """smartctl 6.6 2017-11-05 r4594 [x86_64-linux-5.10.0-8-2-amd64] (local build)
Copyright (C) 2002-17, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===
Model Family:     3IE3/3ME3/3ME4 SSDs
Device Model:     (S42) 3IE3
Serial Number:    BCA11712280210689
LU WWN Device Id: 5 24693f 2ca215959
Firmware Version: S16425i
User Capacity:    16,013,942,784 bytes [16.0 GB]
Sector Size:      512 bytes logical/physical
Rotation Rate:    Solid State Device
Form Factor:      2.5 inches
Device is:        In smartctl database [for details use: -P show]
ATA Version is:   ATA8-ACS (minor revision not indicated)
SATA Version is:  SATA 3.0, 6.0 Gb/s (current: 6.0 Gb/s)
Local Time is:    Thu Mar 31 03:00:15 2022 UTC
SMART support is: Available - device has SMART capability.
SMART support is: Enabled

=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

General SMART Values:
Offline data collection status:  (0x00) Offline data collection activity
                                        was never started.
                                        Auto Offline Data Collection: Disabled.
Total time to complete Offline 
data collection:                (   32) seconds.
Offline data collection
capabilities:                    (0x00)         Offline data collection not supported.
SMART capabilities:            (0x0003) Saves SMART data before entering
                                        power-saving mode.
                                        Supports SMART auto save timer.
Error logging capability:        (0x00) Error logging NOT supported.
                                        No General Purpose Logging support.
SCT capabilities:              (0x0039) SCT Status supported.
                                        SCT Error Recovery Control supported.
                                        SCT Feature Control supported.
                                        SCT Data Table supported.

SMART Attributes Data Structure revision number: 16
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE
  1 Raw_Read_Error_Rate     0x0000   000   000   000    Old_age   Offline      -       0
  2 Throughput_Performance  0x0000   000   000   000    Old_age   Offline      -       0
  3 Spin_Up_Time            0x0000   000   000   000    Old_age   Offline      -       0
  5 Later_Bad_Block         0x0013   100   100   001    Pre-fail  Always       -       0
  7 Seek_Error_Rate         0x0000   000   000   000    Old_age   Offline      -       0
  8 Seek_Time_Performance   0x0000   000   000   000    Old_age   Offline      -       0
  9 Power_On_Hours          0x0002   030   000   000    Old_age   Always       -       26142
 10 Spin_Retry_Count        0x0000   000   000   000    Old_age   Offline      -       0
 12 Power_Cycle_Count       0x0002   148   000   000    Old_age   Always       -       7828
163 Total_Bad_Block_Count   0x0000   000   000   000    Old_age   Offline      -       8
168 SATA_PHY_Error_Count    0x0000   000   000   000    Old_age   Offline      -       0
169 Remaining_Lifetime_Perc 0x0000   095   000   000    Old_age   Offline      -       95
175 Bad_Cluster_Table_Count 0x0000   000   000   000    Old_age   Offline      -       0
192 Power-Off_Retract_Count 0x0000   000   000   000    Old_age   Offline      -       0
194 Temperature_Celsius     0x0000   030   100   000    Old_age   Offline      -       30 (2 100 0 0 0)
197 Current_Pending_Sector  0x0012   000   100   000    Old_age   Always       -       0
225 Data_Log_Write_Count    0x0000   000   029   000    Old_age   Offline      -       45712577
240 Write_Head              0x0000   000   000   000    Old_age   Offline      -       0
165 Max_Erase_Count         0x0002   220   001   000    Old_age   Always       -       988
167 Average_Erase_Count     0x0002   213   001   000    Old_age   Always       -       981
170 Spare_Block_Count       0x0003   100   001   000    Pre-fail  Always       -       146
171 Program_Fail_Count      0x0002   000   001   000    Old_age   Always       -       0
172 Erase_Fail_Count        0x0002   000   001   000    Old_age   Always       -       0
176 RANGE_RECORD_Count      0x0000   100   001   000    Old_age   Offline      -       0
187 Reported_Uncorrect      0x0002   000   001   000    Old_age   Always       -       0
229 Flash_ID                0x0002   100   001   000    Old_age   Always       -       0x517693943a98
232 Spares_Remaining_Perc   0x0003   100   001   000    Pre-fail  Always       -       0
235 Later_Bad_Blk_Inf_R/W/E 0x0002   000   000   000    Old_age   Always       -       0 0 0
241 Host_Writes_32MiB       0x0002   100   001   000    Old_age   Always       -       178564
242 Host_Reads_32MiB        0x0002   100   001   000    Old_age   Always       -       760991

SMART Error Log not supported

SMART Self-test Log not supported

Selective Self-tests/Logging not supported"""

output_Innodisk_ssd = """smartctl 6.6 2017-11-05 r4594 [x86_64-linux-4.19.0-12-2-amd64] (local build)
Copyright (C) 2002-17, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===
Model Family:     Innodisk 1ME3/3ME/3SE SSDs
Device Model:     InnoDisk Corp. - mSATA 3ME
Serial Number:    20171126AAAA11730156
Firmware Version: S140714
User Capacity:    32,017,047,552 bytes [32.0 GB]
Sector Size:      512 bytes logical/physical
Rotation Rate:    Solid State Device
Form Factor:      2.5 inches
Device is:        In smartctl database [for details use: -P show]
ATA Version is:   ACS-2 (minor revision not indicated)
SATA Version is:  SATA 3.0, 6.0 Gb/s (current: 6.0 Gb/s)
Local Time is:    Thu Mar 31 08:24:17 2022 UTC
SMART support is: Available - device has SMART capability.
SMART support is: Enabled

=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

General SMART Values:
Offline data collection status:  (0x00) Offline data collection activity
                                        was never started.
                                        Auto Offline Data Collection: Disabled.
Total time to complete Offline 
data collection:                (   32) seconds.
Offline data collection
capabilities:                    (0x00)         Offline data collection not supported.
SMART capabilities:            (0x0003) Saves SMART data before entering
                                        power-saving mode.
                                        Supports SMART auto save timer.
Error logging capability:        (0x00) Error logging NOT supported.
                                        General Purpose Logging supported.
SCT capabilities:              (0x0039) SCT Status supported.
                                        SCT Error Recovery Control supported.
                                        SCT Feature Control supported.
                                        SCT Data Table supported.

SMART Attributes Data Structure revision number: 16
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE
  1 Raw_Read_Error_Rate     0x0000   000   000   000    Old_age   Offline      -       0
  2 Throughput_Performance  0x0000   000   000   000    Old_age   Offline      -       0
  3 Spin_Up_Time            0x0000   000   000   000    Old_age   Offline      -       0
  5 Reallocated_Sector_Ct   0x0002   100   100   000    Old_age   Always       -       0
  7 Seek_Error_Rate         0x0000   000   000   000    Old_age   Offline      -       0
  8 Seek_Time_Performance   0x0000   000   000   000    Old_age   Offline      -       0
  9 Power_On_Hours          0x0002   100   100   000    Old_age   Always       -       32474
 10 Spin_Retry_Count        0x0000   000   000   000    Old_age   Offline      -       0
 12 Power_Cycle_Count       0x0002   100   100   000    Old_age   Always       -       297
168 SATA_PHY_Error_Count    0x0000   000   000   000    Old_age   Offline      -       0
169 Unknown_Innodisk_Attr   0x0000   000   000   000    Old_age   Offline      -       0x000000000000
175 Bad_Cluster_Table_Count 0x0000   000   000   000    Old_age   Offline      -       0
192 Power-Off_Retract_Count 0x0000   000   000   000    Old_age   Offline      -       0
  1 Raw_Read_Error_Rate     0x0000   000   000   000    Old_age   Offline      -       2199023255552
197 Current_Pending_Sector  0x0000   000   000   000    Old_age   Offline      -       0
240 Write_Head              0x0000   000   000   000    Old_age   Offline      -       0
225 Unknown_Innodisk_Attr   0x0000   000   000   000    Old_age   Offline      -       0
170 Bad_Block_Count         0x0003   100   100   ---    Pre-fail  Always       -       0 47 0
173 Erase_Count             0x0002   100   100   ---    Old_age   Always       -       0 7280 7192
229 Flash_ID                0x0002   100   100   ---    Old_age   Always       -       0x50769394de98
236 Unstable_Power_Count    0x0002   100   100   ---    Old_age   Always       -       0
235 Later_Bad_Block         0x0002   100   000   ---    Old_age   Always       -       0
176 Uncorr_RECORD_Count     0x0000   100   000   ---    Old_age   Offline      -       0

Read SMART Log Directory failed: scsi error badly formed scsi parameters

SMART Error Log not supported

SMART Self-test Log not supported

Selective Self-tests/Logging not supported

"""

output_Innodisk_vendor_info = """********************************************************************************************
* Innodisk iSMART V3.9.41                                                       2018/05/25 *
********************************************************************************************
Model Name: InnoDisk Corp. - mSATA 3ME              
FW Version: S140714 
Serial Number: 20171126AAAA11730156
Health: 0.00 
Capacity: 29.818199 GB
P/E Cycle: 3000 
Lifespan : 0 (Years : 0 Months : 0 Days : 0) 
Write Protect: Disable 
InnoRobust: Enable 
--------------------------------------------------------------------------------------------
ID    SMART Attributes                            Value           Raw Value 
--------------------------------------------------------------------------------------------
[09]  Power On Hours                              [32474]         [0902006464DA7E0000000000] 
[0C]  Power Cycle Count                           [  297]         [0C0200646429010000000000] 
[AA]  Total Bad Block Count                       [   47]         [AA0300646400002F00000000] 
[AD]  Erase Count Max.                            [ 7280]         [AD02006464181C701C000000] 
[AD]  Erase Count Avg.                            [ 7192]         [AD02006464181C701C000000] 
[C2]  Temperature                                 [    0]         [000000000000000000000000] 
[EB]  Later Bad Block                             [    0]         [EB0200640000000000000000] 
[EB]  Read Block                                  [    0]         [EB0200640000000000000000] 
[EB]  Write Block                                 [    0]         [EB0200640000000000000000] 
[EB]  Erase Block                                 [    0]         [EB0200640000000000000000] 
[EC]  Unstable Power Count                        [    0]         [EC0200646400000000000000] 
"""

output_lack_info_ssd = """smartctl 7.2 2020-12-30 r5155 [x86_64-linux-5.10.0-8-2-amd64] (local build)
Copyright (C) 2002-20, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===

=== START OF SMART DATA SECTION ===

  0       5275     0  0x0001  0x0004      -            0     1     -"""

class TestSsdGeneric:
    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell', mock.MagicMock(return_value=output_ssd))
    def test_ssd(self):
        # Test parsing a normal ssd info
        ssd = SsdUtil('/dev/sda')
        assert(ssd.get_health() == '95')
        assert(ssd.get_model() == '(S42) 3IE3')
        assert(ssd.get_firmware() == 'S16425i')
        assert(ssd.get_temperature() == '30')
        assert(ssd.get_serial() == 'BCA11712280210689')

    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell', mock.MagicMock(return_value=output_lack_info_ssd))
    def test_ssd_with_na_path(self):
        # Test parsing normal ssd info which lack of expected sections
        ssd = SsdUtil('/dev/sda')
        assert(ssd.get_health() == 'N/A')
        assert(ssd.get_model() == 'N/A')
        assert(ssd.get_firmware() == "N/A")
        assert(ssd.get_temperature() == "N/A")
        assert(ssd.get_serial() == "N/A")

    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell', mock.MagicMock(return_value=output_Innodisk_ssd))
    def test_Innodisk_ssd(self):
        # Test parsing Innodisk ssd info
        Innodisk_ssd = SsdUtil('/dev/sda')
        assert(Innodisk_ssd.get_health() == 'N/A')
        assert(Innodisk_ssd.get_model() == 'InnoDisk Corp. - mSATA 3ME')
        assert(Innodisk_ssd.get_firmware() == "S140714")
        assert(Innodisk_ssd.get_temperature() == 'N/A')
        assert(Innodisk_ssd.get_serial() == "20171126AAAA11730156")

        Innodisk_ssd.vendor_ssd_info = output_Innodisk_vendor_info
        Innodisk_ssd.parse_vendor_ssd_info('InnoDisk')
        assert(Innodisk_ssd.get_health() == '0')
        assert(Innodisk_ssd.get_model() == 'InnoDisk Corp. - mSATA 3ME')
        assert(Innodisk_ssd.get_firmware() == "S140714")
        assert(Innodisk_ssd.get_temperature() == '0')
        assert(Innodisk_ssd.get_serial() == "20171126AAAA11730156")

