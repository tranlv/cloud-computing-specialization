*****************
Components of Ryu
*****************

Executables
===========

bin/ryu-manager
---------------

The main executable.


Base components
===============

ryu.base.app_manager
--------------------
.. automodule:: ryu.base.app_manager


OpenFlow controller
===================

ryu.controller.controller
-------------------------
.. automodule:: ryu.controller.controller

ryu.controller.dpset
--------------------
.. automodule:: ryu.controller.dpset

ryu.controller.ofp_event
------------------------
.. automodule:: ryu.controller.ofp_event

ryu.controller.ofp_handler
--------------------------
.. automodule:: ryu.controller.ofp_handler


OpenFlow wire protocol encoder and decoder
==========================================

ryu.ofproto.ofproto_v1_0
------------------------
.. automodule:: ryu.ofproto.ofproto_v1_0

ryu.ofproto.ofproto_v1_0_parser
-------------------------------
.. automodule:: ryu.ofproto.ofproto_v1_0_parser

ryu.ofproto.ofproto_v1_2
------------------------
.. automodule:: ryu.ofproto.ofproto_v1_2

ryu.ofproto.ofproto_v1_2_parser
-------------------------------
.. automodule:: ryu.ofproto.ofproto_v1_2_parser

ryu.ofproto.ofproto_v1_3
------------------------
.. automodule:: ryu.ofproto.ofproto_v1_3

ryu.ofproto.ofproto_v1_3_parser
-------------------------------
.. automodule:: ryu.ofproto.ofproto_v1_3_parser

ryu.ofproto.ofproto_v1_4
------------------------
.. automodule:: ryu.ofproto.ofproto_v1_4

ryu.ofproto.ofproto_v1_4_parser
-------------------------------
.. automodule:: ryu.ofproto.ofproto_v1_4_parser


Ryu applications
================

ryu.app.cbench
--------------
.. automodule:: ryu.app.cbench

ryu.app.simple_switch
---------------------
.. automodule:: ryu.app.simple_switch

ryu.app.simple_isolation
------------------------
.. automodule:: ryu.app.simple_isolation

ryu.app.simple_vlan
-------------------
.. automodule:: ryu.app.simple_vlan

ryu.app.gre_tunnel
------------------
.. automodule:: ryu.app.gre_tunnel

ryu.app.tunnel_port_updater
---------------------------
.. automodule:: ryu.app.tunnel_port_updater

ryu.app.quantum_adapter
-----------------------
.. automodule:: ryu.app.quantum_adapter

ryu.app.rest
------------
.. automodule:: ryu.app.rest

ryu.app.rest_conf_switch
------------------------
.. automodule:: ryu.app.rest_conf_switch

ryu.app.rest_quantum
--------------------
.. automodule:: ryu.app.rest_quantum

ryu.app.rest_tunnel
-------------------
.. automodule:: ryu.app.rest_tunnel

ryu.topology
------------
.. automodule:: ryu.topology


Libraries
=========

ryu.lib.packet
--------------
.. automodule:: ryu.lib.packet

ryu.lib.ovs
-----------
.. automodule:: ryu.lib.ovs

ryu.lib.of_config
-----------------
.. automodule:: ryu.lib.of_config

ryu.lib.netconf
---------------
.. automodule:: ryu.lib.netconf

ryu.lib.xflow
-------------
.. automodule:: ryu.lib.xflow


Third party libraries
=====================

ryu.contrib.ovs
---------------

Open vSwitch python binding. Used by ryu.lib.ovs.

ryu.contrib.oslo.config
-----------------------

Oslo configuration library. Used for ryu-manager's command-line options
and configuration files.

ryu.contrib.ncclient
--------------------

Python library for NETCONF client. Used by ryu.lib.of_config.

