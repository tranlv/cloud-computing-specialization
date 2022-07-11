#!/usr/bin/env python

import itertools
import pprint
import re

def tryint(s):
    return int(s) if s.isdigit() else s

def natural_sort(string):
    return [ tryint(c) for c in re.split('(\d+)', string) ]

class Host(object):
    def __init__(self, name, ip, eth, switch, vlans):
        self.name = name
        self.ip = ip
        self.eth = eth
        self.switch = switch
        self.vlans = vlans

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{0}: ({1}, {2}, {3}, {4})".format(self.name,
                                                  self.ip,
                                                  self.eth,
                                                  self.switch,
                                                  self.vlans)

class CoreSwitch(object):
    def __init__(self, name, dpid, vlans):
        self.name = name
        self.dpid = dpid
        self.vlans = vlans

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{0}: ({1}, {2})".format(self.name,
                                        self.dpid,
                                        self.vlans)

class EdgeSwitch(object):
    def __init__(self, name, dpid, neighbors):
        self.name = name
        self.dpid = dpid
        self.neighbors = neighbors

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "{0}: ({1}, {2})".format(self.name,
                                        self.dpid,
                                        self.neighbors)

class Topology(object):
    def __init__(self, config):
        self.hosts = {}
        self.vlans = {}
        self.switches = []
        self.edgeSwitches = {}
        self.coreSwitches = {}
        self.ports = {}
        self.parse(config)

    def getVlanCore(self, vlan):
        for core in self.coreSwitches.values():
            if vlan in core.vlans:
                return core.name
        return None

    def dpidToName(self, dpid):
        for sw in self.edgeSwitches.values() + self.coreSwitches.values():
            if dpid == sw.dpid:
                return sw.name
        return None

    # XXX: assumes ports are ordered alphabetically by switch, host name
    def parse(self, fname):
        with open(fname) as f:
            contents = self.splitSections(f.readlines(), '*')

        self.coreSwitches = self.parseCores(contents[0])
        self.edgeSwitches = self.parseEdges(contents[1])
        self.switches = self.coreSwitches.keys() + self.edgeSwitches.keys()
        self.hosts = self.parseHosts(contents[1])
        self.ports = self.setPorts()

        for host in self.hosts.values():
            for v in host.vlans:
                if v not in self.vlans.keys():
                    self.vlans[v] = []
                self.vlans[v].append(host.name)

    def setPorts(self):
        ports = {}
        for s in self.coreSwitches.keys():
            ports[s] = {}
            i = 1
            for edge in sorted(self.edgeSwitches.keys(),
                               key=natural_sort):
                ports[s][i] = edge
                ports[s][edge] = i
                i += 1

        for s in self.edgeSwitches.keys():
            ports[s] = {}
            i = 1
            for core in sorted(self.coreSwitches.keys(),
                               key=natural_sort):
                ports[s][i] = core
                ports[s][core] = i
                i += 1

            for host in sorted(self.edgeSwitches[s].neighbors,
                               key=natural_sort):
                ports[s][i] = host
                ports[s][host] = i
                i += 1

        return ports

    def parseEdges(self, cfg):
        s = {}
        for line in cfg:
            fields = line.split(' ')
            name, dpid = fields[0], int(fields[1])
            neighbors = [n.split(',')[0] for n in fields[2:]]
            s[name] = EdgeSwitch(name, dpid, neighbors)
        return s

    def parseCores(self, cfg):
        s = {}
        for line in cfg:
            fields = line.split(' ')
            name, dpid = fields[0], int(fields[1])
            vlan = [] if len(fields) < 3 \
                   else [int(v) for v in fields[2].split(':')]
            s[name] = CoreSwitch(name, dpid, vlan)
        return s

    def parseHosts(self, cfg):
        h = {}
        for line in cfg:
            fields = line.split(' ')
            switch = fields[0]
            for host in fields[2:]:
                hfields = host.split(',')
                name, ip, eth = hfields[0], hfields[1], hfields[2]
                vlans = [int(v) for v in hfields[3].split(':')]
                h[name] = Host(name, ip, eth, switch, vlans)
        return h

    def splitSections(self, contents, separator):
        contents = [j.strip() for j in contents]
        return [list(j) for i,j in
                itertools.groupby(contents, lambda x:x in separator) if not i]
