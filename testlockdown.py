#!/usr/bin/env python

import yaml
import textfsm
from StringIO import StringIO
from radix import Radix

config_file = "config.yml"

config = yaml.load(open(config_file).read())
print config

""" BGP JSON messages:

    { "exabgp": "3.3.0", "time": 1423308720, "neighbor": { "ip":
        "165.254.255.1", "update": { "attribute": { "origin": "igp", "as-path":
            [ 2914, 1299, 8529, 48159, 57543, 61129 ], "med": 0,
            "local-preference": 100, "atomic-aggregate": false, "community": [
            [ 2914, 420 ], [ 2914, 1206 ], [ 2914, 2203 ], [ 2914, 3200 ] ] },
            "announce": { "83.231.213.229" : { "178.157.60.0/24": {  } } } } }
            }

"""

"""
    route:          91.213.230.0/24
    origin:         AS20927

    route:          213.239.64.0/18
    herpa:          dweoinwf
    origin:         AS2116

"""

template = """# textfsm template
Value Required Prefix ([^ ]+)
Value Required Origin ([0-9]+)

Start
  ^route:\s+${Prefix}
  ^origin:\s+AS${Origin} -> Record Start

"""

template_file = StringIO(template)
