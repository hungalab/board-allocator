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
    def __init__(self, app_id, vNode_list, pair_list, communicationFile):
        self.app_id = app_id
        self.vNode_list = vNode_list # list: list of vNode of the App
        self.pair_list = pair_list # list: list of pair of the App
        self.communicationFile = communicationFile

#--------------------------------------------------------------
class Pair:
    def __init__(self, pair_id, src, dst, flow_id):
        self.pair_id = pair_id
        self.src = src
        self.src_vNode = None
        self.dst = dst
        self.dst_vNode = None
        self.flow_id = flow_id
        self.path_id = None # using path list

#--------------------------------------------------------------
class VNode:
    def __init__(self, vNode_id, send_pair_list, recv_pair_list):
        self.vNode_id = vNode_id # int: virtualized node ID
        self.send_pair_list = send_pair_list # list: list of pair to be sent by this VNode
        self.recv_pair_list = recv_pair_list # list: list of pair to be recieved by this VNode
        self.rNode_id = None # allocated node label (label is defined in topologyFile), if the vNode is not allocated (including tmporary), the value is None

#--------------------------------------------------------------
class AllocatorUnit:
    def __init__(self, topology):
        ## topology
        self.topology = topology # the topology for this allocator
        ## allocating object lists
        self.allocating_vNode_list = list() # 1D list: the list of VNodes that are being allocated
        self.allocating_pair_list = list() # 1D list: the list of pairs that are being allocated
        self.allocating_app_list = list() # 1D list: the list of Apps that are being allocated
        ## runnning (allocated) object list
        self.running_vNode_list = list() # 1D list: the list of VNodes that are runnning (allocation is finished)
        self.running_pair_list = list() # 1D list: the list of pairs that are runnning (allocation is finished)
        self.running_app_list = list() # 1D list: the list of Apps that are runnning (allocation is finished)
        ## manage the real node
        self.temp_allocated_rNode_list = list() # 1D list: the list of rNodes that is temporary allocated
        self.empty_rNode_list = list() # 1D list: the list of rNodes that is not allocated (not including temp_allocated_rNode_list)

        # create properties
        self.topology.ep["slot_num"] = self.topology.new_ep("short") # number of slots for each edge
        self.topology.ep["pairs"] = self.topology.new_ep("object") # set of pairs for each edge
        for e in self.topology.edges():
            self.topology.ep.slot_num[e] = 0
            self.topology.ep.pairs[e] = set()
        self.topology.vp["injection_slot_num"] = self.topology.new_vp("short") # number of slots for each injection link
        self.topology.vp["injection_pairs"] = self.topology.new_vp("object") # set of pairs for each injection link
        for v in self.topology.vertices():
            self.topology.vp.injection_slot_num[v] = 0
            self.topology.vp.injection_pairs[v] = set()
    
    ##---------------------------------------------------------
    def add_app(self, app, vNode_list, pair_list):
        self.allocating_app_list.append(app)
        self.allocating_vNode_list += vNode_list
        self.allocating_pair_list += pair_list

    ##---------------------------------------------------------
    def random_single_pair_allocation(self, pair):
        # pick up src and dst rNode_id
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id

        # pick up a path
        path = random.choice(self.st_path_table[src][dst])

        # update injection properties
        exist_flow_set = {exist_pair.flow_id for exist_pair in self.au.topology.vp.injection_pairs[src]}
        if pair.flow_id not in exist_flow_set:
            self.au.topology.vp.injection_slot_num[src] += 1
        self.au.topology.vp.injection_pairs[src].add(pair)

        # update edge properties
        source = path[0]
        for i in range(len(path) - 1):
            target = path[i + 1]
            e = self.au.topology.edge(source, target)
            exist_flow_set = {exist_pair.flow_id for exist_pair in self.au.topology.ep.pairs[e]}
            if pair.flow_id not in exist_flow_set:
                self.au.topology.ep.slot_num[e] += 1
            self.au.topology.ep.pairs[e].add(pair)

    ##---------------------------------------------------------
    def random_single_node_allocation(self, au, vNode):
        # pick up an empty rNove
        map_rNode_id = random.choice(au.empty_rNode_list)
        au.empty_rNode_list.remove(map_rNode_id)

        # temporary node allocation
        au.temp_allocated_rNode_list.append(map_rNode_id)
        vNode.rNode_id = map_rNode_id

        # temporary send-path allocation (if dst node is not allocated, the operation is not executed)
        for send_pair in vNode.send_pair_list:
            if send_pair.dst_vNode.rNode_id != None:
                random_single_pair_allocation(send_pair)
        
        # temporary recv-path allocation (if src node is not allocated, the operation is not executed)
        for recv_pair in vNode.recv_pair_list:
            if recv_pair.src_vNode.rNode_id != None:
                random_single_pair_allocation(recv_pair)

    ##---------------------------------------------------------
    def generate_initial_solution(self):
        # initialize self.au.empty_rNode_list
        self.au.empty_rNode_list = self.au.topology.get_vertices().tolist()

    ##---------------------------------------------------------
    def alns(self, max_execution_time):
        p_break_path = len(self.au.allocating_pair_list) # probability of executing break_path()
        p_node_swap = len(self.au.allocating_vNode_list) # probability of executing node_swap()
        p_range = p_break_path # normalization value

        start_time = time.time()

        # genarate the initial solution
        self.generate_initial_solution()

        while True:
            # execute break_path or node_swap
            if random.randrange(p_range) < p_break_path:
                self.break_path()
            else:
                #self.node_swap()
                pass
            
            # if time is up, break the loop
            if time.time() - start_time >= max_execution_time:
                break
    
    ##---------------------------------------------------------
    def print_allocating_app(self):
        print(" ##### App ##### ")
        all_app_list = self.au.running_app_list + self.allocating_app_list
        for app in all_app_list:
            print("app_id: {}".format(app.app_id))
            print("vNode_id_list: {}".format([vNode.vNode_id for vNode in app.vNode_list]))
            print("pair_id_list: {}".format([pair.pair_id for pair in app.pair_list]))
            print(" --------------------------------------------------- ")

        print("\n ##### vNode ##### ")
        all_vNode_list = self.au.running_vNode_list + self.allocating_vNode_list
        for vNode in all_vNode_list:
            print("vNode_id: {}".format(vNode.vNode_id))
            print("send_pair_id_list: {}".format([send_pair.pair_id for send_pair in vNode.send_pair_list]))
            print("recv_pair_id_list: {}".format([recv_pair.pair_id for recv_pair in vNode.recv_pair_list]))
            print(" --------------------------------------------------- ")
        
        print("\n ##### Pair ##### ")
        all_pair_list = self.au.running_pair_list + self.allocating_pair_list
        for pair in all_pair_list:
            print("pair_id: {}".format(pair.pair_id))
            print("src: {}".format(pair.src))
            print("dst: {}".format(pair.dst))
            print("flow_id: {}".format(pair.flow_id))
            print(" --------------------------------------------------- ")