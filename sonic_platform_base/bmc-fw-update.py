#!/usr/bin/env python3

"""
BMC firmware update utility
Handles BMC firmware update process
"""

import sys

def main():
    try:
        import sonic_platform
        from sonic_py_common.logger import Logger

        logger = Logger('bmc-fw-update')

        if len(sys.argv) != 2:
            logger.log_error("Missing firmware image path argument")
            sys.exit(1)
        image_path = sys.argv[1]

        chassis = sonic_platform.platform.Platform().get_chassis()
        bmc = chassis.get_bmc()
        if bmc is None:
            logger.log_error("Failed to get BMC instance from chassis")
            sys.exit(1)

        logger.log_notice(f"Starting BMC firmware update with {image_path}")
        ret, (error_msg, updated_components) = bmc.update_firmware(image_path)
        if ret != 0:
            logger.log_error(f'Failed to update BMC firmware. Error {ret}: {error_msg}')
            sys.exit(1)

        logger.log_notice(f"Firmware updated successfully via the BMC. Updated components: {updated_components}")

        if bmc.get_firmware_id() in updated_components:
            logger.log_notice("BMC firmware updated successfully, restarting BMC...")
            ret, error_msg = bmc.request_bmc_reset()
            if ret != 0:
                logger.log_error(f'Failed to restart BMC. Error {ret}: {error_msg}')
                sys.exit(1)
            logger.log_notice("BMC firmware update completed successfully")

    except Exception as e:
        logger.log_error(f'BMC firmware update exception: {e}')
        sys.exit(1)

if __name__ == "__main__":
    main()
