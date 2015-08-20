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
            self.conn = psycopg2.connect("dbname=irrexplorer user=irrexplorer")
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

        query = """SELECT route, asn, source FROM routes_view WHERE asn = %s
                   UNION ALL
                   SELECT DISTINCT routes_view.route, NULL::integer, managed_routes_view.source || '_managed' AS managed_routes
                   FROM routes_view INNER JOIN managed_routes_view ON (routes_view.route && managed_routes_view.route)
                   WHERE asn = %s;"""
        return self._execute_fetchall(query, (asn,asn))


    def query_as_deep(self, asn):

        # This query find all prefixes that are registered/homing from and AS number AND
        # any other prefixes that covers/are covered by any of those prefixes
        # Furthermore, managed prefixes and source are returned for matching prefixes.
        # These have NULL as their AS and source field will be source + '_managed'
        query = """SELECT DISTINCT rv.route, rv.asn, rv.source FROM routes_view rv, routes_view r
                   WHERE rv.route && r.route AND r.asn = %s
                   UNION ALL
                   SELECT DISTINCT routes_view.route, NULL::integer, managed_routes_view.source || '_managed' AS managed_routes
                   FROM routes_view INNER JOIN managed_routes_view ON (routes_view.route && managed_routes_view.route)
                   WHERE asn = %s;"""
        return self._execute_fetchall(query, (asn,asn))


    def query_as_contain(self, as_):

        query = "SELECT as_macro, source FROM as_sets_view WHERE %s = any(members);"
        return self._execute_fetchall(query, (as_,))


    def query_as_macro(self, as_macro):

        query = """SELECT members, source FROM as_sets_view WHERE as_macro = %s;"""
        return self._execute_fetchall(query, (as_macro,))


    def query_as_macro_expand(self, as_macro):

        # Recusive sql query, hang on to your shorts
        # Some as macro seem to either take a long time, or somehow loop forever, so added limit
        # The reason for this is not due to cycles as such, but because the query expands every as-macro path
        # This means that the same as macro will be listed multiple times. this means that queries can take a
        # very long. In particular, if there are multiple paths to a big macro, the whole thing will blow up.

        query = """WITH RECURSIVE member_list(as_macro, path, members, source, depth, cycle) AS (
                    SELECT as_macro, ARRAY[as_macro], members, source, 1 AS depth, false FROM as_sets_view WHERE as_macro = %s
                    UNION
                    SELECT a.as_macro, path || a.as_macro,  a.members, a.source, depth+1 AS depth, a.as_macro = ANY(path) AS cycle FROM as_sets_view a
                    JOIN member_list b ON ( a.as_macro = ANY(b.members) AND NOT cycle)
                   )
                SELECT as_macro, source, depth, path, members FROM member_list LIMIT 10000;
                """
        return self._execute_fetchall(query, (as_macro,))



if __name__ == '__main__':

    dsn = "dbname=irrexplorer"
    db = IRRSQLDatabase(dsn)

    print 'Prefix'
    r1 = db.query_prefix('109.105.113.0/24')
    print r1

    print
    print 'Prefix exact'
    r2 = db.query_prefix('109.105.112.0/21', exact=True)
    print r2

    print
    print 'Managed prefix'
    r3 = db.query_managed_prefix('109.105.113.0/24')
    print r3

    print
    print 'AS Prefixes'
    r4 = db.query_as(2603)
    for r,s in r4:
        print r,s

    print
    print 'AS contain'
    r5 = db.query_as_contain('AS-SUNET')
    for m,s in r5:
        print m,s

    print
    print 'AS macro members'
    r6 = db.query_as_macro('AS-IS')
    for m,s in r6:
        print s,m

    print
    print 'AS macro expand'
    r7 = db.query_as_contain('AS-IS')
    for m,s in r7:
        print s,m

