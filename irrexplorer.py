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

from flask import Flask, render_template, request, flash, redirect, \
    url_for
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import TextField, SubmitField
from wtforms.validators import Required


def find_more_specifics(target, prefixes):
    result = []
    for prefix in prefixes:
        if prefix:
            if ipaddr.IPNetwork(prefix) in ipaddr.IPNetwork(target):
                result.append(prefix)
    return result

def find_more_sp_helper(args):
    return find_more_specifics(*args)


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
            results = []
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
                specifics = pool.map(find_more_sp_helper, job_args)
                # next line flattens the list of lists
                for prefix in [item for sublist in specifics for item in sublist]:
                    data = self.tree.search_exact(prefix).data
                    results.append({prefix: data['origins']})
                self.result_queue.put(results)

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
                            rnode.data['origins'] = set([obj['origin']] + list(rnode.data['origins']))

                        # add prefix to the inverse ASN map
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
for dbase in databases:
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
for i in range(0, 45):
    print i
    time.sleep(1)

prefix = "165.254.97.7/32"
for i in lookup_queues:
    print "doing lookup for %s in %s" % (prefix, i)
    lookup_queues[i].put(("search_specifics", prefix))
for i in lookup_queues:
    lookup_queues[i].join()
for i in result_queues:
    print "found in %s %s" % (i, result_queues[i].get())
    result_queues[i].task_done()

prefix = 15562
for i in lookup_queues:
    print "doing lookup for %s in %s" % (prefix, i)
    lookup_queues[i].put(("inverseasn", prefix))
for i in lookup_queues:
    lookup_queues[i].join()
for i in result_queues:
    print "found in %s %s" % (i, result_queues[i].get())
    result_queues[i].task_done()


def query(query_type, target):
    global lookup_queues
    global result_queues
    for i in lookup_queues:
        print "doing lookup for %s in %s" % (target, i)
        lookup_queues[i].put((query_type, target))
    for i in lookup_queues:
        lookup_queues[i].join()
    result = {}
    for i in result_queues:
        result[i] = result_queues[i].get()
        result_queues[i].task_done()
    return result


def is_autnum(autnum):
    try:
        if autnum.startswith('AS'):
            int(autnum[2:])
            return True
        else:
            return False
    except ValueError:
        return False


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

#print lookup_assets(asset="AS-VSNL")
#print lookup_assets(asset="AS-ANTICLOCKWISE")
#print lookup_assets(asset="AS-GLOBEINTERNET-CLIENTS")

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

            if is_autnum(data):
                return redirect(url_for('autnum', autnum=data))

            elif is_ipnetwork(data):
                flash('Just one field is required, fill it in!')
                return redirect(url_for('prefix', prefix=data))

            elif data.startswith('AS'):
                return redirect(url_for('asset', asset=data))

            else:
                return render_template('index.html', form=form)

    @app.route('/autnum/<autnum>')
    def autnum(autnum):
        return str(query("inverseasn", autnum))

    @app.route('/prefix/<path:prefix>')
    def prefix(prefix):
        return str(query("search_specifics", prefix))

    @app.route('/asset/<asset>')
    def asset(asset):
        return str(lookup_assets(asset))

    return app

if __name__ == '__main__':
    create_app().run(host="0.0.0.0",debug=True)
