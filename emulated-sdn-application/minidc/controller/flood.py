#!/usr/bin/env python

from topo import Topology

def add_arpflood(routingTable, topo):
    # core - flood downward
    for core in topo.coreSwitches.values():
        if core.dpid in routingTable.keys():
            for h in topo.hosts.values():
                routingTable[core.dpid].append({
                    'eth_src' : h.eth,
                    'output' : ['flood'],
                    'priority' : 1,
                    'type' : 'src'
                })

    for edge in topo.edgeSwitches.values():
        if edge.dpid not in routingTable.keys():
            routingTable[edge.dpid] = []

        # edge - flood downward, from core to neighboring hosts
        for core in topo.coreSwitches.values():
            inport = topo.ports[edge.name][core.name]
            outports = [topo.ports[edge.name][n]
                        for n in edge.neighbors]
            routingTable[edge.dpid].append({
                'output' : outports,
                'inport' : inport,
                'priority' : 1,
                'type' : 'inport'
            })

        # edge - flood upward, from hosts to cores
        for host in edge.neighbors:
            inport = topo.ports[edge.name][host]
            outports = [topo.ports[edge.name][core]
                        for core in topo.coreSwitches.keys()]
            outports.extend([topo.ports[edge.name][h2]
                             for h2 in edge.neighbors if h2 != host])
            routingTable[edge.dpid].append({
                'output' : outports,
                'inport' : inport,
                'priority' : 1,
                'type' : 'inport'
            })

    # drop all other
    for core in topo.coreSwitches.values():
        if core.dpid not in routingTable.keys():
            routingTable[core.dpid] = []

        routingTable[core.dpid].append({
            'output' : [],
            'priority' : 0,
            'type' : 'none'
        })

    for edge in topo.edgeSwitches.values():
        routingTable[edge.dpid].append({
            'output' : [],
            'priority' : 0,
            'type' : 'none'
        })

    return routingTable
