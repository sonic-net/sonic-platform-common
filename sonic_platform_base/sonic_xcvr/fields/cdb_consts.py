
#CDB Related
CDB1_QUERY_STATUS = "Cdb1QueryStatus"
CDB1_STATUS = "Cdb1Status"
CDB1_CMD_STATUS = "Cdb1CmdStatus"
CDB1_IS_BUSY = "Cdb1IsBusy"
CDB1_HAS_FAILED = "Cdb1HasFailed"
CDB1_CMD_STATUS_FIELD = "Cdb1CmdStatus"
CDB1_COMMAND_RESULT ="Cdb1CommandResult"


#Firmware Info
CDB1_FIRMWARE_INFO = "Cdb1FirmwareInfo"
CDB1_FIRMWARE_STATUS = "Cdb1FirmwareStatus"
CDB1_BANKA_OPER_STATUS = "CdbBankAOperStatus"
CDB1_BANKB_OPER_STATUS = "CdbBankBOperStatus"
CDB1_BANKA_ADMIN_STATUS = "CdbBankAAdminStatus"
CDB1_BANKB_ADMIN_STATUS = "CdbBankBAdminStatus"
CDB1_BANKA_VALID_STATUS = "CdbBankAValidStatus"
CDB1_BANKB_VALID_STATUS = "CdbBankBValidStatus"
CDB1_IMAGE_INFO = "CdbImageInfo"
CDB1_FIRMWARE_VERSION = "Cdb1FirmwareVersion"
CDB1_BANKA_IMAGE_VERSION = "CdbBankAImageVersion"
CDB1_BANKB_IMAGE_VERSION = "CdbBankBImageVersion"
CDB1_BANKA_MAJOR_VERSION = "CdbBankAMajorVersion"
CDB1_BANKB_MAJOR_VERSION = "CdbBankBMajorVersion"
CDB1_BANKA_MINOR_VERSION = "CdbBankAMinorVersion"
CDB1_BANKB_MINOR_VERSION = "CdbBankBMinorVersion"
CDB1_BANKA_BUILD_VERSION = "CdbBankABuildVersion"
CDB1_BANKB_BUILD_VERSION = "CdbBankBBuildVersion"
CDB1_FACTORY_MAJOR_VERSION = "CdbFactoryMajorVersion"
CDB1_FACTORY_MINOR_VERSION = "CdbFactoryMinorVersion"
CDB1_FACTORY_BUILD_VERSION = "CdbFactoryBuildVersion"
CDB1_IMAGEA_VERSION_PRESENT = "CdbImageAVersionPresent"
CDB1_IMAGEB_VERSION_PRESENT = "CdbImageBVersionPresent"
CDB1_FACTIMG_VERSION_PRESENT = "CdbFactoryImgVersionPresent"


# Firmware Management
CDB_FIRMWARE_MGMT_FEATURES = "CdbFirmwareMgmt"
CDB_FIRMWARE_MGMT_ADV = "CdbFirmwareMgmtAdv"
CDB_MAX_DURATION_ENCODING = "CdbMaxDurationEncoding"
CDB_ABORT_CMD_SUPPORTED = "CdbAbortCmdSupported"
CDB_START_CMD_PAYLOAD_SIZE = "CdbStartCmdPayloadSize"
CDB_READ_WRITE_LENGTH_EXT = "CdbReadWriteLengthExt"
CDB_WRITE_MECHANISM = "CdbWriteMechanism"
CDB_READ_MECHANISM = "CdbReadMechanism"
CDB_MAX_DURATION_START = "CdbMaxDurationStart"
CDB_MAX_DURATION_ABORT = "CdbMaxDurationAbort"
CDB_MAX_DURATION_WRITE = "CdbMaxDurationWrite"
CDB_MAX_DURATION_COMPLETE = "CdbMaxDurationComplete"
CDB_MAX_DURATION_COPY = "CdbMaxDurationCopy"


LPL_PAGE = 0x9F
EPL_PAGE = 0xA0
EPL_MAX_PAGES = 16
PAGE_SIZE = 128
CDB_LPL_CMD_START_OFFSET = 128
RPL_DATA_START_OFFSET = 136
LPL_MAX_PAYLOAD_SIZE = 116
EPL_MAX_PAYLOAD_SIZE = 2048

CDB_MAX_ACCESS_HOLD_OFF_PERIOD = 4960 # tCDBF msec
CDB_MAX_CAPTURE_TIME = 100 # tCDBC msec
CDB_RUN_FIRMWARE_CMD_TIMEOUT = 15000 # Delay to switch to new firmware in msec
CDB_TIMEOUT_SAFETY_MARGIN = 5000 # Safety margin for timeouts in msec

#CDB Commands
CDB_CMD_ID_LEN = 2
CDB_QUERY_STATUS_CMD = 0x0000
CDB_ENTER_PASSWORD_CMD = 0x0001
CDB_PASSWORD_ERROR_CODE = 0x06
CDB_PASSWORD_ERROR_STATUS = 0x46
CDB_DEFAULT_PASSWORD = 0x00001011
# CMIS Password Entry Area: page 00h bytes 122-125 (linear offset 122 in lower
# memory), 32-bit host password written MSB-first. This is the standard,
# universally-supported way to unlock password-protected CDB/EEPROM access.
CDB_HOST_PASSWORD_ENTRY_OFFSET = 122
CDB_HOST_PASSWORD_ENTRY_SIZE = 4
# CMIS revision: page 00h byte 1, major = bits 7-4, minor = bits 3-0
# (e.g. 0x53 -> CMIS 5.3). Used to decide whether the PasswordCmdResult
# register below is defined for this module.
CDB_CMIS_REVISION = "CdbCmisRevision"
# PasswordCmdResult (00h:42.3-0) is only defined from CMIS 5.3 onward; on
# earlier modules those bits are reserved and must not be interpreted.
CDB_PASSWORD_RESULT_MIN_CMIS_REV = (5, 3)
# CMIS PasswordCmdResult register: page 00h byte 42, bits 3-0 (00h:42.3-0).
# Reports the result of the most recent password entry/change written to the
# Password Entry Area (00h:118-125). Writing the password only delivers it; its
# acceptance is reported asynchronously here (per CMIS 8.2.14).
CDB_PASSWORD_CMD_RESULT = "CdbPasswordCmdResult"
CDB_PASSWORD_CMD_RESULT_CODE = "CdbPasswordCmdResultCode"
CDB_PASSWORD_RESULT_NOT_SUPPORTED = 0x0    # not supported (legacy before CMIS 5.3)
CDB_PASSWORD_RESULT_MODULE_ACCEPTED = 0x1  # module password entry/change accepted
CDB_PASSWORD_RESULT_HOST_ACCEPTED = 0x2    # host password entry/change accepted
CDB_PASSWORD_RESULT_NOT_ACCEPTED = 0x3     # password entry not accepted
CDB_PASSWORD_RESULT_IN_PROGRESS = 0x8      # password validation in progress
# Poll bound for PasswordCmdResult after writing the Password Entry Area. The
# module updates the result within tWRITE and may reject reads (or report
# "in progress") until then; give it a small margin.
CDB_PASSWORD_RESULT_POLL_INTERVAL = 100    # msec
CDB_PASSWORD_RESULT_POLL_TIMEOUT = 1000    # msec
CDB_CHANGE_PASSWORD_CMD = 0x0002
CDB_ABORT_CMD = 0x0003
CDB_MODULE_FEATURE_CMD= 0x0004
CDB_GET_FIRMWARE_MGMT_FEATURES_CMD = 0x0041
CDB_GET_FIRMWARE_INFO_CMD = 0x0100
CDB_START_FIRMWARE_DOWNLOAD_CMD = 0x0101
CDB_ABORT_FIRMWARE_DOWNLOAD_CMD = 0x0102
CDB_WRITE_FIRMWARE_LPL_CMD = 0x0103
CDB_WRITE_FIRMWARE_EPL_CMD = 0X0104
CDB_COMPLETE_FIRMWARE_DOWNLOAD_CMD = 0x0107
CDB_COPY_FIRMWARE_IMAGE_CMD = 0x0108
CDB_RUN_FIRMWARE_IMAGE_CMD = 0x0109
CDB_COMMIT_FIRMWARE_IMAGE_CMD = 0x010A
