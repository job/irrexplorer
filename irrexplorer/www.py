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
            data = form.field.data
            try:
                int(data)
                return redirect(url_for('asn_search', asn=data))
            except ValueError:
                pass

#            if utils.is_autnum(data):
#                return redirect(url_for('asn_search', asn=data))

            if utils.is_ipnetwork(data):
                flash('Just one field is required, fill it in!')
                return redirect(url_for('prefix_search', prefix=data))

            else:
                return render_template('index.html', form=form)

    @app.route('/asn/<path:asn>')
    def asn_search(asn):
        return render_template('asn.html')

    @app.route('/asn_json/<path:asn>')
    def asn(asn):
        data = report.as_report(pgdb, asn)
        return json.dumps(data)

    @app.route('/prefix/<path:prefix>')
    @app.route('/prefix/', defaults={'prefix': None})
    @app.route('/prefix', defaults={'prefix': None})
    def prefix_search(prefix):
        return render_template('prefix.html')

    @app.route('/exact_prefix/<path:prefix>')
    @app.route('/exact_prefix/', defaults={'prefix': None})
    @app.route('/exact_prefix', defaults={'prefix': None})
    def exact_prefix_search(prefix):
        return render_template('exact_prefix.html')

    # TODO: There is some duplicate code in the next, that should refactored

    @app.route('/prefix_json/<path:prefix>')
    def prefix_json(prefix):
        return do_prefix_report(prefix, exact=False)


    @app.route('/exact_prefix_json/<path:prefix>')
    def exact_prefix_json(prefix):
        return do_prefix_report(prefix, exact=True)


    def do_prefix_report(prefix, exact):

        try:
            ipaddr.IPNetwork(prefix)
        except ValueError:
            msg = 'Could not parse input %s as ip address or prefix' % prefix
            print msg
            abort(400, msg)

        try:
            prefix_data = report.prefix_report(pgdb, prefix, exact=exact)
            return json.dumps(prefix_data)
        except report.NoPrefixError as e:
            print e
            abort(400, str(e))
        except Exception as e:
            print e
            traceback.print_tb()
            msg = 'Error processing prefix %s: %s' % (prefix, str(e))
            print msg
            abort(500, msg)


#    @app.route('/asset/<asset>')
#    def asset(asset):
#        return str(utils.lookup_assets(asset))

    return app
