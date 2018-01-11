#! /usr/bin/python
#-------------------------------------------------------------------------------
#
# Copyright 2012 Cumulus Networks, inc  all rights reserved
#
#-------------------------------------------------------------------------------
#
try:
    import sys
    import os
    import time
    import socket
    import re
except ImportError, e:
    raise ImportError (str(e) + "- required module not found")

#-------------------------------------------------------------------------------
#

class bcmshell (object):

    """Simple expect like class that connects to a BCM diag shell, exported as a
    socket fd by switchd, allowing users to run commands and extract delimited
    output.  bcmdiag opens the socket file, flushes the socket's read side and
    issues commands via bcmdiag.run().  The command output, upto the diag shell
    prompt, is read from the socket and returned to the caller."""

    version = "1.0"

    #---------------
    #
    def __init__(self, keepopen=False, timeout=10, opennow=False, logfileobj=None,
                 socketname="/var/run/docker-syncd/sswsyncd.socket", prompt='^drivshell>\s*$'):
        """Constructor:

        keepopen - indicates that switchd socket should be kept open between
        uses because the invoking application has a bunch of consecutive
        activity.  In this use case, the socket must be explicitly closed by
        bcmshell.close() to allow multiplexing of multiple applications.

        timeout - the time, in seconds, that bcmshell.run() will sit on the
        domain socket wait for read input.  Note that as long as the socket is
        handing us data, we'll keep reading for up <timeout> seconds.

        logfileobj - a file object that should log all issued commands.  None
        disables command logging; sys.stdout logs every command to stdout.
        logfileobj is flushed after every write.

        socketname - the name of the switchd socket file.

        prompt - the diag shell prompt that delimits the end of output"""

        if type(prompt) is not str:
            raise SyntaxError("bcmshell constructor prompt expects an re string")
        else:
            self.re_prompt = re.compile(prompt, re.MULTILINE)
            self.re_connectprompt = re.compile("bcmshell\r\n" + prompt, re.MULTILINE)

        if timeout <= 0:
            raise ValueError("bcmshell.timeout must be > 0")
        else:
            self.timeout = timeout
            if timeout > 180:
                sys.stderr.write("warning: bcmshell.timeout, %s, is > 180s\n" %
                                 str(self.timeout))

        if not os.access(socketname, os.F_OK):
            raise ValueError("socket %s does not exist" % socketname)
        elif not os.access(socketname, os.R_OK | os.W_OK):
            raise ValueError("missing read/write permissions for %s" % socketname)
        else:
            self.socketname = socketname

        if logfileobj is None:
            self.logfileobj = None
        elif type(logfileobj) is not file:
            raise TypeError("bcmshell.logfileobj must be a file object not %s" %
                            type(logfileobj))
        elif 'w' not in logfileobj.mode:
            raise TypeError("bcmshell.logfileobj is not a writeable file object")
        else:
            self.logfileobj = logfileobj
            
        self.keepopen = keepopen
        self.socketobj = None
        self.buffer = ''

        # text editing tools
        #
        self.re_oneline          = re.compile('\n\s+')
        self.re_reg_parse_raw    = re.compile('^[\w()]+\.(.+)\[.*=(.*)$')
        self.re_reg_parse_fields = re.compile('^[\w()]+\.(.+)\[.*\<(.*)\>')
        self.re_get_field        = re.compile('^(.+)=(.+)')
        self.re_table_header     = re.compile('^.*:[ <]+', re.MULTILINE)
        self.re_table_trailer    = re.compile('[ >]+$', re.MULTILINE)
        self.re_conv             = re.compile(r'(\d+|\D+)')

        # interface name conversion
        #
        self.modname = dict()
        for I in range(0, 63):
            self.modname['xe' + str(I)] = 'swp' + str(I)

        # open socket if required
        #
        if opennow and keepopen:
            self.__open__()

    #---------------
    #
    def __del__(self):

        """Destructor: flush and close all files that we opened"""

        try:
            self.close()
        except:
            pass

    #---------------
    #
    def __str__(self):

        """Return object state in human-readable form"""
        
        s = []
        s.append(repr(self))
        s.append('version: ' + self.version)
        s.append('keepopen: ' + str(self.keepopen))
        s.append('timeout: ' + str(self.timeout) + ' seconds')
        s.append('logfileobj: ' + str(self.logfileobj))
        s.append('socketname: ' + str(self.socketname))
        s.append('socketobj: ' + str(self.socketobj))
        s.append('prompt: \"' + str(self.re_prompt.pattern) + '\"')
        s.append('buffer (last 100 chars): ' + str(self.buffer)[-100:])
        return '\n'.join(s)

    #---------------
    #
    def getreg(self, reg, fields=False):

        """Get device register(s) by name.

        The general format in which registers are returned from the shell is
        reg_name(N).M=V for raw values and reg_name(N).M=<F1=V1,F2=V2> where N
        is an array index, M is a module or port name, V is a value, and F is a
        field name.  Register/field values are all converted to unsigned
        integers.  There is a built in name converstion fucntion to change
        Broadcom "xe*" port names to "swp*" names that match the kernel.

        bcmshell.getreg('reg_name') returns dict of lists of values.  As an
        optimization, if there is only one entry in the dict, only the list of
        values is returned and if there is only one entry in each list, only the
        values are returned

        Examples:
        bcmshell.getreg('cmic_config') returns a value...
            1057759299.

        bcmshell.getreg('protocol_pkt_control') returns a list of values...
            [0, 0, 0, ..., 0]

        bcmshell.getreg('egr_mtu') returns a dict of values....
            {'cpu0': 0x3fff,
             'xe0': 0x3fff,
             ...
             'lb0': 0x3fff}

        bcmshell.getreg('pg_min_cell') returns a dict of lists of values....
            {'cpu0:'[0, 0, 0, 0, 0, 0, 0, 0],
             'xe0': [0, 0, 0, 0, 0, 0, 0, 0],
             ...
             'lb0': [0, 0, 0, 0, 0, 0, 0, 0]}


        bcmshell.getreg('reg_name', True) returns dict of lists of dicts of
        field/values.  The same optimizations used for raw values apply.

        Examples:
        bcmshell.getreg('cmic_config', True) returns a dict of field/values...
            {'IGNORE_MMU_BKP_TXDMA_PKT': 0, 
             'EN_SER_INTERLEAVE_PARITY': 1,
             'MIIM_ADDR_MAP_ENABLE': 1,
             'IGNORE_MMU_BKP_REMOTE_PKT': 0,
             ...
             'DMA_GARBAGE_COLLECT_EN': 0}

        bcmshell.getreg('protocol_pkt_control', True) returns 
            [{'SRP_PKT_TO_CPU':0, 'SRP_FWD_ACTION':0,... 'ARP_REPLY_DROP':0},
             {'SRP_PKT_TO_CPU':0, 'SRP_FWD_ACTION':0,... 'ARP_REPLY_DROP':0},
             ...
             {'SRP_PKT_TO_CPU':0, 'SRP_FWD_ACTION':0,... 'ARP_REPLY_DROP':0}]

        bcmshell.getreg('egr_mtu', fields=True) returns a dict of dicts...
            {'cpu0': {'MTU_SIZE',0x3fff, 'MTU_ENABLE',0},
            'xe0': {'MTU_SIZE',0x3fff, 'MTU_ENABLE',0},
            ...
            'lb0':  {'MTU_SIZE',0x3fff, 'MTU_ENABLE',0}}

        bcmshell.getreg('pg_min_cell') returns a dict of lists of values....
            {'cpu0:'[{'PG_MIN':0}, {'PG_MIN':0},... {'PG_MIN':0}],
             'xe0:'[{'PG_MIN':0}, {'PG_MIN':0},... {'PG_MIN':0}],
             ...
             'lb0:'[{'PG_MIN':0}, {'PG_MIN':0},... {'PG_MIN':0}]}
        """
        
        # make sure everything is sane and read the register
        #
        if type(reg) is not str:
            raise TypeError("expecting string argument to bmcdiag.getreg(reg)")
        elif reg.find('\n') >= 0:
            raise ValueError("unexpected newline in bmcdiag.getreg(%s)" % reg )
        elif reg.find('\s') >= 0:
            raise ValueError("unexpected whitespace in bmcdiag.getreg(%s)" % reg)

        if fields:
            t = self.run('getreg ' + reg)
        else:
            t = self.run('getreg raw ' + reg)

        if 'Syntax error parsing' in t:
            raise RuntimeError('\"%s\" is not a register' % reg)

        # get the results into a list
        #
        t = self.re_oneline.sub('', t)
        t = t.split('\n')
        if t[-1] is '':
            t.pop()

        # get the results into a dict (module) of lists (array) of values/fields
        #
        def __parse_reg__(text, fields=False):
            if fields:
                m = self.re_reg_parse_fields.search(text)
                s = m.group(2).split(',')
                t = dict([self.__get_field__(S) for S in s])
            else:
                m = self.re_reg_parse_raw.search(text)
                t = int(m.group(2), 16)
            return(self.modname.get(m.group(1), m.group(1)), t)

        t = [__parse_reg__(T, fields) for T in t]
        d = dict()
        for I in t:
            if I[0] in d:
                d[I[0]].append(I[1])
            else:
                d[I[0]] = [I[1]]

        # now optimize the return
        #
        for I in iter(d):
            if len(d[I]) is 1:
                d[I] = d[I][0]

        if len(d) is 1:
            return d.values()[0]
        else:
            return d


    #---------------
    #
    def gettable(self, table, fields=False, start=None, entries=None):

        """Get device memory based table(s) by name.  Tables are returned as a
        list of value/field-dict.  Table entry/field values are converted into
        unsigned integers.  If "fields" is set to True, we return a list of
        dictionaries of field/value.

        Examples:
        bcmshell.gettable('egr_ing_port') returns
            [0, 0, 0, ... 0]

        bcmshell.gettable('egr_ing_port', True) returns
            [{'HIGIG2': 0, 'PORT_TYPE': 0},
             {'HIGIG2': 0, 'PORT_TYPE': 0},
             {'HIGIG2': 0, 'PORT_TYPE': 0},
             ...
             {'HIGIG2': 0, 'PORT_TYPE': 0}]
        """
        
        if type(table) is not str:
            raise TypeError("bcmshell.gettable(table) expects string not %s" %
                            type(table))
        elif table.find('\n') >= 0:
            raise ValueError("unexpected newline in bmcshell.gettable(%s)" %
                             table )
        elif table.find('\s') >= 0:
            raise ValueError("unexpected whitespace in bmcshell.gettable(%s)" %
                             table)

        cmd = 'dump all'
        if not fields:
            cmd += ' raw'
        cmd += " %s" % table
        if start != None or entries != None:
            cmd += " %d" % (start or 0)
            cmd += " %d" % (entries or 1)
        
        t = self.run(cmd)

        if 'Unknown option or memory' in t:
            raise RuntimeError('\"%s\" is not a table' % table)

        if 'out of range' in t:
            err = table
            if start != None or entries != None:
                err += " %d" % (start or 0)
                err += " %d" % (entries or 1)
            raise IndexError('\"%s\" table index is out of range' % err)

        # get all of the return into a list
        #
        t = self.re_oneline.sub('', t)
        t = self.re_table_header.sub('', t)
        t = self.re_table_trailer.sub('', t)
        t = t.split('\n')
        if t[-1] is '':
            t.pop()

        # parse the contents
        #
        def __parse_table__(text, fields=False):
            if fields:
                t = text.split(',')
                v = [self.__get_field__(T) for T in t]
                return dict(v)
            else:
                t = text.split()
                v = 0
                for I in range(len(t)):
                    v += (int(t[I], 16) << (32 * I))
                return v
        t = [__parse_table__(T, fields) for T in t]

        return t

    #---------------
    #
    def cmd(self, cmd):

        """Run a command and print the results"""

        s = self.run(cmd)
        if 'Unknown command:' in s:
            raise ValueError(s)
        print s

                
    #---------------
    #
    def prettyprint(self, d, level=0):

        """Print the structured output generated by getreg and gettable in a 
        human readable format"""

        s = level * 8 * " "
        if type(d) is dict:
            for I in sorted(d, key=self.__name_conv__):
                if type(d[I]) is int:
                    print "%s %30s: " % (s, I),
                else:
                    print "%s %s:" % (s, I) 
                self.prettyprint(d[I], (level + 1))
        elif type(d) is list:
            for I in range(len(d)):
                i = "[" + str(I) + "]"
                if type(d[I]) is int or type(d[I]) is long:
                    print "%s %10s: " % (s, i),
                else:
                    print "%s %s:" % (s, i) 
                self.prettyprint(d[I], (level + 1))
        else:
            print "%s" % (hex(d))

                
    #---------------
    #
    def close(self):

        """Close the socket object"""

        if self.socketobj is not None:
            self.socketobj.shutdown(socket.SHUT_RDWR)
            self.socketobj.close()
            self.socketobj = None

    #---------------
    #
    def run(self, cmd):

        """Issue the command to the diag shell and collect the return data until
        we detect the prompt.  cmd must be a string and must not include a
        newline, i.e. we expect a single command to be run per call."""

        if type(cmd) is not str:
            raise TypeError("expecting string argument to bmcdiag.run(cmd)")
        elif cmd.find('\n') >= 0:
            raise ValueError("unexpected newline in bmcdiag.run(cmd)")

        self.__open__()
        try:
            self.socketobj.sendall(cmd + '\n')
        except socket.error as (errno, errstr):
            raise IOError("unable to send command \"%s\", %s" % (cmd, errstr))

        self.buffer = ''
        self.socketobj.settimeout(self.timeout)
        quitting_time = time.time() + self.timeout
        while True:
            try:
                self.buffer += self.socketobj.recv(4096)
            except socket.timeout:
                raise RuntimeError("recv stalled for %d seconds" % self.timeout)
            found = self.re_prompt.search(self.buffer)
            if found:
                break
            if time.time() > quitting_time:
                raise RuntimeError("accepting input for %d seconds" % self.timeout)

        if found.end(0) != len(self.buffer):
            raise RuntimeError("prompt detected in the middle of input")
        
        if not self.keepopen:
            self.close()
        return self.buffer[:found.start(0)]

    #---------------
    #
    def __name_conv__(self, s):
        l = self.re_conv.findall(s)
        for I in range(len(l)):
            if l[I].isdigit():
                l[I] = int(l[I])
        return l

    #---------------
    #
    def __get_field__(self, text):
        m = self.re_get_field.search(text)
        return (m.group(1), int(m.group(2), 16))
        
    #---------------
    #
    def __open__(self):
        
        """Open the bcm diag shell socket exported by switchd.  Complete any
        dangling input by issuing a newline and flush the read side in case the
        last user left something lying around.  No-op if the socket is already
        open.  NOTE: socket.connect is non-blocking, so we need to exchange
        a command with the bcm diag shell to know that we've actually obtained
        socket ownership."""

        if self.socketobj is None:
            timeout = self.timeout
            while True:
                try:
                    self.socketobj = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    self.socketobj.settimeout(self.timeout)
                    self.socketobj.connect(self.socketname)
                except socket.error as (errno, errstr):
                    if timeout == 0:
                        raise IOError("unable to open %s, %s" % (self.socketname, errstr))
                    time.sleep(1)
                    timeout -= 1
                else:
                    break;


            # flush out the socket in case it was left dirty
            try:
                self.socketobj.sendall('echo bcmshell\n')
                quitting_time = time.time() + self.timeout
                buf = ''
                while True:
                    try:
                        buf += self.socketobj.recv(1024)
                    except socket.timeout:
                        raise IOError("unable to receive data from %s for %d seconds" %
                                      (self.socketname, self.timeout))

                    found = self.re_connectprompt.search(buf)
                    if found:
                        break
                    if time.time() > quitting_time:
                        raise IOError("unable to flush %s for %d seconds" %
                                      (self.socketname, self.timeout))

            except socket.error as (errno, errstr):
                raise IOError("Socket error: unable to flush %s on open: %s" % (self.socketname, errstr))
            except IOError as e:
                raise IOError("unable to flush %s on open: %s" % (self.socketname, e.message))
            except:
                raise IOError("unable to flush %s on open" % self.socketname)
