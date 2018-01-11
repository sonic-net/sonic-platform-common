#!/usr/bin/python
# Copyright 2012 Cumulus Networks LLC, all rights reserved

try:
    import os
    import exceptions
    import binascii
    import subprocess
except ImportError, e:
    raise ImportError (str(e) + "- required module not found")

i2c_root = '/sys/class/i2c-adapter/'
mtd_root = '/dev/mtd'
dts_root = '/proc/device-tree/'
sys_dev  = '/sys/devices/'

#
# This routine takes a token list containing the desired eeprom types
# (e.g. 'sfp', 'psu', 'board'), and returns a dict of {[dts path:(dev attrs)]}
# for the corresponding eeproms. For those accessible via i2c, the attrs
# will contain (i2c bus index, i2c device number).  For those mounted to
# /dev/mtd, the attrs will be (mtd partition number).
#
def get_dev_attr_from_dtb(tokens):

    dts_paths = []
    i2c_devices = []
    sub_devices = []

    eep_dict = {}

    #
    # first try i2c
    #
    try:
        ph = subprocess.Popen(['/bin/ls', '-R', dts_root],
                              stdout=subprocess.PIPE,
                              shell=False, stderr=subprocess.STDOUT)
        cmdout = ph.communicate()[0]
        ph.wait()
    except OSError, e:
        raise OSError("cannot access directory")

    lines = cmdout.splitlines()
    for I in lines:
        if not I.endswith(':') or 'i2c' not in I:
            continue

        I = I.rstrip(':\n\r')
        last = I.split('/')[-1]
        if 'i2c' in last:
            depth = I.count('i2c')
            while len(sub_devices) < depth:
                sub_devices.append([])
            sub_devices[depth-1].append(I)
        elif 'eeprom' in last:
            dts_paths.append(I)

    # re-order the device heirarchy and build the device list
    for i in sub_devices:
        for j in i:
            i2c_devices.append(j)

    for eep in dts_paths:
        instance = ''
        if os.path.isfile('/'.join([eep, 'label'])):
            F = open('/'.join([eep, 'label']), "rb")
            instance = F.read().partition('_eeprom')[0]
            F.close()

        # check for read-only
        read_only = os.path.isfile('/'.join([eep, 'read-only']))

        for t in tokens:
            if t not in eep and t not in instance:
                continue

            # get the i2c idx by matching the path prefix
            i2c_idx = i2c_devices.index(eep.rsplit('/', 1)[0])

            # read the reg
            reg_path = '/'.join([eep, 'reg'])
            F = open(reg_path, "rb")
            o = F.read()
            reg = binascii.b2a_hex(o)[-2:]
            F.close()

            eep_dict[eep] = {'type': 'i2c', \
                             'dev-id': i2c_idx, \
                             'reg': reg, \
                             'ro': read_only}
            break


    #
    # now try flash
    #
    try:
        ph = subprocess.Popen(['/bin/grep', '-r', 'eeprom', dts_root],
                              stdout=subprocess.PIPE,
                              shell=False, stderr=subprocess.STDOUT)
        cmdout = ph.communicate()[0]
        ph.wait()
    except OSError, e:
        raise OSError("cannot access directory")

    lines = cmdout.splitlines()
    for I in lines:
        if 'flash' not in I or 'label' not in I:
            continue

        eep = I.partition(dts_root)[2].rpartition('label')[0]
        full_eep = '/'.join([dts_root, eep])
        F = open('/'.join([full_eep, 'label']), "rb")
        instance = F.read().partition('_eeprom')[0]
        F.close()

        read_only = os.path.isfile('/'.join([full_eep, 'read-only']))

        for t in tokens:
            if t not in instance:
                continue

            mtd_n = eep.partition('partition@')[2].rstrip('/')
            eep_dict[full_eep] = {'type': 'mtd', \
                                  'dev-id': mtd_n, \
                                  'ro': read_only}

    return eep_dict


def dev_attr_to_path(dev_attrs):
    dev_path = ''
    if dev_attrs['type'] == 'i2c':
        dev_path = i2c_root + 'i2c-' + str(dev_attrs['dev-id']) + '/' + \
                   str(dev_attrs['dev-id']) + '-00' + str(dev_attrs['reg']) + \
                   '/' + 'eeprom'
    elif dev_attrs['type'] == 'mtd':
        dev_path = mtd_root + dev_attrs['dev-id']

    return dev_path
