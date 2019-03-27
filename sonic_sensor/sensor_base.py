#!/usr/bin/python

#########################################################################
#									#
# sensor_base.py							#
#									#
# Abstract base class for implementing a platform-specific class	#
# to interact with sensors available from different sources in SONiC	#
#########################################################################

import subprocess
import sys

class SensorBase(object):
        """
        Abstract base class for interfacing with a sensor
        """
        def __init__(self):
                self.ssh_connection = None

        def get_local_data(self):
                """
                Retrieves output derived from inbuilt sensors detected in SONiC CPU
                Returns:
                        string: voltages, fans and  temps output derived from inbuilt sensors detected in SONiC CPU
                """
                sensor_cmd = "sensors"
                p = subprocess.Popen(sensor_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate()
                ## Wait for end of command. Get return returncode ##
                returncode = p.returncode
                ## if no error, get the sensor result ##
                if returncode == 0:
                        print("*************** SONiC CPU OUTPUT ***********")
                        print(stdout.rstrip("\n"))
                else:
			print('exit code: {}. Error -> {}'.format(returncode, stderr))
                        sys.stderr.write(stderr)

        def get_data_api(self):
                self.get_local_data()
