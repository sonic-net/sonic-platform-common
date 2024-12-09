'''
    local_users_passwords_reset_base.py

    Abstract base class for implementing platform-specific
    local users' passwords reset base functionality for SONiC
'''
try:
    import json
    import subprocess

    from sonic_py_common.logger import Logger
except ImportError as e:
    raise ImportError (str(e) + "- required module not found")

# Global logger class instance
logger = Logger()


DEFAULT_USERS_FILEPATH = '/etc/sonic/default_users.json'


class LocalUsersConfigurationResetBase(object):
    """
    Abstract base class for resetting local users' passwords on the switch
    """
    def should_trigger(self):
        '''
        define the condition to trigger
        '''
        # the condition to trigger start() method, the default implementation will be by checking if a long reboot press was detected.
        raise NotImplementedError

    @staticmethod
    def reset_password(user, hashed_password, expire=False):
        '''
        This method is used to reset the user's password and expire it (optional) using Linux shell commands.
        '''
        # Use 'chpasswd' shell command to change password
        subprocess.call([f"echo '{user}:{hashed_password}' | sudo chpasswd -e"], shell=True)
        if expire:
            # Use 'passwd' shell command to expire password
            subprocess.call(['sudo', 'passwd', '-e', f'{user}'])

    def start(self):
        '''
        The functionality defined is to restore original password and expire it for default local users.
        It is done by reading default users file and resetting passwords using Linux shell commands.
        '''
        default_users = {}

        # Fetch local users information from default_users
        with open(DEFAULT_USERS_FILEPATH) as f:
            default_users = json.load(f)

        logger.log_info('Restoring default users\' passwords and expiring them')
        for user in default_users.keys():
            hashed_password = default_users.get(user, {}).get('password')
            if hashed_password:
                self.reset_password(user, hashed_password, expire=True)
