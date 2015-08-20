# Copyright (C) 2015 Job Snijders <job@instituut.net>
# Copyright (C) 2015 NORDUnet A/S
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

import socket

from irrexplorer import irrparser


DEFAULT_PORT = 43


class NRTMError(Exception):
    pass



class NRTMStreamer(object):
    """nrtm client class"""
    def __init__(self, host, source, start_serial, port=DEFAULT_PORT):

        self.host = host
        self.source = source
        self.serial = start_serial
        self.port = port


    def nrtm_connect(self):

        (family, socktype, proto, canonname, sockaddr) = socket.getaddrinfo(self.host, self.port, 0, socket.SOCK_STREAM)[0]
        s = socket.socket(family, socktype, proto)
        s.connect(sockaddr)
        f = s.makefile()
        f.write('!!\n!nIRRExplorer\n')
        f.flush()
        #f.write('-k -g {}:3:{}-LAST\n'.format(self.source, self.serial))
        f.write('-g {}:3:{}-LAST\n'.format(self.source, self.serial))
        f.flush()
        return f


    def stream(self):

        data_source = self.nrtm_connect()
        #data_source = open('nrtm.dump')

        for line in data_source:

            if not line.strip():
                continue # blank line

            if line.startswith('%'):
                # print '>>', line,
                c_line = line[1:].strip()
                if c_line == '':
                    continue # blank comment

                cl = c_line.lower()

                if cl.startswith('start'):
                    print c_line
                elif cl.startswith(('error','warning')):
                    raise NRTMError(c_line)
                elif cl.startswith('end'):
                    raise StopIteration
                else:
                    print 'Did not understand the following comment line:'
                    print line,
                continue

            if line.startswith(('#', 'C')):
                continue

            if line.startswith(('ADD', 'DEL')):
                tag, serial = line.strip().split(' ')
                obj = irrparser.irrParser(data_source).next()
                if obj:
                    yield tag, int(serial), obj
                else:
                    yield None, None, (None, (None, None, None))

            else:
                print 'Did not understand the following line:'
                print line,


# Streaming and data source needs better seperation for testing

# if __name__ == '__main__':
#     f = open('nrtm.dump')
#     for tag, serial, (obj_type, obj_data) in nrtmParser(f):
#         obj, data, source = obj_data
#         print tag, serial, obj_type, obj, source

