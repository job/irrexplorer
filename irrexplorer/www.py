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

from irrexplorer import utils, report
from irrexplorer.utils import Prefix, ASNumber, ASMacro

import ipaddr
import json
import traceback

from flask import Flask, render_template, request, flash, redirect, url_for, abort
from flask_bootstrap import Bootstrap
from flask_wtf import Form
from wtforms import TextField, SubmitField
from wtforms.validators import Required





class InputForm(Form):
    field = TextField('Data', description='Input ASN, AS-SET or Prefix.', validators=[Required()])
    submit_button = SubmitField('Submit')


def create_app(pgdb, configfile=None):
    app = Flask('IRRExplorer')
    app.config.from_pyfile('appconfig.cfg')
    Bootstrap(app)

    @app.route('/', methods=['GET', 'POST'])
    def index():
        form = InputForm()
        if request.method == 'GET':
            return render_template('index.html', form=form)

        if request.method == 'POST':
            # note: the form won't submit with empty data, so we don't have to handle that
            data = str(form.field.data).upper()
            print 'Form data:', data

            try:
                sv = utils.classifySearchString(data)
                return redirect(url_for('search', data=sv.value))

            except ValueError:
                flash('Invalid search data')
                return render_template('index.html', form=form)

    # -- search --
    @app.route('/search/<path:data>')
    @app.route('/search/', defaults={'data': None})
    @app.route('/search', defaults={'data': None})
    def search(data):

        form = InputForm()

        query_data = request.args.get('data')
        if query_data:
            # this means that we got search request
            print 'query data', query_data
            return redirect(url_for('search', data=query_data))

        if not data:
            flash('No search data provided')
            return render_template('index.html', form=form)

        try:
            sv = utils.classifySearchString(data)

            tables = []

            # page: title (object type : data)

            # json url for each table, not per report...
            # stuff that is needed per table:
            # id (tables.key)
            # name
            # source url
            # column ordering (first, and last, we cannot do complete until we get results)
            # note (optional)

            if type(sv) is Prefix:
                json_url =  None
                title = 'Prefix: ' + sv.value
                tables.append({
                    'id'           : 'prefixes',
                    'title'        : 'Matching prefixes',
                    'url'          : '/json/prefix/' + sv.value,
                    'start_fields' : ["prefix", "bgp" ]
                })

            if type(sv) is ASNumber:
                title = 'AS Number: ' + data
                tables.append({
                    'id'           : 'prefixes',
                    'title'        : 'Prefixes',
                    'url'          : '/json/as_prefixes/' + str(sv.value),
                    'start_fields' : ["prefix", "bgp" ]
                })

            if type(sv) is ASMacro:
                title = 'AS Macro: ' + data
                tables.append({
                    'id'           : 'expanded',
                    'title'        : 'Macro Expansion',
                    'url'          : '/json/macro_expand/' + sv.value,
                    'start_fields' : ["as_macro", "depth", "path", "source", "members"]
                })

            if type(sv) in (ASNumber, ASMacro):
                key = 'AS' + str(sv.value) if type(sv) is ASNumber else str(sv.value)
                tables.append({
                    'id'           : 'macros',
                    'title'        : 'Included in the following macros:',
                    'url'          : '/json/macro_contain/' + key,
                    'start_fields' : ["as_macro", "source" ]
                })

            return render_template('search.html', form=form, title=title, tables=tables)


        except ValueError:
            flash('Invalid search data')
            form = InputForm()
            return render_template('index.html', form=form)


    # -- json reports --

    @app.route('/json/prefix/<path:prefix>')
    def prefix(prefix):
        data = report.prefix(pgdb, prefix, exact=False)
        return json.dumps(data)

    @app.route('/json/as_prefixes/<path:as_number>')
    def as_prefixes(as_number):
        data = report.as_prefixes(pgdb, int(as_number))
        return json.dumps(data)

    @app.route('/json/macro_expand/<path:as_macro>')
    def macro_expand(as_macro):
        data = report.macro_expand(pgdb, as_macro)
        return json.dumps(data)

    @app.route('/json/macro_contain/<path:as_object>')
    def as_contain(as_object):
        data = report.macro_contain(pgdb, as_object)
        return json.dumps(data)


## not used anymore, but the error messaging might be useful
#    def do_prefix_report(prefix, exact):
#
#        try:
#            ipaddr.IPNetwork(prefix)
#        except ValueError:
#            msg = 'Could not parse input %s as ip address or prefix' % prefix
#            print msg
#            abort(400, msg)
#
#        try:
#            prefix_data = report.prefix_report(pgdb, prefix, exact=exact)
#            return json.dumps(prefix_data)
#        except report.NoPrefixError as e:
#            print e
#            abort(400, str(e))
#        except Exception as e:
#            print e
#            traceback.print_tb()
#            msg = 'Error processing prefix %s: %s' % (prefix, str(e))
#            print msg
#            abort(500, msg)


    return app

