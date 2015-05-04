#!/usr/bin/env python
# Copyright (c) 2015, Job Snijders
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
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from irrexplorer import config
from irrexplorer import nrtm
from threading import Thread
from radix import Radix
from Queue import Queue

databases = config('irrexplorer_config.yml').databases
nrtm_queue = Queue()


def connect_nrtm(config, nrtm_queue):
    feed = nrtm.client(**config)
    for cmd, serial, obj in feed.get():
        if not obj:
            continue
#        print cmd, obj
        nrtm_queue.put((cmd, serial, obj, config['dbname']))


def radix_maintainer(nrtm_queue):
    import time
    time.sleep(15)
    while True:
        update = nrtm_queue.get()
        print update
        nrtm_queue.task_done()


for dbase in databases:
    name = dbase.keys().pop()
    client_config = dict(d.items()[0] for d in dbase[name])
    print client_config
    worker = Thread(target=connect_nrtm, args=(client_config, nrtm_queue))
    worker.setDaemon(True)
    worker.start()

worker = Thread(target=radix_maintainer, args=(nrtm_queue,))
worker.setDaemon(True)
worker.start()

nrtm_queue.join()

"""
from irrexplorer.nrtm import client
a = client(nrtmhost='whois.radb.net',
           nrtmport=43,
           serial='ftp://ftp.radb.net/radb/dbase/RADB.CURRENTSERIAL',
           dump='ftp://ftp.radb.net/radb/dbase/radb.db.gz',
           dbase="RADB")

while True:
    for i in a.get():
        print i
"""

