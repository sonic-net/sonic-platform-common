from ...cdb.cdb_fw import CdbFwHandler

# Vendor custom CDB handler inheriting base community handler
class BaillyCdbFwHandler(CdbFwHandler):
    def __init__(self, reader, writer, cdb_map):
        super().__init__(reader, writer, cdb_map)

    # Reuse parent implementation for consistent opcodes (no override needed)
    # Override single opcode method only if Bailly hardware has different logic
    def write_epl_block(self, address, data):
        # Example: OE firmware strip 4-byte header, vendor custom logic
        stripped = data[4:]
        return super().write_epl_block(address, stripped)
    # Override start download to inject CPO partition ID (0x0101)
    def start_fw_download(self, filepath):
        # Inject CPO partition info before parent download initialization
        # Todo
        return super().start_fw_download(filepath)