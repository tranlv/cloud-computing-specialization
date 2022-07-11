# Copyright (C) 2011, 2012 Nippon Telegraph and Telephone Corporation.
# Copyright (C) 2011, 2012 Isaku Yamahata <yamahata at valinux co jp>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Decoder/Encoder implementations of OpenFlow 1.0.
"""

import struct
import binascii

from ofproto_parser import StringifyMixin, MsgBase, msg_str_attr
from ryu.lib import addrconv
from ryu.lib import mac
from ryu.lib.pack_utils import msg_pack_into
from . import ofproto_common
from . import ofproto_parser
from . import ofproto_v1_0 as ofproto
from . import nx_match
from ryu import utils

import logging
LOG = logging.getLogger('ryu.ofproto.ofproto_v1_0_parser')

_MSG_PARSERS = {}


def _set_msg_type(msg_type):
    '''Annotate corresponding OFP message type'''
    def _set_cls_msg_type(cls):
        cls.cls_msg_type = msg_type
        return cls
    return _set_cls_msg_type


def _register_parser(cls):
    '''class decorator to register msg parser'''
    assert cls.cls_msg_type is not None
    assert cls.cls_msg_type not in _MSG_PARSERS
    _MSG_PARSERS[cls.cls_msg_type] = cls.parser
    return cls


@ofproto_parser.register_msg_parser(ofproto.OFP_VERSION)
def msg_parser(datapath, version, msg_type, msg_len, xid, buf):
    parser = _MSG_PARSERS.get(msg_type)
    return parser(datapath, version, msg_type, msg_len, xid, buf)


# OFP_MSG_REPLY = {
#     OFPFeaturesRequest: OFPSwitchFeatures,
#     OFPBarrierRequest: OFPBarrierReply,
#     OFPQueueGetConfigRequest: OFPQueueGetConfigReply,
#
#     # ofp_stats_request -> ofp_stats_reply
#     OFPDescStatsRequest: OFPDescStatsReply,
#     OFPFlowStatsRequest: OFPFlowStatsReply,
#     OFPAggregateStatsRequest: OFPAggregateStatsReply,
#     OFPTableStatsRequest: OFPTableStatsReply,
#     OFPPortStatsRequest: OFPPortStatsReply,
#     OFPQueueStatsRequest: OFPQueueStatsReply,
#     OFPVendorStatsRequest: OFPVendorStatsReply,
#     }
def _set_msg_reply(msg_reply):
    '''Annotate OFP reply message class'''
    def _set_cls_msg_reply(cls):
        cls.cls_msg_reply = msg_reply
        return cls
    return _set_cls_msg_reply


#
# common structures
#

class OFPPhyPort(ofproto_parser.namedtuple('OFPPhyPort', (
        'port_no', 'hw_addr', 'name', 'config', 'state', 'curr', 'advertised',
        'supported', 'peer'))):

    _TYPE = {
        'ascii': [
            'hw_addr',
        ],
        'utf-8': [
            # OF spec is unclear about the encoding of name.
            # we assumes UTF-8, which is used by OVS.
            'name',
        ]
    }

    @classmethod
    def parser(cls, buf, offset):
        port = struct.unpack_from(ofproto.OFP_PHY_PORT_PACK_STR,
                                  buf, offset)
        port = list(port)
        i = cls._fields.index('hw_addr')
        port[i] = addrconv.mac.bin_to_text(port[i])
        i = cls._fields.index('name')
        port[i] = port[i].rstrip('\0')
        return cls(*port)


class OFPMatch(StringifyMixin):
    def __init__(self, wildcards=None, in_port=None, dl_src=None, dl_dst=None,
                 dl_vlan=None, dl_vlan_pcp=None, dl_type=None, nw_tos=None,
                 nw_proto=None, nw_src=None, nw_dst=None,
                 tp_src=None, tp_dst=None, nw_src_mask=32, nw_dst_mask=32):
        super(OFPMatch, self).__init__()
        wc = ofproto.OFPFW_ALL
        if in_port is None:
            self.in_port = 0
        else:
            wc &= ~ofproto.OFPFW_IN_PORT
            self.in_port = in_port

        if dl_src is None:
            self.dl_src = mac.DONTCARE
        else:
            wc &= ~ofproto.OFPFW_DL_SRC
            if dl_src == 0:
                self.dl_src = mac.DONTCARE
            else:
                self.dl_src = dl_src

        if dl_dst is None:
            self.dl_dst = mac.DONTCARE
        else:
            wc &= ~ofproto.OFPFW_DL_DST
            if dl_dst == 0:
                self.dl_dst = mac.DONTCARE
            else:
                self.dl_dst = dl_dst

        if dl_vlan is None:
            self.dl_vlan = 0
        else:
            wc &= ~ofproto.OFPFW_DL_VLAN
            self.dl_vlan = dl_vlan

        if dl_vlan_pcp is None:
            self.dl_vlan_pcp = 0
        else:
            wc &= ~ofproto.OFPFW_DL_VLAN_PCP
            self.dl_vlan_pcp = dl_vlan_pcp

        if dl_type is None:
            self.dl_type = 0
        else:
            wc &= ~ofproto.OFPFW_DL_TYPE
            self.dl_type = dl_type

        if nw_tos is None:
            self.nw_tos = 0
        else:
            wc &= ~ofproto.OFPFW_NW_TOS
            self.nw_tos = nw_tos

        if nw_proto is None:
            self.nw_proto = 0
        else:
            wc &= ~ofproto.OFPFW_NW_PROTO
            self.nw_proto = nw_proto

        if nw_src is None:
            self.nw_src = 0
        else:
            wc &= (32 - nw_src_mask) << ofproto.OFPFW_NW_SRC_SHIFT \
                | ~ofproto.OFPFW_NW_SRC_MASK
            self.nw_src = nw_src

        if nw_dst is None:
            self.nw_dst = 0
        else:
            wc &= (32 - nw_dst_mask) << ofproto.OFPFW_NW_DST_SHIFT \
                | ~ofproto.OFPFW_NW_DST_MASK
            self.nw_dst = nw_dst

        if tp_src is None:
            self.tp_src = 0
        else:
            wc &= ~ofproto.OFPFW_TP_SRC
            self.tp_src = tp_src

        if tp_dst is None:
            self.tp_dst = 0
        else:
            wc &= ~ofproto.OFPFW_TP_DST
            self.tp_dst = tp_dst

        if wildcards is None:
            self.wildcards = wc
        else:
            self.wildcards = wildcards

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_MATCH_PACK_STR, buf, offset,
                      self.wildcards, self.in_port, self.dl_src,
                      self.dl_dst, self.dl_vlan, self.dl_vlan_pcp,
                      self.dl_type, self.nw_tos, self.nw_proto,
                      self.nw_src, self.nw_dst, self.tp_src, self.tp_dst)

    @classmethod
    def parse(cls, buf, offset):
        match = struct.unpack_from(ofproto.OFP_MATCH_PACK_STR,
                                   buf, offset)
        return cls(*match)


class OFPActionHeader(StringifyMixin):
    _base_attributes = ['type', 'len']

    def __init__(self, type_, len_):
        self.type = type_
        self.len = len_

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_ACTION_HEADER_PACK_STR,
                      buf, offset, self.type, self.len)


class OFPAction(OFPActionHeader):
    _ACTION_TYPES = {}

    @staticmethod
    def register_action_type(type_, len_):
        def _register_action_type(cls):
            cls.cls_action_type = type_
            cls.cls_action_len = len_
            OFPAction._ACTION_TYPES[cls.cls_action_type] = cls
            return cls
        return _register_action_type

    def __init__(self):
        cls = self.__class__
        super(OFPAction, self).__init__(cls.cls_action_type,
                                        cls.cls_action_len)

    @classmethod
    def parser(cls, buf, offset):
        type_, len_ = struct.unpack_from(
            ofproto.OFP_ACTION_HEADER_PACK_STR, buf, offset)
        cls_ = cls._ACTION_TYPES.get(type_)
        assert cls_ is not None
        return cls_.parser(buf, offset)


@OFPAction.register_action_type(ofproto.OFPAT_OUTPUT,
                                ofproto.OFP_ACTION_OUTPUT_SIZE)
class OFPActionOutput(OFPAction):
    # NOTE: The reason of this magic number (0xffe5)
    #       is because there is no good constant in of1.0.
    #       The same value as OFPCML_MAX of of1.2 and of1.3 is used.
    def __init__(self, port, max_len=0xffe5):
        super(OFPActionOutput, self).__init__()
        self.port = port
        self.max_len = max_len

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, port, max_len = struct.unpack_from(
            ofproto.OFP_ACTION_OUTPUT_PACK_STR, buf, offset)
        assert type_ == ofproto.OFPAT_OUTPUT
        assert len_ == ofproto.OFP_ACTION_OUTPUT_SIZE
        return cls(port, max_len)

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_ACTION_OUTPUT_PACK_STR, buf,
                      offset, self.type, self.len, self.port, self.max_len)


@OFPAction.register_action_type(ofproto.OFPAT_SET_VLAN_VID,
                                ofproto.OFP_ACTION_VLAN_VID_SIZE)
class OFPActionVlanVid(OFPAction):
    def __init__(self, vlan_vid):
        super(OFPActionVlanVid, self).__init__()
        self.vlan_vid = vlan_vid

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, vlan_vid = struct.unpack_from(
            ofproto.OFP_ACTION_VLAN_VID_PACK_STR, buf, offset)
        assert type_ == ofproto.OFPAT_SET_VLAN_VID
        assert len_ == ofproto.OFP_ACTION_VLAN_VID_SIZE
        return cls(vlan_vid)

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_ACTION_VLAN_VID_PACK_STR,
                      buf, offset, self.type, self.len, self.vlan_vid)


@OFPAction.register_action_type(ofproto.OFPAT_SET_VLAN_PCP,
                                ofproto.OFP_ACTION_VLAN_PCP_SIZE)
class OFPActionVlanPcp(OFPAction):
    def __init__(self, vlan_pcp):
        super(OFPActionVlanPcp, self).__init__()
        self.vlan_pcp = vlan_pcp

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, vlan_pcp = struct.unpack_from(
            ofproto.OFP_ACTION_VLAN_PCP_PACK_STR, buf, offset)
        assert type_ == ofproto.OFPAT_SET_VLAN_PCP
        assert len_ == ofproto.OFP_ACTION_VLAN_PCP_SIZE
        return cls(vlan_pcp)

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_ACTION_VLAN_PCP_PACK_STR,
                      buf, offset, self.type, self.len, self.vlan_pcp)


@OFPAction.register_action_type(ofproto.OFPAT_STRIP_VLAN,
                                ofproto.OFP_ACTION_HEADER_SIZE)
class OFPActionStripVlan(OFPAction):
    def __init__(self):
        super(OFPActionStripVlan, self).__init__()

    @classmethod
    def parser(cls, buf, offset):
        type_, len_ = struct.unpack_from(
            ofproto.OFP_ACTION_HEADER_PACK_STR, buf, offset)
        assert type_ == ofproto.OFPAT_STRIP_VLAN
        assert len_ == ofproto.OFP_ACTION_HEADER_SIZE
        return cls()


class OFPActionDlAddr(OFPAction):
    def __init__(self, dl_addr):
        super(OFPActionDlAddr, self).__init__()
        self.dl_addr = dl_addr

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, dl_addr = struct.unpack_from(
            ofproto.OFP_ACTION_DL_ADDR_PACK_STR, buf, offset)
        assert type_ in (ofproto.OFPAT_SET_DL_SRC,
                         ofproto.OFPAT_SET_DL_DST)
        assert len_ == ofproto.OFP_ACTION_DL_ADDR_SIZE
        return cls(dl_addr)

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_ACTION_DL_ADDR_PACK_STR,
                      buf, offset, self.type, self.len, self.dl_addr)


@OFPAction.register_action_type(ofproto.OFPAT_SET_DL_SRC,
                                ofproto.OFP_ACTION_DL_ADDR_SIZE)
class OFPActionSetDlSrc(OFPActionDlAddr):
    def __init__(self, dl_addr):
        super(OFPActionSetDlSrc, self).__init__(dl_addr)


@OFPAction.register_action_type(ofproto.OFPAT_SET_DL_DST,
                                ofproto.OFP_ACTION_DL_ADDR_SIZE)
class OFPActionSetDlDst(OFPActionDlAddr):
    def __init__(self, dl_addr):
        super(OFPActionSetDlDst, self).__init__(dl_addr)


class OFPActionNwAddr(OFPAction):
    def __init__(self, nw_addr):
        super(OFPActionNwAddr, self).__init__()
        self.nw_addr = nw_addr

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, nw_addr = struct.unpack_from(
            ofproto.OFP_ACTION_NW_ADDR_PACK_STR, buf, offset)
        assert type_ in (ofproto.OFPAT_SET_NW_SRC,
                         ofproto.OFPAT_SET_NW_DST)
        assert len_ == ofproto.OFP_ACTION_NW_ADDR_SIZE
        return cls(nw_addr)

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_ACTION_NW_ADDR_PACK_STR,
                      buf, offset, self.type, self.len, self.nw_addr)


@OFPAction.register_action_type(ofproto.OFPAT_SET_NW_SRC,
                                ofproto.OFP_ACTION_NW_ADDR_SIZE)
class OFPActionSetNwSrc(OFPActionNwAddr):
    def __init__(self, nw_addr):
        super(OFPActionSetNwSrc, self).__init__(nw_addr)


@OFPAction.register_action_type(ofproto.OFPAT_SET_NW_DST,
                                ofproto.OFP_ACTION_NW_ADDR_SIZE)
class OFPActionSetNwDst(OFPActionNwAddr):
    def __init__(self, nw_addr):
        super(OFPActionSetNwDst, self).__init__(nw_addr)


@OFPAction.register_action_type(ofproto.OFPAT_SET_NW_TOS,
                                ofproto.OFP_ACTION_NW_TOS_SIZE)
class OFPActionSetNwTos(OFPAction):
    def __init__(self, tos):
        super(OFPActionSetNwTos, self).__init__()
        self.tos = tos

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, tos = struct.unpack_from(
            ofproto.OFP_ACTION_NW_TOS_PACK_STR, buf, offset)
        assert type_ == ofproto.OFPAT_SET_NW_TOS
        assert len_ == ofproto.OFP_ACTION_NW_TOS_SIZE
        return cls(tos)

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_ACTION_NW_TOS_PACK_STR,
                      buf, offset, self.type, self.len, self.tos)


class OFPActionTpPort(OFPAction):
    def __init__(self, tp):
        super(OFPActionTpPort, self).__init__()
        self.tp = tp

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, tp = struct.unpack_from(
            ofproto.OFP_ACTION_TP_PORT_PACK_STR, buf, offset)
        assert type_ in (ofproto.OFPAT_SET_TP_SRC,
                         ofproto.OFPAT_SET_TP_DST)
        assert len_ == ofproto.OFP_ACTION_TP_PORT_SIZE
        return cls(tp)

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_ACTION_TP_PORT_PACK_STR,
                      buf, offset, self.type, self.len, self.tp)


@OFPAction.register_action_type(ofproto.OFPAT_SET_TP_SRC,
                                ofproto.OFP_ACTION_TP_PORT_SIZE)
class OFPActionSetTpSrc(OFPActionTpPort):
    def __init__(self, tp):
        super(OFPActionSetTpSrc, self).__init__(tp)


@OFPAction.register_action_type(ofproto.OFPAT_SET_TP_DST,
                                ofproto.OFP_ACTION_TP_PORT_SIZE)
class OFPActionSetTpDst(OFPActionTpPort):
    def __init__(self, tp):
        super(OFPActionSetTpDst, self).__init__(tp)


@OFPAction.register_action_type(ofproto.OFPAT_ENQUEUE,
                                ofproto.OFP_ACTION_ENQUEUE_SIZE)
class OFPActionEnqueue(OFPAction):
    def __init__(self, port, queue_id):
        super(OFPActionEnqueue, self).__init__()
        self.port = port
        self.queue_id = queue_id

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, port, queue_id = struct.unpack_from(
            ofproto.OFP_ACTION_ENQUEUE_PACK_STR, buf, offset)
        assert type_ == ofproto.OFPAT_ENQUEUE
        assert len_ == ofproto.OFP_ACTION_ENQUEUE_SIZE
        return cls(port, queue_id)

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_ACTION_ENQUEUE_PACK_STR, buf, offset,
                      self.type, self.len, self.port, self.queue_id)


@OFPAction.register_action_type(ofproto.OFPAT_VENDOR, 0)
class OFPActionVendor(OFPAction):
    _ACTION_VENDORS = {}

    @staticmethod
    def register_action_vendor(vendor):
        def _register_action_vendor(cls):
            cls.cls_vendor = vendor
            OFPActionVendor._ACTION_VENDORS[cls.cls_vendor] = cls
            return cls
        return _register_action_vendor

    def __init__(self):
        super(OFPActionVendor, self).__init__()
        self.vendor = self.cls_vendor

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, vendor = struct.unpack_from(
            ofproto.OFP_ACTION_VENDOR_HEADER_PACK_STR, buf, offset)
        cls_ = cls._ACTION_VENDORS.get(vendor)
        return cls_.parser(buf, offset)


@OFPActionVendor.register_action_vendor(ofproto_common.NX_EXPERIMENTER_ID)
class NXActionHeader(OFPActionVendor):
    _NX_ACTION_SUBTYPES = {}

    @staticmethod
    def register_nx_action_subtype(subtype, len_):
        def _register_nx_action_subtype(cls):
            cls.cls_action_len = len_
            cls.cls_subtype = subtype
            NXActionHeader._NX_ACTION_SUBTYPES[cls.cls_subtype] = cls
            return cls
        return _register_nx_action_subtype

    def __init__(self):
        super(NXActionHeader, self).__init__()
        self.subtype = self.cls_subtype

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.OFP_ACTION_HEADER_PACK_STR,
                      buf, offset, self.type, self.len)

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, vendor, subtype = struct.unpack_from(
            ofproto.NX_ACTION_HEADER_PACK_STR, buf, offset)
        cls_ = cls._NX_ACTION_SUBTYPES.get(subtype)
        return cls_.parser(buf, offset)


class NXActionResubmitBase(NXActionHeader):
    def __init__(self, in_port, table):
        super(NXActionResubmitBase, self).__init__()
        assert self.subtype in (ofproto.NXAST_RESUBMIT,
                                ofproto.NXAST_RESUBMIT_TABLE)
        self.in_port = in_port
        self.table = table

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_RESUBMIT_PACK_STR, buf, offset,
                      self.type, self.len, self.vendor, self.subtype,
                      self.in_port, self.table)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_RESUBMIT, ofproto.NX_ACTION_RESUBMIT_SIZE)
class NXActionResubmit(NXActionResubmitBase):
    def __init__(self, in_port=ofproto.OFPP_IN_PORT):
        super(NXActionResubmit, self).__init__(in_port, 0)

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, vendor, subtype, in_port, table = struct.unpack_from(
            ofproto.NX_ACTION_RESUBMIT_PACK_STR, buf, offset)
        return cls(in_port)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_RESUBMIT_TABLE, ofproto.NX_ACTION_RESUBMIT_SIZE)
class NXActionResubmitTable(NXActionResubmitBase):
    def __init__(self, in_port=ofproto.OFPP_IN_PORT, table=0xff):
        super(NXActionResubmitTable, self).__init__(in_port, table)

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, vendor, subtype, in_port, table = struct.unpack_from(
            ofproto.NX_ACTION_RESUBMIT_PACK_STR, buf, offset)
        return cls(in_port, table)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_SET_TUNNEL, ofproto.NX_ACTION_SET_TUNNEL_SIZE)
class NXActionSetTunnel(NXActionHeader):
    def __init__(self, tun_id):
        super(NXActionSetTunnel, self).__init__()
        self.tun_id = tun_id

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_SET_TUNNEL_PACK_STR, buf,
                      offset, self.type, self.len, self.vendor, self.subtype,
                      self.tun_id)

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, vendor, subtype, tun_id = struct.unpack_from(
            ofproto.NX_ACTION_SET_TUNNEL_PACK_STR, buf, offset)
        return cls(tun_id)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_SET_QUEUE, ofproto.NX_ACTION_SET_QUEUE_SIZE)
class NXActionSetQueue(NXActionHeader):
    def __init__(self, queue_id):
        super(NXActionSetQueue, self).__init__()
        self.queue_id = queue_id

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_SET_QUEUE_PACK_STR, buf,
                      offset, self.type, self.len, self.vendor,
                      self.subtype, self.queue_id)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype, queue_id) = struct.unpack_from(
            ofproto.NX_ACTION_SET_QUEUE_PACK_STR, buf, offset)
        return cls(queue_id)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_POP_QUEUE, ofproto.NX_ACTION_POP_QUEUE_SIZE)
class NXActionPopQueue(NXActionHeader):
    def __init__(self):
        super(NXActionPopQueue, self).__init__()

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_POP_QUEUE_PACK_STR, buf,
                      offset, self.type, self.len, self.vendor,
                      self.subtype)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype) = struct.unpack_from(
            ofproto.NX_ACTION_POP_QUEUE_PACK_STR, buf, offset)
        return cls()


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_REG_MOVE, ofproto.NX_ACTION_REG_MOVE_SIZE)
class NXActionRegMove(NXActionHeader):
    def __init__(self, n_bits, src_ofs, dst_ofs, src, dst):
        super(NXActionRegMove, self).__init__()
        self.n_bits = n_bits
        self.src_ofs = src_ofs
        self.dst_ofs = dst_ofs
        self.src = src
        self.dst = dst

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_REG_MOVE_PACK_STR, buf,
                      offset, self.type, self.len, self.vendor,
                      self.subtype, self.n_bits, self.src_ofs, self.dst_ofs,
                      self.src, self.dst)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype, n_bits, src_ofs, dst_ofs,
            src, dst) = struct.unpack_from(
            ofproto.NX_ACTION_REG_MOVE_PACK_STR, buf, offset)
        return cls(n_bits, src_ofs, dst_ofs, src, dst)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_REG_LOAD, ofproto.NX_ACTION_REG_LOAD_SIZE)
class NXActionRegLoad(NXActionHeader):
    def __init__(self, ofs_nbits, dst, value):
        super(NXActionRegLoad, self).__init__()
        self.ofs_nbits = ofs_nbits
        self.dst = dst
        self.value = value

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_REG_LOAD_PACK_STR, buf,
                      offset, self.type, self.len, self.vendor,
                      self.subtype, self.ofs_nbits, self.dst, self.value)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype, ofs_nbits, dst,
            value) = struct.unpack_from(
            ofproto.NX_ACTION_REG_LOAD_PACK_STR, buf, offset)
        return cls(ofs_nbits, dst, value)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_SET_TUNNEL64, ofproto.NX_ACTION_SET_TUNNEL64_SIZE)
class NXActionSetTunnel64(NXActionHeader):
    def __init__(self, tun_id):
        super(NXActionSetTunnel64, self).__init__()
        self.tun_id = tun_id

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_SET_TUNNEL64_PACK_STR, buf,
                      offset, self.type, self.len, self.vendor, self.subtype,
                      self.tun_id)

    @classmethod
    def parser(cls, buf, offset):
        type_, len_, vendor, subtype, tun_id = struct.unpack_from(
            ofproto.NX_ACTION_SET_TUNNEL64_PACK_STR, buf, offset)
        return cls(tun_id)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_MULTIPATH, ofproto.NX_ACTION_MULTIPATH_SIZE)
class NXActionMultipath(NXActionHeader):
    def __init__(self, fields, basis, algorithm, max_link, arg,
                 ofs_nbits, dst):
        super(NXActionMultipath, self).__init__()
        self.fields = fields
        self.basis = basis
        self.algorithm = algorithm
        self.max_link = max_link
        self.arg = arg
        self.ofs_nbits = ofs_nbits
        self.dst = dst

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_MULTIPATH_PACK_STR, buf,
                      offset, self.type, self.len, self.vendor, self.subtype,
                      self.fields, self.basis, self.algorithm, self.max_link,
                      self.arg, self.ofs_nbits, self.dst)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype, fields, basis, algorithm,
            max_link, arg, ofs_nbits, dst) = struct.unpack_from(
            ofproto.NX_ACTION_MULTIPATH_PACK_STR, buf, offset)
        return cls(fields, basis, algorithm, max_link, arg, ofs_nbits,
                   dst)


@NXActionHeader.register_nx_action_subtype(ofproto.NXAST_NOTE, 0)
class NXActionNote(NXActionHeader):
    def __init__(self, note):
        super(NXActionNote, self).__init__()
        # should check here if the note is valid (only hex values)
        pad = (len(note) + 10) % 8
        if pad:
            note += [0x0 for i in range(8 - pad)]
        self.note = note
        self.len = len(note) + 10

    def serialize(self, buf, offset):
        note = self.note
        extra = None
        extra_len = len(self.note) - 6
        if extra_len > 0:
            extra = note[6:]
        note = note[0:6]
        msg_pack_into(ofproto.NX_ACTION_NOTE_PACK_STR, buf,
                      offset, self.type, self.len, self.vendor, self.subtype,
                      *note)
        if extra_len > 0:
            msg_pack_into('B' * extra_len, buf,
                          offset + ofproto.NX_ACTION_NOTE_SIZE,
                          *extra)

    @classmethod
    def parser(cls, buf, offset):
        note = struct.unpack_from(
            ofproto.NX_ACTION_NOTE_PACK_STR, buf, offset)
        (type_, len_, vendor, subtype) = note[0:4]
        note = [i for i in note[4:]]
        if len_ > ofproto.NX_ACTION_NOTE_SIZE:
            note_start = offset + ofproto.NX_ACTION_NOTE_SIZE
            note_end = note_start + len_ - ofproto.NX_ACTION_NOTE_SIZE
            note += [int(binascii.b2a_hex(i), 16) for i
                     in buf[note_start:note_end]]
        return cls(note)


class NXActionBundleBase(NXActionHeader):
    def __init__(self, algorithm, fields, basis, slave_type, n_slaves,
                 ofs_nbits, dst, slaves):
        super(NXActionBundleBase, self).__init__()
        _len = ofproto.NX_ACTION_BUNDLE_SIZE + len(slaves) * 2
        _len += (_len % 8)
        self.len = _len

        self.algorithm = algorithm
        self.fields = fields
        self.basis = basis
        self.slave_type = slave_type
        self.n_slaves = n_slaves
        self.ofs_nbits = ofs_nbits
        self.dst = dst
        self.slaves = slaves

    def serialize(self, buf, offset):
        slave_offset = offset + ofproto.NX_ACTION_BUNDLE_SIZE

        for s in self.slaves:
            msg_pack_into('!H', buf, slave_offset, s)
            slave_offset += 2

        pad_len = (len(self.slaves) * 2 +
                   ofproto.NX_ACTION_BUNDLE_SIZE) % 8

        if pad_len != 0:
            msg_pack_into('%dx' % pad_len, buf, slave_offset)

        msg_pack_into(ofproto.NX_ACTION_BUNDLE_PACK_STR, buf,
                      offset, self.type, self.len, self.vendor, self.subtype,
                      self.algorithm, self.fields, self.basis,
                      self.slave_type, self.n_slaves,
                      self.ofs_nbits, self.dst)

    @classmethod
    def parser(cls, action_cls, buf, offset):
        (type_, len_, vendor, subtype, algorithm, fields, basis,
            slave_type, n_slaves, ofs_nbits, dst) = struct.unpack_from(
            ofproto.NX_ACTION_BUNDLE_PACK_STR, buf, offset)
        slave_offset = offset + ofproto.NX_ACTION_BUNDLE_SIZE

        slaves = []
        for i in range(0, n_slaves):
            s = struct.unpack_from('!H', buf, slave_offset)
            slaves.append(s[0])
            slave_offset += 2

        return action_cls(algorithm, fields, basis, slave_type,
                          n_slaves, ofs_nbits, dst, slaves)


@NXActionHeader.register_nx_action_subtype(ofproto.NXAST_BUNDLE, 0)
class NXActionBundle(NXActionBundleBase):
    def __init__(self, algorithm, fields, basis, slave_type, n_slaves,
                 ofs_nbits, dst, slaves):
        super(NXActionBundle, self).__init__(
            algorithm, fields, basis, slave_type, n_slaves,
            ofs_nbits, dst, slaves)

    @classmethod
    def parser(cls, buf, offset):
        return NXActionBundleBase.parser(NXActionBundle, buf, offset)


@NXActionHeader.register_nx_action_subtype(ofproto.NXAST_BUNDLE_LOAD, 0)
class NXActionBundleLoad(NXActionBundleBase):
    def __init__(self, algorithm, fields, basis, slave_type, n_slaves,
                 ofs_nbits, dst, slaves):
        super(NXActionBundleLoad, self).__init__(
            algorithm, fields, basis, slave_type, n_slaves,
            ofs_nbits, dst, slaves)

    @classmethod
    def parser(cls, buf, offset):
        return NXActionBundleBase.parser(NXActionBundleLoad, buf, offset)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_AUTOPATH, ofproto.NX_ACTION_AUTOPATH_SIZE)
class NXActionAutopath(NXActionHeader):
    def __init__(self, ofs_nbits, dst, id_):
        super(NXActionAutopath, self).__init__()
        self.ofs_nbits = ofs_nbits
        self.dst = dst
        self.id = id_

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_AUTOPATH_PACK_STR, buf, offset,
                      self.type, self.len, self.vendor, self.subtype,
                      self.ofs_nbits, self.dst, self.id)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype, ofs_nbits, dst,
            id_) = struct.unpack_from(
            ofproto.NX_ACTION_AUTOPATH_PACK_STR, buf, offset)
        return cls(ofs_nbits, dst, id_)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_OUTPUT_REG, ofproto.NX_ACTION_OUTPUT_REG_SIZE)
class NXActionOutputReg(NXActionHeader):
    def __init__(self, ofs_nbits, src, max_len):
        super(NXActionOutputReg, self).__init__()
        self.ofs_nbits = ofs_nbits
        self.src = src
        self.max_len = max_len

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_OUTPUT_REG_PACK_STR, buf, offset,
                      self.type, self.len, self.vendor, self.subtype,
                      self.ofs_nbits, self.src, self.max_len)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype, ofs_nbits, src,
            max_len) = struct.unpack_from(
            ofproto.NX_ACTION_OUTPUT_REG_PACK_STR, buf, offset)
        return cls(ofs_nbits, src, max_len)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_EXIT, ofproto.NX_ACTION_HEADER_SIZE)
class NXActionExit(NXActionHeader):
    def __init__(self):
        super(NXActionExit, self).__init__()

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_HEADER_PACK_STR, buf, offset,
                      self.type, self.len, self.vendor, self.subtype)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype) = struct.unpack_from(
            ofproto.NX_ACTION_HEADER_PACK_STR, buf, offset)
        return cls()


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_DEC_TTL, ofproto.NX_ACTION_HEADER_SIZE)
class NXActionDecTtl(NXActionHeader):
    def __init__(self):
        super(NXActionDecTtl, self).__init__()

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_HEADER_PACK_STR, buf, offset,
                      self.type, self.len, self.vendor, self.subtype)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype) = struct.unpack_from(
            ofproto.NX_ACTION_HEADER_PACK_STR, buf, offset)
        return cls()


@NXActionHeader.register_nx_action_subtype(ofproto.NXAST_LEARN, 0)
class NXActionLearn(NXActionHeader):
    def __init__(self, idle_timeout, hard_timeout, priority, cookie, flags,
                 table_id, fin_idle_timeout, fin_hard_timeout, spec):
        super(NXActionLearn, self).__init__()
        len_ = len(spec) + ofproto.NX_ACTION_LEARN_SIZE
        pad_len = 8 - (len_ % 8)
        self.len = len_ + pad_len

        self.idle_timeout = idle_timeout
        self.hard_timeout = hard_timeout
        self.priority = priority
        self.cookie = cookie
        self.flags = flags
        self.table_id = table_id
        self.fin_idle_timeout = fin_idle_timeout
        self.fin_hard_timeout = fin_hard_timeout
        self.spec = spec + bytearray('\x00' * pad_len)

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_LEARN_PACK_STR, buf, offset,
                      self.type, self.len, self.vendor, self.subtype,
                      self.idle_timeout, self.hard_timeout, self.priority,
                      self.cookie, self.flags, self.table_id,
                      self.fin_idle_timeout, self.fin_hard_timeout)
        buf += self.spec

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype, idle_timeout, hard_timeout, priority,
            cookie, flags, table_id, fin_idle_timeout,
            fin_hard_timeout) = struct.unpack_from(
            ofproto.NX_ACTION_LEARN_PACK_STR, buf, offset)
        spec = buf[offset + ofproto.NX_ACTION_LEARN_SIZE:]
        return cls(idle_timeout, hard_timeout, priority,
                   cookie, flags, table_id, fin_idle_timeout,
                   fin_hard_timeout, spec)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_CONTROLLER, ofproto.NX_ACTION_CONTROLLER_SIZE)
class NXActionController(NXActionHeader):
    def __init__(self, max_len, controller_id, reason):
        super(NXActionController, self).__init__()
        self.max_len = max_len
        self.controller_id = controller_id
        self.reason = reason

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_CONTROLLER_PACK_STR, buf, offset,
                      self.type, self.len, self.vendor, self.subtype,
                      self.max_len, self.controller_id, self.reason, 0)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype, max_len, controller_id, reason,
            _zero) = struct.unpack_from(
            ofproto.NX_ACTION_CONTROLLER_PACK_STR, buf, offset)
        return cls(max_len, controller_id, reason)


@NXActionHeader.register_nx_action_subtype(
    ofproto.NXAST_FIN_TIMEOUT, ofproto.NX_ACTION_FIN_TIMEOUT_SIZE)
class NXActionFinTimeout(NXActionHeader):
    def __init__(self, fin_idle_timeout, fin_hard_timeout):
        super(NXActionFinTimeout, self).__init__()
        self.fin_idle_timeout = fin_idle_timeout
        self.fin_hard_timeout = fin_hard_timeout

    def serialize(self, buf, offset):
        msg_pack_into(ofproto.NX_ACTION_FIN_TIMEOUT_PACK_STR, buf, offset,
                      self.type, self.len, self.vendor, self.subtype,
                      self.fin_idle_timeout, self.fin_hard_timeout)

    @classmethod
    def parser(cls, buf, offset):
        (type_, len_, vendor, subtype, fin_idle_timeout,
            fin_hard_timeout) = struct.unpack_from(
            ofproto.NX_ACTION_FIN_TIMEOUT_PACK_STR, buf, offset)
        return cls(fin_idle_timeout, fin_hard_timeout)


class OFPDescStats(ofproto_parser.namedtuple('OFPDescStats', (
        'mfr_desc', 'hw_desc', 'sw_desc', 'serial_num', 'dp_desc'))):

    _TYPE = {
        'ascii': [
            'mfr_desc',
            'hw_desc',
            'sw_desc',
            'serial_num',
            'dp_desc',
        ]
    }

    @classmethod
    def parser(cls, buf, offset):
        desc = struct.unpack_from(ofproto.OFP_DESC_STATS_PACK_STR,
                                  buf, offset)
        desc = list(desc)
        desc = map(lambda x: x.rstrip('\0'), desc)
        stats = cls(*desc)
        stats.length = ofproto.OFP_DESC_STATS_SIZE
        return stats


class OFPFlowStats(StringifyMixin):
    def __init__(self):
        super(OFPFlowStats, self).__init__()
        self.length = None
        self.table_id = None
        self.match = None
        self.duration_sec = None
        self.duration_nsec = None
        self.priority = None
        self.idle_timeout = None
        self.hard_timeout = None
        self.cookie = None
        self.packet_count = None
        self.byte_count = None
        self.actions = None

    @classmethod
    def parser(cls, buf, offset):
        flow_stats = cls()

        flow_stats.length, flow_stats.table_id = struct.unpack_from(
            ofproto.OFP_FLOW_STATS_0_PACK_STR, buf, offset)
        offset += ofproto.OFP_FLOW_STATS_0_SIZE

        flow_stats.match = OFPMatch.parse(buf, offset)
        offset += ofproto.OFP_MATCH_SIZE

        (flow_stats.duration_sec,
         flow_stats.duration_nsec,
         flow_stats.priority,
         flow_stats.idle_timeout,
         flow_stats.hard_timeout,
         flow_stats.cookie,
         flow_stats.packet_count,
         flow_stats.byte_count) = struct.unpack_from(
            ofproto.OFP_FLOW_STATS_1_PACK_STR, buf, offset)
        offset += ofproto.OFP_FLOW_STATS_1_SIZE

        flow_stats.actions = []
        length = ofproto.OFP_FLOW_STATS_SIZE
        while length < flow_stats.length:
            action = OFPAction.parser(buf, offset)
            flow_stats.actions.append(action)

            offset += action.len
            length += action.len

        return flow_stats


class OFPAggregateStats(ofproto_parser.namedtuple('OFPAggregateStats', (
        'packet_count', 'byte_count', 'flow_count'))):
    @classmethod
    def parser(cls, buf, offset):
        agg = struct.unpack_from(
            ofproto.OFP_AGGREGATE_STATS_REPLY_PACK_STR, buf, offset)
        stats = cls(*agg)
        stats.length = ofproto.OFP_AGGREGATE_STATS_REPLY_SIZE
        return stats


class OFPTableStats(ofproto_parser.namedtuple('OFPTableStats', (
        'table_id', 'name', 'wildcards', 'max_entries', 'active_count',
        'lookup_count', 'matched_count'))):

    _TYPE = {
        'utf-8': [
            # OF spec is unclear about the encoding of name.
            # we assumes UTF-8.
            'name',
        ]
    }

    @classmethod
    def parser(cls, buf, offset):
        tbl = struct.unpack_from(ofproto.OFP_TABLE_STATS_PACK_STR,
                                 buf, offset)
        tbl = list(tbl)
        i = cls._fields.index('name')
        tbl[i] = tbl[i].rstrip('\0')
        stats = cls(*tbl)
        stats.length = ofproto.OFP_TABLE_STATS_SIZE
        return stats


class OFPPortStats(ofproto_parser.namedtuple('OFPPortStats', (
        'port_no', 'rx_packets', 'tx_packets', 'rx_bytes', 'tx_bytes',
        'rx_dropped', 'tx_dropped', 'rx_errors', 'tx_errors',
        'rx_frame_err', 'rx_over_err', 'rx_crc_err', 'collisions'))):
    @classmethod
    def parser(cls, buf, offset):
        port = struct.unpack_from(ofproto.OFP_PORT_STATS_PACK_STR,
                                  buf, offset)
        stats = cls(*port)
        stats.length = ofproto.OFP_PORT_STATS_SIZE
        return stats


class OFPQueueStats(ofproto_parser.namedtuple('OFPQueueStats', (
        'port_no', 'queue_id', 'tx_bytes', 'tx_packets', 'tx_errors'))):
    @classmethod
    def parser(cls, buf, offset):
        queue = struct.unpack_from(ofproto.OFP_QUEUE_STATS_PACK_STR,
                                   buf, offset)
        stats = cls(*queue)
        stats.length = ofproto.OFP_QUEUE_STATS_SIZE
        return stats


class OFPVendorStats(ofproto_parser.namedtuple('OFPVendorStats',
                                               ('specific_data'))):
    @classmethod
    def parser(cls, buf, offset):
        stats = cls(buf[offset:])
        stats.length = len(stats.specific_data)
        return stats


class NXFlowStats(StringifyMixin):
    def __init__(self):
        super(NXFlowStats, self).__init__()
        self.length = None
        self.table_id = None
        self.duration_sec = None
        self.duration_nsec = None
        self.priority = None
        self.idle_timeout = None
        self.hard_timeout = None
        self.match_len = None
        self.idle_age = None
        self.hard_age = None
        self.cookie = None
        self.packet_count = None
        self.byte_count = None

    @classmethod
    def parser(cls, buf, offset):
        original_offset = offset
        nxflow_stats = cls()
        (nxflow_stats.length, nxflow_stats.table_id,
         nxflow_stats.duration_sec, nxflow_stats.duration_nsec,
         nxflow_stats.priority, nxflow_stats.idle_timeout,
         nxflow_stats.hard_timeout, nxflow_stats.match_len,
         nxflow_stats.idle_age, nxflow_stats.hard_age,
         nxflow_stats.cookie, nxflow_stats.packet_count,
         nxflow_stats.byte_count) = struct.unpack_from(
            ofproto.NX_FLOW_STATS_PACK_STR, buf, offset)
        offset += ofproto.NX_FLOW_STATS_SIZE

        fields = []
        match_len = nxflow_stats.match_len
        match_len -= 4
        while match_len > 0:
            field = nx_match.MFField.parser(buf, offset)
            offset += field.length
            match_len -= field.length
            fields.append(field)
        nxflow_stats.fields = fields

        actions = []
        total_len = original_offset + nxflow_stats.length
        match_len = nxflow_stats.match_len
        offset += utils.round_up(match_len, 8) - match_len
        while offset < total_len:
            action = OFPAction.parser(buf, offset)
            actions.append(action)
            offset += action.len
        nxflow_stats.actions = actions

        return nxflow_stats


class NXAggregateStats(ofproto_parser.namedtuple('NXAggregateStats', (
        'packet_count', 'byte_count', 'flow_count'))):
    @classmethod
    def parser(cls, buf, offset):
        agg = struct.unpack_from(
            ofproto.NX_AGGREGATE_STATS_REPLY_PACK_STR, buf, offset)
        stats = cls(*agg)
        stats.length = ofproto.NX_AGGREGATE_STATS_REPLY_SIZE

        return stats


class OFPQueuePropHeader(StringifyMixin):
    _QUEUE_PROPERTIES = {}

    @staticmethod
    def register_queue_property(prop_type, prop_len):
        def _register_queue_propery(cls):
            cls.cls_prop_type = prop_type
            cls.cls_prop_len = prop_len
            OFPQueuePropHeader._QUEUE_PROPERTIES[prop_type] = cls
            return cls
        return _register_queue_propery

    def __init__(self):
        self.property = self.cls_prop_type
        self.len = self.cls_prop_len

    @classmethod
    def parser(cls, buf, offset):
        property_, len_ = struct.unpack_from(
            ofproto.OFP_QUEUE_PROP_HEADER_PACK_STR, buf, offset)
        prop_cls = cls._QUEUE_PROPERTIES[property_]
        assert property_ == prop_cls.cls_prop_type
        assert len_ == prop_cls.cls_prop_len

        offset += ofproto.OFP_QUEUE_PROP_HEADER_SIZE
        return prop_cls.parser(buf, offset)


@OFPQueuePropHeader.register_queue_property(
    ofproto.OFPQT_NONE, ofproto.OFP_QUEUE_PROP_HEADER_SIZE)
class OFPQueuePropNone(OFPQueuePropHeader):
    def __init__(self):
        super(OFPQueuePropNone, self).__init__()

    @classmethod
    def parser(cls, buf, offset):
        return cls()


@OFPQueuePropHeader.register_queue_property(
    ofproto.OFPQT_MIN_RATE, ofproto.OFP_QUEUE_PROP_MIN_RATE_SIZE)
class OFPQueuePropMinRate(OFPQueuePropHeader):
    def __init__(self, rate):
        super(OFPQueuePropMinRate, self).__init__()
        self.rate = rate

    @classmethod
    def parser(cls, buf, offset):
        (rate,) = struct.unpack_from(
            ofproto.OFP_QUEUE_PROP_MIN_RATE_PACK_STR,
            buf, offset)
        return cls(rate)


class OFPPacketQueue(StringifyMixin):
    def __init__(self, queue_id, len_):
        self.queue_id = queue_id
        self.len = len_
        self.properties = None

    @classmethod
    def parser(cls, buf, offset):
        queue_id, len_ = struct.unpack_from(
            ofproto.OFP_PACKET_QUEUE_PQCK_STR, buf, offset)
        packet_queue = cls(queue_id, len_)

        packet_queue.properties = []
        cur_len = ofproto.OFP_PACKET_QUEUE_SIZE
        offset += ofproto.OFP_PACKET_QUEUE_SIZE
        while (cur_len + ofproto.OFP_QUEUE_PROP_HEADER_SIZE <=
               packet_queue.len):
            prop = OFPQueuePropHeader.parser(buf, offset)
            packet_queue.properties.append(prop)

            cur_len += prop.len
            offset += prop.len

        return packet_queue

#
# Symmetric messages
# parser + serializer
#


@_register_parser
@_set_msg_type(ofproto.OFPT_HELLO)
class OFPHello(MsgBase):
    def __init__(self, datapath):
        super(OFPHello, self).__init__(datapath)


@_register_parser
@_set_msg_type(ofproto.OFPT_ERROR)
class OFPErrorMsg(MsgBase):
    def __init__(self, datapath, type_=None, code=None, data=None):
        super(OFPErrorMsg, self).__init__(datapath)
        self.type = type_
        self.code = code
        self.data = data

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        msg = super(OFPErrorMsg, cls).parser(datapath, version, msg_type,
                                             msg_len, xid, buf)
        msg.type, msg.code = struct.unpack_from(
            ofproto.OFP_ERROR_MSG_PACK_STR, msg.buf,
            ofproto.OFP_HEADER_SIZE)
        msg.data = msg.buf[ofproto.OFP_ERROR_MSG_SIZE:]
        return msg

    def _serialize_body(self):
        assert self.data is not None
        msg_pack_into(ofproto.OFP_ERROR_MSG_PACK_STR, self.buf,
                      ofproto.OFP_HEADER_SIZE, self.type, self.code)
        self.buf += self.data


@_register_parser
@_set_msg_type(ofproto.OFPT_ECHO_REQUEST)
class OFPEchoRequest(MsgBase):
    def __init__(self, datapath, data=None):
        super(OFPEchoRequest, self).__init__(datapath)
        self.data = data

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        msg = super(OFPEchoRequest, cls).parser(datapath, version, msg_type,
                                                msg_len, xid, buf)
        msg.data = msg.buf[ofproto.OFP_HEADER_SIZE:]
        return msg

    def _serialize_body(self):
        if self.data is not None:
            self.buf += self.data


@_register_parser
@_set_msg_type(ofproto.OFPT_ECHO_REPLY)
class OFPEchoReply(MsgBase):
    def __init__(self, datapath, data=None):
        super(OFPEchoReply, self).__init__(datapath)
        self.data = data

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        msg = super(OFPEchoReply, cls).parser(datapath, version, msg_type,
                                              msg_len, xid, buf)
        msg.data = msg.buf[ofproto.OFP_HEADER_SIZE:]
        return msg

    def _serialize_body(self):
        assert self.data is not None
        self.buf += self.data


@_register_parser
@_set_msg_type(ofproto.OFPT_VENDOR)
class OFPVendor(MsgBase):
    _VENDORS = {}

    @staticmethod
    def register_vendor(id_):
        def _register_vendor(cls):
            OFPVendor._VENDORS[id_] = cls
            return cls
        return _register_vendor

    def __init__(self, datapath):
        super(OFPVendor, self).__init__(datapath)
        self.data = None
        self.vendor = None

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        msg = super(OFPVendor, cls).parser(datapath, version, msg_type,
                                           msg_len, xid, buf)
        (msg.vendor,) = struct.unpack_from(
            ofproto.OFP_VENDOR_HEADER_PACK_STR, msg.buf,
            ofproto.OFP_HEADER_SIZE)

        cls_ = cls._VENDORS.get(msg.vendor)
        if cls_:
            msg.data = cls_.parser(datapath, msg.buf, 0)
        else:
            msg.data = msg.buf[ofproto.OFP_VENDOR_HEADER_SIZE:]

        return msg

    def serialize_header(self):
        msg_pack_into(ofproto.OFP_VENDOR_HEADER_PACK_STR,
                      self.buf, ofproto.OFP_HEADER_SIZE, self.vendor)

    def _serialize_body(self):
        assert self.data is not None
        self.serialize_header()
        self.buf += self.data


@OFPVendor.register_vendor(ofproto_common.NX_EXPERIMENTER_ID)
class NiciraHeader(OFPVendor):
    _NX_SUBTYPES = {}

    @staticmethod
    def register_nx_subtype(subtype):
        def _register_nx_subtype(cls):
            cls.cls_subtype = subtype
            NiciraHeader._NX_SUBTYPES[cls.cls_subtype] = cls
            return cls
        return _register_nx_subtype

    def __init__(self, datapath, subtype):
        super(NiciraHeader, self).__init__(datapath)
        self.vendor = ofproto_common.NX_EXPERIMENTER_ID
        self.subtype = subtype

    def serialize_header(self):
        super(NiciraHeader, self).serialize_header()
        msg_pack_into(ofproto.NICIRA_HEADER_PACK_STR,
                      self.buf, ofproto.OFP_HEADER_SIZE,
                      self.vendor, self.subtype)

    @classmethod
    def parser(cls, datapath, buf, offset):
        vendor, subtype = struct.unpack_from(
            ofproto.NICIRA_HEADER_PACK_STR, buf,
            offset + ofproto.OFP_HEADER_SIZE)
        cls_ = cls._NX_SUBTYPES.get(subtype)
        return cls_.parser(datapath, buf,
                           offset + ofproto.NICIRA_HEADER_SIZE)


class NXTSetFlowFormat(NiciraHeader):
    def __init__(self, datapath, flow_format):
        super(NXTSetFlowFormat, self).__init__(
            datapath, ofproto.NXT_SET_FLOW_FORMAT)
        self.format = flow_format

    def _serialize_body(self):
        self.serialize_header()
        msg_pack_into(ofproto.NX_SET_FLOW_FORMAT_PACK_STR,
                      self.buf, ofproto.NICIRA_HEADER_SIZE, self.format)


class NXTFlowMod(NiciraHeader):
    def __init__(self, datapath, cookie, command,
                 idle_timeout=0, hard_timeout=0,
                 priority=ofproto.OFP_DEFAULT_PRIORITY,
                 buffer_id=0xffffffff, out_port=ofproto.OFPP_NONE,
                 flags=0, rule=None, actions=None):

        # the argument, rule, is positioned at the one before the last due
        # to the layout struct nxt_flow_mod.
        # Although rule must be given, default argument to rule, None,
        # is given to allow other default value of argument before rule.
        assert rule is not None

        if actions is None:
            actions = []
        super(NXTFlowMod, self).__init__(datapath, ofproto.NXT_FLOW_MOD)
        self.cookie = cookie
        self.command = command
        self.idle_timeout = idle_timeout
        self.hard_timeout = hard_timeout
        self.priority = priority
        self.buffer_id = buffer_id
        self.out_port = out_port
        self.flags = flags
        self.rule = rule
        self.actions = actions

    def _serialize_body(self):
        self.serialize_header()

        offset = ofproto.NX_FLOW_MOD_SIZE
        match_len = nx_match.serialize_nxm_match(self.rule, self.buf, offset)
        offset += nx_match.round_up(match_len)

        msg_pack_into(ofproto.NX_FLOW_MOD_PACK_STR,
                      self.buf, ofproto.NICIRA_HEADER_SIZE,
                      self.cookie, self.command, self.idle_timeout,
                      self.hard_timeout, self.priority, self.buffer_id,
                      self.out_port, self.flags, match_len)

        if self.actions is not None:
            for a in self.actions:
                a.serialize(self.buf, offset)
                offset += a.len


class NXTRoleRequest(NiciraHeader):
    def __init__(self, datapath, role):
        super(NXTRoleRequest, self).__init__(
            datapath, ofproto.NXT_ROLE_REQUEST)
        self.role = role

    def _serialize_body(self):
        self.serialize_header()
        msg_pack_into(ofproto.NX_ROLE_PACK_STR,
                      self.buf, ofproto.NICIRA_HEADER_SIZE, self.role)


@NiciraHeader.register_nx_subtype(ofproto.NXT_ROLE_REPLY)
class NXTRoleReply(NiciraHeader):
    def __init__(self, datapath, role):
        super(NXTRoleReply, self).__init__(
            datapath, ofproto.NXT_ROLE_REPLY)
        self.role = role

    @classmethod
    def parser(cls, datapath, buf, offset):
        (role,) = struct.unpack_from(
            ofproto.NX_ROLE_PACK_STR, buf, offset)
        return cls(datapath, role)


class NXTFlowModTableId(NiciraHeader):
    def __init__(self, datapath, set_):
        super(NXTFlowModTableId, self).__init__(
            datapath, ofproto.NXT_FLOW_MOD_TABLE_ID)
        self.set = set_

    def _serialize_body(self):
        self.serialize_header()
        msg_pack_into(ofproto.NX_FLOW_MOD_TABLE_ID_PACK_STR,
                      self.buf, ofproto.NICIRA_HEADER_SIZE,
                      self.set)


@NiciraHeader.register_nx_subtype(ofproto.NXT_FLOW_REMOVED)
class NXTFlowRemoved(NiciraHeader):
    def __init__(self, datapath, cookie, priority, reason,
                 duration_sec, duration_nsec, idle_timeout, match_len,
                 packet_count, byte_count, match):
        super(NXTFlowRemoved, self).__init__(
            datapath, ofproto.NXT_FLOW_REMOVED)
        self.cookie = cookie
        self.priority = priority
        self.reason = reason
        self.duration_sec = duration_sec
        self.duration_nsec = duration_nsec
        self.idle_timeout = idle_timeout
        self.match_len = match_len
        self.packet_count = packet_count
        self.byte_count = byte_count
        self.match = match

    @classmethod
    def parser(cls, datapath, buf, offset):
        (cookie, priority, reason, duration_sec, duration_nsec,
         idle_timeout, match_len,
         packet_count, byte_count) = struct.unpack_from(
            ofproto.NX_FLOW_REMOVED_PACK_STR, buf, offset)
        offset += (ofproto.NX_FLOW_REMOVED_SIZE
                   - ofproto.NICIRA_HEADER_SIZE)
        match = nx_match.NXMatch.parser(buf, offset, match_len)
        return cls(datapath, cookie, priority, reason, duration_sec,
                   duration_nsec, idle_timeout, match_len, packet_count,
                   byte_count, match)


class NXTSetPacketInFormat(NiciraHeader):
    def __init__(self, datapath, packet_in_format):
        super(NXTSetPacketInFormat, self).__init__(
            datapath, ofproto.NXT_SET_PACKET_IN_FORMAT)
        self.format = packet_in_format

    def _serialize_body(self):
        self.serialize_header()
        msg_pack_into(ofproto.NX_SET_PACKET_IN_FORMAT_PACK_STR,
                      self.buf, ofproto.NICIRA_HEADER_SIZE,
                      self.format)


@NiciraHeader.register_nx_subtype(ofproto.NXT_PACKET_IN)
class NXTPacketIn(NiciraHeader):
    def __init__(self, datapath, buffer_id, total_len, reason, table_id,
                 cookie, match_len, match, frame):
        super(NXTPacketIn, self).__init__(
            datapath, ofproto.NXT_PACKET_IN)
        self.buffer_id = buffer_id
        self.total_len = total_len
        self.reason = reason
        self.table_id = table_id
        self.cookie = cookie
        self.match_len = match_len
        self.match = match
        self.frame = frame

    @classmethod
    def parser(cls, datapath, buf, offset):
        (buffer_id, total_len, reason, table_id,
         cookie, match_len) = struct.unpack_from(
            ofproto.NX_PACKET_IN_PACK_STR, buf, offset)

        offset += (ofproto.NX_PACKET_IN_SIZE
                   - ofproto.NICIRA_HEADER_SIZE)

        match = nx_match.NXMatch.parser(buf, offset, match_len)
        offset += (match_len + 7) / 8 * 8
        frame = buf[offset:]
        if total_len < len(frame):
            frame = frame[:total_len]
        return cls(datapath, buffer_id, total_len, reason, table_id,
                   cookie, match_len, match, frame)


class NXTFlowAge(NiciraHeader):
    def __init__(self, datapath):
        super(NXTFlowAge, self).__init__(
            datapath, ofproto.NXT_FLOW_AGE)

    def _serialize_body(self):
        self.serialize_header()


class NXTSetAsyncConfig(NiciraHeader):
    def __init__(self, datapath, packet_in_mask, port_status_mask,
                 flow_removed_mask):
        super(NXTSetAsyncConfig, self).__init__(
            datapath, ofproto.NXT_SET_ASYNC_CONFIG)
        self.packet_in_mask = packet_in_mask
        self.port_status_mask = port_status_mask
        self.flow_removed_mask = flow_removed_mask

    def _serialize_body(self):
        self.serialize_header()
        msg_pack_into(ofproto.NX_ASYNC_CONFIG_PACK_STR,
                      self.buf, ofproto.NICIRA_HEADER_SIZE,
                      self.packet_in_mask[0], self.packet_in_mask[1],
                      self.port_status_mask[0], self.port_status_mask[1],
                      self.flow_removed_mask[0], self.flow_removed_mask[1])


class NXTSetControllerId(NiciraHeader):
    def __init__(self, datapath, controller_id):
        super(NXTSetControllerId, self).__init__(
            datapath, ofproto.NXT_SET_CONTROLLER_ID)
        self.controller_id = controller_id

    def _serialize_body(self):
        self.serialize_header()
        msg_pack_into(ofproto.NX_CONTROLLER_ID_PACK_STR,
                      self.buf, ofproto.NICIRA_HEADER_SIZE,
                      self.controller_id)


#
# asymmetric message (datapath -> controller)
# parser only
#


@_register_parser
@_set_msg_type(ofproto.OFPT_FEATURES_REPLY)
class OFPSwitchFeatures(MsgBase):
    def __init__(self, datapath, datapath_id=None, n_buffers=None,
                 n_tables=None, capabilities=None, actions=None, ports=None):
        super(OFPSwitchFeatures, self).__init__(datapath)
        self.datapath_id = datapath_id
        self.n_buffers = n_buffers
        self.n_tables = n_tables
        self.capabilities = capabilities
        self.actions = actions
        self.ports = ports

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        msg = super(OFPSwitchFeatures, cls).parser(datapath, version, msg_type,
                                                   msg_len, xid, buf)
        (msg.datapath_id,
         msg.n_buffers,
         msg.n_tables,
         msg.capabilities,
         msg.actions) = struct.unpack_from(
            ofproto.OFP_SWITCH_FEATURES_PACK_STR, msg.buf,
            ofproto.OFP_HEADER_SIZE)

        msg.ports = {}
        n_ports = ((msg_len - ofproto.OFP_SWITCH_FEATURES_SIZE) /
                   ofproto.OFP_PHY_PORT_SIZE)
        offset = ofproto.OFP_SWITCH_FEATURES_SIZE
        for _i in range(n_ports):
            port = OFPPhyPort.parser(msg.buf, offset)
            # print 'port = %s' % str(port)
            msg.ports[port.port_no] = port
            offset += ofproto.OFP_PHY_PORT_SIZE

        return msg


@_register_parser
@_set_msg_type(ofproto.OFPT_PORT_STATUS)
class OFPPortStatus(MsgBase):
    def __init__(self, datapath, reason=None, desc=None):
        super(OFPPortStatus, self).__init__(datapath)
        self.reason = reason
        self.desc = desc

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        msg = super(OFPPortStatus, cls).parser(datapath, version, msg_type,
                                               msg_len, xid, buf)
        msg.reason = struct.unpack_from(
            ofproto.OFP_PORT_STATUS_PACK_STR,
            msg.buf, ofproto.OFP_HEADER_SIZE)[0]
        msg.desc = OFPPhyPort.parser(msg.buf,
                                     ofproto.OFP_PORT_STATUS_DESC_OFFSET)
        return msg


@_register_parser
@_set_msg_type(ofproto.OFPT_PACKET_IN)
class OFPPacketIn(MsgBase):
    def __init__(self, datapath, buffer_id=None, total_len=None, in_port=None,
                 reason=None, data=None):
        super(OFPPacketIn, self).__init__(datapath)
        self.buffer_id = buffer_id
        self.total_len = total_len
        self.in_port = in_port
        self.reason = reason
        self.data = data

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        msg = super(OFPPacketIn, cls).parser(datapath, version, msg_type,
                                             msg_len, xid, buf)
        (msg.buffer_id,
         msg.total_len,
         msg.in_port,
         msg.reason) = struct.unpack_from(
            ofproto.OFP_PACKET_IN_PACK_STR,
            msg.buf, ofproto.OFP_HEADER_SIZE)
        msg.data = msg.buf[ofproto.OFP_PACKET_IN_SIZE:]
        if msg.total_len < len(msg.data):
            # discard padding for 8-byte alignment of OFP packet
            msg.data = msg.data[:msg.total_len]
        return msg


@_register_parser
@_set_msg_type(ofproto.OFPT_GET_CONFIG_REPLY)
class OFPGetConfigReply(MsgBase):
    def __init__(self, datapath):
        super(OFPGetConfigReply, self).__init__(datapath)

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        msg = super(OFPGetConfigReply, cls).parser(datapath, version, msg_type,
                                                   msg_len, xid, buf)
        (msg.flags, msg.miss_send_len) = struct.unpack_from(
            ofproto.OFP_SWITCH_CONFIG_PACK_STR,
            msg.buf, ofproto.OFP_HEADER_SIZE)
        return msg


@_register_parser
@_set_msg_type(ofproto.OFPT_BARRIER_REPLY)
class OFPBarrierReply(MsgBase):
    def __init__(self, datapath):
        super(OFPBarrierReply, self).__init__(datapath)


@_register_parser
@_set_msg_type(ofproto.OFPT_FLOW_REMOVED)
class OFPFlowRemoved(MsgBase):
    def __init__(self, datapath):
        super(OFPFlowRemoved, self).__init__(datapath)

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        msg = super(OFPFlowRemoved, cls).parser(datapath, version, msg_type,
                                                msg_len, xid, buf)

        msg.match = OFPMatch.parse(msg.buf, ofproto.OFP_HEADER_SIZE)

        (msg.cookie,
         msg.priority,
         msg.reason,
         msg.duration_sec,
         msg.duration_nsec,
         msg.idle_timeout,
         msg.packet_count,
         msg.byte_count) = struct.unpack_from(
            ofproto.OFP_FLOW_REMOVED_PACK_STR0, msg.buf,
            ofproto.OFP_HEADER_SIZE + ofproto.OFP_MATCH_SIZE)

        return msg


@_register_parser
@_set_msg_type(ofproto.OFPT_QUEUE_GET_CONFIG_REPLY)
class OFPQueueGetConfigReply(MsgBase):
    def __init__(self, datapath):
        super(OFPQueueGetConfigReply, self).__init__(datapath)

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        msg = super(OFPQueueGetConfigReply, cls).parser(
            datapath, version, msg_type, msg_len, xid, buf)

        offset = ofproto.OFP_HEADER_SIZE
        (msg.port,) = struct.unpack_from(
            ofproto.OFP_QUEUE_GET_CONFIG_REPLY_PACK_STR, msg.buf, offset)

        msg.queues = []
        offset = ofproto.OFP_QUEUE_GET_CONFIG_REPLY_SIZE
        while offset + ofproto.OFP_PACKET_QUEUE_SIZE <= msg_len:
            queue = OFPPacketQueue.parser(msg.buf, offset)
            msg.queues.append(queue)

            offset += queue.len

        return msg


def _set_stats_type(stats_type, stats_body_cls):
    def _set_cls_stats_type(cls):
        cls.cls_stats_type = stats_type
        cls.cls_stats_body_cls = stats_body_cls
        return cls
    return _set_cls_stats_type


@_register_parser
@_set_msg_type(ofproto.OFPT_STATS_REPLY)
class OFPStatsReply(MsgBase):
    _STATS_MSG_TYPES = {}

    @staticmethod
    def register_stats_type(body_single_struct=False):
        def _register_stats_type(cls):
            assert cls.cls_stats_type is not None
            assert cls.cls_stats_type not in OFPStatsReply._STATS_MSG_TYPES
            assert cls.cls_stats_body_cls is not None
            cls.cls_body_single_struct = body_single_struct
            OFPStatsReply._STATS_MSG_TYPES[cls.cls_stats_type] = cls
            return cls
        return _register_stats_type

    def __init__(self, datapath):
        super(OFPStatsReply, self).__init__(datapath)
        self.type = None
        self.flags = None
        self.body = None

    @classmethod
    def parser_stats_body(cls, buf, msg_len, offset):
        body_cls = cls.cls_stats_body_cls
        body = []
        while offset < msg_len:
            entry = body_cls.parser(buf, offset)
            body.append(entry)
            offset += entry.length

        if cls.cls_body_single_struct:
            return body[0]
        return body

    @classmethod
    def parser_stats(cls, datapath, version, msg_type, msg_len, xid, buf):
        # call MsgBase::parser, not OFPStatsReply::parser
        msg = MsgBase.parser.__func__(
            cls, datapath, version, msg_type, msg_len, xid, buf)
        msg.body = msg.parser_stats_body(msg.buf, msg.msg_len,
                                         ofproto.OFP_STATS_MSG_SIZE)
        return msg

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf):
        type_, flags = struct.unpack_from(ofproto.OFP_STATS_MSG_PACK_STR,
                                          buffer(buf),
                                          ofproto.OFP_HEADER_SIZE)
        stats_type_cls = cls._STATS_MSG_TYPES.get(type_)
        msg = stats_type_cls.parser_stats(
            datapath, version, msg_type, msg_len, xid, buf)
        msg.type = type_
        msg.flags = flags
        return msg


@OFPStatsReply.register_stats_type(body_single_struct=True)
@_set_stats_type(ofproto.OFPST_DESC, OFPDescStats)
@_set_msg_type(ofproto.OFPT_STATS_REPLY)
class OFPDescStatsReply(OFPStatsReply):
    def __init__(self, datapath):
        super(OFPDescStatsReply, self).__init__(datapath)


@OFPStatsReply.register_stats_type()
@_set_stats_type(ofproto.OFPST_FLOW, OFPFlowStats)
@_set_msg_type(ofproto.OFPT_STATS_REPLY)
class OFPFlowStatsReply(OFPStatsReply):
    def __init__(self, datapath):
        super(OFPFlowStatsReply, self).__init__(datapath)


@OFPStatsReply.register_stats_type()
@_set_stats_type(ofproto.OFPST_AGGREGATE, OFPAggregateStats)
@_set_msg_type(ofproto.OFPT_STATS_REPLY)
class OFPAggregateStatsReply(OFPStatsReply):
    def __init__(self, datapath):
        super(OFPAggregateStatsReply, self).__init__(datapath)


@OFPStatsReply.register_stats_type()
@_set_stats_type(ofproto.OFPST_TABLE, OFPTableStats)
@_set_msg_type(ofproto.OFPT_STATS_REPLY)
class OFPTableStatsReply(OFPStatsReply):
    def __init__(self, datapath):
        super(OFPTableStatsReply, self).__init__(datapath)


@OFPStatsReply.register_stats_type()
@_set_stats_type(ofproto.OFPST_PORT, OFPPortStats)
@_set_msg_type(ofproto.OFPT_STATS_REPLY)
class OFPPortStatsReply(OFPStatsReply):
    def __init__(self, datapath):
        super(OFPPortStatsReply, self).__init__(datapath)


@OFPStatsReply.register_stats_type()
@_set_stats_type(ofproto.OFPST_QUEUE, OFPQueueStats)
@_set_msg_type(ofproto.OFPT_STATS_REPLY)
class OFPQueueStatsReply(OFPStatsReply):
    def __init__(self, datapath):
        super(OFPQueueStatsReply, self).__init__(datapath)


@OFPStatsReply.register_stats_type()
@_set_stats_type(ofproto.OFPST_VENDOR, OFPVendorStats)
@_set_msg_type(ofproto.OFPT_STATS_REPLY)
class OFPVendorStatsReply(OFPStatsReply):
    _STATS_VENDORS = {}

    @staticmethod
    def register_stats_vendor(vendor):
        def _register_stats_vendor(cls):
            cls.cls_vendor = vendor
            OFPVendorStatsReply._STATS_VENDORS[cls.cls_vendor] = cls
            return cls
        return _register_stats_vendor

    def __init__(self, datapath):
        super(OFPVendorStatsReply, self).__init__(datapath)

    @classmethod
    def parser_stats(cls, datapath, version, msg_type, msg_len, xid,
                     buf):
        (type_,) = struct.unpack_from(
            ofproto.OFP_VENDOR_STATS_MSG_PACK_STR, buffer(buf),
            ofproto.OFP_STATS_MSG_SIZE)

        cls_ = cls._STATS_VENDORS.get(type_)

        if cls_ is None:
            msg = MsgBase.parser.__func__(
                cls, datapath, version, msg_type, msg_len, xid, buf)
            body_cls = cls.cls_stats_body_cls
            body = body_cls.parser(buf,
                                   ofproto.OFP_STATS_MSG_SIZE)
            msg.body = body
            return msg

        return cls_.parser(
            datapath, version, msg_type, msg_len, xid, buf,
            ofproto.OFP_VENDOR_STATS_MSG_SIZE)


@OFPVendorStatsReply.register_stats_vendor(ofproto_common.NX_EXPERIMENTER_ID)
class NXStatsReply(OFPStatsReply):
    _NX_STATS_TYPES = {}

    @staticmethod
    def register_nx_stats_type(body_single_struct=False):
        def _register_nx_stats_type(cls):
            assert cls.cls_stats_type is not None
            assert cls.cls_stats_type not in \
                NXStatsReply._NX_STATS_TYPES
            assert cls.cls_stats_body_cls is not None
            cls.cls_body_single_struct = body_single_struct
            NXStatsReply._NX_STATS_TYPES[cls.cls_stats_type] = cls
            return cls
        return _register_nx_stats_type

    @classmethod
    def parser_stats_body(cls, buf, msg_len, offset):
        body_cls = cls.cls_stats_body_cls
        body = []
        while offset < msg_len:
            entry = body_cls.parser(buf, offset)
            body.append(entry)
            offset += entry.length

        if cls.cls_body_single_struct:
            return body[0]
        return body

    @classmethod
    def parser_stats(cls, datapath, version, msg_type, msg_len, xid,
                     buf, offset):
        msg = MsgBase.parser.__func__(
            cls, datapath, version, msg_type, msg_len, xid, buf)
        msg.body = msg.parser_stats_body(msg.buf, msg.msg_len, offset)

        return msg

    @classmethod
    def parser(cls, datapath, version, msg_type, msg_len, xid, buf,
               offset):
        (type_,) = struct.unpack_from(
            ofproto.NX_STATS_MSG_PACK_STR, buffer(buf), offset)
        offset += ofproto.NX_STATS_MSG0_SIZE

        cls_ = cls._NX_STATS_TYPES.get(type_)

        msg = cls_.parser_stats(
            datapath, version, msg_type, msg_len, xid, buf, offset)

        return msg


@NXStatsReply.register_nx_stats_type()
@_set_stats_type(ofproto.NXST_FLOW, NXFlowStats)
class NXFlowStatsReply(NXStatsReply):
    def __init__(self, datapath):
        super(NXFlowStatsReply, self).__init__(datapath)


@NXStatsReply.register_nx_stats_type()
@_set_stats_type(ofproto.NXST_AGGREGATE, NXAggregateStats)
class NXAggregateStatsReply(NXStatsReply):
    def __init__(self, datapath):
        super(NXAggregateStatsReply, self).__init__(datapath)


#
# controller-to-switch message
# serializer only
#


@_set_msg_reply(OFPSwitchFeatures)
@_set_msg_type(ofproto.OFPT_FEATURES_REQUEST)
class OFPFeaturesRequest(MsgBase):
    def __init__(self, datapath):
        super(OFPFeaturesRequest, self).__init__(datapath)


@_set_msg_type(ofproto.OFPT_GET_CONFIG_REQUEST)
class OFPGetConfigRequest(MsgBase):
    def __init__(self, datapath):
        super(OFPGetConfigRequest, self).__init__(datapath)


@_set_msg_type(ofproto.OFPT_SET_CONFIG)
class OFPSetConfig(MsgBase):
    def __init__(self, datapath, flags=None, miss_send_len=None):
        super(OFPSetConfig, self).__init__(datapath)
        self.flags = flags
        self.miss_send_len = miss_send_len

    def _serialize_body(self):
        assert self.flags is not None
        assert self.miss_send_len is not None
        msg_pack_into(ofproto.OFP_SWITCH_CONFIG_PACK_STR,
                      self.buf, ofproto.OFP_HEADER_SIZE,
                      self.flags, self.miss_send_len)


@_set_msg_type(ofproto.OFPT_PACKET_OUT)
class OFPPacketOut(MsgBase):
    def __init__(self, datapath, buffer_id=None, in_port=None, actions=None,
                 data=None):
        super(OFPPacketOut, self).__init__(datapath)
        self.buffer_id = buffer_id
        self.in_port = in_port
        self._actions_len = None
        self.actions = actions
        self.data = data

    def _serialize_body(self):
        assert self.buffer_id is not None
        assert self.in_port is not None
        assert self.actions is not None

        self._actions_len = 0
        offset = ofproto.OFP_PACKET_OUT_SIZE
        for a in self.actions:
            a.serialize(self.buf, offset)
            offset += a.len
            self._actions_len += a.len

        if self.data is not None:
            assert self.buffer_id == 0xffffffff
            self.buf += self.data

        msg_pack_into(ofproto.OFP_PACKET_OUT_PACK_STR,
                      self.buf, ofproto.OFP_HEADER_SIZE,
                      self.buffer_id, self.in_port, self._actions_len)


@_set_msg_type(ofproto.OFPT_FLOW_MOD)
class OFPFlowMod(MsgBase):
    def __init__(self, datapath, match, cookie, command,
                 idle_timeout=0, hard_timeout=0,
                 priority=ofproto.OFP_DEFAULT_PRIORITY,
                 buffer_id=0xffffffff, out_port=ofproto.OFPP_NONE,
                 flags=0, actions=None):
        if actions is None:
            actions = []
        super(OFPFlowMod, self).__init__(datapath)
        self.match = match
        self.cookie = cookie
        self.command = command
        self.idle_timeout = idle_timeout
        self.hard_timeout = hard_timeout
        self.priority = priority
        self.buffer_id = buffer_id
        self.out_port = out_port
        self.flags = flags
        self.actions = actions

    def _serialize_body(self):
        offset = ofproto.OFP_HEADER_SIZE
        self.match.serialize(self.buf, offset)

        offset += ofproto.OFP_MATCH_SIZE
        msg_pack_into(ofproto.OFP_FLOW_MOD_PACK_STR0, self.buf, offset,
                      self.cookie, self.command,
                      self.idle_timeout, self.hard_timeout,
                      self.priority, self.buffer_id, self.out_port,
                      self.flags)

        offset = ofproto.OFP_FLOW_MOD_SIZE
        if self.actions is not None:
            for a in self.actions:
                a.serialize(self.buf, offset)
                offset += a.len


@_set_msg_type(ofproto.OFPT_PORT_MOD)
class OFPPortMod(MsgBase):

    _TYPE = {
        'ascii': [
            'hw_addr',
        ]
    }

    def __init__(self, datapath, port_no=0, hw_addr='00:00:00:00:00:00',
                 config=0, mask=0, advertise=0):
        super(OFPPortMod, self).__init__(datapath)
        self.port_no = port_no
        self.hw_addr = hw_addr
        self.config = config
        self.mask = mask
        self.advertise = advertise

    def _serialize_body(self):
        msg_pack_into(ofproto.OFP_PORT_MOD_PACK_STR,
                      self.buf, ofproto.OFP_HEADER_SIZE,
                      self.port_no, addrconv.mac.text_to_bin(self.hw_addr),
                      self.config, self.mask, self.advertise)


@_set_msg_reply(OFPBarrierReply)
@_set_msg_type(ofproto.OFPT_BARRIER_REQUEST)
class OFPBarrierRequest(MsgBase):
    def __init__(self, datapath):
        super(OFPBarrierRequest, self).__init__(datapath)


@_set_msg_reply(OFPQueueGetConfigReply)
@_set_msg_type(ofproto.OFPT_QUEUE_GET_CONFIG_REQUEST)
class OFPQueueGetConfigRequest(MsgBase):
    def __init__(self, datapath, port):
        super(OFPQueueGetConfigRequest, self).__init__(datapath)
        self.port = port

    def _serialize_body(self):
        msg_pack_into(ofproto.OFP_QUEUE_GET_CONFIG_REQUEST_PACK_STR,
                      self.buf, ofproto.OFP_HEADER_SIZE, self.port)


class OFPStatsRequest(MsgBase):
    def __init__(self, datapath, flags):
        assert flags == 0       # none yet defined

        super(OFPStatsRequest, self).__init__(datapath)
        self.type = self.__class__.cls_stats_type
        self.flags = flags

    def _serialize_stats_body(self):
        pass

    def _serialize_body(self):
        msg_pack_into(ofproto.OFP_STATS_MSG_PACK_STR,
                      self.buf, ofproto.OFP_HEADER_SIZE,
                      self.type, self.flags)
        self._serialize_stats_body()


@_set_msg_reply(OFPDescStatsReply)
@_set_stats_type(ofproto.OFPST_DESC, OFPDescStats)
@_set_msg_type(ofproto.OFPT_STATS_REQUEST)
class OFPDescStatsRequest(OFPStatsRequest):
    def __init__(self, datapath, flags):
        super(OFPDescStatsRequest, self).__init__(datapath, flags)


class OFPFlowStatsRequestBase(OFPStatsRequest):
    def __init__(self, datapath, flags, match, table_id, out_port):
        super(OFPFlowStatsRequestBase, self).__init__(datapath, flags)
        self.match = match
        self.table_id = table_id
        self.out_port = out_port

    def _serialize_stats_body(self):
        offset = ofproto.OFP_STATS_MSG_SIZE
        self.match.serialize(self.buf, offset)

        offset += ofproto.OFP_MATCH_SIZE
        msg_pack_into(ofproto.OFP_FLOW_STATS_REQUEST_ID_PORT_STR,
                      self.buf, offset, self.table_id, self.out_port)


@_set_msg_reply(OFPFlowStatsReply)
@_set_stats_type(ofproto.OFPST_FLOW, OFPFlowStats)
@_set_msg_type(ofproto.OFPT_STATS_REQUEST)
class OFPFlowStatsRequest(OFPFlowStatsRequestBase):
    def __init__(self, datapath, flags, match, table_id, out_port):
        super(OFPFlowStatsRequest, self).__init__(
            datapath, flags, match, table_id, out_port)


@_set_msg_reply(OFPAggregateStatsReply)
@_set_stats_type(ofproto.OFPST_AGGREGATE, OFPAggregateStats)
@_set_msg_type(ofproto.OFPT_STATS_REQUEST)
class OFPAggregateStatsRequest(OFPFlowStatsRequestBase):
    def __init__(self, datapath, flags, match, table_id, out_port):
        super(OFPAggregateStatsRequest, self).__init__(
            datapath, flags, match, table_id, out_port)


@_set_msg_reply(OFPTableStatsReply)
@_set_stats_type(ofproto.OFPST_TABLE, OFPTableStats)
@_set_msg_type(ofproto.OFPT_STATS_REQUEST)
class OFPTableStatsRequest(OFPStatsRequest):
    def __init__(self, datapath, flags):
        super(OFPTableStatsRequest, self).__init__(datapath, flags)


@_set_msg_reply(OFPPortStatsReply)
@_set_stats_type(ofproto.OFPST_PORT, OFPPortStats)
@_set_msg_type(ofproto.OFPT_STATS_REQUEST)
class OFPPortStatsRequest(OFPStatsRequest):
    def __init__(self, datapath, flags, port_no):
        super(OFPPortStatsRequest, self).__init__(datapath, flags)
        self.port_no = port_no

    def _serialize_stats_body(self):
        msg_pack_into(ofproto.OFP_PORT_STATS_REQUEST_PACK_STR,
                      self.buf, ofproto.OFP_STATS_MSG_SIZE, self.port_no)


@_set_msg_reply(OFPQueueStatsReply)
@_set_stats_type(ofproto.OFPST_QUEUE, OFPQueueStats)
@_set_msg_type(ofproto.OFPT_STATS_REQUEST)
class OFPQueueStatsRequest(OFPStatsRequest):
    def __init__(self, datapath, flags, port_no, queue_id):
        super(OFPQueueStatsRequest, self).__init__(datapath, flags)
        self.port_no = port_no
        self.queue_id = queue_id

    def _serialize_stats_body(self):
        msg_pack_into(ofproto.OFP_QUEUE_STATS_REQUEST_PACK_STR,
                      self.buf, ofproto.OFP_STATS_MSG_SIZE,
                      self.port_no, self.queue_id)


@_set_msg_reply(OFPVendorStatsReply)
@_set_stats_type(ofproto.OFPST_VENDOR, OFPVendorStats)
@_set_msg_type(ofproto.OFPT_STATS_REQUEST)
class OFPVendorStatsRequest(OFPStatsRequest):
    def __init__(self, datapath, flags, vendor, specific_data=None):
        super(OFPVendorStatsRequest, self).__init__(datapath, flags)
        self.vendor = vendor
        self.specific_data = specific_data

    def _serialize_vendor_stats(self):
        self.buf += self.specific_data

    def _serialize_stats_body(self):
        msg_pack_into(ofproto.OFP_VENDOR_STATS_MSG_PACK_STR,
                      self.buf, ofproto.OFP_STATS_MSG_SIZE,
                      self.vendor)
        self._serialize_vendor_stats()


class NXStatsRequest(OFPVendorStatsRequest):
    def __init__(self, datapath, flags, subtype):
        super(NXStatsRequest, self).__init__(datapath, flags,
                                             ofproto_common.NX_EXPERIMENTER_ID)
        self.subtype = subtype

    def _serialize_vendor_stats_body(self):
        pass

    def _serialize_vendor_stats(self):
        msg_pack_into(ofproto.NX_STATS_MSG_PACK_STR, self.buf,
                      ofproto.OFP_VENDOR_STATS_MSG_SIZE,
                      self.subtype)
        self._serialize_vendor_stats_body()


class NXFlowStatsRequest(NXStatsRequest):
    def __init__(self, datapath, flags, out_port, table_id, rule=None):
        super(NXFlowStatsRequest, self).__init__(datapath, flags,
                                                 ofproto.NXST_FLOW)
        self.out_port = out_port
        self.table_id = table_id
        self.rule = rule
        self.match_len = 0

    def _serialize_vendor_stats_body(self):
        if self.rule is not None:
            offset = ofproto.NX_STATS_MSG_SIZE + \
                ofproto.NX_FLOW_STATS_REQUEST_SIZE
            self.match_len = nx_match.serialize_nxm_match(
                self.rule, self.buf, offset)

        msg_pack_into(
            ofproto.NX_FLOW_STATS_REQUEST_PACK_STR,
            self.buf, ofproto.NX_STATS_MSG_SIZE, self.out_port,
            self.match_len, self.table_id)


class NXAggregateStatsRequest(NXStatsRequest):
    def __init__(self, datapath, flags, out_port, table_id, rule=None):
        super(NXAggregateStatsRequest, self).__init__(
            datapath, flags, ofproto.NXST_AGGREGATE)
        self.out_port = out_port
        self.table_id = table_id
        self.rule = rule
        self.match_len = 0

    def _serialize_vendor_stats_body(self):
        if self.rule is not None:
            offset = ofproto.NX_STATS_MSG_SIZE + \
                ofproto.NX_AGGREGATE_STATS_REQUEST_SIZE
            self.match_len = nx_match.serialize_nxm_match(
                self.rule, self.buf, offset)

        msg_pack_into(
            ofproto.NX_AGGREGATE_STATS_REQUEST_PACK_STR,
            self.buf, ofproto.NX_STATS_MSG_SIZE, self.out_port,
            self.match_len, self.table_id)
