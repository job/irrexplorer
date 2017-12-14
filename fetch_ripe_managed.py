#!/usr/bin/env python3

# Job Snijders <job@instituut.net>

from aggregate6 import aggregate

import ipaddress
import requests
import sys

ripe_url = "http://ftp.ripe.net/ripe/stats/delegated-ripencc-latest"

r = requests.get(ripe_url)

pfx_list = []

for entry in str(r.text).split('\n'):
    if not entry:
        continue
    try:
        afi, start_ip, count = entry.split('|')[2:5]
    except ValueError as e:
        print(entry)
        sys.exit(1)
    ip_type = entry.split('|')[-1]
    if not ip_type in ["allocated", "assigned"]:
        continue
    if afi == "ipv4":
        first_ip = ipaddress.ip_address(start_ip)
        last = int(first_ip) + int(count) - 1
        last_ip = ipaddress.ip_address(last)
        cidrs = ipaddress.summarize_address_range(first_ip, last_ip)
        for prefix in cidrs:
            pfx_list.append(str(prefix))
    if afi == "ipv6":
        pfx_list.append(("{}/{}".format(start_ip, count)))

for prefix in aggregate(pfx_list):
    print(prefix)
