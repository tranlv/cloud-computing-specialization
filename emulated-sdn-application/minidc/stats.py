#!/usr/bin/env python

import json
import random
import SocketServer
import thread
import threading
import time
import os

import minidc.controller.bwmon

AVG_TRIALS = 20
JSON_MAX = 30
PTILE = 95
SLEEP = 2

def dashboardPath(infoFile):
    path = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(os.path.join(path, "dashboard"))
    return os.path.normpath(os.path.join(path, infoFile))

class CsvProvider(object):
    def __init__(self, outFile=None):
        self.outFile = outFile
        self.tuples = []

    def add(self, tup):
        self.tuples.append(tup)

    def clear(self):
        self.tuples = []

    def toCsv(self):
        s = ""
        for t in self.tuples:
            s += ",".join(map(str, t)) + "\n"
        return s

    def write(self):
        if self.outFile is not None:
            target = open(self.outFile, 'w')
            target.write(self.toCsv())
            target.close()

class JsonProvider(object):
    def __init__(self, outFile=None, ttyOut=False):
        self.outFile = outFile
        self.ttyOut = ttyOut
        self.lock = thread.allocate_lock()
        self.cont = True

    def update(self):
        while self.cont:
            if self.outFile is not None:
                target = open(self.outFile, 'w')
                target.write(self.getJson())
                target.close()
                time.sleep(SLEEP)

    def start(self):
        self.updateThread = threading.Thread(target=self.update)
        self.updateThread.start()

    def stop(self):
        self.cont = False

    def getJson(self):
        pass

class BandwidthStatsProvider(JsonProvider):
    def __init__(self, csvProvider, outFile, ttyOut=False):
        super(BandwidthStatsProvider, self).__init__(outFile, ttyOut)
        self.totals = {}
        self.slices = {}
        self.csvProvider = csvProvider

    def add(self, host, txbytes, rxbytes):
        try:
            self.lock.acquire()

            if host not in self.totals:
                self.totals[host] = []
                self.totals[host].append({ 'in' : 0,
                                           'out' : 0
                                       })
                self.slices[host] = []

            last = self.totals[host][-1]
            rxslice = rxbytes - last['in']
            txslice = txbytes - last['out']

            self.slices[host].append({ 'in': rxslice,
                                       'out': txslice
                                   })
            self.totals[host].append({ 'in': rxbytes,
                                       'out': txbytes
                                   })

            # truncate
            if len(self.totals[host]) > JSON_MAX:
                start = len(self.totals[host]) - JSON_MAX
                self.totals[host] = self.totals[host][start:]
                self.slices[host] = self.slices[host][start:]

        finally:
            self.lock.release()

    def computeShare(self):
        if self.csvProvider is None:
            return

        try:
            self.lock.acquire()
            totalbw = 0

            # add header for d3
            self.csvProvider.add(("host", "bwshare"))
            for host in self.slices.keys():
                totalbw += self.slices[host][-1]['out']

            for host in self.slices.keys():
                totalbw = float(totalbw)
                if totalbw > 0:
                    share = round(self.slices[host][-1]['out'] / totalbw, 3)
                    self.csvProvider.add((host, share))
        finally:
            self.lock.release()

    def update(self):
        while self.cont:
            if self.outFile is not None:
                target = open(self.outFile, 'w')
                target.write(self.getJson())
                target.close()

            if self.csvProvider is not None:
                self.computeShare()
                self.csvProvider.write()
                self.csvProvider.clear()
            time.sleep(SLEEP)

    def getJson(self):
        try:
            self.lock.acquire()
            j = {}
            j['results'] = []

            for host in self.totals.keys():
                for attrib in ['in', 'out']:
                    param = {}
                    param['param'] = "{0}-{1}".format(host, attrib)
                    param['val'] = []

                    for stat in self.slices[host]:
                        param['val'].append(stat[attrib])

                    j['results'].append(param)

            return json.dumps(j)
        finally:
            self.lock.release()

class MemcachedStatsProvider(JsonProvider):
    def __init__(self, outFile, ttyOut=False):
        super(MemcachedStatsProvider, self).__init__(outFile, ttyOut)
        self.vals = {}
        self.avgs = {}
        self.ptile = {}

    def add(self, host, time):
        try:
            self.lock.acquire()
            if host not in self.vals:
                self.vals[host] = []
            self.vals[host].append(time)
        finally:
            self.lock.release()

    def avg(self):
        try:
            self.lock.acquire()

            for host in self.vals.keys():
                if host not in self.avgs:
                    self.avgs[host] = []
                    self.ptile[host] = []

                while len(self.vals[host]) >= AVG_TRIALS:
                    consumed = self.vals[host][:AVG_TRIALS]
                    self.vals[host] = self.vals[host][AVG_TRIALS:]
                    consumed.sort()
                    ptileIndex = int((PTILE / 100.0) * len(consumed)) - 1
                    medianIndex = int(len(consumed) / 2) - 1

                    self.ptile[host].append(consumed[ptileIndex])
                    self.avgs[host].append(consumed[medianIndex])

                    if self.ttyOut:
                        print "{0} - PageLoad: Median={1}ms, 95til={2}ms".format(
                            host,
                            consumed[medianIndex],
                            consumed[ptileIndex])

                # truncate
                if len(self.avgs[host]) > JSON_MAX:
                    start = len(self.avgs[host]) - JSON_MAX
                    self.avgs[host] = self.avgs[host][start:]
                    self.ptile[host] = self.ptile[host][start:]
        finally:
            self.lock.release()

    def getJson(self):
        self.avg()
        try:
            self.lock.acquire()
            j = {}
            j['results'] = []

            for host in self.avgs.keys():
                param = {}
                param['param'] = host + "-median"
                param['val'] = list(self.avgs[host])
                j['results'].append(param)

            for host in self.ptile.keys():
                param = {}
                param['param'] = host + "-95tile"
                param['val'] = list(self.ptile[host])
                j['results'].append(param)

            return json.dumps(j)
        finally:
            self.lock.release()

mcStats = MemcachedStatsProvider(dashboardPath("memstats.json"), ttyOut=True)
drpPktStats = CsvProvider(dashboardPath("droppedpkts.csv"))
bwShare = CsvProvider(dashboardPath("bwshare.csv"))
bwStats = BandwidthStatsProvider(csvProvider=bwShare,
                                 outFile=dashboardPath("bwplot.json"))
tenantShare = CsvProvider(dashboardPath("tenantshare.csv"))
tenantStats = BandwidthStatsProvider(csvProvider=tenantShare,
                                 outFile=dashboardPath("tenantplot.json"))
tenantInfo = CsvProvider(dashboardPath("tenants.csv"))
roleInfo = CsvProvider(dashboardPath("roles.csv"))
