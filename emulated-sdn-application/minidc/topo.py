#!/usr/bin/env python

"""
FattreeTopology: creates a simple fattree topology with N edge switches
    connected to N-1 core switches.  Each edge switch connects to 2 hosts.
"""

from mininet.topo import Topo

class FattreeTopology(Topo):
    def build(self, numEdgeSwitches=2, bw=20, hostsPerEdge=2):
        linkopts = dict(bw=bw, delay='1ms', max_queue_size=500, loss=0, use_htb=True)
        numHosts = numEdgeSwitches * hostsPerEdge
        numCoreSwitches = numEdgeSwitches - 1

        hostIds = range(1, numHosts+1)
        firstSwitch = max(101, numHosts+1)
        edgeSwitchIds = range(firstSwitch, numEdgeSwitches + firstSwitch)
        coreSwitchIds= range(numEdgeSwitches + firstSwitch,
                            numEdgeSwitches + firstSwitch + numCoreSwitches)

        self._coreSwitches = []
        self._edgeSwitches = []
        self._hosts = []
        self._links = {}

        for s in coreSwitchIds:
            switch = self.addSwitch('s%s' % s, protocols='OpenFlow13')
            self._coreSwitches.append(switch)
            self._links[switch] = []
        for s in edgeSwitchIds:
            switch = self.addSwitch('s%s' % s, protocols='OpenFlow13')
            self._edgeSwitches.append(switch)
            self._links[switch] = []

        for i, s1 in enumerate(self._coreSwitches):
            for j, s2 in enumerate(self._edgeSwitches):
                self.addLink(s1, s2, **linkopts)
                self._links[s1].append(s2)
                self._links[s2].append(s1)

        for i, h in enumerate(hostIds):
            host = self.addHost('h%s' % h)
            self._hosts.append(host)
            switchNum = firstSwitch + (h % numEdgeSwitches)
            switch = "s%s" % switchNum
            self.addLink(switch, host, **linkopts)
            self._links[host] = [switch]
            self._links[switch].append(host)
