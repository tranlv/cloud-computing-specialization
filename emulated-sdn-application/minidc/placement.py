#!/usr/bin/env python

from minidc.profiles import MemcacheProfile, RepMemcacheProfile, VidstreamProfile, IperfProfile

# placement of profile roles among physical hosts
PLACEMENT = "sequential"

def inorderPlacement(numHosts, numEdgeSwitches):
    l = []
    r = range(numHosts)
    for i in range(len(r)/2):
        l.append(r[i])
        l.append(r[i + len(r)/2])
    return l

def parityPlacement(numHosts, numEdgeSwitches):
    r = range(numHosts)
    l = []
    for h in r:
        if h%2 == 1:
            l.append(h)
    for h in r:
        if h%2 == 0:
            l.append(h)
    return l

def seqPlacement(numHosts, numEdgeSwitches):
    return range(numHosts)

def randPlacement(numHosts, numEdgeSwitches):
    r = range(numHosts)
    random.shuffle(r)
    return r

def getPlacement(numHosts, numEdgeSwitches):
    return PLACEMENT_TYPES[PLACEMENT](numHosts, numEdgeSwitches)

PLACEMENT_TYPES = { "sequential" : seqPlacement,
                    "random" : randPlacement,
                    "parity" : parityPlacement,
                    "inorder" : inorderPlacement,
}
