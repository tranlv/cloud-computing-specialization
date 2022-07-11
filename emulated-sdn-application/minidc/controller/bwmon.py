#!/usr/bin/env python

import os

from ryu.base import app_manager
from ryu.controller import dpset
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub

from bwstats import BandwidthStats
from topo import Topology

cfgfile = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "config.txt"))

STAT_REQUEST_PERIOD = 5

'''
Useful Topology class functions/properties:

    Topology.hosts - a dictionary of Host objects keyed on host name
    Topology.switches - a list of switch names
    Topology.coreSwitches - dictionary of CoreSwitch objects keyed on
                        switch name
    Topology.edgeSwitches - dictionary of EdgeSwitch objects keyed on
                        switch name
    Topology.vlans - dictionary of vlan members, keyed on the vlan id (an integer)
    Topology.ports[sw][inNode] - returns the port number on switch sw connected to
                             the adjacent node inNode, if inNode is a node name
                             (ie, switch or host).  If inNode is a number, returns
                             the node or switch name on that port on switch sw.
    Topology.getVlanCore(vlanId) - returns the core switch pre-assigned for the
                               vlan vlanId
    Topology.dpidToName(dpid) - returns the switch name associated with the
                                specified dpid


Useful CoreSwitch class functions/properties:

    CoreSwitch.name - the name of the switch (eg, 's101')
    CoreSwitch.dpid - the dpid of the switch (eg, 101)
    CoreSwitch.vlans - list of pre-assigned vlans for the switch to handle


Useful EdgeSwitch class functions/properties:

    EdgeSwitch.name - the name of the switch (eg, 's101')
    EdgeSwitch.dpid - the dpid of the switch (eg, 101)
    EdgeSwitch.neighbors - list of hosts' names (eg, 'h6') attached to
                           the switch


Useful Host class functions/properties:

    Host.name - the name of the host (eg, 'h6')
    Host.eth - the MAC address of the host
    Host.switch - the switch to which the host is connected
    Host.vlans - a list of vlans with which the host is associated


Use BandwidthStats class functions/properties:

    BandwidthStats.addHostBwStat(hostname, txbytes, rxbytes) - log transmitted
                        and received bytes for the specified host
    BandwidthStats.hostBwString() - returns pretty-printed string for bandwidth
                        usage (transmitted and received bytes) by host
    BandwidthStats.tenantBwString() - returns pretty-printed string for
                        bandwidth usage (transmitted and received) by tenant


Useful OFPortStats class functions/properties:

     OFPortStats.port_no - the port number for the statistic
     OFPortStats.rx_bytes - the number of received bytes from port_no
     OFPortStats.tx_bytes - the number of transmitted bytes from port_no
'''

class BandwidthMonitor(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'dpset' : dpset.DPSet,
    }

    def __init__(self, *args, **kwargs):
        super(BandwidthMonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.dpset = kwargs['dpset']
        self.topo = Topology(cfgfile)
        self.bwstats = BandwidthStats(self.topo)
        self.monitor_thread = hub.spawn(self.monitor)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def stateChangeHandler(self, ev):
        datapath = ev.datapath
        if datapath.id:
            if ev.state == MAIN_DISPATCHER:
                if not datapath.id in self.datapaths:
                    self.logger.debug('register datapath: %016x', datapath.id)
                    self.datapaths[datapath.id] = datapath
            elif ev.state == DEAD_DISPATCHER:
                if datapath.id in self.datapaths:
                    self.logger.debug('unregister datapath: %016x', datapath.id)
                    del self.datapaths[datapath.id]

    def monitor(self):
        while True:
            self.statsReplied = 0
            for dp in self.datapaths.values():
                self.requestStats(dp)
            hub.sleep(STAT_REQUEST_PERIOD)

    def requestStats(self, datapath):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def statsReplyHandler(self, ev):
        # Here, a datapath (ie, switch) responds to the stats request.
        body = ev.msg.body
        datapath = ev.msg.datapath
        dpid = datapath.id

        # name of switch reporting data, name will be something like s101 or s102
        name = self.topo.dpidToName(dpid)

        totalDropped = 0
        for stat in body:
            totalDropped += stat.tx_dropped
            totalDropped += stat.rx_dropped
        self.bwstats.addDroppedPktStat(name, totalDropped)

        # ASSIGNMENT 2:
        # If the switch reporting the statistic is an edge switch, and the
        # port connects to a host, log the statistic to bwstats, using
        # self.bwstats.addHostBwStat(hostname, transmitted bytes, received bytes)
        # (Hint: you can look up the switch or host connected to a port using
        #  self.topo.ports[switch name][port number])
        for stat in body:
            # check if switch reporting the statistic is an edge switch
            if name in self.topo.edgeSwitches.keys() and stat.port_no in self.topo.ports[name].keys():
                device = self.topo.ports[name][stat.port_no]
                if device in self.topo.hosts.keys():
                    transmitted_bytes = stat.tx_bytes
                    received_bytes = stat.rx_bytes
                    self.bwstats.addHostBwStat(device , transmitted_bytes, received_bytes)

        # periodically print tenant bandwidth usage
        self.statsReplied += 1
        if self.statsReplied == len(self.datapaths):
            self.bwstats.updateTenantStats()
            self.logger.info(self.bwstats.tenantBwString())
