#!/usr/bin/env python

def getSourceMap():

    sources = {}
    for line in open('sources.map').readlines():
        source, id_ = line.strip().split(',')
        sources[source] = id_

    return sources


if __name__ == '__main__':
    for k,v in getSourceMap().items():
        print k,v

