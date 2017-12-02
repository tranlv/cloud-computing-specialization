/**********************************
 * FILE NAME: MP1Node.cpp
 *
 * DESCRIPTION: Membership protocol run by this Node.
 * 				Definition of MP1Node class functions.
 **********************************/

#include "MP1Node.h"

/*
 * Note: You can change/add any functions in MP1Node.{h,cpp}
 */

/**
 * Overloaded Constructor of the MP1Node class
 * You can add new members to the class if you think it
 * is necessary for your logic to work
 */
MP1Node::MP1Node(Member *member, Params *params, EmulNet *emul, Log *log, Address *address) {
	for( int i = 0; i < 6; i++ ) {
		NULLADDR[i] = 0;
	}
	this->memberNode = member;
	this->emulNet = emul;
	this->log = log;
	this->par = params;
	this->memberNode->addr = *address;
}

/**
 * Destructor of the MP1Node class
 */
MP1Node::~MP1Node() {}

/**
 * FUNCTION NAME: recvLoop
 *
 * DESCRIPTION: This function receives message from the network and pushes into the queue
 * 				This function is called by a node to receive messages currently waiting for it
 */
int MP1Node::recvLoop() {
    if ( memberNode->bFailed ) {
    	return false;
    }
    else {
    	return emulNet->ENrecv(&(memberNode->addr), enqueueWrapper, NULL, 1, &(memberNode->mp1q));
    }
}

/**
 * FUNCTION NAME: enqueueWrapper
 *
 * DESCRIPTION: Enqueue the message from Emulnet into the queue
 */
int MP1Node::enqueueWrapper(void *env, char *buff, int size) {
	Queue q;
	return q.enqueue((queue<q_elt> *)env, (void *)buff, size);
}

/**
 * FUNCTION NAME: nodeStart
 *
 * DESCRIPTION: This function bootstraps the node
 * 				All initializations routines for a member.
 * 				Called by the application layer.
 */
void MP1Node::nodeStart(char *servaddrstr, short servport) {
    Address joinaddr;
    joinaddr = getJoinAddress();

    // Self booting routines
    if( initThisNode(&joinaddr) == -1 ) {
#ifdef DEBUGLOG
        log->LOG(&memberNode->addr, "init_thisnode failed. Exit.");
#endif
        exit(1);
    }

    if( !introduceSelfToGroup(&joinaddr) ) {
        finishUpThisNode();
#ifdef DEBUGLOG
        log->LOG(&memberNode->addr, "Unable to join self to group. Exiting.");
#endif
        exit(1);
    }

    return;
}

/**
 * FUNCTION NAME: initThisNode
 *
 * DESCRIPTION: Find out who I am and start up
 */
int MP1Node::initThisNode(Address *joinaddr) {
	//int id = *(int*)(&memberNode->addr.addr);
	//int port = *(short*)(&memberNode->addr.addr[4]);

	memberNode->bFailed = false;
	memberNode->inited = true;
	memberNode->inGroup = false;
    // node is up!
	memberNode->nnb = 0;
	memberNode->heartbeat = 0;
	memberNode->pingCounter = TFAIL;
	memberNode->timeOutCounter = -1;
    initMemberListTable(memberNode);

    return 0;
}

/**
 * FUNCTION NAME: introduceSelfToGroup
 *
 * DESCRIPTION: Join the distributed system
 */

int MP1Node::introduceSelfToGroup(Address *joinaddr) {
	MessageHdr *msg;
#ifdef DEBUGLOG
    static char s[1024];
#endif

    if ( 0 == memcmp((char *)&(memberNode->addr.addr), (char *)&(joinaddr->addr), sizeof(memberNode->addr.addr))) {
        // I am the group booter (first process to join the group). Boot up the group
#ifdef DEBUGLOG
        log->LOG(&memberNode->addr, "Starting up group...");
#endif
        memberNode->inGroup = true;
    }
    else {
        size_t msgsize = sizeof(MessageHdr) + sizeof(joinaddr->addr) + sizeof(long) + 1;
        msg = (MessageHdr *) malloc(msgsize * sizeof(char));

        // create JOINREQ message: format of data is {struct Address myaddr}
        msg->msgType = JOINREQ;
        memcpy((char *)(msg+1), &memberNode->addr.addr, sizeof(memberNode->addr.addr));
        memcpy((char *)(msg+1) + 1 + sizeof(memberNode->addr.addr), &memberNode->heartbeat, sizeof(long));

#ifdef DEBUGLOG
        sprintf(s, "Trying to join...");
        log->LOG(&memberNode->addr, s);
#endif

        // send JOINREQ message to introducer member
        emulNet->ENsend(&memberNode->addr, joinaddr, (char *)msg, msgsize);

        free(msg);
    }

    return 1;

}

/**
 * FUNCTION NAME: finishUpThisNode
 *
 * DESCRIPTION: Wind up this node and clean up state
 */
int MP1Node::finishUpThisNode(){
    //Node is down
    memberNode->inited = false;

    //clean up node tate
    CleanupNodeState();
    return 0;
}

void MP1Node::CleanupNodeState() {

    //indicating  this member is not in the group
    memberNode->inGroup = false;

    // number of my neighbors
    memberNode->nnb = 0;

    // the node's own heartbeat
    memberNode->heartbeat = 0;
    memberNode->pingCounter = TFAIL;
    memberNode->timeOutCounter = -1;
    initMemberListTable(memberNode);
}


/**
 * FUNCTION NAME: nodeLoop
 *
 * DESCRIPTION: Executed periodically at each member
 * 				Check your messages in queue and perform membership protocol duties
 */
void MP1Node::nodeLoop() {
    if (memberNode->bFailed) {
    	return;
    }

    // Check my messages
    checkMessages();

    // Wait until you're in the group...
    if( !memberNode->inGroup ) {
    	return;
    }

    // ...then jump in and share your responsibilites!
    nodeLoopOps();

    return;
}

/**
 * FUNCTION NAME: checkMessages
 *
 * DESCRIPTION: Check messages in the queue and call the respective message handler
 */
void MP1Node::checkMessages() {
    void *ptr;
    int size;

    // Pop waiting messages from memberNode's mp1q
    while (!memberNode->mp1q.empty() ) {
    	ptr = memberNode->mp1q.front().elt;
    	size = memberNode->mp1q.front().size;
    	memberNode->mp1q.pop();
    	recvCallBack((void *)memberNode, (char *)ptr, size);
    }
    return;
}

/**
 * FUNCTION NAME: recvCallBack
 *
 * DESCRIPTION: Message handler for different message types
 *              where the nodes receive messages           
 */
bool MP1Node::recvCallBack(void *env, char *data, int size) {

    MessageHdr *msg = (MessageHdr*) malloc(size * sizeof(char));
    memcpy(msg, data, sizeof(MessageHdr));

    MsgTypes msg_type = msg->msgType;

    if (msg_type == JOINREQ) {
        // read message data
        int id;
        short port;
        long heartbeat;
        memcpy(&id, data + sizeof(MessageHdr), sizeof(int));
        memcpy(&port, data + sizeof(MessageHdr) + sizeof(int), sizeof(short));
        memcpy(&heartbeat, data + sizeof(MessageHdr) + sizeof(int) + sizeof(short), sizeof(long));

        // create new membership entry and add to the membership list of the node
        UpdateMembershipList(id, port, heartbeat, memberNode->timeOutCounter);

        //send JOINREP msg
        Address newNodeAddress = GetNodeAddress(id, port);

        SendJOINREPLYMessage(&newNodeAddress);

    } else if (msg_type == JOINREP) {
        memberNode->inGroup = true;

        //Deserialize member list and items to the membership list of the node
        DeserializeMembershipListForJOINREPMessageReceiving(data);
    } else if (msg_type == HEARTBEAT) {

        // read message data
        int id;
        short port;
        long heartbeat;
        memcpy(&id, data + sizeof(MessageHdr), sizeof(int));
        memcpy(&port, data + sizeof(MessageHdr) + sizeof(int), sizeof(short));
        memcpy(&heartbeat, data + sizeof(MessageHdr) + sizeof(int) + sizeof(short), sizeof(long));

        // create new membership entry and add to the membership list of the node
        if (this->GetNodeInMembershipList(id) != NULL) {
            UpdateMembershipList(id, port, heartbeat, memberNode->timeOutCounter);
        } else {
            // update the membership entry
            MemberListEntry * node = GetNodeInMembershipList(id);
            node->setheartbeat(heartbeat);
            node->settimestamp(memberNode->timeOutCounter);
        }
    }

    return true;
}


/**
 * FUNCTION NAME: nodeLoopOps
 *
 * DESCRIPTION: Check if any node hasn't responded within a timeout period 
 * 				and then delete the nodes
 * 				Propagate your membership list
 */
void MP1Node::nodeLoopOps() {

    //check if node should send a new heartbeat
    if (memberNode->heartbeat == 0) {
        //increment no of hearbeat
        memberNode->heartbeat++;

        // send heatbeat msg to all nodes
        for (vector<MemberListEntry>::iterator it = memberNode->memberList.begin();
             it != memberNode->memberList.end(); it++) {
            Address nodeAddress = GetNodeAddress(it->id, it->getport());
            if (!IsAddressEqualToNodeAddress(&nodeAddress)) {}
        }
        //reset ping counter
        memberNode->pingCounter = TFAIL;
    } else {
        // decrement ping counter
        memberNode->pingCounter--;
    }

    //check if any node has failed
    for (vector<MemberListEntry>::iterator it = memberNode->memberList.begin(); it != memberNode->memberList.end(); ++it) {
        Address nodeAddress = GetNodeAddress(it->id, it->getport());
        if (!IsAddressEqualToNodeAddress(&nodeAddress)) {
            // after T(cleanup) seconds, it will delete the member from the list.
            if(memberNode->timeOutCounter - it->timestamp > TREMOVE) {
                //remove node
                memberNode->memberList.erase(it);

                #ifdef DEBUGLOG
                log->logNodeRemove(&memberNode->addr, &nodeAddress);
                #endif

                break;
            }
        }
    }

    //increment over counter
    memberNode->timeOutCounter++;

    return;
}

bool MP1Node::IsAddressEqualToNodeAddress (Address * address) {
    return memcmp((char*)&memberNode->addr.addr, (char*)&(address->addr), sizeof(memberNode->addr.addr));

}

/**
 * FUNCTION NAME: isNullAddress
 *
 * DESCRIPTION: Function checks if the address is NULL
 */
int MP1Node::isNullAddress(Address *addr) {
	return (memcmp(addr->addr, NULLADDR, 6) == 0 ? 1 : 0);
}

/**
 * FUNCTION NAME: getJoinAddress
 *
 * DESCRIPTION: Returns the Address of the coordinator
 */
Address MP1Node::getJoinAddress() {
    Address joinaddr;

    memset(&joinaddr, 0, sizeof(Address));
    *(int *)(&joinaddr.addr) = 1;
    *(short *)(&joinaddr.addr[4]) = 0;

    return joinaddr;
}

/**
 * FUNCTION NAME: initMemberListTable
 *
 * DESCRIPTION: Initialize the membership add
 */
void MP1Node::initMemberListTable(Member *memberNode) {
	memberNode->memberList.clear();
}

/**
 * FUNCTION NAME: printAddress
 *
 * DESCRIPTION: Print the Address
 */
void MP1Node::printAddress(Address *addr)
{
    printf("%d.%d.%d.%d:%d \n",  addr->addr[0],addr->addr[1],addr->addr[2],
                                                       addr->addr[3], *(short*)&addr->addr[4]) ;    
}


void MP1Node::UpdateMembershipList(int id, short port, long heartbeat, long timeStamp) {

    //if new node is not in the membership list then create and add a new member list entry
    if (this->GetNodeInMembershipList(id) == NULL) {
        MemberListEntry * newEntry = new MemberListEntry(id, port, heartbeat, timeStamp);
        memberNode->memberList.insert(memberNode->memberList.end(), * newEntry);

        Address newEntryAddress = GetNodeAddress(id, port);
#ifdef DEBUGLOG
        //void logNodeAdd(Address *, Address *);
        log->logNodeAdd(& memberNode->addr, &newEntryAddress);
#endif

        delete newEntry;
    }
}


Address MP1Node::GetNodeAddress(int id, short port) {
    Address nodeAddress;

    memset(&nodeAddress, 0, sizeof(Address));
    *(int*)(&nodeAddress.addr) = id;
    *(short*)(&nodeAddress.addr[4]) = port;

    return nodeAddress;
}


// get node with id
MemberListEntry* MP1Node::GetNodeInMembershipList(int id) {
    MemberListEntry* entry = NULL;

    for (std::vector<MemberListEntry>::iterator it = memberNode->memberList.begin();
         it != memberNode-> memberList.end(); ++it) {
        if(it->id == id) {
            entry = it.base();
            break;
        }
    }

    return entry;
}


void MP1Node::SendJOINREPLYMessage(Address * joinAddr) {
    size_t membership_list_size = sizeof(int) + sizeof(short) + sizeof(long) + sizeof(long);

    size_t msg_size = sizeof(MessageHdr) + sizeof(int) + (memberNode->memberList.size() * membership_list_size);
    MessageHdr * msg = (MessageHdr*) malloc(msg_size * sizeof(char));
    msg->msgType = JOINREP;
    memcpy((char*)(msg + 1), &memberNode->addr.addr, sizeof(memberNode->addr.addr));
    memcpy((char*)(msg + 1) + sizeof(memberNode->addr.addr), (&memberNode->heartbeat), sizeof(long));

#ifdef DEBUGLOG
    log->LOG(&memberNode->addr, "trying to join...");
#endif

    // send JOINREQ mesg to introducer member
    emulNet->ENsend(&memberNode->addr, joinAddr, (char*)msg, msg_size);

    free(msg);

}

void MP1Node::SerializeMembershipListForJOINREPMessageSending(MessageHdr* msg) {
    // serialize number of items
    int number_of_items = memberNode->memberList.size();
    memcpy((char*) (msg + 1), &number_of_items, sizeof(int));

    //serialize number of items
    int offset = sizeof(int);

    for (vector<MemberListEntry>::iterator it = memberNode->memberList.begin();
         it != memberNode->memberList.end(); it++) {
        memcpy((char*)(msg + 1) + offset, &it->id, sizeof(int));
        offset += sizeof(int);

        memcpy((char *)(msg + 1) + offset, &it->port, sizeof(short));
        offset += sizeof(short);

        memcpy((char *)(msg + 1) + offset, &it->heartbeat, sizeof(long));
        offset += sizeof(long);

        memcpy((char *)(msg + 1) + offset, &it->timestamp, sizeof(long));
        offset += sizeof(long);
    }
}


void MP1Node::DeserializeMembershipListForJOINREPMessageReceiving(char *data) {
    // read msg data
    int number_of_items;
    memcpy(&number_of_items, data + sizeof(MessageHdr), sizeof(int));

    // deserialize member list of entries
    int offset = sizeof(int);

    for (int i =0; i< number_of_items; i++) {
        int id;
        short port;
        long heartbeat;
        long timestamp;

        memcpy(&id, data + sizeof(MessageHdr) + offset, sizeof(int));
        offset += sizeof(int);

        memcpy(&port, data + sizeof(MessageHdr) + offset, sizeof(short));
        offset += sizeof(short);

        memcpy(&heartbeat, data + sizeof(MessageHdr) + offset, sizeof(long));
        offset += sizeof(long);

        memcpy(&timestamp, data + sizeof(MessageHdr) + offset, sizeof(long));
        offset += sizeof(long);

        UpdateMembershipList(id, port, heartbeat, timestamp);

    }
}
