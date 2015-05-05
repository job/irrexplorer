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

import multiprocessing
import radix


class NRTMWorker(multiprocessing.Process):
    """
    Launches an nrtm.client() instance and feeds the output in to a
    radix tree. Somehow allow other processes to lookup entries in the
    radix tree. Destroy & rebuild radix tree when serial overruns and
    a new connection must be established with the NRTM host.
    """
    def __init__(self, feedconfig, cmd_queue, result_queue):
        """
        Constructor.
        @param config dict() with NRTM host information
        @param nrtm_queue Queue() where NRTM output goes
        """
        multiprocessing.Process.__init__(self)
        self.feedconfig = feedconfig
        self.cmd_queue = cmd_queue
        self.result_queue = result_queue
        self.tree = radix.Radix()
        self.dbname = feedconfig['dbname']

# TODO
# add completly new rnode from irr
# add completly new rnode from bgp
# add more data to existing rnode
# remove data from existing rnode
# remove existing rnode (last bgp or irr withdraw)

    def run(self):
        """
        Process run method, fetch NRTM updates and put them in the
        a radix tree.
        """
        feed = nrtm.client(**self.feedconfig)
        while True:
            for cmd, serial, obj in feed.get():
                if not obj:
                    continue
                if not self.dbname == obj['source']:
                    """ ignore updates for which the source does not
                    match the configured/expected database """
                    continue
                if obj['kind'] in ["route", "route6"]:
                    if cmd == "ADD":
                        if not self.tree.search_exact(obj['name']):
                            rnode = self.tree.add(obj['name'])
                            rnode.data['origins'] = [obj['origin']]
                        else:
                            rnode.data['origins'] = set([obj['origin']] + list(rnode.data['origins']))
            lookup, target = self.cmd_queue.get()
            if not lookup:
                continue
            if lookup == "prefix":
                result = self.tree.search_exact(target)
                self.result_queue.put(result.data)

# deprecated
#class Radix_maintainer(threading.Thread):
#    """
#    Consumes NRTM + BGP updates and stores them in a central
#    radix tree.
#    """
#    def __init__(self, nrtm_queue):
#        """
#        Constructor.
#
#        @param nrtm_queue Queue() from which NRTM/BGP updates are taken
#        """
#        threading.Thread.__init__(self)
#        self.nrtm_queue = nrtm_queue
#        self.tree = radix.Radix()
#
#    def run(self):
#        while True:
#            update = self.nrtm_queue.get()

databases = config('irrexplorer_config.yml').databases
lookup_queues = {}
result_queues = {}
for dbase in databases[0:2]:
    name = dbase.keys()[0]
    feedconfig = dbase[name]
    feedconfig = dict(d.items()[0] for d in feedconfig)
    lookup_queues[name] = multiprocessing.Queue()
    result_queues[name] = multiprocessing.Queue()
    worker = NRTMWorker(feedconfig, lookup_queues[name], result_queues[name])
    worker.start()

#worker = Radix_maintainer(nrtm_queue)
#worker.setDaemon(True)
#worker.start()

import time
time.sleep(5)
for i in lookup_queues:
    lookup_queues[i].put(("prefix", "1.0.128.0/17"))
    time.sleep(1)
for i in result_queues:
    print result_queues[i].get()


time.sleep(100000)

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
