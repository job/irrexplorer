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

"""
This module provides a small abstraction over the sql database.
"""

import psycopg2



class IRRSQLDatabase:

    def __init__(self, dsn):

        self.dsn = dsn
        self.conn = None


    def _get_cursor(self):

        if self.conn is None:
            self.conn = psycopg2.connect("dbname=irrexplorer user=htj")
        return self.conn.cursor()


    def _execute_fetchall(self, query, args):

        cur = self._get_cursor()
        cur.execute(query, args)
        rows = cur.fetchall()
        return rows


    def query_prefix(self, prefix, exact=False):
        # query irr databases (and maybe the bgp stuff as well)
        if exact:
            query = "SELECT route, asn, source FROM routes_view WHERE route = %s;"
        else:
            query = "SELECT route, asn, source FROM routes_view WHERE route && %s;"

        return self._execute_fetchall(query, (prefix,))


    def query_managed_prefix(self, prefix):

        query = "SELECT route, source FROM managed_routes_view WHERE route && %s;"
        return self._execute_fetchall(query, (prefix,))


    def query_source(self, source):
        """
        source --> [ (route, asn) ]
        """
        query = "SELECT route, asn FROM routes_view WHERE source = %s;"
        return self._execute_fetchall(query, (source,))


    def query_as(self, asn):

        query = "SELECT route, source FROM routes_view WHERE asn = %s;"
        return self._execute_fetchall(query, (asn,))


    def query_as_contain(self, as_):

        query = "SELECT as_macro, source FROM as_sets_view WHERE %s = any(members);"
        return self._execute_fetchall(query, (as_,))



if __name__ == '__main__':

    dsn = "dbname=irrexplorer"
    db = IRRSQLDatabase(dsn)

    r = db.query_prefix('109.105.113.0/24')
    print 'matching', r

    r2 = db.query_prefix('109.105.113.0/24', exact=True)
    print 'exact', r2

    r3 = db.query_managed_prefix('109.105.113.0/24')
    print 'managed', r3
    print

    print 'as routes'
    r4 = db.query_as(2603)
    for r,s in r4:
        print r,s

    print 'as in macros'
    r5 = db.query_as_contain('AS2603')
    for m,s in r5:
        print m,s


