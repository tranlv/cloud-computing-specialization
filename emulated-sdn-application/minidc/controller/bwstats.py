#!/usr/bin/env python

import math
import os
import sys
import topo

if 'PYTHONPATH' in os.environ:
    sys.path = os.environ['PYTHONPATH'].split(':') + sys.path

# add minidc path
dcdir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", ".."))
sys.path.append(dcdir)
import minidc.stats

def conv_bytes(size):
    if size <= 0:
        return "{0}B".format(size)

    sz = ("B", "KB", "MB", "GB", "TB", "PB", "EB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size/p, 2)
    return "{0}{1}".format(s, sz[i])

class BandwidthStats(object):
    def __init__(self, topo):
        self.topo = topo
        self.hostBw = {}
        self.vlanBw = {}
        self.swDroppedPkts = {}
        self.dpCounter = 0
        minidc.stats.bwStats.start()
        minidc.stats.tenantStats.start()

        for host in self.topo.hosts.keys():
            self.hostBw[host] = {
                'in' : 0,
                'out' : 0
            }

        for vlan in self.topo.vlans.keys():
            self.vlanBw[vlan] = {
                'in' : 0,
                'out' : 0
            }

        for sw in self.topo.switches:
            self.swDroppedPkts[sw] = 0

    def addDroppedPktStat(self, sw, droppedPkts):
        self.swDroppedPkts[sw] = droppedPkts

    def addHostBwStat(self, host, txbytes, rxbytes):
        # reverse rx/tx since rx bytes on switch == tx bytes from host
        host_rx = txbytes
        host_tx = rxbytes
        self.hostBw[host]['in'] = host_rx
        self.hostBw[host]['out'] = host_tx
        minidc.stats.bwStats.add(host, host_tx, host_rx)

    def updateTenantStats(self):
        for vlan in self.vlanBw.keys():
            self.vlanBw[vlan] = {
                'in' : 0,
                'out' : 0
            }

        for host in self.hostBw.keys():
            for vlan in self.topo.hosts[host].vlans:
                self.vlanBw[vlan]['in'] += self.hostBw[host]['in']
                self.vlanBw[vlan]['out'] += self.hostBw[host]['out']

        for vlan in self.vlanBw.keys():
            minidc.stats.tenantStats.add("vlan" + str(vlan),
                                         self.vlanBw[vlan]['out'],
                                         self.vlanBw[vlan]['in'])

        # TODO: refactor this
        # occasionally write dropped pkt stats
        self.dpCounter += 1
        if self.dpCounter > 1:
            self.dpCounter = 0
            #tot = sum(self.swDroppedPkts.values())
            minidc.stats.drpPktStats.add(("sw", "dpkts"))
            for sw, dpkts in self.swDroppedPkts.iteritems():
                #p = 0 if tot == 0 else float(dpkts / tot)
                minidc.stats.drpPktStats.add((sw, dpkts))
            minidc.stats.drpPktStats.write()
            minidc.stats.drpPktStats.clear()

    def hostBwString(self):
        s = "*********** Host BW Usage **********\n"
        for h, b in self.hostBw.iteritems():
            s += "{0} in  = {1}\n".format(h, conv_bytes(b['in']))
            s += "{0} out = {1}\n".format(h, conv_bytes(b['out']))

        return s

    def tenantBwString(self):
        s = "*********** Tenant BW Usage **********\n"
        for v, b in self.vlanBw.iteritems():
            if v >= 0:
                s += "{0} in  = {1}\n".format(v, conv_bytes(b['in']))
                s += "{0} out = {1}\n".format(v, conv_bytes(b['out']))

        return s
