#!/usr/bin/env python

"""
HostRole: superclass for all roles (single instance of an application)
    running on a host.

ChromeClient: starts a chrome instance on the host

MemcacheServer: starts a memcached instance on the host on the default port

WgetClient: retrieves specified page from a specified server and averages
    response time over specified number of trials

PhpServer: starts php server on a specified port using a specified 
    document root directory

PhpServerMemcacheClient: starts a php server as a memcached client, modifying
    template php document to use specified memcached server(s) IP address(es)
"""

import os
import re
import subprocess
import sys
import threading
from time import time, sleep

from mininet.net import Mininet
from mininet.cli import CLI

import minidc.stats

def start(mn, *procs):
    map(lambda p: p.init(), procs)
    map(lambda p: p.start(), procs)

def stop(*procs):
    map(lambda p: p.stop(), procs)

class HostRole(object):
    def __init__(self, host):
        self.procStr = None
        self.proc = None
        self.host = host
        self.stdout = "/tmp/{0}-{1}.log".format(host.IP(),
                                                self.__class__.__name__)
        self.stderr = "/tmp/{0}-{1}.err".format(host.IP(),
                                                self.__class__.__name__)
    def init(self):
        pass

    def start(self):
        self.proc = self.host.popen(self.procStr,
                                    stdout=open(self.stdout, "wb"),
                                    stderr=open(self.stderr, "wb"))
    def stop(self):
        # subclasses can call proc.wait(), so proc may have already terminated
        try:
            self.proc.terminate()
        except Exception:
            pass

    def IP(self):
        return self.host.IP()

    def __repr__(self):
        return self.__str__()

class EmptyRole(HostRole):
    def __init__(self, host, name="Empty"):
        super(EmptyRole, self).__init__(host)
        self.name = name

    def init(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def __str__(self):
        return self.name

class ChromeClient(HostRole):
    def __init__(self, host, url=None, datadir="./"):
        super(ChromeClient, self).__init__(host)
        self.datadir = os.path.join(datadir, host.name + "-datadir")
        self.procStr = "/opt/google/chrome/google-chrome --enable-logging --v=1 --user-data-dir={0} {1}".format(self.datadir, url)

    def __str__(self):
        return "Chrome Client"

class MemcacheServer(HostRole):
    def __init__(self, host):
        super(MemcacheServer, self).__init__(host)
        self.procStr = "memcached -u nobody"

    def __str__(self):
        return "Memcached Server"

class WgetClient(HostRole):
    def __init__(self, host, url, trials=-1, toFile=False):
        super(WgetClient, self).__init__(host)
        self.trials = trials
        self.procStr = "wget -q -O - {0}".format(url)
        self.cont = True
        self.toFile = toFile

    def start(self):
        thread = threading.Thread(target=self.threadStart)
        thread.start()

    def stop(self):
        super(WgetClient, self).stop()
        self.cont = False

    def threadStart(self):
        loadtimes = []
        rettimes = []

        i = 0
        while self.cont and (self.trials == -1 or i < self.trials):
            i += 1
            elapsed = time()
            if self.toFile:
                self.proc = self.host.popen(self.procStr,
                                            stdout=open(self.stdout, "ab+"),
                                            stderr=open(self.stderr, "ab+"))
                self.proc.wait()
            else:
                self.proc = self.host.popen(self.procStr,
                                            stdout=subprocess.PIPE,
                                            stderr=open(self.stderr, "ab+"))
                text = self.proc.communicate()[0]

            # save load time
            elapsed = time() - elapsed
            loadtimes.append(elapsed)

            if not self.toFile:
                p = re.compile('\d*[.]?\d+')
                finds = p.findall(text)
                if len(finds) > 0:
                    rettimes.append(float(finds[0]))
                    minidc.stats.mcStats.add(self.host.name,
                                             float(finds[0]))

        if self.toFile:
            # parse output for memcache times
            lines = [line.strip() for line in open(self.stdout)]
            p = re.compile('\d*[.]?\d+')
            rettimes = []
            for line in lines:
                finds = p.findall(line)
                if len(finds) > 0:
                    rettimes.append(float(finds[0]))

        if len(rettimes) > 0:
            retavg = (reduce(lambda x, y: x + y, rettimes) / len(rettimes))
            loadavg = (reduce(lambda x, y: x + y, loadtimes) / len(loadtimes)) * 1000

            print "{0}: Avg times - obj: {1}, load: {2}".format(self.IP(),
                                                                round(retavg, 3),
                                                                round(loadavg, 3))

#       print "\n****************************************************"
#       print "Average obj retrieval time:", round(retavg, 3), "ms"
#       print "Average load time:", round(loadavg, 3), "ms"
#       print "****************************************************\n"

    def __str__(self):
        return "Wget Client"

class PhpServer(HostRole):
    def __init__(self, host, wwwdir, port=80, page="index.php"):
        super(PhpServer, self).__init__(host)
        self.procStr = "sudo php -S {0}:{1} -t {2}".format(host.IP(),
                                                           port,
                                                           wwwdir)
        self.port = port
        self.page = page
        self.wwwdir = wwwdir

    def url(self):
        return "http://{0}:{1}".format(self.host.IP(),
                                           self.port)

    def docUrl(self):
        return "http://{0}:{1}/{2}".format(self.host.IP(),
                                           self.port,
                                           self.page)
    def __str__(self):
        return "PHP Server"

class PhpServerMemcacheClient(PhpServer):
    def __init__(self, host, wwwdir, mcSrvList=None, port=80, template=None, outFile="index.php"):
        super(PhpServerMemcacheClient, self).__init__(host, wwwdir, port, page=outFile)
        self.mcSrvList = mcSrvList
        self.outFile = outFile
        self.template = template

    def init(self):
        if self.template:
            srvs = "array(" + ",".join(["array('%s', 11211)" % s for s in self.mcSrvList]) + ")"
            php = ""
            f = open(self.template)
            lines = f.readlines()
            for l in lines:
                l =re.sub("addServer\(.*\)", "addServers(" + srvs + ")", l)
                php += l
            f.close()
            f = open(self.wwwdir + "/" + self.outFile, 'w+')
            f.write(php)
            f.close()

    def __str__(self):
        return "PHP Server (Memcached Client)"

class RepGetClient(HostRole):
    def __init__(self, host, srvs, trials=-1, activeReps=None):
        super(RepGetClient, self).__init__(host)
        self.trials = trials
        self.procStr = None
        self.cont = True
        self.srvs = srvs
        self.host = host
        self.lock = threading.Lock()
        if activeReps is None:
            self.activeReps = len(self.srvs)
        else:
            self.activeReps = activeReps

    def start(self):
        thread = threading.Thread(target=self.threadStart)
        thread.start()

    def stop(self):
        self.cont = False

    def execPhp(self, code):
        proc = self.host.popen(['php'],
                            stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            close_fds=True)
        output = proc.communicate(code)[0]
        try:
            os.kill(proc.pid, signal.SIGTERM)
        except:
            pass
        return output

    def setActiveReps(self, num):
        self.lock.acquire()
        try:
            self.activeReps = num
            print "{0}: using {1} replicated servers".format(self.host.name,
                                                             self.activeReps)
        finally:
            self.lock.release()

    def threadStart(self):
        rettimes = []

        print "{0} using {1} replicas".format(self.host.name,
                                              self.activeReps)

        iters = 0
        while self.cont and (self.trials == -1 or iters < self.trials):
            iters += 1

            self.lock.acquire()
            try:
                active = self.srvs[:self.activeReps]
            finally:
                self.lock.release()

            threadtimes = [None] * len(active)
            threads = [None] * len(active)
            if True:
                for i, h in enumerate(active):
                    threads[i] = threading.Thread(target=self.mcget,
                                                  args=(h, threadtimes, i))
                    threads[i].start()

                for i in range(len(threads)):
                    threads[i].join()

#                print threadtimes
                minidc.stats.mcStats.add(self.host.name,
                                         round(max(threadtimes) * 1000, 3))

                # save some CPU cycles, throttle memcache requests
                sleep(0.2)

    def mcget(self, srv, result, index):
        code = "<?php $mem = new Memcached();\n"
        code += "$mem->addServer(\"" + srv + "\", 11211);\n"
        code += """$time_start = microtime(true);
        $result = $mem->get("blah");
        if ($result) {
           //echo "Item retrieved from memcached";
        } else {
           //echo "No matching key, adding";
           $mem->set("blah", "blah", 3600) or die("Couldn't save to mc");
        }

        $time_end = microtime(true);
        $time = $time_end - $time_start;
        //$time = round($time * 1000, 3);
        echo "\r\n$time";
        ?>"""

        res = self.execPhp(code)
        try:
            elapsed = float(res)
        except:
            elapsed = -1
        result[index] = elapsed

    def __str__(self):
        return "Replicated Memcached Client"
