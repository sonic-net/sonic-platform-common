
import sys
if sys.version_info.major == 3:
    from unittest import mock
else:
    import mock

from sonic_platform_base.sonic_ssd.ssd_generic import SsdUtil

output_nvme_ssd = """smartctl 7.2 2020-12-30 r5155 [x86_64-linux-5.10.0-8-2-amd64] (local build)
Copyright (C) 2002-20, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===
Model Number:                       SFPC020GM1EC2TO-I-5E-11P-STD
Serial Number:                      A0221030722410000027
Firmware Version:                   COT6OQ
PCI Vendor/Subsystem ID:            0x1dd4
IEEE OUI Identifier:                0x8c6078
Controller ID:                      1
NVMe Version:                       1.3
Number of Namespaces:               1
Namespace 1 Size/Capacity:          20,014,718,976 [20.0 GB]
Namespace 1 Formatted LBA Size:     512
Namespace 1 IEEE EUI-64:            486834 133070001b
Local Time is:                      Tue Mar  1 06:35:23 2022 UTC
Firmware Updates (0x12):            1 Slot, no Reset required
Optional Admin Commands (0x0016):   Format Frmw_DL Self_Test
Optional NVM Commands (0x001f):     Comp Wr_Unc DS_Mngmt Wr_Zero Sav/Sel_Feat
Log Page Attributes (0x0e):         Cmd_Eff_Lg Ext_Get_Lg Telmtry_Lg
Maximum Data Transfer Size:         64 Pages
Warning  Comp. Temp. Threshold:     105 Celsius
Critical Comp. Temp. Threshold:     120 Celsius

Supported Power States
St Op     Max   Active     Idle   RL RT WL WT  Ent_Lat  Ex_Lat
 0 +     3.50W       -        -    0  0  0  0        0       0
 1 +     2.50W       -        -    1  1  1  1        0       0
 2 +     1.50W       -        -    2  2  2  2        0       0
 3 -   0.0200W       -        -    3  3  3  3     2200    3000
 4 -   0.0100W       -        -    4  4  4  4    15000   12000

Supported LBA Sizes (NSID 0x1)
Id Fmt  Data  Metadt  Rel_Perf
 0 +     512       0         0

=== START OF SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

SMART/Health Information (NVMe Log 0x02)
Critical Warning:                   0x00
Temperature:                        37 Celsius
Available Spare:                    100%
Available Spare Threshold:          10%
Percentage Used:                    0%
Data Units Read:                    1,546,369 [791 GB]
Data Units Written:                 7,118,163 [3.64 TB]
Host Read Commands:                 27,027,268
Host Write Commands:                87,944,082
Controller Busy Time:               5,660
Power Cycles:                       455
Power On Hours:                     3,638
Unsafe Shutdowns:                   435
Media and Data Integrity Errors:    0
Error Information Log Entries:      5,275
Warning  Comp. Temperature Time:    0
Critical Comp. Temperature Time:    0
Temperature Sensor 1:               41 Celsius
Temperature Sensor 2:               38 Celsius

Error Information (NVMe Log 0x01, 16 of 64 entries)
Num   ErrCount  SQId   CmdId  Status  PELoc          LBA  NSID    VS
  0       5275     0  0x0001  0x0004      -            0     1     -"""

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
Health: 82.34%
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

output_Innodisk_missing_names_ssd = """smartctl 6.6 2017-11-05 r4594 [armv7l-linux-4.19.0-12-2-armmp] (local build)
Copyright (C) 2002-17, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===
Model Family:     Innodisk 3IE3/3ME3/3ME4 SSDs
Device Model:     M.2 (S42) 3ME4
Serial Number:    YCA12003110020080
LU WWN Device Id: 5 02b2a2 01d1c1b1a
Firmware Version: L17606
User Capacity:    16,013,942,784 bytes [16.0 GB]
Sector Size:      512 bytes logical/physical
Rotation Rate:    Solid State Device
Device is:        In smartctl database [for details use: -P show]
ATA Version is:   ACS-3 T13/2161-D revision 4
SATA Version is:  SATA 3.2, 6.0 Gb/s (current: 6.0 Gb/s)
Local Time is:    Tue Apr 26 00:57:00 2022 UTC
SMART support is: Available - device has SMART capability.
SMART support is: Enabled

=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

General SMART Values:
Offline data collection status:  (0x02) Offline data collection activity
                    was completed without error.
                    Auto Offline Data Collection: Disabled.
Total time to complete Offline
data collection:        (   32) seconds.
Offline data collection
capabilities:            (0x00)     Offline data collection not supported.
SMART capabilities:            (0x0002) Does not save SMART data before
                    entering power-saving mode.
                    Supports SMART auto save timer.
Error logging capability:        (0x00) Error logging NOT supported.
                    General Purpose Logging supported.

SMART Attributes Data Structure revision number: 16
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE
  1 Raw_Read_Error_Rate     0x0000   000   000   000    Old_age   Offline      -       0
  2 Throughput_Performance  0x0000   000   000   000    Old_age   Offline      -       0
  5 Later_Bad_Block         0x0012   100   100   001    Old_age   Always       -       0
  7 Seek_Error_Rate         0x0000   000   000   000    Old_age   Offline      -       0
  8 Seek_Time_Performance   0x0000   000   000   000    Old_age   Offline      -       0
  9 Power_On_Hours          0x0012   253   000   000    Old_age   Always       -       14151
 10 Spin_Retry_Count        0x0000   000   000   000    Old_age   Offline      -       0
 12 Power_Cycle_Count       0x0012   036   000   000    Old_age   Always       -       36
163 Total_Bad_Block_Count   0x0000   000   000   000    Old_age   Offline      -       9
168 SATA_PHY_Error_Count    0x0000   000   000   000    Old_age   Offline      -       0
169 Unknown Attribute       0x0000   094   000   000    Old_age   Offline      -       94
175 Bad_Cluster_Table_Count 0x0000   000   000   000    Old_age   Offline      -       0
192 Power-Off_Retract_Count 0x0012   000   000   000    Old_age   Always       -       3
194 Unknown Attribute       0x0002   039   100   000    Old_age   Always       -       39 (3 42 0 33 0)
197 Current_Pending_Sector  0x0000   000   000   000    Old_age   Offline      -       0
225 Data_Log_Write_Count    0x0000   000   000   000    Old_age   Offline      -       0
240 Write_Head              0x0000   000   000   000    Old_age   Offline      -       0
165 Max_Erase_Count         0x0012   223   100   000    Old_age   Always       -       223
167 Average_Erase_Count     0x0012   000   100   000    Old_age   Always       -       187
170 Spare_Block_Count       0x0013   100   100   010    Pre-fail  Always       -       72
171 Program_Fail_Count      0x0012   000   100   000    Old_age   Always       -       0
172 Erase_Fail_Count        0x0012   000   100   000    Old_age   Always       -       0
176 RANGE_RECORD_Count      0x0000   000   000   000    Old_age   Offline      -       0
184 End-to-End_Error        0x0012   000   000   000    Old_age   Always       -       0
187 Reported_Uncorrect      0x0012   000   000   000    Old_age   Always       -       0
229 Flash_ID                0x0000   100   100   000    Old_age   Offline      -       0x51769394de98
232 Spares_Remaining_Perc   0x0013   000   000   000    Pre-fail  Always       -       0
235 Later_Bad_Blk_Inf_R/W/E 0x0002   000   000   000    Old_age   Always       -       0 0 0
241 Host_Writes_32MiB       0x0002   100   100   000    Old_age   Always       -       14452
242 Host_Reads_32MiB        0x0002   100   100   000    Old_age   Always       -       42566

SMART Error Log not supported

SMART Self-test Log not supported

Selective Self-tests/Logging not supported

"""

output_virtium_generic = """
smartctl 7.2 2020-12-30 r5155 [x86_64-linux-5.10.0-18-2-amd64] (local build)
Copyright (C) 2002-20, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===
Device Model:     StorFly VSF302XC016G-MLX1
Serial Number:    52586-0705
Firmware Version: 0202-001
User Capacity:    15,804,137,472 bytes [15.8 GB]
Sector Size:      512 bytes logical/physical
Rotation Rate:    Solid State Device
TRIM Command:     Available, deterministic, zeroed
Device is:        Not in smartctl database [for details use: -P showall]
ATA Version is:   ACS-2 (minor revision not indicated)
SATA Version is:  SATA 3.1, 6.0 Gb/s (current: 6.0 Gb/s)
Local Time is:    Wed Oct 18 09:58:57 2023 IDT
SMART support is: Available - device has SMART capability.
SMART support is: Enabled

=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

General SMART Values:
Offline data collection status:  (0x00) Offline data collection activity
                                        was never started.
                                        Auto Offline Data Collection: Disabled.
Self-test execution status:      (   0) The previous self-test routine completed
                                        without error or no self-test has ever 
                                        been run.
Total time to complete Offline 
data collection:                (    0) seconds.
Offline data collection
capabilities:                    (0x71) SMART execute Offline immediate.
                                        No Auto Offline data collection support.
                                        Suspend Offline collection upon new
                                        command.
                                        No Offline surface scan supported.
                                        Self-test supported.
                                        Conveyance Self-test supported.
                                        Selective Self-test supported.
SMART capabilities:            (0x0002) Does not save SMART data before
                                        entering power-saving mode.
                                        Supports SMART auto save timer.
Error logging capability:        (0x01) Error logging supported.
                                        General Purpose Logging supported.
Short self-test routine 
recommended polling time:        (   1) minutes.
Extended self-test routine
recommended polling time:        (   1) minutes.
Conveyance self-test routine
recommended polling time:        (   1) minutes.

SMART Attributes Data Structure revision number: 1
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE
  1 Raw_Read_Error_Rate     0x0000   100   100   070    Old_age   Offline      -       0
  5 Reallocated_Sector_Ct   0x0000   100   100   000    Old_age   Offline      -       0
  9 Power_On_Hours          0x0000   100   100   000    Old_age   Offline      -       1223
 12 Power_Cycle_Count       0x0000   100   100   000    Old_age   Offline      -       17413
160 Unknown_Attribute       0x0000   100   100   000    Old_age   Offline      -       0
161 Unknown_Attribute       0x0000   100   100   000    Old_age   Offline      -       180
163 Unknown_Attribute       0x0000   100   100   000    Old_age   Offline      -       9
164 Unknown_Attribute       0x0000   100   100   000    Old_age   Offline      -       5105664
165 Unknown_Attribute       0x0000   100   100   000    Old_age   Offline      -       2524
166 Unknown_Attribute       0x0000   100   100   000    Old_age   Offline      -       2393
167 Unknown_Attribute       0x0000   100   100   000    Old_age   Offline      -       2444
168 Unknown_Attribute       0x0000   100   100   000    Old_age   Offline      -       20000
177 Wear_Leveling_Count     0x0000   100   100   050    Old_age   Offline      -       22301
178 Used_Rsvd_Blk_Cnt_Chip  0x0000   100   100   000    Old_age   Offline      -       0
181 Program_Fail_Cnt_Total  0x0000   100   100   000    Old_age   Offline      -       0
182 Erase_Fail_Count_Total  0x0000   100   100   000    Old_age   Offline      -       0
187 Reported_Uncorrect      0x0000   100   100   000    Old_age   Offline      -       0
192 Power-Off_Retract_Count 0x0000   100   100   000    Old_age   Offline      -       12514
194 Temperature_Celsius     0x0000   100   100   000    Old_age   Offline      -       19
195 Hardware_ECC_Recovered  0x0000   100   100   000    Old_age   Offline      -       0
196 Reallocated_Event_Count 0x0000   100   100   016    Old_age   Offline      -       0
198 Offline_Uncorrectable   0x0000   100   100   000    Old_age   Offline      -       0
199 UDMA_CRC_Error_Count    0x0000   100   100   050    Old_age   Offline      -       0
232 Available_Reservd_Space 0x0000   100   100   000    Old_age   Offline      -       100
241 Total_LBAs_Written      0x0000   100   100   000    Old_age   Offline      -       629509
242 Total_LBAs_Read         0x0000   100   100   000    Old_age   Offline      -       1482095
248 Unknown_Attribute       0x0000   100   100   000    Old_age   Offline      -       88
249 Unknown_Attribute       0x0000   100   100   000    Old_age   Offline      -       100

SMART Error Log Version: 1
No Errors Logged

SMART Self-test log structure revision number 1
No self-tests have been logged.  [To run self-tests, use: smartctl -t]

SMART Selective self-test log data structure revision number 1
 SPAN  MIN_LBA  MAX_LBA  CURRENT_TEST_STATUS
    1        0        0  Not_testing
    2        0        0  Not_testing
    3        0        0  Not_testing
    4        0        0  Not_testing
    5        0        0  Not_testing
    6        0    65535  Read_scanning was never started
Selective self-test flags (0x0):
  After scanning selected spans, do NOT read-scan remainder of disk.
If Selective self-test is pending on power-up, resume after 0 minute delay.
"""

output_virtium_generic_vsfdm8xc240g_v11_t = """
smartctl 7.2 2020-12-30 r5155 [x86_64-linux-5.10.0-12-2-amd64] (local build)
Copyright (C) 2002-20, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===
Device Model:     VSFDM8XC240G-V11-T
Serial Number:    60237-0037
Firmware Version: 0913-000
User Capacity:    240,057,409,536 bytes [240 GB]
Sector Size:      512 bytes logical/physical
Rotation Rate:    Solid State Device
Form Factor:      2.5 inches
TRIM Command:     Available, deterministic, zeroed
Device is:        Not in smartctl database [for details use: -P showall]
ATA Version is:   ACS-3 (minor revision not indicated)
SATA Version is:  SATA 3.2, 6.0 Gb/s (current: 6.0 Gb/s)
Local Time is:    Wed Feb  8 02:11:48 2023 UTC
SMART support is: Available - device has SMART capability.
SMART support is: Enabled

=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

General SMART Values:
Offline data collection status:  (0x00) Offline data collection activity
                                        was never started.
                                        Auto Offline Data Collection: Disabled.
Self-test execution status:      (   0) The previous self-test routine completed
                                        without error or no self-test has ever
                                        been run.
Total time to complete Offline
data collection:                (    0) seconds.
Offline data collection
capabilities:                    (0x73) SMART execute Offline immediate.
                                        Auto Offline data collection on/off support.
                                        Suspend Offline collection upon new
                                        command.
                                        No Offline surface scan supported.
                                        Self-test supported.
                                        Conveyance Self-test supported.
                                        Selective Self-test supported.
SMART capabilities:            (0x0003) Saves SMART data before entering
                                        power-saving mode.
                                        Supports SMART auto save timer.
Error logging capability:        (0x01) Error logging supported.
                                        General Purpose Logging supported.
Short self-test routine
recommended polling time:        (   2) minutes.
Extended self-test routine
recommended polling time:        (  15) minutes.
Conveyance self-test routine
recommended polling time:        (   0) minutes.
SCT capabilities:              (0x0031) SCT Status supported.
                                        SCT Feature Control supported.
                                        SCT Data Table supported.

SMART Attributes Data Structure revision number: 1
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE
  1 Raw_Read_Error_Rate     0x000b   100   100   000    Pre-fail  Always       -       0
  5 Reallocated_Sector_Ct   0x0013   100   100   000    Pre-fail  Always       -       0
  9 Power_On_Hours          0x0012   100   100   000    Old_age   Always       -       221
 12 Power_Cycle_Count       0x0012   100   100   000    Old_age   Always       -       156
 14 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       469427376
 15 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       468862128
 16 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       1436
 17 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       1436
100 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       6823
168 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       0
170 Unknown_Attribute       0x0003   100   100   000    Pre-fail  Always       -       0
172 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       0
173 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       12
174 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       155
175 Program_Fail_Count_Chip 0x0012   100   100   000    Old_age   Always       -       1
181 Program_Fail_Cnt_Total  0x0012   100   100   000    Old_age   Always       -       0
187 Reported_Uncorrect      0x0012   100   100   000    Old_age   Always       -       0
194 Temperature_Celsius     0x0023   066   048   000    Pre-fail  Always       -       34 (Min/Max 27/52)
197 Current_Pending_Sector  0x0032   100   100   000    Old_age   Always       -       0
198 Offline_Uncorrectable   0x0012   100   100   000    Old_age   Always       -       0
199 UDMA_CRC_Error_Count    0x000b   100   100   000    Pre-fail  Always       -       0
202 Unknown_SSD_Attribute   0x0012   000   000   000    Old_age   Always       -       0
231 Unknown_SSD_Attribute   0x0013   100   100   000    Pre-fail  Always       -       100
232 Available_Reservd_Space 0x0013   100   100   000    Pre-fail  Always       -       0
234 Unknown_Attribute       0x000b   100   100   000    Pre-fail  Always       -       131292480
235 Unknown_Attribute       0x000b   100   100   000    Pre-fail  Always       -       347463360
241 Total_LBAs_Written      0x0012   100   100   000    Old_age   Always       -       302116658
242 Total_LBAs_Read         0x0012   100   100   000    Old_age   Always       -       45606297
247 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       347463360
248 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       1

SMART Error Log Version: 1
No Errors Logged

SMART Self-test log structure revision number 1
No self-tests have been logged.  [To run self-tests, use: smartctl -t]

SMART Selective self-test log data structure revision number 1
 SPAN  MIN_LBA  MAX_LBA  CURRENT_TEST_STATUS
    1        0        0  Not_testing
    2        0        0  Not_testing
    3        0        0  Not_testing
    4        0        0  Not_testing
    5        0        0  Not_testing
Selective self-test flags (0x0):
  After scanning selected spans, do NOT read-scan remainder of disk.
If Selective self-test is pending on power-up, resume after 0 minute delay.
"""

output_virtium_vendor ="""
SMART attributes 
 ID                    Attribute   High Raw    Low Raw Value Worst Threshold 
  1          Raw_Read_Error_Rate          0          0   100   100        70 
  5           Reserved_Attribute          0          0   100   100         0 
  9               Power_On_Hours          0       1223   100   100         0 
 12            Power_Cycle_Count          0      17413   100   100         0 
160   Uncorrectable_Sector_Count          0          0   100   100         0 
161            Valid_Spare_Block          0        180   100   100         0 
163           Reserved_Attribute          0          9   100   100         0 
164           Reserved_Attribute          0    5105665   100   100         0 
165          Maximum_Erase_Count          0       2524   100   100         0 
166           Reserved_Attribute          0       2393   100   100         0 
167          Average_Erase_Count          0       2444   100   100         0 
168               NAND_Endurance          0      20000   100   100         0 
177           Reserved_Attribute          0      22301   100   100        50 
178           Reserved_Attribute          0          0   100   100         0 
181           Total_Program_Fail          0          0   100   100         0 
182             Total_Erase_Fail          0          0   100   100         0 
187    Uncorrectable_Error_Count          0          0   100   100         0 
192      Sudden_Power_Lost_Count          0      12514   100   100         0 
194          Temperature_Celsius          0         17   100   100         0 
195       Hardware_ECC_Recovered          0          0   100   100         0 
196      Reallocated_Event_Count          0          0   100   100        16 
198           Reserved_Attribute          0          0   100   100         0 
199         UDMA_CRC_Error_Count          0          0   100   100        50 
232           Reserved_Attribute          0        100   100   100         0 
241           Total_LBAs_Written          0     629509   100   100         0 
242              Total_LBAs_Read          0    1482095   100   100         0 
248          Remaining_Life_Left          0         88   100   100         0 
249  Remaining_Spare_Block_Count          0        100   100   100         0 
"""

output_virtium_vendor_vsfdm8xc240g_v11_t = """
SMART attributes
 ID                    Attribute   High Raw    Low Raw Value Worst Threshold
  1          Raw_Read_Error_Rate          0          0   100   100         0
  5           Reserved_Attribute          0          0   100   100         0
  9               Power_On_Hours          0        221   100   100         0
 12            Power_Cycle_Count          0        156   100   100         0
 14           Reserved_Attribute          0  469427376   100   100         0
 15           Reserved_Attribute          0  468862128   100   100         0
 16           Reserved_Attribute          0       1436   100   100         0
 17           Reserved_Attribute          0       1436   100   100         0
100           Reserved_Attribute          0       6823   100   100         0
168               NAND_Endurance          0          0   100   100         0
170           Reserved_Attribute          0          0   100   100         0
172           Reserved_Attribute          0          0   100   100         0
173           Reserved_Attribute          0         12   100   100         0
174           Reserved_Attribute          0        155   100   100         0
175           Reserved_Attribute          0          1   100   100         0
181           Total_Program_Fail          0          0   100   100         0
187    Uncorrectable_Error_Count          0          0   100   100         0
194          Temperature_Celsius         52         34    66    48         0
197 Current_Pending_Sector_Count          0          0   100   100         0
198           Reserved_Attribute          0          0   100   100         0
199         UDMA_CRC_Error_Count          0          0   100   100         0
202                   TRIM_Count          0          0     0     0         0
231           Reserved_Attribute          0         98   100   100         0
232           Reserved_Attribute          0          0   100   100         0
234           Reserved_Attribute          0  131296768   100   100         0
235           Reserved_Attribute          0  347463680   100   100         0
241           Total_LBAs_Written          0  302116658   100   100         0
242              Total_LBAs_Read          0   45608497   100   100         0
247           Reserved_Attribute          0  347463680   100   100         0
248          Remaining_Life_Left          0          0     1   100         0
"""

output_virtium_no_remain_life = """
SMART attributes
 ID                    Attribute   High Raw    Low Raw Value Worst Threshold
  1          Raw_Read_Error_Rate          0          0   100   100        70
  5           Reserved_Attribute          0          0   100   100         0
  9               Power_On_Hours          0       1288   100   100         0
 12            Power_Cycle_Count          0        106   100   100         0
160   Uncorrectable_Sector_Count          0          0   100   100         0
161            Valid_Spare_Block          0        267   100   100         0
163           Reserved_Attribute          0         16   100   100         0
164           Reserved_Attribute          0     243145   100   100         0
165          Maximum_Erase_Count          0        194   100   100         0
166           Reserved_Attribute          0         89   100   100         0
167          Average_Erase_Count          0        116   100   100         0
168               NAND_Endurance          0      20000   100   100         0
177           Reserved_Attribute          0        775   100   100        50
178           Reserved_Attribute          0          0   100   100         0
181           Total_Program_Fail          0          0   100   100         0
182             Total_Erase_Fail          0          0   100   100         0
187    Uncorrectable_Error_Count          0          0   100   100         0
192      Sudden_Power_Lost_Count          0         44   100   100         0
194          Temperature_Celsius          0         35   100   100         0
195       Hardware_ECC_Recovered          0          0   100   100         0
196      Reallocated_Event_Count          0          0   100   100        16
198           Reserved_Attribute          0          0   100   100         0
199         UDMA_CRC_Error_Count          0          1   100   100        50
232           Reserved_Attribute          0        100   100   100         0
241           Total_LBAs_Written          0      63134   100   100         0
242              Total_LBAs_Read          0    8235204   100   100         0
248          Remaining_Life_Left          0        100   100   100         0
249  Remaining_Spare_Block_Count          0        100   100   100         0
"""

output_virtium_invalid_nand_endurance = """
SMART attributes
 ID                    Attribute   High Raw    Low Raw Value Worst Threshold
167          Average_Erase_Count          0        116   100   100         0
168               NAND_Endurance          0          0   100   100         0
"""

output_virtium_invalid_remain_life = """
SMART attributes
 ID                    Attribute   High Raw    Low Raw Value Worst Threshold
"""

output_swissbit_vendor = """
smartctl 7.2 2020-12-30 r5155 [x86_64-linux-5.10.0-23-2-amd64] (local build)
Copyright (C) 2002-20, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===
Device Model:     SFSA160GM2AK2TO-I-8C-22K-STD
Serial Number:    00006022750795000010
Firmware Version: SBR15004
User Capacity:    160,041,885,696 bytes [160 GB]
Sector Size:      512 bytes logical/physical
Rotation Rate:    Solid State Device
Form Factor:      2.5 inches
TRIM Command:     Available, deterministic, zeroed
Device is:        Not in smartctl database [for details use: -P showall]
ATA Version is:   ACS-3 (minor revision not indicated)
SATA Version is:  SATA 3.2, 6.0 Gb/s (current: 6.0 Gb/s)
Local Time is:    Wed Aug  2 08:24:31 2023 UTC
SMART support is: Available - device has SMART capability.
SMART support is: Enabled

=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

General SMART Values:
Offline data collection status:  (0x00) Offline data collection activity
                                        was never started.
                                        Auto Offline Data Collection: Disabled.
Self-test execution status:      (   0) The previous self-test routine completed
                                        without error or no self-test has ever
                                        been run.
Total time to complete Offline
data collection:                (    0) seconds.
Offline data collection
capabilities:                    (0x53) SMART execute Offline immediate.
                                        Auto Offline data collection on/off support.
                                        Suspend Offline collection upon new
                                        command.
                                        No Offline surface scan supported.
                                        Self-test supported.
                                        No Conveyance Self-test supported.
                                        Selective Self-test supported.
SMART capabilities:            (0x0003) Saves SMART data before entering
                                        power-saving mode.
                                        Supports SMART auto save timer.
Error logging capability:        (0x01) Error logging supported.
                                        General Purpose Logging supported.
Short self-test routine
recommended polling time:        (   2) minutes.
Extended self-test routine
recommended polling time:        (  15) minutes.
SCT capabilities:              (0x0031) SCT Status supported.
                                        SCT Feature Control supported.
                                        SCT Data Table supported.

SMART Attributes Data Structure revision number: 1
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE
  1 Raw_Read_Error_Rate     0x000b   100   100   000    Pre-fail  Always       -       0
  5 Reallocated_Sector_Ct   0x0013   100   100   000    Pre-fail  Always       -       0
  9 Power_On_Hours          0x0012   100   100   000    Old_age   Always       -       825
 12 Power_Cycle_Count       0x0012   100   100   000    Old_age   Always       -       447
 16 Unknown_Attribute       0x0112   100   100   001    Old_age   Always       -       4
 17 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       30000
160 Unknown_Attribute       0x0002   100   100   000    Old_age   Always       -       0
161 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       15401195
163 Unknown_Attribute       0x0003   100   100   000    Pre-fail  Always       -       33
164 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       6506
165 Unknown_Attribute       0x0002   100   100   000    Old_age   Always       -       38
166 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       1
167 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       4
168 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       30000
169 Unknown_Attribute       0x0003   100   100   000    Pre-fail  Always       -       421
193 Unknown_SSD_Attribute   0x0012   100   100   000    Old_age   Always       -       0
194 Temperature_Celsius     0x0023   100   100   000    Pre-fail  Always       -       25 (Min/Max 22/45)
195 Hardware_ECC_Recovered  0x0012   100   100   000    Old_age   Always       -       0
196 Reallocated_Event_Count 0x0012   000   000   000    Old_age   Always       -       0
198 Offline_Uncorrectable   0x0012   100   100   000    Old_age   Always       -       0
199 UDMA_CRC_Error_Count    0x000b   100   100   000    Pre-fail  Always       -       0
215 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       4275
231 Unknown_SSD_Attribute   0x1913   100   100   025    Pre-fail  Always       -       100
235 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       1302467136
237 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       0
241 Total_LBAs_Written      0x0012   100   100   000    Old_age   Always       -       1186450104
242 Total_LBAs_Read         0x0012   100   100   000    Old_age   Always       -       2257141451
243 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       0
244 Unknown_Attribute       0x0012   100   100   000    Old_age   Always       -       0
248 Unknown_Attribute       0x0112   100   100   001    Old_age   Always       -       100

SMART Error Log Version: 1
No Errors Logged

SMART Self-test log structure revision number 1
No self-tests have been logged.  [To run self-tests, use: smartctl -t]

SMART Selective self-test log data structure revision number 1
 SPAN  MIN_LBA  MAX_LBA  CURRENT_TEST_STATUS
    1        0        0  Not_testing
    2        0        0  Not_testing
    3        0        0  Not_testing
    4        0        0  Not_testing
    5        0        0  Not_testing
Selective self-test flags (0x0):
  After scanning selected spans, do NOT read-scan remainder of disk.
If Selective self-test is pending on power-up, resume after 0 minute delay.
"""

output_transcend_vendor = """
scopepro-cli 1.21 2023/11/24
Copyright (c) 2021-24, Transcend information, Inc. All rights reserved.

[/dev/sda]
---------- Disk Information ----------
Model                   :TS32XBTMM1600
FW Version              :O0918B
Serial No               :F318410080
Support Interface       :SATA
---------------- S.M.A.R.T Information ----------------
01 Read Error Rate      0
05 Reallocated Sectors Count    0
09 Power-On Hour Count  2295
0C Power Cycle Count    2580
A0 Uncorrectable sectors count when read/write  0
A1 Number of Valid Spare Blocks 56
A3 Number of Initial Invalid Blocks     12
A4 Total Erase Count    924312
A5 Maximum Erase Count  931
A6 Minimum Erase Count  831
A7 Average Erase Count  898
A8 Max Erase Count of Spec      3000
A9 Remain Life (percentage)     71
AF Program fail count in worst die      0
B0 Erase fail count in worst die        0
B1 Total Wear Level Count       481
B2 Runtime Invalid Block Count  0
B5 Total Program Fail Count     0
B6 Total Erase Fail Count       0
C0 Power-Off Retract Count      59
C2 Controlled Temperature       40
C3 Hardware ECC Recovered       1668
C4 Reallocation Event Count     0
C5 Current Pending Sector Count 0
C6 Uncorrectable Error Count Off-Line   0
C7 Ultra DMA CRC Error Count    0
E8 Available Reserved Space     100
F1 Total LBA Written (each write unit=32MB)     671696
F2 Total LBA Read (each read unit=32MB) 393162
F5 Flash Write Sector Count     924312
---------------- Health Information ----------------
Health Percentage: 71%
"""

output_wdc_vendor = """
smartctl 7.2 2020-12-30 r5155 [x86_64-linux-5.10.0-18-2-amd64] (local build)
Copyright (C) 2002-20, Bruce Allen, Christian Franke, www.smartmontools.org

=== START OF INFORMATION SECTION ===
Device Model:     WDC PC SA530 SDASN8Y1T00
Serial Number:    2122FF441406
LU WWN Device Id: 5 001b44 4a7dc5677
Firmware Version: 40103000
User Capacity:    1,024,209,543,168 bytes [1.02 TB]
Sector Size:      512 bytes logical/physical
Rotation Rate:    Solid State Device
Form Factor:      M.2
TRIM Command:     Available, deterministic, zeroed
Device is:        Not in smartctl database [for details use: -P showall]
ATA Version is:   ACS-4 T13/BSR INCITS 529 revision 5
SATA Version is:  SATA 3.3, 6.0 Gb/s (current: 6.0 Gb/s)
Local Time is:    Thu Feb 15 14:12:34 2024 UTC
SMART support is: Available - device has SMART capability.
SMART support is: Enabled

=== START OF READ SMART DATA SECTION ===
SMART overall-health self-assessment test result: PASSED

General SMART Values:
Offline data collection status:  (0x00)	Offline data collection activity
					was never started.
					Auto Offline Data Collection: Disabled.
Self-test execution status:      (   0)	The previous self-test routine completed
					without error or no self-test has ever 
					been run.
Total time to complete Offline 
data collection: 		(    0) seconds.
Offline data collection
capabilities: 			 (0x11) SMART execute Offline immediate.
					No Auto Offline data collection support.
					Suspend Offline collection upon new
					command.
					No Offline surface scan supported.
					Self-test supported.
					No Conveyance Self-test supported.
					No Selective Self-test supported.
SMART capabilities:            (0x0003)	Saves SMART data before entering
					power-saving mode.
					Supports SMART auto save timer.
Error logging capability:        (0x01)	Error logging supported.
					General Purpose Logging supported.
Short self-test routine 
recommended polling time: 	 (   2) minutes.
Extended self-test routine
recommended polling time: 	 (  10) minutes.

SMART Attributes Data Structure revision number: 4
Vendor Specific SMART Attributes with Thresholds:
ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE
  5 Reallocated_Sector_Ct   0x0032   100   100   ---    Old_age   Always       -       0
  9 Power_On_Hours          0x0032   100   100   ---    Old_age   Always       -       18904
 12 Power_Cycle_Count       0x0032   100   100   ---    Old_age   Always       -       169
165 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       28311878
166 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       1
167 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       54
168 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       10
169 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       361
170 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       0
171 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       0
172 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       0
173 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       5
174 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       61
184 End-to-End_Error        0x0032   100   100   ---    Old_age   Always       -       0
187 Reported_Uncorrect      0x0032   100   100   ---    Old_age   Always       -       0
188 Command_Timeout         0x0032   100   100   ---    Old_age   Always       -       0
194 Temperature_Celsius     0x0022   077   059   ---    Old_age   Always       -       23 (Min/Max 16/59)
199 UDMA_CRC_Error_Count    0x0032   100   100   ---    Old_age   Always       -       0
230 Unknown_SSD_Attribute   0x0032   001   001   ---    Old_age   Always       -       279176151105
232 Available_Reservd_Space 0x0033   100   100   004    Pre-fail  Always       -       100
233 Media_Wearout_Indicator 0x0032   100   100   ---    Old_age   Always       -       5374
234 Unknown_Attribute       0x0032   100   100   ---    Old_age   Always       -       7530
241 Total_LBAs_Written      0x0030   253   253   ---    Old_age   Offline      -       6756
242 Total_LBAs_Read         0x0030   253   253   ---    Old_age   Offline      -       963
244 Unknown_Attribute       0x0032   000   100   ---    Old_age   Always       -       0

SMART Error Log Version: 1
No Errors Logged

SMART Self-test log structure revision number 1
No self-tests have been logged.  [To run self-tests, use: smartctl -t]

Selective Self-tests/Logging not supported
"""

class TestSsdGeneric:
    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell', mock.MagicMock(return_value=output_nvme_ssd))
    def test_nvme_ssd(self):
        # Test parsing nvme ssd info
        nvme_ssd = SsdUtil('/dev/nvme0n1')
        assert(nvme_ssd.get_health() == 100.0)
        assert(nvme_ssd.get_model() == 'SFPC020GM1EC2TO-I-5E-11P-STD')
        assert(nvme_ssd.get_firmware() == "COT6OQ")
        assert(nvme_ssd.get_temperature() == 37)
        assert(nvme_ssd.get_serial() == "A0221030722410000027")

    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell', mock.MagicMock(return_value=output_lack_info_ssd))
    def test_nvme_ssd_with_na_path(self):
        # Test parsing nvme ssd info which lack of expected sections
        nvme_ssd = SsdUtil('/dev/nvme0n1')
        assert(nvme_ssd.get_health() == 'N/A')
        assert(nvme_ssd.get_model() == 'N/A')
        assert(nvme_ssd.get_firmware() == "N/A")
        assert(nvme_ssd.get_temperature() == "N/A")
        assert(nvme_ssd.get_serial() == "N/A")

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
        assert(Innodisk_ssd.get_health() == '0x000000000000')
        assert(Innodisk_ssd.get_model() == 'InnoDisk Corp. - mSATA 3ME')
        assert(Innodisk_ssd.get_firmware() == "S140714")
        assert(Innodisk_ssd.get_temperature() == 'N/A')
        assert(Innodisk_ssd.get_serial() == "20171126AAAA11730156")

        Innodisk_ssd.vendor_ssd_info = output_Innodisk_vendor_info
        Innodisk_ssd.parse_vendor_ssd_info('InnoDisk')
        assert(Innodisk_ssd.get_health() == '82.34')
        assert(Innodisk_ssd.get_model() == 'InnoDisk Corp. - mSATA 3ME')
        assert(Innodisk_ssd.get_firmware() == "S140714")
        assert(Innodisk_ssd.get_temperature() == '0')
        assert(Innodisk_ssd.get_serial() == "20171126AAAA11730156")

    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell', mock.MagicMock(return_value=output_Innodisk_missing_names_ssd))
    def test_Innodisk_missing_names_ssd(self):
        # Test parsing Innodisk ssd info
        Innodisk_ssd = SsdUtil('/dev/sda')
        Innodisk_ssd.vendor_ssd_info = ''
        Innodisk_ssd.parse_vendor_ssd_info('InnoDisk')
        assert(Innodisk_ssd.get_health() == '94')
        assert(Innodisk_ssd.get_temperature() == '39')

    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell', mock.MagicMock(return_value=output_Innodisk_missing_names_ssd))
    def test_Innodisk_missing_names_ssd_2(self):
        # Test parsing Innodisk ssd info
        Innodisk_ssd = SsdUtil('/dev/sda')
        Innodisk_ssd.vendor_ssd_info = 'ERROR message from cmd'
        Innodisk_ssd.parse_vendor_ssd_info('InnoDisk')
        assert(Innodisk_ssd.get_health() == '94')
        assert(Innodisk_ssd.get_temperature() == '39')


    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell')
    def test_virtium_ssd(self, mock_exec):
        mock_exec.side_effect = [output_virtium_generic_vsfdm8xc240g_v11_t, output_virtium_vendor_vsfdm8xc240g_v11_t]
        virtium_ssd = SsdUtil('/dev/sda')
        assert virtium_ssd.get_health() == 98
        assert virtium_ssd.get_model() == 'VSFDM8XC240G-V11-T'
        assert virtium_ssd.get_firmware() == "0913-000"
        assert virtium_ssd.get_temperature() == '34'
        assert virtium_ssd.get_serial() == "60237-0037"

        mock_exec.side_effect = [output_virtium_generic, output_virtium_vendor]
        virtium_ssd = SsdUtil('/dev/sda')
        assert virtium_ssd.get_health() == 87.78
        assert virtium_ssd.get_model() == 'StorFly VSF302XC016G-MLX1'
        assert virtium_ssd.get_firmware() == "0202-001"
        assert virtium_ssd.get_temperature() == '17'
        assert virtium_ssd.get_serial() == "52586-0705"

        mock_exec.side_effect = [output_virtium_generic, output_virtium_no_remain_life]
        virtium_ssd = SsdUtil('/dev/sda')
        assert virtium_ssd.get_health() == 99.42

        mock_exec.side_effect = [output_virtium_generic, output_virtium_invalid_nand_endurance]
        virtium_ssd = SsdUtil('/dev/sda')
        assert virtium_ssd.get_health() == "N/A"

        mock_exec.side_effect = [output_virtium_generic, output_virtium_invalid_remain_life]
        virtium_ssd = SsdUtil('/dev/sda')
        assert virtium_ssd.get_health() == "N/A"

    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell')
    def test_swissbit_ssd(self, mock_exec):
        mock_exec.return_value = output_swissbit_vendor
        swissbit_ssd = SsdUtil('/dev/sda')
        assert swissbit_ssd.get_health() == '100'
        assert swissbit_ssd.get_model() == 'SFSA160GM2AK2TO-I-8C-22K-STD'
        assert swissbit_ssd.get_firmware() == "SBR15004"
        assert swissbit_ssd.get_temperature() == '25'
        assert swissbit_ssd.get_serial() == "00006022750795000010"

    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell')
    def test_transcend_ssd(self, mock_exec):
        mock_exec.return_value = output_transcend_vendor
        transcend_ssd = SsdUtil('/dev/sda')
        transcend_ssd.vendor_ssd_info = mock_exec.return_value
        transcend_ssd.parse_vendor_ssd_info('Transcend')
        assert transcend_ssd.get_health() == '71'
        assert transcend_ssd.get_model() == 'TS32XBTMM1600'
        assert transcend_ssd.get_firmware() == "O0918B"
        assert transcend_ssd.get_temperature() == '40'
        assert transcend_ssd.get_serial() == "F318410080"

    @mock.patch('sonic_platform_base.sonic_ssd.ssd_generic.SsdUtil._execute_shell')
    def test_wdc_ssd(self, mock_exec):
        mock_exec.return_value = output_wdc_vendor
        wdc_ssd = SsdUtil('/dev/sda')
        assert wdc_ssd.get_health() == '98'
        assert wdc_ssd.get_model() == 'WDC PC SA530 SDASN8Y1T00'
        assert wdc_ssd.get_firmware() == "40103000"
        assert wdc_ssd.get_temperature() == '23'
        assert wdc_ssd.get_serial() == "2122FF441406"
