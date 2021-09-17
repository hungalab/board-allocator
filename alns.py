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
import random
import pickle

import networkx as nx

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode

#--------------------------------------------------------------
def random_pair_allocation(au, pair_id):
    # pick up src and dst rNode_id
    pair = au.pair_dict[pair_id]
    src = au.vNode_dict[pair.src_vNode_id].rNode_id
    dst = au.vNode_dict[pair.dst_vNode_id].rNode_id

    # pick up a path
    path = random.choice(au.st_path_table[src][dst])
    pair.path = path

    # update injection attributes
    exist_flow_set = {au.pair_dict[exist_pair_id].flow_id \
                      for exist_pair_id in au.topology.nodes[src]['injection_pairs']}
    if pair.flow_id not in exist_flow_set:
        au.topology.nodes[src]['injection_slot_num'] += 1
    au.topology.nodes[src]['injection_pairs'].add(pair.pair_id)

    # update edge attributes
    source = path[0]
    for i in range(len(path) - 1):
        target = path[i + 1]
        exist_flow_set = {au.pair_dict[exist_pair_id].flow_id \
                          for exist_pair_id in au.topology.edges[source, target]['pairs']}
        if pair.flow_id not in exist_flow_set:
            au.topology.edges[source, target]['slot_num'] += 1
        au.topology.edges[source, target]['pairs'].add(pair.pair_id)
        source = target

#--------------------------------------------------------------
def pair_deallocation(au, pair_id):
    # modify the correspond pair and abstract the path
    pair = au.pair_dict[pair_id]
    path = pair.path
    pair.path = None

    # update injection attributes
    source = path[0]
    au.topology.nodes[source]['injection_pairs'].remove(pair.pair_id)
    rest_flow_set = {au.pair_dict[rest_pair_id].flow_id \
                     for rest_pair_id in au.topology.nodes[source]['injection_pairs']}
    if pair.flow_id not in rest_flow_set:
        au.topology.nodes[source]['injection_slot_num'] -= 1
    
    # update edge attributes
    for i in range(len(path) - 1):
        target = path[i + 1]
        au.topology.edges[source, target]['pairs'].remove(pair.pair_id)
        rest_flow_set = {au.pair_dict[rest_pair_id].flow_id \
                         for rest_pair_id in au.topology.edges[source, target]['pairs']}
        if pair.flow_id not in rest_flow_set:
            au.topology.edges[source, target]['slot_num'] -= 1
        source =target

#--------------------------------------------------------------
def random_node_allocation(au, vNode_id):
    # pick up an empty rNove
    map_rNode_id = random.choice(au.empty_rNode_list)
    au.empty_rNode_list.remove(map_rNode_id)

    # temporary node allocation
    vNode = au.vNode_dict[vNode_id]
    au.temp_allocated_rNode_dict[map_rNode_id] = vNode.vNode_id
    vNode.rNode_id = map_rNode_id

    # temporary send-path allocation (if dst node is not allocated, the operation is not executed)
    for send_pair_id in vNode.send_pair_id_list:
        if au.vNode_dict[au.pair_dict[send_pair_id].dst_vNode_id].rNode_id != None:
            random_pair_allocation(au, send_pair_id)
    
    # temporary recv-path allocation (if src node is not allocated, the operation is not executed)
    for recv_pair_id in vNode.recv_pair_id_list:
        if au.vNode_dict[au.pair_dict[recv_pair_id].src_vNode_id].rNode_id != None:
            random_pair_allocation(au, recv_pair_id)

#--------------------------------------------------------------
def node_allocation(au, vNode_id, rNode_id):
    # pick up an empty rNove
    map_rNode_id = rNode_id
    au.empty_rNode_list.remove(map_rNode_id)

    # temporary node allocation
    vNode = au.vNode_dict[vNode_id]
    au.temp_allocated_rNode_dict[map_rNode_id] = vNode.vNode_id
    vNode.rNode_id = map_rNode_id

    # temporary send-path allocation (if dst node is not allocated, the operation is not executed)
    for send_pair_id in vNode.send_pair_id_list:
        if au.vNode_dict[au.pair_dict[send_pair_id].dst_vNode_id].rNode_id != None:
            random_pair_allocation(au, send_pair_id)
    
    # temporary recv-path allocation (if src node is not allocated, the operation is not executed)
    for recv_pair_id in vNode.recv_pair_id_list:
        if au.vNode_dict[au.pair_dict[recv_pair_id].src_vNode_id].rNode_id != None:
            random_pair_allocation(au, recv_pair_id)

#--------------------------------------------------------------
def node_deallocation(au, vNode_id):
    # modify the correspond vNode and abstract the rNode_id
    vNode = au.vNode_dict[vNode_id]
    rNode_id = vNode.rNode_id
    vNode.rNode_id = None

    # node deallocation (update the list and dict)
    au.temp_allocated_rNode_dict.pop(rNode_id)
    au.empty_rNode_list.append(rNode_id)

    # send-path deallocation
    for send_pair_id in vNode.send_pair_id_list:
        if au.pair_dict[send_pair_id].path != None:
            pair_deallocation(au, send_pair_id)
    
    # recv-path deallocation
    for recv_pair_id in vNode.recv_pair_id_list:
        if au.pair_dict[recv_pair_id].path != None:
            pair_deallocation(au, recv_pair_id)

#--------------------------------------------------------------
def generate_initial_solution(au):
    # initialize au.empty_rNode_list
    au.empty_rNode_list = list(range(nx.number_of_nodes(au.topology)))
    for vNode_id in au.running_vNode_id_list:
        rNode_id = au.vNode_dict[vNode_id].rNode_id
        if rNode_id != None:
            au.empty_rNode_list.remove(rNode_id)
    
    # allocate rNodes
    for vNode_id in au.allocating_vNode_id_list:
        random_node_allocation(au, vNode_id)

#--------------------------------------------------------------
def update_path(au):
    selected_pair_id = random.choice(au.allocating_pair_id_list)
    pair_deallocation(au, selected_pair_id)
    random_pair_allocation(au, selected_pair_id)

#--------------------------------------------------------------
def node_swap(au):
    # select a temporary allocated rNode_id
    temp_allocated_rNode_list = list(au.temp_allocated_rNode_dict.keys())
    rNode_id0 = random.choice(temp_allocated_rNode_list)

    # select swaped rNode_id
    candidate_list = au.empty_rNode_list + temp_allocated_rNode_list
    rNode_id1 = random.choice(candidate_list)

    # deallocate rNode_id0
    vNode_id0 = au.temp_allocated_rNode_dict[rNode_id0]
    node_deallocation(au, vNode_id0)

    # if rNode_id1 has a vNode, deallocate vNode_id1 and allocate it to rNode_id0
    try:
        vNode_id1 = au.temp_allocated_rNode_dict[rNode_id1]
    except KeyError:
        pass
    else:
        node_deallocation(au, vNode_id1)
        node_allocation(au, vNode_id1, rNode_id0)
    
    # allocate rNode_id0 to rNode_id1
    node_allocation(au, vNode_id0, rNode_id1)

#--------------------------------------------------------------
def alns(au, max_execution_time):
    p_break_path = len(au.allocating_pair_id_list) # probability of executing break_path()
    p_node_swap = len(au.allocating_vNode_id_list) # probability of executing node_swap()
    p_range = p_break_path + p_node_swap # normalization value

    loops = 0
    mid_results = list()

    start_time = time.time()

    # genarate the initial solution
    generate_initial_solution(au)
    best = au.save_au()
    best_slot_num = au.get_slot_num()

    while True:
        loops += 1

        # execute break_path or node_swap
        if random.randrange(p_range) < p_break_path:
            update_path(au)
        else:
            node_swap(au)

        # evaluation
        slot_num = au.get_slot_num()
        if slot_num < best_slot_num:
            best = au.save_au()
            best_slot_num = slot_num
        else:
            au = AllocatorUnit.load_au(obj=best)
        
        mid_results.append(best)
        
        
        # if time is up, break the loop
        if time.time() - start_time >= max_execution_time:
            print("number of loops: {}".format(loops))
            print("number of slots: {}".format(best_slot_num))
            with open('result.pickle', 'wb') as f:
                pickle.dump(mid_results, f, protocol=pickle.HIGHEST_PROTOCOL)
            break
