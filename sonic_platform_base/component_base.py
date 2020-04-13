#
# component_base.py
#
# Abstract base class for implementing a platform-specific class
# to interact with a chassis/module component (e.g., BIOS, CPLD, FPGA, etc.) in SONiC
#


class ComponentBase(object):
    """
    Abstract base class for implementing a platform-specific class
    to interact with a chassis/module component (e.g., BIOS, CPLD, FPGA, etc.)
    """

    def get_name(self):
        """
        Retrieves the name of the component

        Returns:
            A string containing the name of the component
        """
        raise NotImplementedError

    def get_description(self):
        """
        Retrieves the description of the component

        Returns:
            A string containing the description of the component
        """
        raise NotImplementedError

    def get_firmware_version(self):
        """
        Retrieves the firmware version of the component

        Returns:
            A string containing the firmware version of the component
        """
        raise NotImplementedError

    def get_available_firmware_version(self, image_path):
        """
        Retrieves the available firmware version of the component

        Args:
            image_path: A string, path to firmware image

        Returns:
            A string containing the available firmware version of the component
        """
        raise NotImplementedError

    def get_update_notification(self, image_path):
        """
        Retrieves a notification on what should be done in order to complete
        the component firmware update

        Args:
            image_path: A string, path to firmware image

        Returns:
            A string containing the component firmware update notification if required.
            By default 'None' value will be used, which indicates that no actions are required
        """
        return None

    def install_firmware(self, image_path):
        """
        Installs firmware to the component.
        It's user's responsibility to complete firmware update
        in case some extra steps are required (e.g., reboot, power cycle, etc.)

        Args:
            image_path: A string, path to firmware image

        Returns:
            A boolean, True if install was successful, False if not
        """
        raise NotImplementedError

    def update_firmware(self, image_path):
        """
        Updates firmware of the component.
        It's API's responsibility to complete firmware update
        in case some extra steps are required (e.g., reboot, power cycle, etc.)

        Args:
            image_path: A string, path to firmware image

        Raises:
            RuntimeError: update failed
        """
        raise NotImplementedError

    def is_delayed_firmware_update_supported(self, image_path):
        """
        Retrieves a value indicating whether immediate actions are required
        to complete the component firmware update (e.g., reboot, power cycle, etc.)

        Args:
            image_path: A string, path to firmware image

        Returns:
            A boolean, True if delayed firmware update supported, False if not
        """
        raise NotImplementedError
