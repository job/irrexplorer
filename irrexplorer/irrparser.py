#!/usr/bin/env python

import sys


AS_SET = 'as-set'
ROUTE  = 'route'


def readAttr(line):
    sp = line.split(':',1)[1]
    if '#' in sp:
        sp = sp.split('#',1)[0]
    return sp.strip()


def convertASDot(origin):
    if '.' in origin:
        high, low = map(int, origin.split('.'))
        origin = (high << 16) + low
    return origin


def irrParser(datasource):

    obj_type = None
    object_  = None
    origin   = None
    source   = None
    members  = []

    for line in datasource:

        if line == '\n': # new block
            if obj_type == AS_SET:
                yield AS_SET, (object_, members, source)
            elif obj_type == ROUTE:
                yield ROUTE, (object_, origin, source)

            obj_type = object_ = origin = source = ctx = None
            members = []
            continue

        if line.startswith('route:') or line.startswith('route6:'):
            object_ = readAttr(line)
            obj_type = ROUTE
            ctx = None

        elif line.startswith('as-set:'):
            object_ = readAttr(line)
            obj_type = AS_SET
            ctx = None

        elif line.startswith('origin:'):
            origin = readAttr(line)[2:]
            origin = convertASDot(origin)
            origin = int(origin)
            ctx = None

        elif line.startswith('source:'):
            source = readAttr(line).lower()
            ctx = None

        elif line.startswith('members:'):
            members += [ m.strip() for m in readAttr(line).split(',') if m.strip() ]
            ctx = members

        elif line.startswith((' ','\t')) and ctx:
            ctx += [ m.strip() for m in line.split(',') if m.strip() ]

        else:
            ctx = None


def nrtmParser(data_source):

    for line in data_source:

        if line.startswith(('%', '#', 'C')):
            continue
        if line.startswith(('ADD', 'DEL')):
            tag, serial = line.strip().split(' ')
            obj = irrParser(data_source).next()
            yield tag, serial, obj



if __name__ == '__main__':
    f = open('nrtm.dump')
    for tag, serial, (obj_type, obj_data) in nrtmParser(f):
        obj, data, source = obj_data
        print tag, serial, obj_type, obj, source

