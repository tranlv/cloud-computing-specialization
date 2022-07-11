#!/usr/bin/env python

import socket
import sys
import xmlrpclib
import time

def usage():
    print "Usage: {0} [client name] [number of active servers]".format(sys.argv[0])
    print "(type {0} -h for details)".format(sys.argv[0])
    print "\nconfigure memcached replication"
    sys.exit(0)

if len(sys.argv) != 3:
    usage()
    sys.exit(0)

try:
    active = int(sys.argv[2])
except ValueError:
    print "Expected integer value for number of servers, given: {0}".format(sys.argv[2])
    sys.exit(0)

try:
    proxy = xmlrpclib.ServerProxy("http://localhost:9000/")
    res = proxy.set_active(sys.argv[1], active)
    print res
except socket.error:
    print "Unable to connect to memcached client"

sys.exit(0)
