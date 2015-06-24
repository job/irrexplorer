#!/usr/bin/env python
# Copyright (c) 2015, Job Snijders
# Copyright (c) 2015, NORDUnet A/S
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

import time


SOURCE = 'source'
BGP = 'bgp'

# we should generate these from the database sometime...
IRR_DBS = ['afrinic', 'altdb', 'apnic', 'arin', 'bboi', 'bell', 'gt', 'jpirr', 'level3', 'nttcom', 'radb', 'rgnet', 'savvis', 'tc', 'ripe']


class NoPrefixError(Exception):
    pass



def add_prefix_advice(prefixes):

    # default, primary, succes, info, warning, danger
    for pfx, pfx_data in prefixes.items():
        print 'Prefix: %s, data: %s' % (pfx, pfx_data)
        pfx_source = pfx_data[SOURCE]

        anywhere = set()
        for db in IRR_DBS:
            if db in pfx_source:
                for entry in pfx_source[db]:
                    anywhere.add(entry)
        anywhere = list(anywhere)

        anywhere_not_ripe = set()
        for db in IRR_DBS:
            if db in pfx_source and db != 'ripe':
                for entry in pfx_source[db]:
                    anywhere_not_ripe.add(entry)
        anywhere_not_ripe = list(anywhere_not_ripe)

        print '  IRR orgins:', anywhere
        print '  IRR orgins % ripe:', anywhere_not_ripe

        if not BGP in pfx_data:
            bgp_origin = None
        else:
            if len(pfx_data[BGP]) > 2:
                print 'Multiple BGP sources:', pfx_data[BGP], 'only using first origin'
            bgp_origin = list(pfx_data[BGP])[0]

        if pfx_data['ripe_managed']:

            if 'ripe' in pfx_source:

                if bgp_origin and bgp_origin in pfx_source['ripe']:

                    if len(anywhere) == 1 and bgp_origin not in anywhere_not_ripe:
                        pfx_data['advice'] = "Perfect"
                        pfx_data['label'] = "success"

                    elif bgp_origin == anywhere_not_ripe:
                        pfx_data['advice'] = "Proper RIPE DB object, but foreign or proxy objects also exist"
                        pfx_data['label'] = "warning"

                    elif bgp_origin in anywhere_not_ripe:
                        pfx_data['advice'] = "Proper RIPE DB object, but foreign objects also exist, consider removing these"
                        pfx_data['label'] = "warning"

                    else:
                        pfx_data['advice'] = "Looks good, but multiple entries exists in RIPE DB"
                        pfx_data['label'] = "success"

                elif BGP in pfx_source:
                    pfx_data['advice'] = "Prefix is in DFZ, but registered with wrong origin in RIPE!"
                    pfx_data['label'] = "danger"

                else:
                    # same as last else clause, not sure if this could actually be first
                    pfx_data['advice'] = "Not seen in BGP, but (legacy?) route-objects exist, consider clean-up"
                    pfx_data['label'] = "warning"

            else:   # no ripe registration

                if bgp_origin:
                    pfx_data['advice'] = "Prefix is in DFZ, but NOT registered in RIPE!"
                    pfx_data['label'] = "danger"

                else:
                    pfx_data['advice'] = "Route objects in foreign registries exist, consider moving them to RIPE DB"
                    pfx_data['label'] = "warning"

        elif bgp_origin: # not ripe managed, but have bgp_origin

            if bgp_origin in anywhere:

                if len(anywhere) == 1:
                    pfx_data['advice'] = "Looks good: in BGP consistent origin AS in route-objects"
                    pfx_data['label'] = "success"
                else:
                    pfx_data['advice'] = "Multiple route-object exist with different origins"
                    pfx_data['label'] = 'warning'

            else:
                pfx_data['advice'] = "Prefix in DFZ, but no route-object with correct origin anywhere"
                pfx_data['label'] = "danger"

        else: # not ripe managed, no bgp origin
            pfx_data['advice'] = "Not seen in BGP, but (legacy?) route-objects exist, consider clean-up"
            pfx_data['label'] = "warning"


    return prefixes



def prefix_report(pgdb, prefix, exact=False):
    """
        - find least specific
        - search in BGP for more specifics
        - search in IRR for more specifics
        - check all prefixes whether they are RIPE managed or not
        - return dict
    """

    t_start = time.time()

    print
    print 'Prefix report: %s, exact=%s' % (prefix, exact)

    routes = pgdb.query_prefix(prefix, exact=False)
    prefixes = {}
    for pfx, asn, source in routes:
        ps = prefixes.setdefault(pfx, {}).setdefault(SOURCE, {})
        ps.setdefault(source, []).append(asn)

    for pfx_data in prefixes.values():
        if BGP in pfx_data[SOURCE]:
            pfx_data[BGP] = pfx_data[SOURCE].pop(BGP)

    print 'Prefixes:'
    for pd in prefixes.items():
        print pd

    # TODO if we find any prefixes larger than the inputted one, we should find prefixes covered by that prefixes
    # Go through the prefixes, find the shortest one, if it is different from the inputted one, do another search

#    if exact:
#        bgp_specifics = other_query("BGP", "search_exact", prefix)
#        irr_specifics = irr_query("search_exact", prefix)
#    else:
#        tree = radix.Radix()
#        bgp_aggregate = other_query("BGP", "search_aggregate", prefix)
#        if bgp_aggregate:
#            bgp_aggregate = bgp_aggregate[0]
#            tree.add(bgp_aggregate)
#        irr_aggregate = irr_query("search_aggregate", prefix)
#        for r in irr_aggregate:
#            if irr_aggregate[r]:
#                tree.add(irr_aggregate[r][0])
#        aggregate = tree.search_worst(prefix)
#        if not aggregate:
#            raise NoPrefixError("Could not find any matching prefix in IRR or BGP tables for %s" % prefix)
#
#        aggregate = aggregate.prefix
#
#        bgp_specifics = other_query("BGP", "search_specifics", aggregate)
#        irr_specifics = irr_query("search_specifics", aggregate)

#    prefixes = {}
#    for p in bgp_specifics:
#        if p not in prefixes:
#            prefixes[p] = {'bgp_origin': bgp_specifics[p]['origins']}
#        else:
#            prefixes[p]['bgp_origin'] = bgp_specifics[p]['origins']
#    for db in irr_specifics:
#        if irr_specifics[db]:
#            for p in irr_specifics[db]:
#                if p not in prefixes:
#                    prefixes[p] = {}
#                    prefixes[p]['bgp_origin'] = False
#
#    """
#    irr_specifics looks like:
#        {'apnic': {}, 'gt': {}, 'bboi': {}, 'radb': {}, 'jpirr': {},
#        'bell': {}, 'altdb': {}, 'rgnet': {}, 'savvis': {}, 'level3': {},
#        'ripe': {'85.184.0.0/16': {'origins': [8935]}},
#        'arin': {}, 'afrinic': {}, 'tc': {}}
#    """
#    print "prefix_report: Lookup prefixes: %s" % prefixes
#    print "prefix_report: Lookup irr_specifics: %s" % irr_specifics


    for pfx, pfx_data in prefixes.items():
        managed_routes = pgdb.query_managed_prefix(pfx) # this can be done better
        print 'Managed routes for prefix %s --> %s' % (pfx, managed_routes)
        # we only do ripe managed routes at the moment, so if/else if fine
        managed = True if managed_routes else False
        pfx_data['ripe_managed'] = managed

    add_prefix_advice(prefixes)

    print 'Advice:'
    for p,d in prefixes.items():
        print '%s: %s' % (p,d['advice'])

    # OK, this is not how i want to do things, but I cannot figure out the javascript stuff
    for pfx_data in prefixes.values():
        pfx_data.update(pfx_data.pop(SOURCE))

    # print msg # have to get this into the web page as well...

    t_delta = time.time() - t_start
    print 'Time for prefix report for %s: %s\n' % (prefix, round(t_delta,2))

    return prefixes



def as_report(pgdb, as_number):

    print 'as_report', as_number

    t_start = time.time()

    prefixes = pgdb.query_as(as_number)

#    result = { 'prefixes':{}, 'macros':[] }
    result = {}
    for route, source in prefixes:
        #result['prefixes'].setdefault(route, []).append(source)
        #result.setdefault(route, []).append(source)
        result.setdefault(route, {})[source] = True

#       macros = pgdb.query_as_contain('AS' + as_number)
#    for macro, source in macros:
#        result['macros'].append(macro)

    t_delta = time.time() - t_start
    print
    print 'Time for as report for %s: %s' % (as_number, round(t_delta,2))
    print

    # print result
    return result


