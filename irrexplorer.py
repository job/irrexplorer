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

import ipaddr
import threading
import multiprocessing
import radix


class TreeLookup(threading.Thread):
    def __init__(self, tree, asn_prefix_map, assets,
                 lookup_queue, result_queue):
        threading.Thread.__init__(self)
        self.tree = tree
        self.lookup_queue = lookup_queue
        self.result_queue = result_queue
        self.asn_prefix_map = asn_prefix_map
        self.assets = assets

    def run(self):
        while True:
            lookup, target = self.lookup_queue.get()
            results = []
            if not lookup:
                continue
            if lookup == "search_specifics":
                data = None
                if self.tree.search_exact(target):
                    data = self.tree.search_exact(target).data
                    results.append((target, data))
                for prefix in self.tree.prefixes():
                    if ipaddr.IPNetwork(prefix) in ipaddr.IPNetwork(target):
                        data = self.tree.search_exact(prefix).data
                        results.append((prefix, data))
                self.result_queue.put(results)

            elif lookup == "inverseasn":
                if target in self.asn_prefix_map:
                    self.result_queue.put(self.asn_prefix_map['target'])
                else:
                    self.result_queue.put([])

            self.lookup_queue.task_done()


class NRTMWorker(multiprocessing.Process):
    """
    Launches an nrtm.client() instance and feeds the output in to a
    radix tree. Somehow allow other processes to lookup entries in the
    radix tree. Destroy & rebuild radix tree when serial overruns and
    a new connection must be established with the NRTM host.
    """
    def __init__(self, feedconfig, lookup_queue, result_queue):
        """
        Constructor.
        @param config dict() with NRTM host information
        @param nrtm_queue Queue() where NRTM output goes
        """
        multiprocessing.Process.__init__(self)
        self.feedconfig = feedconfig
        self.lookup_queue = lookup_queue
        self.result_queue = result_queue
        self.tree = radix.Radix()
        self.dbname = feedconfig['dbname']
        self.asn_prefix_map = {}
        self.assets = {}
        self.lookup = TreeLookup(self.tree, self.asn_prefix_map, self.assets,
                                 self.lookup_queue, self.result_queue)

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
        self.lookup.setDaemon(True)
        self.lookup.start()

        feed = nrtm.client(**self.feedconfig)
        while True:
            for cmd, serial, obj in feed.get():
                if not obj:
                    continue
                try:
                    if not self.dbname == obj['source']:
                        """ ignore updates for which the source does not
                        match the configured/expected database """
                        continue
                except:
                    print "ERROR: weird object: %s" % obj
                    continue

                if obj['kind'] in ["route", "route6"]:
                    if cmd == "ADD":
                        if not self.tree.search_exact(obj['name']):
                            # FIXME does sometimes fails in the pure python
                            # py-radix
                            rnode = self.tree.add(obj['name'])
                            rnode.data['origins'] = [obj['origin']]
                        else:
                            rnode.data['origins'] = set([obj['origin']] + list(rnode.data['origins']))
                        if obj['origin'] not in self.asn_prefix_map:
                            self.asn_prefix_map[obj['origin']] = [obj['name']]
                        else:
                            self.asn_prefix_map[obj['origin']].append(obj['name'])
                    else:
                        self.tree.delete(obj['name'])
                        self.asn_prefix_map[obj['origin']].remove(obj['name'])
                if obj['kind'] == "as-set":
                    if cmd == "ADD":
                        self.assets[obj['name']] = obj['members']
                    else:
                        del self.assets[obj['name']]

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
    lookup_queues[name] = multiprocessing.JoinableQueue()
    result_queues[name] = multiprocessing.JoinableQueue()
    worker = NRTMWorker(feedconfig, lookup_queues[name], result_queues[name])
    worker.start()

#worker = Radix_maintainer(nrtm_queue)
#worker.setDaemon(True)
#worker.start()

import time
for i in range(0, 15):
    print i
    time.sleep(1)

prefix = "2401:4800::/32"
for i in lookup_queues:
    print "doing lookup for %s in %s" % (prefix, i)
    lookup_queues[i].put(("search_specifics", prefix))
for i in lookup_queues:
    lookup_queues[i].join()
for i in result_queues:
    print "found in %s %s" % (i, result_queues[i].get())

prefix = "AS15562"
for i in lookup_queues:
    print "doing lookup for %s in %s" % (prefix, i)
    lookup_queues[i].put(("inverseasn", prefix))
for i in lookup_queues:
    lookup_queues[i].join()
for i in result_queues:
    print "found in %s %s" % (i, result_queues[i].get())

""" main thread to keep the programme alive """
while True:
    time.sleep(10)
