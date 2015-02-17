#!/usr/bin/env python
# Copyright (C) 2014 Job Snijders <job@instituut.net>
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
# ARISING IN ANY WAY OUT OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
    Parse RPSL as-set, route, route6 objects
    Return the important parts
"""


def parse_object(rpsl_object):
    """
    Args:
        rpsl_object (list): single object

    Returns:
        None if the object is not of interest
        (dict) if the object was route{,6} or as-set
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
        return result

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
        result['members'] = set(filter(None, result['members']))
        return result


def parse_dump(dumpfile):
    """
    Take a file and find objects of interest, Can be called as generator

    Args:
        dumpfile (file)

    Returns:
        dict or None
    """
    rpsl_object = []
    for line in dumpfile:
        if line.startswith(('%', '#')):
            continue
        if line.strip():
            rpsl_object.append(line)
        else:
            if rpsl_object:
                yield parse_object(rpsl_object)
            rpsl_object = []


if __name__ == '__main__':
    dump_file = open('irrtest.data')
    print list(parse_dump(dump_file))
