import random

import networkx as nx

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
    au.flow_dict_for_slot_allocation_valid = False

    return au

#--------------------------------------------------------------
def pair_allocation(au, pair_id, path):
    # pick up src and dst rNode_id
    pair = au.pair_dict[pair_id]
    src = pair.src_vNode.rNode_id
    dst = pair.dst_vNode.rNode_id

    # update path
    #if path[0] != src or path[-1] != dst:
    #    raise ValueError("Error: The path {} does not match this pair \
    #                        (src: {}, dst: {}).".format(path, src, dst))
    pair.path = path

    # slot_list invalidation
    au.flow_dict_for_slot_allocation_valid = False

    return au

#--------------------------------------------------------------
def pair_deallocation(au, pair_id):
    # modify the correspond pair and abstract the path
    pair = au.pair_dict[pair_id]
    path = pair.path
    pair.path = None

    # slot_list invalidation
    au.flow_dict_for_slot_allocation_valid = False

    return au

#--------------------------------------------------------------
def random_node_allocation(au, vNode_id):
    # pick up an empty rNove
    map_rNode_id = random.choice(list(au.empty_rNode_set))
    au.empty_rNode_set.remove(map_rNode_id)

    # temporary node allocation
    vNode = au.vNode_dict[vNode_id]
    au.temp_allocated_rNode_dict[map_rNode_id] = vNode.vNode_id
    vNode.rNode_id = map_rNode_id

    # temporary send-path allocation (if dst node is not allocated, the operation is not executed)
    for send_pair in vNode.send_pair_list:
        if send_pair.dst_vNode.rNode_id is not None:
            random_pair_allocation(au, send_pair.pair_id)
    
    # temporary recv-path allocation (if src node is not allocated, the operation is not executed)
    for recv_pair in vNode.recv_pair_list:
        if recv_pair.src_vNode.rNode_id is not None:
            random_pair_allocation(au, recv_pair.pair_id)

    return au

#--------------------------------------------------------------
def node_allocation(au, vNode_id, rNode_id):
    # pick up an empty rNove
    map_rNode_id = rNode_id
    au.empty_rNode_set.remove(map_rNode_id)

    # temporary node allocation
    vNode = au.vNode_dict[vNode_id]
    au.temp_allocated_rNode_dict[map_rNode_id] = vNode.vNode_id
    vNode.rNode_id = map_rNode_id

    # temporary send-path allocation (if dst node is not allocated, the operation is not executed)
    for send_pair in vNode.send_pair_list:
        if send_pair.dst_vNode.rNode_id is not None:
            random_pair_allocation(au, send_pair.pair_id)
    
    # temporary recv-path allocation (if src node is not allocated, the operation is not executed)
    for recv_pair in vNode.recv_pair_list:
        if recv_pair.src_vNode.rNode_id is not None:
            random_pair_allocation(au, recv_pair.pair_id)
    
    return au

#--------------------------------------------------------------
def node_deallocation(au, vNode_id):
    # modify the correspond vNode and abstract the rNode_id
    vNode = au.vNode_dict[vNode_id]
    rNode_id = vNode.rNode_id
    vNode.rNode_id = None

    # node deallocation (update the list and dict)
    au.temp_allocated_rNode_dict.pop(rNode_id)
    au.empty_rNode_set.add(rNode_id)

    # send-path deallocation
    for send_pair in vNode.send_pair_list:
        if send_pair.path is not None:
            pair_deallocation(au, send_pair.pair_id)
    
    # recv-path deallocation
    for recv_pair in vNode.recv_pair_list:
        if recv_pair.path is not None:
            pair_deallocation(au, recv_pair.pair_id)
    
    return au

#--------------------------------------------------------------
def generate_initial_solution(au):
    # allocate rNodes
    for vNode in au.allocating_vNode_list:
        if vNode.rNode_id is None:
            random_node_allocation(au, vNode.vNode_id)

    return au

#--------------------------------------------------------------
def random_update_path(au):
    selected_pair = random.choice(au.allocating_pair_list)
    pair_deallocation(au, selected_pair.pair_id)
    random_pair_allocation(au, selected_pair.pair_id)

    return au

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

    return au

#--------------------------------------------------------------
def node_swap(au, target_vNode_id=None):
    # select a temporary allocated rNode_id
    temp_allocated_rNode_list = list(au.temp_allocated_rNode_dict.keys())
    if target_vNode_id is None:
        rNode_id0 = random.choice(temp_allocated_rNode_list)
    else: 
        rNode_id0 = au.vNode_dict[target_vNode_id].rNode_id

    # select swapped rNode_id
    candidate_list = list(au.empty_rNode_set) + temp_allocated_rNode_list
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
    
    # allocate vNode_id0 to rNode_id1
    node_allocation(au, vNode_id0, rNode_id1)

    return au

#--------------------------------------------------------------
def break_and_repair(au, target_num, target='node'):
    if target not in ['node', 'pair']:
        raise ValueError("'{}' is invalid.".format(target))
    
    if (not isinstance(target_num, int)):
        raise TypeError("The 1st argument \"target_num\" must be 'int'.")
    
    if target_num < 0:
        raise ValueError("The 1st argument \"target_num\" must be a natural number.")
    
    if target == 'node':
        # break
        target_vNode_id_list = list()
        for i in range(min(target_num, len(au.temp_allocated_rNode_dict))):
            # select a temporary allocated vNode_id to break
            temp_allocated_vNode_list = list(au.temp_allocated_rNode_dict.values())
            vNode_id = random.choice(temp_allocated_vNode_list)

            # deallocate selected vNode_id
            node_deallocation(au, vNode_id)

            # append selected vNode_id to target_vNode_id_list
            target_vNode_id_list.append(vNode_id)

        # repair
        for vNode_id in target_vNode_id_list:
            random_node_allocation(au, vNode_id)
    elif target == 'pair':
        target_num = min(target_num, len(au.allocating_pair_list))
        break_pair_list = random.sample(au.allocating_pair_list, target_num)
        break_pair_id_list = [pair.pair_id for pair in break_pair_list]

        # break
        for pair_id in break_pair_id_list:
            pair_deallocation(au, pair_id)
        
        # repair
        for pair_id in break_pair_id_list:
            random_pair_allocation(au, pair_id)
    
    return au