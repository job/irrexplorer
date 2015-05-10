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

import utils

import radix
import time
import urllib2
import threading
import multiprocessing


class bgpclient(object):
    """ Ingest a BGP tables from NLNOG RING project """
    def __init__(self, bgpdump=None):

        super(bgpclient, self).__init__()

        self.bgpdump = \
            self.fetch_dump("http://lg01.infra.ring.nlnog.net/table.txt")

    def fetch_dump(self, dumpurl):
        req = urllib2.Request(dumpurl)
        response = urllib2.urlopen(req)
        return response.read()

    def get(self):
        if self.bgpdump:
            for line in self.bgpdump.split('\n'):
                try:
                    prefix, origin = line.strip().split(' ')
                except:
                    print line
                yield prefix, int(origin)


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
            results = []
            if not lookup:
                continue
            else:
                print "received lookup!!"
            if lookup == "search_specifics":
                data = None
                pool = multiprocessing.Pool(6)
                parts = [self.prefixes[i::6] for i in range(6)]
                job_args = [(target, p) for p in parts]
                specifics = pool.map(utils.find_more_sp_helper, job_args)
                # next line flattens the list of lists
                for prefix in [item for sublist in specifics for item in sublist]:
                    data = self.tree.search_exact(prefix).data
                    results.append({prefix: data['origins']})
                self.result_queue.put(results)

            elif lookup == "search_aggregate":
                rnode = self.tree.search_worst(target)
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

            self.lookup_queue.task_done()


class BGPWorker(multiprocessing.Process):
    """
    Launch bgpclient() instance, provide a lookup thread
    """
    def __init__(self, lookup_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self.lookup_queue = lookup_queue
        self.result_queue = result_queue
        self.tree = radix.Radix()
        self.prefixes = []
        self.asn_prefix_map = {}
        self.dbname = "BGP"
        self.lookup = BGPLookupWorker(self.tree, self.prefixes,
                                      self.asn_prefix_map, self.lookup_queue,
                                      self.result_queue)
        self.bgpfeed = bgpclient()

    def run(self):
        self.lookup.start()
        while True:
            self.bgpfeed = bgpclient()
            self.temp_tree = radix.Radix()
            self.prefixes_temp = []
            self.asn_prefix_map_temp = {}
            for prefix, origin in self.bgpfeed.get():
                self.prefixes.append(prefix)
                rnode = self.temp_tree.add(prefix)
                rnode.data["origins"] = origin
                if origin not in self.asn_prefix_map.keys():
                    self.asn_prefix_map[origin] = [prefix]
                else:
                    self.asn_prefix_map[origin].append(prefix)
            self.tree = self.temp_tree
            self.prefixes = self.prefixes_temp
            self.asn_prefix_map = self.asn_prefix_map_temp
            print "info: loaded the tree"
            time.sleep(60 * 16)
            print "refreshing trees"

if __name__ == "__main__":
    lookup_queue = multiprocessing.JoinableQueue()
    result_queue = multiprocessing.JoinableQueue()

    a = BGPWorker(lookup_queue, result_queue)
    a.start()
    time.sleep(120)
    lookup_queue.put(("prefixset", ["8.8.8.0/24", "4.0.0.0/8"]))
    lookup_queue.join()
    print result_queue.get()
    lookup_queue.put(("inverseasn", 15562))
    lookup_queue.join()
    print result_queue.get()
    lookup_queue.put(("search_specifics", "8.8.8.0/24"))
    lookup_queue.join()
    print result_queue.get()
