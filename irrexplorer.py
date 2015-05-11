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
from irrexplorer import ripe
from irrexplorer import bgp
from irrexplorer import utils

import threading
import multiprocessing
import radix
import json

from flask import Flask, render_template, request, flash, redirect, \
    url_for
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import TextField, SubmitField
from wtforms.validators import Required


class LookupWorker(threading.Thread):
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
            results = {}
            if not lookup:
                continue
            if lookup == "search_specifics":
                data = None
                # cheat a little by simple sharding!
                # split all prefixes in 6 chunks, have each list worked
                # on by a Proces()
                pool = multiprocessing.Pool(6)
                parts = [self.tree.prefixes()[i::6] for i in range(6)]  # split all pfx in 4 lists
                job_args = [(target, p) for p in parts]  # workaround pool() only accepts 1 arg
                specifics = pool.map(utils.find_more_sp_helper, job_args)
                # next line flattens the list of lists
                for prefix in [item for sublist in specifics for item in sublist]:
                    data = self.tree.search_exact(prefix).data
                    results[prefix] = {}
                    results[prefix]['origins'] = data['origins']
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

            elif lookup == "asset_search":
                if target in self.assets:
                    self.result_queue.put(self.assets[target])
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
        self.lookup = LookupWorker(self.tree, self.asn_prefix_map, self.assets,
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

        self.feed = nrtm.client(**self.feedconfig)
        while True:
            for cmd, serial, obj in self.feed.get():
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
                            rnode = self.tree.search_exact(obj['name'])
                            rnode.data['origins'] = list(set([obj['origin']] + list(rnode.data['origins'])))

                        # add prefix to the inverse ASN map
                        if obj['origin'] not in self.asn_prefix_map:
                            self.asn_prefix_map[obj['origin']] = [obj['name']]
                        else:
                            self.asn_prefix_map[obj['origin']].append(obj['name'])
                    else:
                        try:
                            self.tree.delete(obj['name'])
                            self.asn_prefix_map[obj['origin']].remove(obj['name'])
                        except KeyError:
                            print "ERROR: could not remove this object from the tree in %s" % self.dbname
                            print obj

                if obj['kind'] == "as-set":
                    if cmd == "ADD":
                        self.assets[obj['name']] = obj['members']
                    else:
                        del self.assets[obj['name']]

databases = config('irrexplorer_config.yml').databases
lookup_queues = {}
result_queues = {}
for dbase in databases:
    name = dbase.keys()[0]
    feedconfig = dbase[name]
    feedconfig = dict(d.items()[0] for d in feedconfig)
    lookup_queues[name] = multiprocessing.JoinableQueue()
    result_queues[name] = multiprocessing.JoinableQueue()
    worker = NRTMWorker(feedconfig, lookup_queues[name], result_queues[name])
    worker.start()

# Launch helper processes for BGP & RIPE managed space lookups
for q in ['RIPE-AUTH', 'BGP']:
    lookup_queues[q] = multiprocessing.JoinableQueue()
    result_queues[q] = multiprocessing.JoinableQueue()
worker = bgp.BGPWorker(lookup_queues['BGP'], result_queues['BGP'])
worker.start()
worker = ripe.RIPEWorker(lookup_queues['RIPE-AUTH'],
                         result_queues['RIPE-AUTH'])
worker.start()

import time
for i in range(0, 120):
    print i
    time.sleep(1)


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

def other_query(data_source, query_type, target):
    global lookup_queues
    global result_queues
    lookup_queues[data_source].put((query_type, target))
    lookup_queues[data_source].join()
    result = result_queues[data_source].get()
    result_queues[data_source].task_done()
    return result


def bgp_query():
    pass


def ripe_query():
    pass


def prefix_report(prefix):
    """
        - find least specific
        - search in BGP for more specifics
        - search in IRR for more specifics
        - check all prefixes whether they are RIPE managed or not
        - return dict
    """
    tree = radix.Radix()
    bgp_aggregate = other_query("BGP", "search_aggregate", prefix)
    if bgp_aggregate:
        bgp_aggregate = bgp_aggregate[0]
        tree.add(bgp_aggregate)
    irr_aggregate = irr_query("search_aggregate", prefix)
    for r in irr_aggregate:
        if irr_aggregate[r]:
            tree.add(irr_aggregate[r][0])
    aggregate = tree.search_worst(prefix)
    if not aggregate:
        return """Could not find prefix in IRR or BGP tables: %s""" \
            % tree.prefixes()

    else:
        aggregate = aggregate.prefix
    bgp_specifics = other_query("BGP", "search_specifics", aggregate)
    irr_specifics = irr_query("search_specifics", aggregate)
    prefixes = {}
    for p in bgp_specifics:
        if p not in prefixes:
            prefixes[p] = {'bgp_origin': bgp_specifics[p]['origins']}
        else:
            prefixes[p]['bgp_origin'] = bgp_specifics[p]['origins']

    for db in irr_specifics:
        if not irr_specifics[db]:
            for p in prefixes:
                prefixes[p][db] = False
            continue
        for p in irr_specifics[db]:
            if p not in prefixes:
                prefixes[p] = {}
                prefixes[p][db] = irr_specifics[db][p]['origins']
            else:
                prefixes[p][db] = irr_specifics[db][p]['origins']

    for p in prefixes:
        if p not in bgp_specifics:
            prefixes[p]['bgp_origin'] = False
        if other_query("RIPE-AUTH", "is_covered", p):
            prefixes[p]['ripe_managed'] = True
        else:
            prefixes[p]['ripe_managed'] = False

    return str(prefixes)


class InputForm(Form):
    field2 = TextField('Data', description='Input ASN, AS-SET or Prefix.',
                       validators=[Required()])
    submit_button = SubmitField('Submit')


def create_app(configfile=None):
    app = Flask(__name__)
    app.config.from_pyfile('appconfig.cfg')
    Bootstrap(app)

    @app.route('/', methods=['GET', 'POST'])
    def index():
        form = InputForm()
        if request.method == 'GET':
            return render_template('index.html', form=form)

        if request.method == 'POST':
            data = form.field2.data
            try:
                int(data)
                data = "AS%s" % data
            except ValueError:
                pass

            if utils.is_autnum(data):
                return redirect(url_for('autnum', autnum=data))

            elif utils.is_ipnetwork(data):
                flash('Just one field is required, fill it in!')
                return redirect(url_for('prefix', prefix=data))

#FIXME no support for as-set digging for now
#            elif data.startswith('AS'):
#                return redirect(url_for('asset', asset=data))

            else:
                return render_template('index.html', form=form)

    @app.route('/autnum/<autnum>')
    def autnum(autnum):
        return str(irr_query("inverseasn", autnum))

    @app.route('/prefix')
    def prefix():
        #return prefix_report(prefix)
        return render_template('prefix.html')

    @app.route('/prefix_json/<path:prefix>')
    def prefix_json(prefix):
        prefix_data = prefix_report(prefix)
        return json.dumps(prefix_data)


#    @app.route('/asset/<asset>')
#    def asset(asset):
#        return str(utils.lookup_assets(asset))

    return app

if __name__ == '__main__':
    create_app().run(host="0.0.0.0", debug=True, use_reloader=False)
