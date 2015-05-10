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
import threading
import multiprocessing


class RIPELookupWorker(threading.Thread):
    """
    A lookup thread specific to the BGP data, might be good
    to merge this into the IRR lookup worker at some point.
    """

    def __init__(self, tree, prefixes, lookup_queue, result_queue):
        threading.Thread.__init__(self)
        self.tree = tree
        self.prefixes = prefixes
        self.lookup_queue = lookup_queue
        self.result_queue = result_queue
        #FIXME shipping with hardcoded data is not the nicest approach
        for prefix in open('data/ripe-managed-space.txt').readlines():
            self.tree.add(prefix.strip())
            self.prefixes.append(prefix.strip())

    def run(self):
        while True:
            lookup, target = self.lookup_queue.get()
            if not lookup:
                continue
            if lookup == "is_covered":
                result = self.tree.search_worst(target)
                if result:
                    result = result.prefix
                else:
                    result = None
                self.result_queue.put(result)

            self.lookup_queue.task_done()


class RIPEWorker(multiprocessing.Process):
    """
    FIXME: dynamically fetch & update the RIPE managed tree
    """
    def __init__(self, lookup_queue, result_queue):
        multiprocessing.Process.__init__(self)
        self.lookup_queue = lookup_queue
        self.result_queue = result_queue
        self.tree = radix.Radix()
        self.prefixes = []
        self.dbname = "RIPE-AUTH"
        self.lookup = RIPELookupWorker(self.tree, self.prefixes,
                                       self.lookup_queue, self.result_queue)
        self.lookup.setDaemon(True)
        self.lookup.start()

    def run(self):
        print "INFO: loaded the RIPE managed tree"

if __name__ == "__main__":
    lookup_queue = multiprocessing.JoinableQueue()
    result_queue = multiprocessing.JoinableQueue()

    a = RIPEWorker(lookup_queue, result_queue)
    a.start()
    time.sleep(1)
    lookup_queue.put(("is_covered", "194.33.96.0/24"))
    lookup_queue.join()
    print result_queue.get()
