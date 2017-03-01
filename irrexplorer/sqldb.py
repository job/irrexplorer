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


    def query_prefix(self, prefix):

        query = """SELECT rv.route, rv.asn, rv.source, mrv.source||'_managed' AS managed
                   FROM routes_view rv
                   JOIN routes_view r ON cidr_to_range(rv.route) && cidr_to_range(r.route)
                   LEFT OUTER JOIN managed_routes_view mrv ON rv.route && mrv.route
                   WHERE r.route && %s;"""

        return self._execute_fetchall(query, (prefix,))


    def query_source(self, source):
        """
        source --> [ (route, asn) ]
        """
        query = "SELECT route, asn FROM routes_view WHERE source = %s;"
        return self._execute_fetchall(query, (source,))


    def query_as(self, asn):

        query = """SELECT rv.route, rv.asn, rv.source, mrv.source||'_managed' as managed_routes
                   FROM routes_view rv
                   LEFT OUTER JOIN managed_routes_view mrv ON (rv.route && mrv.route)
                   WHERE rv.asn = %s;"""
        return self._execute_fetchall(query, (asn,))


    def query_as_deep(self, asn):

        # This query find all prefixes that are registered/homing from and AS number AND
        # any other prefixes that covers/are covered by any of those prefixes
        # Furthermore, managed prefixes and source are added for matching prefixes.
        # These have an entry in the fouth column. Note that duplicates can be created here (but managed space should not overlap)
        # The adresss range of 2002::/16 and 192.88.99.0/24 are 6t40 addresses with lots of entries, and hence filtered out

        query = """
                SELECT DISTINCT rv.route, rv.asn, rv.source, mrv.source||'_managed' as managed_routes
                FROM
                    (SELECT DISTINCT route FROM routes_view WHERE asn = %s) r
                    JOIN routes_view rv ON cidr_to_range(r.route) && cidr_to_range(rv.route) AND NOT rv.route <<= '2002::/16'::cidr AND NOT rv.route <<= '192.88.99.0/24'::cidr
                    LEFT OUTER JOIN managed_routes_view mrv ON (rv.route && mrv.route);
                """

        return self._execute_fetchall(query, (asn,))


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
                    SELECT as_macro, ARRAY[as_macro], members, source, 1 AS depth, false FROM as_sets_view WHERE as_macro ILIKE %s
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
    print 'AS Prefixes'
    r4 = db.query_as(2603)
    for r,a,s,m in r4:
        print r,a,s,m

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

