# **Membership Protocol**

Overview
---
The repo contains implementation of Distributed sytem's gossip-style membership protocol.

The project is the first project from University of Illinois at Urbana-Champaign' [cloud computing specialization](https://www.coursera.org/specializations/cloud-computing)

Project Specification
---

Since it is infeasible to run a thousand cluster nodes (peers) over a real network, there is an implementation of an emulated network layer (EmulNet). The membership protocol implementation will sit above EmulNet in a peer- to-peer (P2P) layer, but below an App layer. Think of this like a three-layer protocol stack with Application, P2P, and EmulNet as the three layers (from top to bottom). 

The protocol must satisfy: i) Completeness all the time: every non-faulty process must detect every node join, failure, and leave, and ii) Accuracy of failure detection when there are no message losses and message delays are small. When there are message losses, completeness must be satisfied and accuracy must be high. It must achieve all of these even under simultaneous multiple failures.

There are few implementation options for membership protocols: all-to-all heartbeating, gossip-style heartbeating, or SWIM-style membership. This repo contains gossip-style hearbeating implementation.

Project Architecture
---

The three-layer implementation framework allows users to run multiple copies of peers within one process running a single-threaded simulation engine. Here is how the three layers work.

### Emulated Network: EmulNet

EmulNet provides the following functions:
```
void *ENinit(Address *myaddr, short port);
int ENsend(Address *myaddr, struct address *addr, string data);
int ENrecv(Address *myaddr, int (* enqueue)(void *, char *, int), struct timeval *t, int times, void *queue);
int ENcleanup();
```

ENinit is called once by each node (peer) to initialize its own address (myaddr). ENsend and ENrecv are called by a peer respectively to send and receive waiting messages. ENrecv enqueues a received message using a function specified through a pointer enqueue(). The third and fourth parameters (t and times) are unused for now. You can assume that ENsend and ENrecv are reliable (when there are no message losses in the underlying network). ENcleanup is called at the end of the simulator run to clean up the EmulNet implementation. These functions are provided so that they can later be easily mapped onto implementations that use TCP sockets.

### Application

This layer drives the simulation. Files Application.{cpp,h} contain code for this. Look at the main() function. This runs in synchronous periods (globaltime variable).

During each period, some peers may be started up, and some may be caused to crash- stop. Most importantly, for each peer that is alive, the function nodeLoop() is called. nodeLoop() is implemented in the P2P layer (MP1Node.{cpp,h}) and basically receives all messages that were sent for this peer in the last period, as well as checks whether the application has any new waiting requests.

### P2P Layer

Files MP1Node.{cpp,h} contain code for this. This is the layer responsible for implementing the membership protocol. 

Two message types are currently defined for the P2P layer (MP1Node.cpp implementation) - JOINREQ and JOINREP. Currently, JOINREQ messages are received by the introducer. The introducer is the first peer to join the system (for Linux, this is typically 1.0.0.0:0, due to the big-endianness)

### Logging

Log.{cpp,h} has a LOG() function that prints out node status into a file named dbg.log. Also it implements two functions logNodeAdd and logNodeRemove. Whenever a process adds or removes a member from its membership list, logNodeAdd and logNodeRemove will be used to log these respectively. 

### Others

Params.{cpp,h} contains the setparams() function that initializes several parameters at the simulator start, including the number of peers in the system(EN_GPSZ), and the global time variable globaltime, etc.
The remaining files Member.cpp,h list some necessary definitions and declarations -- see descriptions in the files.

### Why is the Code Structure So Involved? 

There are two reasons. Firstly, think about the issues involved in converting this into a real application. All EN*() functions can be easily replaced with a different set that sends and receives messages through sockets. Then, once the periodic functionalities (e.g., nodeLoop()) are replaced with a thread that wakes up periodically, and appropriate conversions are made for calling the other functions nodeStart() and recvLoop(), the implementation can be made to run over a real network!

Secondly, this structure allows us to debug (and even measure the performance through traces) the membership protocol easily and on a single host machine. Compare this with the debugging challenge for several hundred processes running on a real network. Once the simulation engine works, we can convert the implementation easily into one for a real network, and it will work.

Testing
---

To compile the code, run make.

To execute the program, from the program directory run: ./Application testcases/<test_name>.conf. The conf files contain information about the parameters used by your application:

```
MAX_NNB: val
SINGLE_FAILURE: val DROP MSG: val
MSG_DROP_PROB: val
```

where MAX_NNB represents the max number of neighbors, SINGLE_FAILURE is a one bit 1/0 variable that sets single/multi failure scenarios, MSG_DROP_PROB represents the message drop probability (between 0 and 1) and MSG_DROP is a one bit 1/0 variable that decides if messages will be dropped or not.

There is a grader script Grader.sh. It tests the implementation of membership protocol in 3 scenarios and grades each of them on 3 separate metrics. The scenarios are as follows:

1. Single node failure
2. Multiple node failure
3. Single node failure under a lossy network.

The grader tests the following things: i) whether all nodes joined the peer group correctly, ii) whether all nodes detected the failed node (completeness) and iii) whether the correct failed node was detected (accuracy). Each of these is represented as configuration files inside the testcases folder.


Contribution
---
Contributions are welcome! For bug reports or requests please submit an [issue](https://github.com/tranlyvu/membership-protocol/issues).

Contact-info
---
Feel free to contact me to discuss any issues, questions, or comments.
*  Email: vutransingapore@gmail.com
*  Twitter: [@vutransingapore](https://twitter.com/vutransingapore)
*  GitHub: [Tran Ly Vu](https://github.com/tranlyvu)

License
---
See the [LICENSE](https://github.com/tranlyvu/membership-protocol/blob/master/LICENSE) file for license rights and limitations (Apache License 2.0).