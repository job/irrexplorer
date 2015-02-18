# Copyright (C) 2015 Job Snijders <job@instituut.net>
#
# This file is part of IRR Explorer
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from irrexplorer import parser
import socket

class client(object):
    """nrtm client class"""
    def __init__(self, serial=None, serialoverride=None, dump=None, nrtmhost=None, nrtmport=43):
        super(client, self).__init__()
        if serialoverride is not None:
            self.serial = serialoverride
        else:
            self.setserialfrom(serial)
        if nrtmhost:
            self.host = nrtmhost
            self.port = nrtmport

        if dump:
            self.dump = file(dump)

    def setserialfrom(self, f):
        self.serial=int(open(f).read().strip())

    def get(self):
        if self.dump:
            for obj in parser.parse_dump(self.dump):
                yield 'ADD', 0, obj
        self.dump = None # not necessary
        self.serial = self.serial + 1
        if self.host:
            (family, socktype, proto, canonname, sockaddr) = socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM)[0]
            s = socket.socket(family, socktype, proto)
            s.connect(sockaddr)
            f = s.makefile()
            f.write('-k -g {}:3:{}-LAST\n'.format('REGRESSION', self.serial))
            f.flush()
            for cmd, serial, obj in parser.parse_nrtm_stream(f):
                self.serial = serial
                yield cmd, serial, obj


