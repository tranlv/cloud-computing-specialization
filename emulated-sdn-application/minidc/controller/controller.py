#!/usr/bin/env python

import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer
import threading

from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller import ofp_event

from policy import DefaultPolicy, StaticPolicy, AdaptivePolicy
from bwmon import BandwidthMonitor

class Controller(BandwidthMonitor):
    def __init__(self, *args, **kwargs):
        super(Controller, self).__init__(*args, **kwargs)
        self.rpcStart()
        self.policies = { "default" : DefaultPolicy(self.topo),
                          "static" : StaticPolicy(self.topo),
                          "adaptive" : AdaptivePolicy(self.topo,
                                                      self.bwstats,
                                                      self.logger)
                      }
        self.curpolicy = "default"

    def rpcStart(self):
        self.server = SimpleXMLRPCServer(("localhost", 8000), logRequests=False)
        self.server.register_instance(self)
        self.server.register_function(self.rpcClear, "clear")
        self.server.register_function(self.rpcLoadPolicy, "load")
        self.server.register_function(self.rpcCurrentPolicy, "current")
        thread = threading.Thread(target=self.server.serve_forever)
        thread.start()
        self.logger.info("starting rpc server")

    def rpcLoadPolicy(self, policy):
        self.logger.info("rpc request load rt {0} (cur: {1})".format(policy, self.curpolicy))

        if policy not in self.policies.keys():
            return (False, "Unexpected policy {0}".format(policy))

        if policy == self.curpolicy:
            self.logger.info("rpc request already loaded rt {0}".format(policy))
            return (True, "Policy {0} already loaded".format(policy))

        self.rpcClear()
        self.applyPolicy(policy)
        return (True, "Policy {0} loaded".format(policy))

    def rpcClear(self):
        for dpid, dp in self.dpset.dps.iteritems():
            ofproto = dp.ofproto
            parser = dp.ofproto_parser

            name = self.topo.dpidToName(dpid)
            if name in self.topo.coreSwitches.keys():
                command = ofproto.OFPFF_SEND_FLOW_REM | ofproto.OFPFF_RESET_COUNTS
            else:
                command = ofproto.OFPFF_SEND_FLOW_REM
            mod = parser.OFPFlowMod(
                dp, 0, 0, ofproto.OFPTT_ALL,
                ofproto.OFPFC_DELETE,
                0, 0, 1, ofproto.OFP_NO_BUFFER,
                ofproto.OFPP_ANY, ofproto.OFPG_ANY,
                command,
                parser.OFPMatch(), [])

            dp.send_msg(mod)
        self.logger.info("rpc clear flow tables")
        return (True, "Flow tables cleared")

    def rpcCurrentPolicy(self):
        self.logger.info("rpc request current policy {0}".format(self.curpolicy))
        return (True, self.curpolicy)

    def applyPolicy(self, policy):
        assert policy in self.policies.keys()
        rt = self.policies[policy].routingTable
        self.curpolicy = policy

        for dp in self.dpset.dps.values():
            ofproto = dp.ofproto
            parser = dp.ofproto_parser
            dpid = dp.id

            if dpid in rt.keys():
                for flow in rt[dpid]:
                    match = self.makeMatch(flow, parser)
                    actions = []
                    for outport in flow['output']:
                        if outport == 'flood':
                            actions.append(parser.OFPActionOutput(ofproto.OFPP_FLOOD))
                        else:
                            actions.append(parser.OFPActionOutput(outport))
                    self.add_flow(dp, flow['priority'], match, actions)

    def makeMatch(self, flow, parser):
        if flow['type'] == 'src':
            match = parser.OFPMatch(eth_src=flow['eth_src'])
        elif flow['type'] == 'dst':
            match = parser.OFPMatch(eth_dst=flow['eth_dst'])
        elif flow['type'] == 'inport':
            match = parser.OFPMatch(in_port=flow['inport'])
        elif flow['type'] == 'none':
            match = parser.OFPMatch()
        return match

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath,
                                priority=priority,
                                match=match,
                                instructions=inst)
        self.logger.debug("adding flow %s" % mod)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switchFeaturesHandler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        rt = self.policies[self.curpolicy].routingTable
        if dpid not in rt.keys():
            return

        for flow in rt[dpid]:
            match = self.makeMatch(flow, parser)
            actions = []
            for outport in flow['output']:
                if outport == 'flood':
                    actions.append(parser.OFPActionOutput(ofproto.OFPP_FLOOD))
                else:
                    actions.append(parser.OFPActionOutput(outport))
            self.add_flow(datapath, flow['priority'], match, actions)
