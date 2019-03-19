<p align="center">
	<font size="100" face="arial" color="red"">Membership Protocol Implementation</font>
</p>

<p align="center">
	<a href="https://github.com/tranlyvu/membership-protocol/releases"><img src="https://img.shields.io/github/release/tranlyvu/membership-protocol.svg"></a>
	<a href="https://github.com/tranlyvu/membership-protocol"><img src="http://hits.dwyl.io/tranlyvu/membership-protocol.svg"></a>
    <a href="https://github.com/tranlyvu/membership-protocol"><img src="http://githubbadges.com/star.svg?user=tranlyvu&repo=membership-protocol&style=default"></a>
    <a href="https://github.com/tranlyvu/membership-protocol/fork"><img src="http://githubbadges.com/fork.svg?user=tranlyvu&repo=membership-protocol&style=default"></a>
</p>

---
Implementation of Membership Protocol for failure detection in Distributed System.

The project was forked from University of Illinois at Urbana-Champaign' [Cloud Computing Specialization](https://www.coursera.org/specializations/cloud-computing) programming assignment.

---
Table of contents
---

1. [Project Specification](#Project-Specification)
2. [Project Architecture](#Project-Architecture)
3. [Usage](#Usage)
4. [Real-world application](#Real-world-application)
5. [Contribution](#Contribution)
6. [Release History](#Release-History)
7. [Contact](#Contact)
8. [License](#License)

---
Project Specification
---

Since it is infeasible to run a thousand cluster nodes (peers) over a real network, The project implemented an emulated network layer (EmulNet). The membership protocol implementation will sit above EmulNet in a peer-to-peer (P2P) layer, but below an App layer. Think of this like a three-layer protocol stack with Application, P2P, and EmulNet as the three layers (from top to bottom). 

The protocol will satisfy: 
1. Completeness all the time: every non-faulty process must detect every node join, failure, and leave, and 
2. Accuracy of failure detection when there are no message losses and message delays are small. When there are message losses, completeness must be satisfied and accuracy must be high. It must achieve all of these even under simultaneous multiple failures.

There are 3 implementation for membership protocols: 

1. [All-to-all heartbeating](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.147.1818&rep=rep1&type=pdf) (dafault): Each process pi sends out heartbeat to all the other processes in the system.
2. [Gossip-style heartbeating](https://www.cs.cornell.edu/home/rvr/papers/GossipFD.pdf):  nodes periodically increments its own heartbeat counter and gossip their membership list to a random member at each time T(gossip).
3. [SWIM-style membership](http://www.cs.cornell.edu/projects/Quicksilver/public_pdfs/SWIM.pdf): a process pi randomly sends ping to pj and subsequently indirectly probes pj by randomly selecting k targets and uses them to send a ping to pj if pi does not receive ACK from pj within the pre-specified timeout. 

---
Project Architecture
---

### The Three Layers

The three-layer implementation framework allows users to run multiple copies of peers within one process running a single-threaded simulation engine. Here is how the three layers work.

#### Application

This layer drives the simulation. Files Application.{cpp,h} contain code for this. Look at the main() function. This runs in synchronous periods (globaltime variable).

During each period, some peers may be started up, and some may be caused to crash- stop. Most importantly, for each peer that is alive, the function nodeLoop() is called. nodeLoop() is implemented in the P2P layer (MP1Node.{cpp,h}) and basically receives all messages that were sent for this peer in the last period, as well as checks whether the application has any new waiting requests.

#### P2P Layer

Files MP1Node.{cpp,h} contain code for this. This is the layer responsible for implementing the membership protocol. 

Two message types are currently defined for the P2P layer (MP1Node.cpp implementation) - JOINREQ and JOINREP. Currently, JOINREQ messages are received by the introducer. The introducer is the first peer to join the system (for Linux, this is typically 1.0.0.0:0, due to the big-endianness)

#### Emulated Network: EmulNet

EmulNet provides the following functions:

```
void *ENinit(Address *myaddr, short port);
int ENsend(Address *myaddr, struct address *addr, string data);
int ENrecv(Address *myaddr, int (* enqueue)(void *, char *, int), struct timeval *t, int times, void *queue);
int ENcleanup();
```

ENinit is called once by each node (peer) to initialize its own address (myaddr). ENsend and ENrecv are called by a peer respectively to send and receive waiting messages. ENrecv enqueues a received message using a function specified through a pointer enqueue(). The third and fourth parameters (t and times) are unused for now. You can assume that ENsend and ENrecv are reliable (when there are no message losses in the underlying network). ENcleanup is called at the end of the simulator run to clean up the EmulNet implementation. These functions are provided so that they can later be easily mapped onto implementations that use TCP sockets.

---
### Other classes

Log.{cpp,h} has a LOG() function that prints out node status into a file named dbg.log. Also it implements two functions logNodeAdd and logNodeRemove. Whenever a process adds or removes a member from its membership list, logNodeAdd and logNodeRemove will be used to log these respectively. 

Params.{cpp,h} contains the setparams() function that initializes several parameters at the simulator start, including the number of peers in the system(EN_GPSZ), and the global time variable globaltime, etc.
The remaining files Member.cpp,h list some necessary definitions and declarations -- see descriptions in the files.

---
Usage
---

Downloading a [release](https://github.com/tranlyvu/gossip-style-membership-protocol/releases)

Test cases are provided in testcases directory. The conf files contain information about the parameters used by application:

```
MAX_NNB: val
SINGLE_FAILURE: val
DROP MSG: val
MSG_DROP_PROB: val
```
where MAX_NNB represents the max number of neighbors, SINGLE_FAILURE is a one bit 1/0 variable that sets single/multi failure scenarios, MSG_DROP_PROB represents the message drop probability (between 0 and 1) and MSG_DROP is a one bit 1/0 variable that decides if messages will be dropped or not.

There is a grader script Grader.sh that execute all configurations in testcases folder. It tests the implementation of membership protocol in 3 scenarios and grades each of them on 3 separate metrics. The scenarios are as follows:

1. Single node failure
2. Multiple node failure
3. Single node failure under a lossy network.

The grader tests the following things:

1. whether all nodes joined the peer group correctly,
2. whether all nodes detected the failed node (completeness) and
3. whether the correct failed node was detected (accuracy).

In order to compile and execure 3 scenarios seperately:

```
$ make clean
$ make
$ ./Application testcases/singlefailure.conf

$ ./Application testcases/multifailure.conf

$ ./Application testcases/msgdropsinglefailure.conf
```

Or simply run 3 seperate scripts:

```
$ ./single_failure.sh

$ ./multi_failure.sh

$ ./message_drop_single_failure.sh
```

---
Real-world application
---

This is an experimental protocol implementation project and still under heavy development. I do not yet recommend using in production environments.

However, here are some idea to integrate this into real-world application: All EN*() functions can be easily replaced with a different set that sends and receives messages through sockets. Then, once the periodic functionalities (e.g., nodeLoop()) are replaced with a thread that wakes up periodically, and appropriate conversions are made for calling the other functions nodeStart() and recvLoop(), the implementation can be made to run over a real network!


---
Contribution [![Open Source Helpers][5]][6]
---
[5]: https://www.codetriage.com/tranlyvu/membership-protocol/badges/users.svg
[6]: https://www.codetriage.com/tranlyvu/membership-protocol

Please follow [contribution instruction](https://github.com/tranlyvu/membership-protocol/blob/dev/CONTRIBUTING.md) and [code of conduct](https://github.com/tranlyvu/membership-protocol/blob/dev/CODE-OF-CONDUCT.md)

### Appreciation

Feel free to add your name into the [list of contributors](https://github.com/tranlyvu/membership-protocol/blob/dev/CONTRIBUTORS.md). You will automatically be inducted into Hall of Fame as a way to show my appreciation for your contributions.

### Hall of Fame

[![](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/images/0)](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/links/0)[![](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/images/1)](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/links/1)[![](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/images/2)](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/links/2)[![](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/images/3)](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/links/3)[![](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/images/4)](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/links/4)[![](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/images/5)](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/links/5)[![](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/images/6)](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/links/6)[![](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/images/7)](https://sourcerer.io/fame/tranlyvu/tranlyvu/membership-protocol/links/7)

---
Release History
---

* v1.1.0 (12 Dec 2018)
    * Implemented all-to-all heartbeat option
    * Simplified header file MP1Node.h
    * Added seperate test scripts
    * Moved submit scripts to new directory
    * Added "Real-world application" section in Readme
    * Modified "Usage" and "Project architecture" in Readme

* v1.0.0
    * First official release

---
Contact
---

Feel free to contact me to discuss any issues, questions, or comments.

*  Email: vutransingapore@gmail.com
*  Linkedln: [@vutransingapore](https://www.linkedin.com/in/tranlyvu/)
*  GitHub: [Tran Ly Vu](https://github.com/tranlyvu)
*  Blog: [tranlyvu.github.io](https://tranlyvu.github.io/)

If you like my project, feel fee to leave a few words of appreciation here [![Say Thanks!](https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg)](https://saythanks.io/to/tranlyvu)

---
License
---

See the [LICENSE](https://github.com/tranlyvu/membership-protocol/blob/master/LICENSE) file for license rights and limitations (Apache License 2.0).
