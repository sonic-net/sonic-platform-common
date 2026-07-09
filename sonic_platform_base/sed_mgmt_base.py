"""
    sed_mgmt_base.py

    Base class for SED (Self-Encrypting Drive) password management.
    Platform-specific SedMgmt implementations override the abstract getters.
"""


import subprocess
from sonic_py_common.logger import Logger


logger = Logger('sed_mgmt_base')


SED_CONFIG_PATH = '/etc/sonic/sed_config.conf'


def _read_sed_config_value(key):
    """Read a key=value from SED config file. Returns value or None."""
    try:
        with open(SED_CONFIG_PATH) as f:
            for line in f:
                line = line.strip()
                if line.startswith(key + '='):
                    return line.split('=', 1)[1].strip() or None
    except Exception:
        pass
    return None


class SedMgmtBase:
    """
    Base class for SED password management.
    Implements change_sed_password and reset_sed_password using abstract getters.
    """

    SED_PW_CHANGE_SCRIPT = '/usr/local/bin/sed_pw_change.sh'
    SED_PW_RESET_SCRIPT = '/usr/local/bin/sed_pw_reset.sh'

    def get_min_sed_password_len(self):
        """
        Return minimum allowed SED password length.

        Returns:
            int: Minimum length (e.g. 8).
        """
        raise NotImplementedError

    def get_max_sed_password_len(self):
        """
        Return maximum allowed SED password length.

        Returns:
            int: Maximum length (e.g. 124).
        """
        raise NotImplementedError

    def get_default_sed_password(self):
        """
        Return the platform default SED password.

        Returns:
            str: Default password, or None on failure.
        """
        raise NotImplementedError

    def get_tpm_bank_a_address(self):
        """
        Return TPM bank A persistent handle for SED password (e.g. 0x81010001).

        Returns:
            str: TPM bank A address.
        """
        return _read_sed_config_value('tpm_bank_a')

    def get_tpm_bank_b_address(self):
        """
        Return TPM bank B persistent handle for SED password (e.g. 0x81010002).

        Returns:
            str: TPM bank B address.
        """
        return _read_sed_config_value('tpm_bank_b')

    def change_sed_password(self, new_password):
        """
        Change the SED password. Validates length and runs the common script.

        Args:
            new_password (str): The new password to set.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            min_len = self.get_min_sed_password_len()
            max_len = self.get_max_sed_password_len()
            if len(new_password) < min_len or len(new_password) > max_len:
                logger.log_error(f"SED password length is not valid: {len(new_password)}. min_len: {min_len}, max_len: {max_len}")
                return False
            bank_a = self.get_tpm_bank_a_address()
            bank_b = self.get_tpm_bank_b_address()
            if not bank_a or not bank_b:
                logger.log_error(f"TPM bank address is not valid: bank_a: {bank_a}, bank_b: {bank_b}. Check {SED_CONFIG_PATH}.")
                return False
            subprocess.check_call(
                [self.SED_PW_CHANGE_SCRIPT, '-a', bank_a, '-b', bank_b, '-p', new_password],
                universal_newlines=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            return True
        except Exception as e:
            logger.log_error(f"Failed to change SED password: {e}")
            return False

    def reset_sed_password(self):
        """
        Reset the SED password to the platform default.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            default_pw = self.get_default_sed_password()
            if not default_pw:
                logger.log_error("Failed to get default SED password.")
                return False
            bank_a = self.get_tpm_bank_a_address()
            bank_b = self.get_tpm_bank_b_address()
            if not bank_a or not bank_b:
                logger.log_error(f"TPM bank address is not valid: bank_a: {bank_a}, bank_b: {bank_b}. Check {SED_CONFIG_PATH}.")
                return False
            subprocess.check_call(
                [self.SED_PW_RESET_SCRIPT, '-a', bank_a, '-b', bank_b, '-p', default_pw],
                universal_newlines=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            return True
        except Exception as e:
            logger.log_error(f"Failed to reset SED password: {e}")
            return False
