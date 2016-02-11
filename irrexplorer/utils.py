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

"""
Utility stuff.

Right now it just classifies search strings as the right object.
"""

import ipaddr


class SearchObject(object):

    def __init__(self, value):
        self.value = value


class Prefix(SearchObject): pass # also used for ip addresses
class ASNumber(SearchObject): pass
class ASMacro(SearchObject): pass



def classifySearchString(data):

    data = data.strip()

    try:
        return ASNumber(int(data))
    except ValueError:
        pass

    if data.upper().startswith('AS-'):
        return ASMacro(data.upper()) # as macros are always uppcase

    if data.upper().startswith('AS'):
        try:
            return ASNumber(int(data[2:]))
        except ValueError:
            raise ValueError('Cannot classify %s' % data)

    try:
        ipaddr.IPNetwork(data)
        return Prefix(data)
    except ValueError:
        pass

    raise ValueError('Cannot classify %s' % data)

