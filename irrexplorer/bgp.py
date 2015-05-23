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

import radix
import time
import urllib2
import threading
import multiprocessing


# bgp table from NLNOG RING project
DEFAULT_BGP_SOURCE = "http://lg01.infra.ring.nlnog.net/table.txt"

UPDATE_INTERVAL = 300 # seconds



class BGPClient(object):

    def __init__(self, bgp_source):
        self.bgp_source = bgp_source


    def fetch_table(self):
        if self.bgp_source.startswith('http://') or self.bgp_source.startswith('https://'):
            req = urllib2.Request(self.bgp_source)
            response = urllib2.urlopen(req)
            return response.read()
        else:
            # probably a file
            return open(self.bgp_source).read()

    def get(self):
        prefixes = []
        table_data = self.fetch_table()
        for line in table_data.split('\n'):
            line = line.strip()
            if not line:
                continue
            try:
                prefix, origin = line.strip().split(' ')
                origin = int(origin)
            except Exception as e:
                print 'BGP line parse error:', e, line
            prefixes.append((prefix, origin))
        print "INFO: Collected all prefixes, %i elements" % len(prefixes)
        return prefixes


class BGPLookupWorker(threading.Thread):
    """
    A lookup thread specific to the BGP data, might be good
    to merge this into the IRR lookup worker at some point.
    """

    def __init__(self, tree, prefixes, asn_prefix_map, lookup_queue,
                 result_queue):
        threading.Thread.__init__(self)
        self.tree = tree
        self.prefixes = prefixes
        self.asn_prefix_map = asn_prefix_map
        self.lookup_queue = lookup_queue
        self.result_queue = result_queue

    def run(self):
        while True:
            lookup, target = self.lookup_queue.get()
            results = {}
            if not lookup:
                continue
            else:
                print "received BGP lookup: %s %s" % (lookup, target)

            if lookup == "search_specifics":
                data = None
                for rnode in self.tree.search_covered(target):
                    prefix = rnode.prefix
                    origins = rnode.data['origins']
                    results[prefix] = {}
                    results[prefix]['origins'] = origins
                self.result_queue.put(results)

            elif lookup == "search_exact":
                rnode = self.tree.search_exact(target)
                if not rnode:
                    self.result_queue.put(None)
                else:
                    prefix = rnode.prefix
                    origins = rnode.data['origins']
                    results[prefix] = {}
                    results[prefix]['origins'] = origins
                    self.result_queue.put(results)

            elif lookup == "search_aggregate":
                try:
                    rnode = self.tree.search_worst(target)
                except ValueError:  # not a valid prefix
                    rnode = None
                if not rnode:
                    self.result_queue.put(None)
                else:
                    prefix = rnode.prefix
                    data = rnode.data
                    self.result_queue.put((prefix, data))

            elif lookup == "inverseasn":
                if target in self.asn_prefix_map:
                    self.result_queue.put(self.asn_prefix_map[target])
                else:
                    self.result_queue.put([])

            elif lookup == "prefixset":
                self.result_queue.put(set(target) & set(self.prefixes))

            elif lookup == "exit":
                self.result_queue.put("exit-confirm")
                self.lookup_queue.task_done()
                break

            self.lookup_queue.task_done()


class BGPWorker(multiprocessing.Process):
    """
    Launch bgpclient() instance, provide a lookup thread
    """
    def __init__(self, lookup_queue, result_queue, bgp_source=DEFAULT_BGP_SOURCE):

        multiprocessing.Process.__init__(self)

        self.lookup_queue = lookup_queue
        self.result_queue = result_queue

        self.bgp_client = BGPClient(bgp_source)
        self.tree = radix.Radix()
        self.prefixes = []
        self.asn_prefix_map = {}
        self.dbname = "BGP"
        self.ready_event = multiprocessing.Event()

        self.lookup_worker = None


    def updateTree(self):

        new_tree = radix.Radix()
        new_asn_prefix_map = {}
        new_prefixes = []

        t_start = time.time()
        for prefix, origin in self.bgp_client.get():
            rnode = new_tree.add(prefix)
            rnode.data['origins'] = origin
            new_prefixes.append(prefix)
            new_asn_prefix_map.setdefault(origin, []).append(prefix)

        print 'BGP tree update time', round(time.time() - t_start, 2)

        self.tree = new_tree
        self.asn_prefix_map = new_asn_prefix_map
        self.prefixes = new_prefixes


    def run(self):

        while True:

            self.updateTree()

            if self.lookup_worker:
                # let current lookup worker process current requests, and have it exit
                self.lookup_queue.put(("exit", 1))
                self.lookup_queue.join()
                self.result_queue.get()

            # start new lookup thread
            self.lookup_worker = BGPLookupWorker(self.tree, self.prefixes, self.asn_prefix_map, self.lookup_queue, self.result_queue)
            self.lookup_worker.daemon = True
            self.lookup_worker.start()

            print "INFO: Loaded BGP tree"
            self.ready_event.set()
            time.sleep(UPDATE_INTERVAL)
            print "INFO: Refreshing BGP tree"

if __name__ == "__main__":
    lookup_queue = multiprocessing.JoinableQueue()
    result_queue = multiprocessing.JoinableQueue()

    a = BGPWorker(lookup_queue, result_queue)
    a.start()
    a.ready_event.wait()

    lookup_queue.put(("prefixset", ["8.8.8.0/24", "4.0.0.0/8"]))
    lookup_queue.join()
    print result_queue.get()
    lookup_queue.put(("inverseasn", 15562))
    lookup_queue.join()
    print result_queue.get()
    lookup_queue.put(("search_specifics", "8.8.8.0/24"))
    lookup_queue.join()
    print result_queue.get()
