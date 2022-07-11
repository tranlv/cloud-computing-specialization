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
	/*
	 * This function is partially implemented and may require changes
	 */
	int id = *(int*)(&memberNode->addr.addr);
	int port = *(short*)(&memberNode->addr.addr[4]);

	memberNode->bFailed = false;
	memberNode->inited = true;
	memberNode->inGroup = false;
    // node is up!
	memberNode->nnb = 0;
	memberNode->heartbeat = 0;
	memberNode->pingCounter = TFAIL;
	memberNode->timeOutCounter = -1;
    initMemberListTable(memberNode, id, port);

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

    if (memberNode == nullptr) {    //if memberNode is null, you can't join a group.
        return 0;
    }


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
   /*
    * Your code goes here
    */
    if (memberNode->inited) {
        memberNode->memberList.clear();
        memberNode->inGroup = false;
        memberNode->bFailed = true;
        memberNode->nnb = 0;
        memberNode->heartbeat = 0;
        memberNode->pingCounter = 0;
        memberNode->timeOutCounter = -1;
        memberNode->inited = false;
    }

    return 0;
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
 */
bool MP1Node::recvCallBack(void *env, char *data, int size) {
	/*
	 * Your code goes here
	 */
#ifdef DEBUGLOG
    static char s[1024];
#endif

    MessageHdr* source_message = (MessageHdr*) data;
    Address *source_addr = (Address*)(source_message + 1);

    data += sizeof(MessageHdr) + sizeof(Address) + 1;
    long *received_heartbeat = (long*) data;

    if (source_message->msgType == JOINREQ) {

        // create JOINREP message: format of data is  {} MessageHdr Address heartbeat}
        // read introduceSelfToGroup function to understand how to create message
        MessageHdr* reply_message;
        size_t message_size = sizeof(MessageHdr) + sizeof(memberNode->addr) + sizeof(long) + 1;
        reply_message = (MessageHdr *) malloc(message_size * sizeof(char));

        reply_message->msgType = JOINREP;

        memcpy((char *)(reply_message+1), &memberNode->addr.addr, sizeof(memberNode->addr.addr));
        memcpy((char *)(reply_message+1) + sizeof(memberNode->addr) + 1, 
                        &memberNode->heartbeat, sizeof(long));

#ifdef DEBUGLOG
        sprintf(s, "Sending join_reply message to %d.%d.%d.%d:%d", source_addr->addr[0], source_addr->addr[1],
                             source_addr->addr[2], source_addr->addr[3], *(short *)&source_addr->addr[4]);
        log->LOG(&memberNode->addr, s);
#endif

        emulNet->ENsend(&(memberNode->addr), source_addr, (char *)reply_message, message_size);

        free(reply_message);

    } else if (source_message->msgType == JOINREP) {
        // after receiving reply message
        memberNode->inGroup = true;
    } 

    //update membership in all 3 cases: JOINREQ, JOINREP and HEARTBEAT
    update_membership(source_addr, *received_heartbeat);

    return true;

}


/**
 * FUNCTION NAME: nodeLoopOps
 *
 * DESCRIPTION: Check if any node hasn't responded within a timeout period and then delete
 * 				the nodes from the member list of this node
 * 				Propagate your membership list
 */
void MP1Node::nodeLoopOps() {

	/*
	 * Your code goes here
	 */
    
    if (memberNode->pingCounter == 0) {
        // Increment number of heartbeats
        memberNode->heartbeat++;
        send_heartbeat(&memberNode->addr, memberNode->heartbeat);       
        memberNode->pingCounter = TFAIL;
    } else {
        memberNode->pingCounter--;
    }    

    // do not remove myself, the first node represent myself
    for (vector<MemberListEntry>::iterator it = memberNode->memberList.begin()+1; it != memberNode->memberList.end();) {

        if (par->getcurrtime() - it->gettimestamp() > TREMOVE) {
            Address node_to_remove_addr;
            memcpy(node_to_remove_addr.addr, &(it->id), sizeof(int));
            memcpy(&node_to_remove_addr.addr[4], &(it->port), sizeof(short));  
            log->logNodeRemove(&memberNode->addr, &node_to_remove_addr);    
            it = memberNode->memberList.erase(it);
        } else  {
            ++it;
        }
    }

    return;

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
 * DESCRIPTION: Initialize the membership list
 */
void MP1Node::initMemberListTable(Member *memberNode, int id, int port) {
	memberNode->memberList.clear();

    // must add myself into the membership list
    MemberListEntry myself = MemberListEntry(id, port, memberNode->heartbeat, par->getcurrtime());
    memberNode->memberList.push_back(myself);
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


/**
 * FUNCTION NAME: update_membership
 *
 * DESCRIPTION: update heartbeat received from an adress and sent out to other member if this heartbeat is higher than original value
 */
void MP1Node::update_membership(Address* source_addr, long received_heartbeat) {

    // update every member of list including myself
    for (vector<MemberListEntry>::iterator it = memberNode->memberList.begin(); it != memberNode->memberList.end(); it++) {
        Address a;
        memcpy(a.addr, &(it->id), sizeof(int));
        memcpy(&a.addr[4], &(it->port), sizeof(short));

        //compare content
        if (a == *source_addr) {
            if (received_heartbeat > it->getheartbeat()) {
                it->setheartbeat(received_heartbeat);
                it->settimestamp(par->getcurrtime());

                // IMPORTANT: send heartbeat to other member if we receive a higher heartbeat of a current member
                send_heartbeat(source_addr, received_heartbeat);  
            }
           return;
        }
    }

    // add new member if it is not in the list yet
    MemberListEntry new_entry = MemberListEntry(*((int*)source_addr->addr),
                                 *((short*)&(source_addr->addr[4])), received_heartbeat, par->getcurrtime());
    memberNode->memberList.push_back(new_entry);  
    log->logNodeAdd(&memberNode->addr, source_addr);  
}

/**
 * FUNCTION NAME: send_heartbeat
 *
 * DESCRIPTION: send heartbeat to every members of list including myself
 */
void MP1Node::send_heartbeat(Address * source_addr, long heartbeat) {

    MessageHdr* message;
    size_t heartbeat_size = sizeof(MessageHdr) + sizeof(source_addr->addr) + sizeof(long) + 1;
    message = (MessageHdr*) malloc(heartbeat_size * sizeof(char));

    message->msgType = HEARTBEAT;

     // read introduceSelfToGroup function to understand how to create message
    memcpy((char *)(message+1), source_addr->addr, sizeof(source_addr->addr));
    memcpy((char *)(message+1) + sizeof(source_addr->addr) + 1, &heartbeat, sizeof(long));

    // send to every members of list including myself
    for (vector<MemberListEntry>::iterator it = memberNode->memberList.begin(); it != memberNode->memberList.end(); it++) {
        Address receiver_address;
        memcpy(receiver_address.addr, &(it->id), sizeof(int));
        memcpy(&receiver_address.addr[4], &(it->port), sizeof(short));
        emulNet->ENsend(&memberNode->addr, &receiver_address, (char *)message, heartbeat_size);
    }   

   free(message);

   return;
}
