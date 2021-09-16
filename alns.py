import argparse
import json
import sys, traceback
import os
import os.path
import shutil
import numpy as np
import collections
from collections import OrderedDict
import time

import networkx as nx

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode

#--------------------------------------------------------------
def random_single_pair_allocation(au, pair_id):
    # pick up src and dst rNode_id
    pair = au.pair_dict[pair_id]
    src = au.vNode_dict[pair.src_vNode_id].rNode_id
    dst = au.vNode_dict[pair.dst_vNode_id].rNode_id

    # pick up a path
    path = random.choice(au.st_path_table[src][dst])

    # update injection properties
    exist_flow_set = {au.pair_dict[exist_pair_id].flow_id for exist_pair_id in au.topology.nodes[src]['injection_pairs']}
    if pair.flow_id not in exist_flow_set:
        au.topology.nodes[src]['injection_slot_num'] += 1
    au.topology.nodes[src]['injection_pairs'].add(pair.pair_id)

    # update edge properties
    source = path[0]
    for i in range(len(path) - 1):
        target = path[i + 1]
        exist_flow_set = {au.pair_dict[exist_pair_id].flow_id for exist_pair_id in au.topology.edges[source, target]['pairs']}
        if pair.flow_id not in exist_flow_set:
            au.topology.edges[source, target]['slot_num'] += 1
        au.topology.edges[source, target]['pairs'].add(pair.pair_id)

#--------------------------------------------------------------
def random_single_node_allocation(au, vNode_id):
    # pick up an empty rNove
    map_rNode_id = random.choice(au.empty_rNode_list)
    au.empty_rNode_list.remove(map_rNode_id)

    # temporary node allocation
    au.temp_allocated_rNode_dict[map_rNode_id] = vNode.vNode_id
    vNode.rNode_id = map_rNode_id

    # temporary send-path allocation (if dst node is not allocated, the operation is not executed)
    for send_pair_id in vNode.send_pair_id_list:
        if au.pair_dict[send_pair_id].dst_vNode.rNode_id != None:
            random_single_pair_allocation(au, send_pair_id)
    
    # temporary recv-path allocation (if src node is not allocated, the operation is not executed)
    for recv_pair_id in vNode.recv_pair_id_list:
        if au.pair_dict[recv_pair_id].src_vNode.rNode_id != None:
            random_single_pair_allocation(au, recv_pair_id)

#--------------------------------------------------------------
def generate_initial_solution(au):
    # initialize au.empty_rNode_list
    au.empty_rNode_list = list(range(nx.number_of_nodes(au.topology)))
    for vNode_id in au.running_vNode_id_list:
        rNode_id = au.vNode_dict[vNode_id].rNode_id
        if rNode_id != None:
            au.empty_rNode_list.remove(rNode_id)
    
    # allocate rNodes
    for vNode_id for au.allocating_vNode_id_list:
        random_single_node_allocation(au, vNode_id)

#--------------------------------------------------------------
def alns(au, max_execution_time):
    p_break_path = len(au.allocating_pair_id_list) # probability of executing break_path()
    p_node_swap = len(au.allocating_vNode_id_list) # probability of executing node_swap()
    p_range = p_break_path # normalization value

    start_time = time.time()

    # genarate the initial solution
    generate_initial_solution()

    while True:
        # execute break_path or node_swap
        if random.randrange(p_range) < p_break_path:
            update_path()
        else:
            #self.node_swap()
            pass
        
        # if time is up, break the loop
        if time.time() - start_time >= max_execution_time:
            break
