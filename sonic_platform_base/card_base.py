#
# card_base.py
#
# Abstract base class for implementing a platform-specific class with which
# to interact with a card in SONiC chassis
#

class CardBase(object):
    """
    Abstract base class for implementing a platform specific class to
    represent a control-card, line-card or fabric-card of a chassis
    """

    # Possible card types
    MODULE_TYPE_CONTROL = "CONTROL-CARD"
    MODULE_TYPE_LINE    = "LINE-CARD"
    MODULE_TYPE_FABRIC  = "FABRIC-CARD"

    def get_name(self):
        """
        Retrieves the name of the card

        Returns:
            string: The name of the card
        """
        raise NotImplementedError

    def get_description(self):
        """
        Retrieves the description of the card

        Returns:
            string: The description of the card
        """
        raise NotImplementedError

    def get_instance(self):
        """
        Retrieves the slot where the card is present

        Returns:
            string: slot representation, usually number
        """
        raise NotImplementedError

    def get_type(self):
        """
        Retrieves the type of the card

        Returns:
            string: module-type MODULE_TYPE_CONTROL, MODULE_TYPE_LINE etc
        """
        raise NotImplementedError

    def get_status(self):
        """
        Retrieves the status of the card

        Returns:
            string: The status-string of the card
        """
        raise NotImplementedError

    def reboot_card(self):
        """
        Request to reboot/reset the card

        Returns:
            bool: True if the request has been successful, False if not
        """
        raise NotImplementedError

    def set_admin_state(self, up):
        """
        Request to keep the card in administratively up/down state

        Returns:
            bool: True if the request has been successful, False if not
        """
        raise NotImplementedError
