#!/usr/bin/env python
"""
    Parse RPSL as-set, route, route6 objects
    Return the important parts
"""


def parse_object(rpsl_object):
    """
        rpsl_object (list): single object
    """
    def fetch_value(line):
        return line.split(':', 1)[1].split('#')[0].strip()

    object_type = rpsl_object[0].split(':')[0]
    object_name = fetch_value(rpsl_object.pop(0))
    result = {"kind": object_type, "name": object_name}

    if object_type in ["route", "route6"]:
        for line in rpsl_object:
            if line.split(':')[0] == "origin":
                result['origin'] = fetch_value(line)
            if line.split(':')[0] == "source":
                result['source'] = fetch_value(line)

    elif object_type == "as-set":
        result['members'] = []
        in_members_context = False
        while rpsl_object:
            line = rpsl_object.pop(0).split('#')[0]
            if line.split(':')[0] == "members":
                members = fetch_value(line).split(',')
                result['members'] += map(str.strip, members)
                in_members_context = True
            elif in_members_context and not line.lstrip() == line:
                result['members'] += map(str.strip, line.split(','))
            else:
                in_members_context = False
    return result

rpsl_object = []
for line in open('irrtest.data').readlines():
    if line.strip():
        rpsl_object.append(line)
    else:
        print parse_object(rpsl_object)
        rpsl_object = []
