import random
import copy

#--------------------------------------------------------------
def generate_initial_solution(au):
    # copy au
    au = copy.deepcopy(au)

    # allocate rNodes
    for vNode in au.allocating_vNode_list:
        if vNode.rNode_id is None:
            au.random_node_allocation(vNode.vNode_id)

    return au

#--------------------------------------------------------------
def update_all_paths_of_a_random_node(au):
    # copy au
    au = copy.deepcopy(au)

    # select a temporary allocated rNode_id
    temp_allocated_rNode_list = list(au.temp_allocated_rNode_dict.keys())
    rNode_id = random.choice(temp_allocated_rNode_list)

    # deallocate the selected rNode_id
    vNode_id = au.temp_allocated_rNode_dict[rNode_id]
    au.node_deallocation(vNode_id)

    # allocate vNode to rNode_id (replace vNode to same rNode)
    au.node_allocation(vNode_id, rNode_id)

    return au

#--------------------------------------------------------------
def node_swap(au, target_vNode_id=None):
    # copy au
    au = copy.deepcopy(au)

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
    au.node_deallocation(vNode_id0)

    # if rNode_id1 has a vNode, deallocate vNode_id1 and allocate it to rNode_id0
    try:
        vNode_id1 = au.temp_allocated_rNode_dict[rNode_id1]
    except KeyError:
        pass
    else:
        au.node_deallocation(vNode_id1)
        au.node_allocation(vNode_id1, rNode_id0)
    
    # allocate vNode_id0 to rNode_id1
    au.node_allocation(vNode_id0, rNode_id1)

    return au

#--------------------------------------------------------------
def break_and_repair(au, target_num, target='node'):
    # copy au
    au = copy.deepcopy(au)

    if target not in ['node', 'pair']:
        raise ValueError("'{}' is invalid.".format(target))
    
    if not isinstance(target_num, int):
        raise TypeError("The 1st argument \"target_num\" must be 'int'.")
    
    if target_num < 0:
        raise ValueError("The 1st argument \"target_num\" must be a natural number.")
    
    if target == 'node':
        target_num = min(target_num, len(au.allocating_vNode_list))
        target_vNode_list = random.sample(au.allocating_vNode_list, target_num)

        # break
        for vNode in target_vNode_list:
            au.node_deallocation(vNode.vNode_id)

        # repair
        for vNode in target_vNode_list:
            au.random_node_allocation(vNode.vNode_id)

    elif target == 'pair':
        target_num = min(target_num, len(au.allocating_pair_list))
        break_pair_list = random.sample(au.allocating_pair_list, target_num)

        # break
        for pair in break_pair_list:
            au.pair_deallocation(pair.pair_id)
        
        # repair
        for pair in break_pair_list:
            au.random_pair_allocation(pair.pair_id)
    
    return au