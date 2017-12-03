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

    return 1;
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
 *
 * PARAMS:
 *        char *data : new entry
 *
 */
bool MP1Node::recvCallBack(void *env, char *data, int size) {

    MessageHdr *msg = (MessageHdr*) data;
    MsgTypes msg_type = msg->msgType;

    char * msg_content = data + sizeof(MessageHdr);

    if (msg_type == JOINREP) {
        Address* source = (Address*) msg_content;

        // source ->addr point den char[0]
        // (int*) source ->addr convert to int memory
        // *(int*)(source ->addr) convert to 32-bits int value

        UpdateMembershipList(*(int*)(source ->addr),
                             *(short*)(source -> addr + 4),
                             *(long*)(msg_content + sizeof(Address) + 1),
                             par->getcurrtime());

    } else if (msg_type == JOINREQ) {
        Address* requester = (Address*) msg_content;
        memberNode->inGroup = true;

        UpdateMembershipList(*(int*)(requester ->addr),
                             *(short*)(requester -> addr + 4),
                             *(long*)(msg_content + sizeof(Address) + 1),
                             par->getcurrtime());

        //malloc: Allocates a block of size bytes of memory, returning a pointer to the beginning of the block.

        size_t reply_size = sizeof(MessageHdr) + sizeof(Address) + sizeof(long) + 1;
        MessageHdr * reply_data = (MessageHdr*)malloc(reply_size);
        reply_data->msgType = JOINREP;

        memcpy((char*)(reply_data + 1), &(memberNode->addr), sizeof(Address));
        memcpy((char*)(reply_data) + 1 + sizeof(Address) + 1, &(memberNode->heartbeat), sizeof(long));

        //send reply to entry node
        emulNet->ENsend(&memberNode->addr, requester, (char*) reply_data, reply_size);
        free(reply_data);

    } else if (msg_type == PING) {
        int message_content_size = (int) (size - sizeof(MessageHdr));
        int row_size = sizeof(Address) + sizeof(long);
        vector<MemberListEntry> rec_membership_list = DeserializeData(data, message_content_size/row_size);

        for (vector<MemberListEntry>::iterator it = rec_membership_list.begin();
                it != rec_membership_list.end(); it++) {
            UpdateMembershipList(it->id, it->port, it->heartbeat, it->timestamp);
        }

    }

    return true;
}

void MP1Node::UpdateMembershipList(int id, short port, long heartbeat, long timestamp) {
    Address entry_address = GetNodeAddressFromIdAndPort(id, port);
    bool already_in_list = false;

    for (vector<MemberListEntry>::iterator it = memberNode->memberList.begin();
         it != memberNode->memberList.end(); it++) {

        if(GetNodeAddressFromIdAndPort(it->id, it->port) == entry_address ) { //already exists
            already_in_list = true;
            if (it->getheartbeat() < heartbeat) { //update
                it->settimestamp(par->getcurrtime());
                it->setheartbeat(heartbeat);
            }
        }
    }

    if (!already_in_list) {
        MemberListEntry new_entry = MemberListEntry(id, port, heartbeat, timestamp);
        memberNode->memberList.push_back(new_entry);
    }


#ifdef DEBUGLOG
    //void logNodeAdd(Address *, Address *);
    log->logNodeAdd(& memberNode->addr, & entry_address);
#endif

}

Address MP1Node::GetNodeAddressFromIdAndPort(int id, short port) {
    Address node_address;
    memcpy(&node_address.addr, &id, sizeof(int));
    memcpy(&node_address.addr[4], &port, sizeof(int));
    return node_address;
}

vector<MemberListEntry> MP1Node::DeserializeData(char* table, int rows) {
    vector<MemberListEntry> member_list;
    int entry_size = sizeof(Address) + sizeof(long);
    MemberListEntry temp_entry;

    for (int i = 0; i < rows; i++, table += entry_size) {

        Address* address = (Address*) table;
        int id;
        short port;
        long heartbeat;
        memcpy(&id, address->addr, sizeof(int));
        memcpy(&port, &(address->addr[4]), sizeof(short));
        memcpy(&heartbeat, table + sizeof(Address), sizeof(long));

        temp_entry.setid(id);
        temp_entry.setport(port);
        temp_entry.setheartbeat(heartbeat);
        temp_entry.settimestamp(par->getcurrtime());

        MemberListEntry entry = MemberListEntry(temp_entry);
        member_list.push_back(MemberListEntry(temp_entry));
    }

    return member_list;
}



/**
 * FUNCTION NAME: nodeLoopOps
 *
 * DESCRIPTION: Check if any node hasn't responded within a timeout period 
 * 				and then delete the nodes
 * 				Propagate your membership list
 */
void MP1Node::nodeLoopOps() {

    // check if it is time to ping tohers
    if (memberNode->pingCounter == 0) { //time to ping toehrs
        memberNode->heartbeat++;
        memberNode->memberList[0].heartbeat++;
        PingOthers();

        //reser ping coutter to 5
        memberNode->pingCounter = TFAIL;
    } else {
        memberNode->pingCounter--;
    }

    //check if any node has failed
    CheckFailure();

}

void MP1Node::CheckFailure() {

    for (vector<MemberListEntry>::iterator it = memberNode->memberList.begin() + 1;
        it != memberNode->memberList.end(); it++) {

        Address peer = GetNodeAddressFromIdAndPort(it->id, it->port);
        if (par->getcurrtime() - it->gettimestamp() > TREMOVE) {
#ifdef DEBUGLOG
            log->logNodeRemove(&memberNode->addr, &peer);
#endif
            memberNode->memberList.erase(it);
            it --;
            continue;
        }

        // suspect the peer has failed
        if(par->getcurrtime() - it->gettimestamp() > TFAIL) {
            it->setheartbeat(FAIL);
        }
    }
}

void MP1Node::PingOthers() {
    size_t ping_size = sizeof(MessageHdr) + ((sizeof(Address) + sizeof(long))*memberNode->memberList.size());
    MessageHdr * ping_data = (MessageHdr*)malloc(ping_size);
    ping_data->msgType = PING;
    char* data = SerializeData((char*) (ping_data + 1));

    for (vector<MemberListEntry>::iterator it = memberNode->memberList.begin() + 1;
         it != memberNode->memberList.end(); it++) {

        Address peer = GetNodeAddressFromIdAndPort(it->id, it->port);
        //send to other peer
        emulNet->ENsend(&memberNode->addr, &peer, data, ping_size);
    }

    free(ping_data);

}

char* MP1Node::SerializeData(char *buffer) {
    int index = 0;
    int entry_size = sizeof(Address) + sizeof(long);
    char *entry = (char*)malloc(entry_size);

    for (vector<MemberListEntry>::iterator it = memberNode->memberList.begin();
         it != memberNode->memberList.end(); it++, index += entry_size) {

        Address addr = GetNodeAddressFromIdAndPort(it->id, it->port);
        long heartbeat = it->getheartbeat();

        memcpy(entry, &addr, sizeof(Address));
        memcpy(entry + sizeof(Address), &heartbeat, sizeof(long));

        memcpy(buffer + index, entry, entry_size);
    }

    free(entry);
    return buffer;
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






