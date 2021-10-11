import random

import networkx as nx

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode

#--------------------------------------------------------------
def random_pair_allocation(au, pair_id):
    # pick up src and dst rNode_id
    pair = au.pair_dict[pair_id]
    src = pair.src_vNode.rNode_id
    dst = pair.dst_vNode.rNode_id

    # pick up a path
    path = random.choice(au.st_path_table[src][dst])
    pair.path = path

    # slot_list invalidation
    au.slot_valid = False

#--------------------------------------------------------------
def pair_deallocation(au, pair_id):
    # modify the correspond pair and abstract the path
    pair = au.pair_dict[pair_id]
    path = pair.path
    pair.path = None

    # slot_list invalidation
    au.slot_valid = False

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
    for send_pair in vNode.send_pair_list:
        if send_pair.dst_vNode.rNode_id != None:
            random_pair_allocation(au, send_pair.pair_id)
    
    # temporary recv-path allocation (if src node is not allocated, the operation is not executed)
    for recv_pair in vNode.recv_pair_list:
        if recv_pair.src_vNode.rNode_id != None:
            random_pair_allocation(au, recv_pair.pair_id)

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
    for send_pair in vNode.send_pair_list:
        if send_pair.dst_vNode.rNode_id != None:
            random_pair_allocation(au, send_pair.pair_id)
    
    # temporary recv-path allocation (if src node is not allocated, the operation is not executed)
    for recv_pair in vNode.recv_pair_list:
        if recv_pair.src_vNode.rNode_id != None:
            random_pair_allocation(au, recv_pair.pair_id)

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
    for send_pair in vNode.send_pair_list:
        if send_pair.path != None:
            pair_deallocation(au, send_pair.pair_id)
    
    # recv-path deallocation
    for recv_pair in vNode.recv_pair_list:
        if recv_pair.path != None:
            pair_deallocation(au, recv_pair.pair_id)

#--------------------------------------------------------------
def generate_initial_solution(au):
    # initialize au.empty_rNode_list
    au.empty_rNode_list = list(range(nx.number_of_nodes(au.topology)))
    for vNode in au.running_vNode_list:
        rNode_id = vNode.rNode_id
        if rNode_id != None:
            au.empty_rNode_list.remove(rNode_id)
    
    # allocate rNodes
    for vNode in au.allocating_vNode_list:
        random_node_allocation(au, vNode.vNode_id)

#--------------------------------------------------------------
def random_update_path(au):
    selected_pair = random.choice(au.allocating_pair_list)
    pair_deallocation(au, selected_pair.pair_id)
    random_pair_allocation(au, selected_pair.pair_id)

#--------------------------------------------------------------
def update_all_paths_of_a_random_node(au):
    # select a temporary allocated rNode_id
    temp_allocated_rNode_list = list(au.temp_allocated_rNode_dict.keys())
    rNode_id = random.choice(temp_allocated_rNode_list)

    # deallocate the selected rNode_id
    vNode_id = au.temp_allocated_rNode_dict[rNode_id]
    node_deallocation(au, vNode_id)

    # allocate vNode to rNode_id (replace vNode to same rNode)
    node_allocation(au, vNode_id, rNode_id)