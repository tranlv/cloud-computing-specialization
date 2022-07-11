#!/usr/bin/env python

import os
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer
import threading

from minidc.roles import *

cfd = os.path.dirname(os.path.abspath(__file__))
resdir = os.path.normpath(os.path.join(cfd, "../resources"))
webdir = os.path.normpath(os.path.join(cfd, "../websrv"))

class AppProfile(object):
    def __init__(self, numNodes):
        self.numNodes = numNodes
        self.vlan = -1
        self.apps = []
        self.nodes = []

    def assignVlan(self, vlan):
        self.vlan = vlan

    def start(self):
        map(lambda p: p.init(), self.apps)
        map(lambda p: p.start(), self.apps)

    def stop(self):
        map(lambda p: p.stop(), self.apps)

    def create(self, hosts):
        pass

    def __repr__(self):
        return self.__str__()

    def check_hostlen(self, hostlen):
        if (hostlen < self.numNodes):
            print "*** Warning: {0} expects {1} nodes, {2} given".format(
                self.__class__.__name__, self.numNodes, hostlen)

class EmptyProfile(AppProfile):
    def __init__(self, numNodes):
        super(EmptyProfile, self).__init__(numNodes)

    def create(self, hosts):
        self.check_hostlen(len(hosts))
        self.nodes.extend(hosts)
        self.apps.extend([EmptyRole(h) for h in hosts])

    def __str__(self):
        return "Empty"

class RepMemcacheProfile(AppProfile):
    def __init__(self, numSrvs, numClients, trials, activeReps=None):
        super(RepMemcacheProfile, self).__init__(numSrvs + numClients)
        self.numSrvs = numSrvs
        self.numClients = numClients
        self.trials = trials
        self.clients = {}
        if activeReps is None:
            self.activeReps = numSrvs
        else:
            self.activeReps = activeReps

    def start(self):
        # delay starting the rpc server until mininet starts
        self.rpc_start()
        super(RepMemcacheProfile, self).start()

    def stop(self):
        self.cont = False
        # send rpc request to trigger handle request and end loop
        proxy = xmlrpclib.ServerProxy("http://localhost:9000/")
        res = proxy.shutdown()
        super(RepMemcacheProfile, self).stop()

    def rpc_start(self):
        self.server = SimpleXMLRPCServer(("localhost", 9000), logRequests=False)
        self.server.register_instance(self)
        self.server.register_function(self.rpc_setactive, "set_active")
        self.server.register_function(self.rpc_shutdown, "shutdown")
        rpcthread = threading.Thread(target=self.rpcserve_forever)
        rpcthread.start()

    def rpc_shutdown(self):
        return True

    def rpcserve_forever(self):
        self.cont = True
        while self.cont:
            self.server.handle_request()

    def rpc_setactive(self, client, num):
        if client not in self.clients:
            return (False, "unexpected client {0}, expect one of {1}".format(
                client, self.clients.keys()))

        if num > self.numSrvs:
            return (False,
                    "too many active servers specified. Given: {0}, max: {1}".format(
                        num, self.numSrvs))

        if num == 0:
            return (False, "active servers must be in range (1, {0})".format(self.numSrvs))

        self.clients[client].setActiveReps(num)
        return (True, "{0} - {1} active servers".format(client, num))

    def create(self, hosts):
        self.check_hostlen(len(hosts))
        self.nodes.extend(hosts)

        srvs = []
        self.ips = []
        for i in range(self.numSrvs):
            s = MemcacheServer(hosts[i])
            srvs.append(s)
            self.ips.append(s.IP())

        for i in range(self.numClients):
            cl = RepGetClient(hosts[i + self.numSrvs],
                              self.ips,
                              self.trials,
                              self.activeReps)
            self.clients[cl.host.name] = cl

        self.apps.extend(srvs)
        self.apps.extend(self.clients.values())

    def __str__(self):
        return "Replicated Memcached"

class MemcacheProfile(AppProfile):
    def __init__(self, numNodes, trials):
        super(MemcacheProfile, self).__init__(numNodes)
        self.trials = trials

    def create(self, hosts):
        self.check_hostlen(len(hosts))
        self.nodes.extend(hosts)

        mcsrv = MemcacheServer(hosts[0])
        self.wbsrv = PhpServerMemcacheClient(hosts[1], ".", 
                                             [mcsrv.IP()],
                                             template=os.path.join(webdir, "memcached.php"),
                                             outFile="index-{0}.php".format(hosts[1].IP()))

        clients = []
        for i in range(self.numNodes - 2):
            cl = WgetClient(hosts[i + 2],
                            self.wbsrv.docUrl(),
                            self.trials)
            clients.append(cl)

        self.apps.extend([mcsrv, self.wbsrv])
        self.apps.extend(clients)

    def __str__(self):
        return "Memcached"

class VidstreamProfile(AppProfile):
    def __init__(self, numNodes):
        super(VidstreamProfile, self).__init__(numNodes)

    def create(self, hosts):
        self.check_hostlen(len(hosts))
        self.nodes.extend(hosts)
        srv = PhpServer(hosts[0],
                        os.path.join(resdir, "wwwroot"))

        clients = []
        for i in range(self.numNodes - 1):
            cl = ChromeClient(hosts[i + 1],
                              srv.url() + "/streaming.html",
                              os.path.join(resdir, "chromedatadir"))
            clients.append(cl)

        self.apps.append(srv)
        self.apps.extend(clients)

    def __str__(self):
        return "Video Streaming"

class IperfProfile(AppProfile):
    def __init__(self, numNodes, bw, maxFlows=12):
        super(IperfProfile, self).__init__(numNodes)
        self.bw = bw
        self.maxFlows = maxFlows

    def iperfcmd(self, h1, h2, port):
        h1srv = "iperf -s -p {0} > /dev/null &".format(port)
        h2clnt = "iperf -M 9000 -c {0} -p {1} -u -b {2}M -t 3600 > /dev/null &".format(h1.IP(), port, self.bw)

        print "Iperf: {0} -> {1}".format(h1, h2)
        h1.cmd(h1srv)
        h2.cmd(h2clnt)

    def start(self):
        port_start = 12000
        count = 0
        for h1 in self.nodes:
            for h2 in self.nodes:
                if h1 != h2:
                    if count < self.maxFlows:
                        self.iperfcmd(h1, h2, port_start + count)
                        count += 1

    def stop(self):
        pass

    def create(self, hosts):
        self.check_hostlen(len(hosts))
        self.nodes.extend(hosts)
        for h in hosts:
            self.apps.append(EmptyRole(h, "Iperf Client"))

    def __str__(self):
        return "Iperf ({0})".format(self.bw)
