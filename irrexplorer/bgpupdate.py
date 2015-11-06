#!/usr/bin/env python

"""
Functionality to update BGP entries in IRRExplorer database.
"""

import urllib2
import ipaddr

INSERT_STM = "SELECT create_route (%s, %s, 'bgp');"
DELETE_STM = "DELETE FROM routes USING sources WHERE routes.route = %s AND routes.asn = %s AND routes.source_id = sources.id AND sources.name = 'bgp';"


def updateBGP(source_url, db):

    source_routes = set()

    # get the bgp routes
    for line in urllib2.urlopen(source_url):
        route, asn = line.strip().split(' ')
        source_routes.add( (route, int(asn)) )

    fltrd_source_routes = set()
    for route, asn in source_routes:
        try:
            route_obj = ipaddr.IPNetwork(route)
        except ValueError:
            print 'invalid route in BGP feed: %s' % route
            continue

        # block router2router linknets
        if route_obj.version == 4 and route_obj.prefixlen < 27:
            fltrd_source_routes.add((route, int(asn)))
        if route_obj.version == 6 and route_obj.prefixlen < 124:
            fltrd_source_routes.add((route, int(asn)))

    print 'BGP table fetched and table build, routes:', (len(source_routes))

    # then the database routes
    db_routes = set()
    bgp_rows = db.query_source('bgp')
    print 'Got database entries, routes:', len(bgp_rows)

    for route, asn in bgp_rows:
        db_routes.add((route, int(asn)))

    # calculate the diff, intersection is just for logging
    routes_is = fltrd_source_routes & db_routes
    print 'Unchanged routes: %i' % len(routes_is)

    deprecated_routes = db_routes - fltrd_source_routes
    print 'Deprecated routes:', len(deprecated_routes)

    new_routes = fltrd_source_routes - db_routes
    print 'New routes:', len(new_routes)

    # create + send update statements
    cur = db._get_cursor()

    for route, asn in deprecated_routes:
        cur.execute(DELETE_STM, (route, asn) )

    for route, asn in new_routes:
        cur.execute(INSERT_STM, (route, asn) )

    db.conn.commit()
    cur.close() # so it doesn't linger while sleeping

    print 'BPG update commit done and cursor closed'


