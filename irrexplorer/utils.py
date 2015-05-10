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

import ipaddr

def is_ipnetwork(data):
    try:
        ipaddr.IPNetwork(data)
        return True
    except ValueError:
        return False

def lookup_assets(asset, seen=None):
    if seen is None:
        seen = []

    x = query("asset_search", asset)

    for db in x:
        if not x[db]:
            continue
        for elem in x[db]:
            if elem in seen:
                continue
            if is_autnum(elem):
                seen.append(elem)
            else:
                seen.append(elem)
                seen = lookup_assets(elem, seen)
    return seen

def is_autnum(autnum):
    try:
        if autnum.startswith('AS'):
            int(autnum[2:])
            return True
        else:
            return False
    except ValueError:
        return False

def find_more_specifics(target, prefixes):
    result = []
    for prefix in prefixes:
        if prefix:
            if ipaddr.IPNetwork(prefix) in ipaddr.IPNetwork(target):
                result.append(prefix)
    return result

def find_more_sp_helper(args):
    return find_more_specifics(*args)

def irr_query(query_type, target):
    global lookup_queues
    global result_queues
    for i in lookup_queues:
        if i in ['BGP', 'RIPE-AUTH']:
            continue
        print "doing lookup for %s in %s" % (target, i)
        lookup_queues[i].put((query_type, target))
    for i in lookup_queues:
        if i in ['BGP', 'RIPE-AUTH']:
            continue
        lookup_queues[i].join()
    result = {}
    for i in result_queues:
        if i in ['BGP', 'RIPE-AUTH']:
            continue
        result[i] = result_queues[i].get()
        result_queues[i].task_done()
    return result

if __name__ == "__main__":
    pass
