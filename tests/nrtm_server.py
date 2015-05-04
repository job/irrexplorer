#!/usr/bin/env python
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

"""
    Small script to emulate a NRTM server
    Copyright (C) 2015 Job Snijders <job@instituut.net>

    Registry name: REGRESSION :-)

    Get a sample or NRTM:
        echo -k -g RADB:3:$(echo $(curl -s \
    ftp://ftp.radb.net/radb/dbase/RADB.CURRENTSERIAL) - 5 | bc)-LAST \
    | nc whois.radb.net 43

"""

import time
import socket
from thread import start_new_thread

host = '::'
port = 4444
flowinfo = 0
scopeid = 0
sockaddr = (host, port, flowinfo, scopeid)

nrtm_data_1 = """%START Version: 3 regression 1983029-1983034

ADD 1983029

route:      180.211.93.0/24
descr:      route-object of PT. KINGS NETWORK INDONESIA
            Internet Services Provider
            Bekasi, ID
origin:     AS45725
notify:     windhu@i.net.id
mnt-by:     MAINT-AS45725
changed:    windhu@i.net.id 20150209  #11:51:47Z
source:     REGRESSION

ADD 1983030

route:      180.211.92.0/24
descr:      route-object of PT. KINGS NETWORK INDONESIA
            Internet Services Provider
            Bekasi, ID
origin:     AS45725
notify:     windhu@i.net.id
mnt-by:     MAINT-AS45725
changed:    windhu@i.net.id 20150209  #11:52:15Z
source:     REGRESSION

ADD 1983031

mntner:     MAINT-AS198492
descr:      rPeer Ltd
admin-c:    Denis Nuja
tech-c:     Denis Nuja
upd-to:     denis@falizmaj.org
mnt-nfy:    denis@falizmaj.org
auth:       CRYPT-PW HIDDENCRYPTPW
mnt-by:     MAINT-AS198492
changed:    e@e.net 20150203
source:     REGRESSION

ADD 1983032

aut-num:    AS198492
as-name:    RPEER-1
descr:      rPeer Ltd
admin-c:    Denis Nuja
tech-c:     Denis Nuja
mnt-by:     MAINT-AS198492
changed:    d@d.net
source:     REGRESSION

ADD 1983033

route:      91.235.170.0/23
descr:      rPeer Ltd
origin:     AS198492
mnt-by:     MAINT-AS198492
changed:    d@d.com
source:     REGRESSION

ADD 1983034

aut-num:    AS198492
as-name:    RPEER-1
descr:      rPeer Ltd
import:     from AS174   accept any
import:     from AS9119   accept any
import:     from AS198785   accept any
export:     to AS174   announce AS198492
export:     to AS9119   announce AS198492
export:     to AS198785   announce AS198492
admin-c:    Denis Nuja
tech-c:     Denis Nuja
mnt-by:     MAINT-AS198492
changed:    d@d.com
source:     REGRESSION

%END REGRESSION
"""

nrtm_data_2 = """
ADD 1983035

route:          5.8.47.0/24
descr:          Depo Data Center
origin:         AS50896
mnt-by:         MNT-DEPO40
changed:        unread@ripe.net 20000101
source:         REGRESSION
remarks:        ****************************
remarks:        * THIS OBJECT IS MODIFIED
remarks:        * Please note that all data that is generally regarded as personal
remarks:        * data has been removed from this object.
remarks:        * To view the original object, please query the RIPE Database at:
remarks:        * http://www.ripe.net/whois
remarks:        ****************************

"""


def clientthread(conn):
    conn.send('% Welcome to the NRTM test server.\n\n')
    while True:
        data = conn.recv(1024).strip()
        if not data:
            break
        print data
        if data == "-k -g REGRESSION:3:1983029-LAST":
            # send feed (copied from RADB)
            print "sending:"
            print nrtm_data_1
            conn.sendall(nrtm_data_1)
            # keep socket open, act like persistent
            time.sleep(10)
            # client requested refresh, but instead gets latest object
            print "sending:"
            print nrtm_data_2
            conn.sendall(nrtm_data_2)
            time.sleep(1)
            conn.close()
        if data == "!q":
            conn.close()
    conn.close()

if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(sockaddr)
    sock.listen(10)
    while True:
        conn, addr = sock.accept()
        print 'Connected with ' + addr[0] + ':' + str(addr[1])
        start_new_thread(clientthread, (conn,))
    sock.close()
