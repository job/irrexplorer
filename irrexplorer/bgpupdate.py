#!/usr/bin/env python

"""
Functionality to update BGP entries in IRRExplorer database.
"""

import urllib2
import ipaddr
import logging

INSERT_STM = "SELECT create_route (%s, %s, 'bgp');"
DELETE_STM = "DELETE FROM routes USING sources WHERE routes.route = %s AND routes.asn = %s AND routes.source_id = sources.id AND sources.name = 'bgp';"


def updateBGP(source_url, db):

    logging.info('Updating BGP information')

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
            logging.error('Invalid route in BGP feed: %s' % route)
            continue

        # block router2router linknets / small blocks
        if route_obj.version == 4 and route_obj.prefixlen >= 29:
            continue
        if route_obj.version == 6 and route_obj.prefixlen >= 124:
            continue

        fltrd_source_routes.add((route, int(asn)))

    logging.info('BGP table fetched and table build, %i routes' % (len(source_routes)))

    # then the database routes
    db_routes = set()
    bgp_rows = db.query_source('bgp')
    logging.info('Got database entries, %i routes' % len(bgp_rows))

    for route, asn in bgp_rows:
        db_routes.add((route, int(asn)))

    # calculate the diff, intersection is just for logging
    routes_is = fltrd_source_routes & db_routes
    deprecated_routes = db_routes - fltrd_source_routes
    new_routes = fltrd_source_routes - db_routes

    logging.info('Routes: %i unchanged / %i deprecated / %i new' % (len(routes_is), len(deprecated_routes), len(new_routes)))

    # create + send update statements
    cur = db._get_cursor()

    for route, asn in deprecated_routes:
        cur.execute(DELETE_STM, (route, asn) )

    for route, asn in new_routes:
        cur.execute(INSERT_STM, (route, asn) )

    db.conn.commit()
    cur.close() # so it doesn't linger while sleeping

    logging.info('BPG update commit done and cursor closed')


