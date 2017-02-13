# Copyright (C) 2015 Job Snijders <job@instituut.net>
# Copyright (C) 2015 NORDUnet A/S
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

        if line.startswith('route:') or line.startswith('route6:'):
            object_ = readAttr(line)
            obj_type = ROUTE
            ctx = None

        elif line.startswith('as-set:'):
            object_ = readAttr(line).upper()
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

    if obj_type == AS_SET:
        return AS_SET, (object_, members, source)
    elif obj_type == ROUTE:
        return ROUTE, (object_, origin, source)
    else:  # in case no route{,6} or as-set was found
        return None, None
