import json
import sys, traceback
import os
import os.path
import shutil
import numpy as np
import collections
from collections import OrderedDict
import time
import random

import graph_tool.all as gt

#--------------------------------------------------------------
class App:
    def __init__(self, app_id, vNode_id_list, pair_id_list, communicationFile):
        self.app_id = app_id
        self.vNode_id_list = vNode_id_list # list: list of vNode_id of the App
        self.pair_id_list = pair_id_list # list: list of pair_id of the App
        self.communicationFile = communicationFile

#--------------------------------------------------------------
class Pair:
    def __init__(self, pair_id, src, dst, flow_id):
        self.pair_id = pair_id
        self.src_vNode_id = src
        self.dst_vNode_id = dst
        self.flow_id = flow_id
        self.path_id = None # using path list

#--------------------------------------------------------------
class VNode:
    def __init__(self, vNode_id, send_pair_id_list, recv_pair_id_list):
        self.vNode_id = vNode_id # int: virtualized node ID
        self.send_pair_id_list = send_pair_id_list # list: list of pair_id to be sent by this VNode
        self.recv_pair_id_list = recv_pair_id_list # list: list of pair_id to be recieved by this VNode
        self.rNode_id = None # allocated node label (label is defined in topologyFile), if the vNode is not allocated (including tmporary), the value is None

#--------------------------------------------------------------
class AllocatorUnit:
    def __init__(self, topology):
        ## topology
        self.topology = topology # the topology for this allocator
        ## dictionaries (vNode, pair, app)
        self.vNode_dict = dict()
        self.pair_dict = dict()
        self.app_dict = dict()
        ## allocating object lists
        self.allocating_vNode_id_list = list() # 1D list: the list of VNodes' id that are being allocated
        self.allocating_pair_id_list = list() # 1D list: the list of pairs' id that are being allocated
        self.allocating_app_id_list = list() # 1D list: the list of Apps' id that are being allocated
        ## runnning (allocated) object list
        self.running_vNode_id_list = list() # 1D list: the list of VNodes' id that are runnning (allocation is finished)
        self.running_pair_id_list = list() # 1D list: the list of pairs' id that are runnning (allocation is finished)
        self.running_app_id_list = list() # 1D list: the list of Apps' id that are runnning (allocation is finished)
        ## manage the real node
        self.temp_allocated_rNode_dict = dict() # 1D dict: the dict of rNodes' id that is temporary allocated
        self.empty_rNode_list = list() # 1D list: the list of rNodes that is not allocated (not including temp_allocated_rNode_dict)

        # create properties
        self.topology.ep["slot_num"] = self.topology.new_ep("short") # number of slots for each edge
        self.topology.ep["pairs"] = self.topology.new_ep("object") # set of pairs' id for each edge
        for e in self.topology.edges():
            self.topology.ep.slot_num[e] = 0
            self.topology.ep.pairs[e] = set()
        self.topology.vp["injection_slot_num"] = self.topology.new_vp("short") # number of slots for each injection link
        self.topology.vp["injection_pairs"] = self.topology.new_vp("object") # set of pairs' id for each injection link
        for v in self.topology.vertices():
            self.topology.vp.injection_slot_num[v] = 0
            self.topology.vp.injection_pairs[v] = set()
    
    ##---------------------------------------------------------
    def add_app(self, app, vNode_list, pair_list):
        # add app
        self.app_dict[app.app_id] = app
        self.allocating_app_id_list.append(app.app_id)

        # add vNodes
        for vNode in vNode_list:
            self.vNode_dict[vNode.vNode_id] = vNode
            self.allocating_vNode_id_list.append(vNode.vNode_id)
        
        # add pairs
        for pair in pair_list:
            self.pair_dict[pair.pair_id] = pair
            self.allocating_pair_id_list.append(pair.pair_id)

    ##---------------------------------------------------------
    def print_allocating_app(self):
        print(" ##### App ##### ")
        all_app_list = list(self.running_app_list.values()) + list(self.allocating_app_list.values())
        for app in all_app_list:
            print("app_id: {}".format(app.app_id))
            print("vNode_id_list: {}".format([vNode.vNode_id for vNode in app.vNode_list]))
            print("pair_id_list: {}".format([pair.pair_id for pair in app.pair_list]))
            print(" --------------------------------------------------- ")

        print("\n ##### vNode ##### ")
        all_vNode_list = list(self.running_vNode_list.values()) + list(self.allocating_vNode_list.values())
        for vNode in all_vNode_list:
            print("vNode_id: {}".format(vNode.vNode_id))
            print("send_pair_id_list: {}".format([send_pair.pair_id for send_pair in vNode.send_pair_list]))
            print("recv_pair_id_list: {}".format([recv_pair.pair_id for recv_pair in vNode.recv_pair_list]))
            print(" --------------------------------------------------- ")
        
        print("\n ##### Pair ##### ")
        all_pair_list = list(self.running_pair_list.values()) + list(self.allocating_pair_list.values())
        for pair in all_pair_list:
            print("pair_id: {}".format(pair.pair_id))
            print("src: {}".format(pair.src))
            print("dst: {}".format(pair.dst))
            print("flow_id: {}".format(pair.flow_id))
            print(" --------------------------------------------------- ")