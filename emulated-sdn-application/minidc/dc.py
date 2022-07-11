#!/usr/bin/env python

"""
Datacenter: creates tenant profiles, assigning unique VLANs to each.
"""

import os
import random

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.node import RemoteController
from mininet.node import Host

from minidc.placement import *
from minidc.profiles import *
from minidc.topo import FattreeTopology
import minidc.stats as stats

cfd = os.path.dirname(os.path.abspath(__file__))
cfgfile = os.path.normpath(os.path.join(cfd, "config.txt"))

class Datacenter:
    def __init__(self, numEdgeSwitches=2):
        self.numEdgeSwitches = numEdgeSwitches
        self.vlans = 0
        self.tenants = []
        self.potentialTenantTypes = []
        self.vlanMap = {}

    def getVlan(self, hostname):
        if hostname in self.vlanMap.keys():
            return self.vlanMap[hostname]
        else:
            # host has no role, assign it all vlans
            return ":".join("%s" % i for i in range(self.vlans))

    def assign(self, hosts, tenant, indices):
        h = [hosts[x] for x in indices]
        tenant.create(h)
        for i in h:
            self.vlanMap[i.name] = tenant.vlan

    def setup(self, hosts, tenants):
        # add tenant
        for t in tenants:
            t.assignVlan(self.vlans)
            self.vlans += 1
            self.tenants.append(t)

        p = getPlacement(len(hosts), self.numEdgeSwitches)
        index = 0

        # assign hosts to each tenant
        for t in self.tenants:
            self.assign(hosts, t, p[index : index + t.numNodes])
            index += t.numNodes

        self.printAssignments()
        self.logAssignments()

    def printAssignments(self):
        for t in self.tenants:
            roleStr = ", ".join(["{0}={1}".format(h.host.name, h)
                                 for h in t.apps])
            hostStr = ", ".join([h.name for h in t.nodes])
            print "VLAN {0}: {1} - [{2}]".format(t.vlan, t, hostStr)
            print "    ", format(roleStr)

    def logAssignments(self):
        for t in self.tenants:
            stats.tenantInfo.add((t.vlan, str(t), len(t.apps)))
            for h in t.apps:
                stats.roleInfo.add((h.host.name, t.vlan, str(h)))

        stats.tenantInfo.write()
        stats.roleInfo.write()

    def start(self):
        map(lambda p: p.start(), self.tenants)

    def stop(self):
        map(lambda p: p.stop(), self.tenants)

def writeConfig(net, topo, dc, outFile="config.txt"):
    lines = ""

    coreNum = 0
    for c in topo._coreSwitches:
        # assign vlans
        v = []
        for vid in range(dc.vlans):
            if vid % len(topo._coreSwitches) == coreNum:
                v.append(vid)
        node = net.get(c)
        lines += "{0} {1} {2}\n".format(node.name, int(node.dpid, 16), ":".join("%s" % i for i in v))
        coreNum += 1
    lines += "*\n"
    for e in topo._edgeSwitches:
        adjacent = [x for x in topo._links[e] if not topo.isSwitch(x)]
        l = ["%s,%s,%s,%s" % (net.get(x).name, net.get(x).IP(), net.get(x).MAC(), dc.getVlan(net.get(x).name)) for x in adjacent]
        node = net.get(e)
        lines += "{0} {1} {2}\n".format(node.name, int(node.dpid, 16), " ".join(l))
    lines += "*\n"
    for e in topo._hosts:
        lines += e + "\n"

    with open(cfgfile, "wb") as f:
        f.write(lines)

def run(remoteCtrl=False):
    tenants = []
    tenants.append(MemcacheProfile(numNodes=3, trials=-1))
    tenants.append(IperfProfile(numNodes=3, bw=1.2, maxFlows=12))

    topo = FattreeTopology(numEdgeSwitches=3, bw=5)

    if remoteCtrl:
        c = RemoteController('rmController','127.0.0.1')
        net = Mininet(topo=topo, link=TCLink, controller=c)
    else:
        net = Mininet(topo, link=TCLink)

    dc = Datacenter()

    dc.setup(net.hosts, tenants)

    writeConfig(net, topo, dc)

    dc.start()
    net.start()
    dumpNodeConnections(net.hosts)
    CLI(net)

    dc.stop()
    net.stop()

if __name__ == '__main__':
    run()
