#!/usr/bin/env python

import socket
import sys
import xmlrpclib
import time

RT_DEF="default"
RT_BET="static"
RT_ADP="adaptive"

def usage():
    print "Usage: {0} [options]".format(sys.argv[0])
    print "(type {0} -h for details)".format(sys.argv[0])
    print "\nconfigure ryu routing policy at runtime"
    print "\nOptions:"
    print "  -h, --help\t\tshow this help message and exit"
    print "  -d, --default\t\tload default routing policy"
    print "  -s, --static\t\tload static routing policy"
    print "  -a, --adaptive\tload adaptive routing policy"
    print "  -c, --current\t\tshow current policy"
    sys.exit(0)

if len(sys.argv) != 2:
    usage()
    sys.exit(0)

try:
    proxy = xmlrpclib.ServerProxy("http://localhost:8000/")

    if sys.argv[1] in ["-h", "--help"]:
        usage()
    elif sys.argv[1] in ["-d", "--default"]:
        print "Old policy:", proxy.current()
        res = proxy.load(RT_DEF)
        print res
        print "New policy:", proxy.current()
    elif sys.argv[1] in ["-s", "--static"]:
        print "Old policy:", proxy.current()
        res = proxy.load(RT_BET)
        print res
        print "New policy:", proxy.current()
    elif sys.argv[1] in ["-a", "--adaptive"]:
        print "Old policy:", proxy.current()
        res = proxy.load(RT_ADP)
        print res
        print "New policy:", proxy.current()
    elif sys.argv[1] in ["-c", "--current"]:
        print "Current policy:", proxy.current()
    else:
        print "Unrecognized option", sys.argv[1]

except socket.error:
    print "Unable to connect to Ryu controller"

sys.exit(0)
