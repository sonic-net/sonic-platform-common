"""
    cdb.py

    Implementation of CDB codes
"""

from ...codes.xcvr_codes import XcvrCodes

class CdbCodes(XcvrCodes):
    CDB_IN_PROGRESS = {
        0x00: "Reserved",
        0x01: "Command is captured but not processed",
        0x02: "Command checking is in progress",
        0x03: "Command execution is progress",
        0x04: "Reserved",
        0x2F: "Reserved",
        0x30: "Custom",
        0x3F: "Custom"
    }

    CDB_CMD_SUCCESS = {
        0x00: "Reserved",
        0x01: "Command completed successfully",
        0x02: "Reserved",
        0x03: "Previous CMD was ABORTED by CMD Abort",
        0x04: "Reserved",
        0x1F: "Reserved",
        0x20: "Custom",
        0x3F: "Custom"
    }

    CDB_CMD_FAILED = {
        0x00: "Reserved",
        0x01: "CMDID unknown",
        0x02: "Parameter range error or parameter not supported",
        0x03: "Previous CMD was not properly ABORTED (by CMD Abort)",
        0x04: "Command checking time out",
        0x05: "CdbChkCode Error",
        0x06: "Password related error (command specific meaning)",
        0x07: "Command not compatible with operating status",
        0x08: "Reserved",
        0x1F: "Reserved",
        0x20: "For individual STS command or task error",
        0x3F: "Custom"
    }

    CDB_QUERY_STATUS = {
        0x00: "Module Boot up",
        0x01: "Host Password Accepted",
        0x10: "Module Password Accepted"
    }

    CDB_WRITE_METHOD = {
        0x00: "None",
        0x01: "LPL",
        0x02: "EPL",
        0x03: "LPL and EPL"
    }

    CDB_READ_METHOD = {
        0x00: "None",
        0x01: "LPL",
        0x02: "EPL",
        0x03: "LPL and EPL"
    }

