import time
import random

import networkx as nx

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode
import oplib

#--------------------------------------------------------------
def node_swap(au):
    # select a temporary allocated rNode_id
    temp_allocated_rNode_list = list(au.temp_allocated_rNode_dict.keys())
    rNode_id0 = random.choice(temp_allocated_rNode_list)

    # select swapped rNode_id
    candidate_list = list(au.empty_rNode_set) + temp_allocated_rNode_list
    rNode_id1 = random.choice(candidate_list)

    # deallocate rNode_id0
    vNode_id0 = au.temp_allocated_rNode_dict[rNode_id0]
    oplib.node_deallocation(au, vNode_id0)

    # if rNode_id1 has a vNode, deallocate vNode_id1 and allocate it to rNode_id0
    try:
        vNode_id1 = au.temp_allocated_rNode_dict[rNode_id1]
    except KeyError:
        pass
    else:
        oplib.node_deallocation(au, vNode_id1)
        oplib.node_allocation(au, vNode_id1, rNode_id0)
    
    # allocate vNode_id0 to rNode_id1
    oplib.node_allocation(au, vNode_id0, rNode_id1)

#--------------------------------------------------------------
def break_and_repair(au, target_node_num):
    # break
    target_vNode_id_list = list()
    for i in range(target_node_num):
        # select a temporary allocated vNode_id to break
        temp_allocated_vNode_list = list(au.temp_allocated_rNode_dict.values())
        vNode_id = random.choice(temp_allocated_vNode_list)

        # deallocate selected vNode_id
        oplib.node_deallocation(au, vNode_id)

        # append selected vNode_id to target_vNode_id_list
        target_vNode_id_list.append(vNode_id)

    # repair
    for vNode_id in target_vNode_id_list:
        oplib.random_node_allocation(au, vNode_id)

#--------------------------------------------------------------
def alns(au, max_execution_time):
    # probability changer
    p_range = min(2, len(au.allocating_vNode_list)) + 1 # normalization value

    loops = 0
    cnt_slot_change = 0
    cnt_total_hops_change = 0
    updatelog = list()

    start_time = time.time()

    # genarate the initial solution
    oplib.generate_initial_solution(au)
    best = au.save_au()
    best_slot_num = au.get_slot_num()
    best_total_hops = au.get_total_communication_hops()

    while time.time() - start_time < max_execution_time:
        loops += 1

        # break and repair
        target_node_num = random.randrange(1, p_range)
        break_and_repair(au, target_node_num)

        # evaluation
        slot_num = au.get_slot_num()
        total_hops = au.get_total_communication_hops()
        if slot_num < best_slot_num:
            updatelog.append("{:>6}th loop: update for slot decrease (slots: {} -> {}, hops: {} -> {})".format(loops, best_slot_num, slot_num, best_total_hops, total_hops))
            best = au.save_au()
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_slot_change += 1
        elif (slot_num == best_slot_num) and (total_hops < best_total_hops):
            updatelog.append("{:>6}th loop: update for total hops decrease (slots: {} -> {}, hops: {} -> {})".format(loops, best_slot_num, slot_num, best_total_hops, total_hops))
            best = au.save_au()
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_total_hops_change += 1
        else:
            au = AllocatorUnit.load_au_from_obj(best)

    # logs
    print("number of loops: {}".format(loops))
    print("number of updates for slot decrease: {}".format(cnt_slot_change))
    print("number of updates for total slot decrease: {}".format(cnt_total_hops_change))
    print("allocated rNode_id: {}".format(au.temp_allocated_rNode_dict))
    for elm in updatelog:
        print(elm)

    return AllocatorUnit.load_au_from_obj(best)

#--------------------------------------------------------------
def alns2(au, max_execution_time):
    # probability changer
    p_range = 2 # normalization value

    # variables for log
    loops = 0
    cnt_slot_change = 0
    cnt_total_hops_change = 0
    updatelog = list()

    # start timer
    start_time = time.time()

    # genarate the initial solution
    oplib.generate_initial_solution(au)
    best = au.save_au()
    best_slot_num = au.get_slot_num()
    best_total_hops = au.get_total_communication_hops()

    while time.time() - start_time < max_execution_time:
        loops += 1

        # execute node_swap
        node_swap(au)

        # evaluation
        slot_num = au.get_slot_num()
        total_hops = au.get_total_communication_hops()
        if slot_num < best_slot_num:
            updatelog.append("{:>6}th loop: update for slot decrease (slots: {} -> {}, hops: {} -> {})".format(loops, best_slot_num, slot_num, best_total_hops, total_hops))
            best = au.save_au()
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_slot_change += 1
        elif (slot_num == best_slot_num) and (total_hops < best_total_hops):
            updatelog.append("{:>6}th loop: update for total hops decrease (slots: {} -> {}, hops: {} -> {})".format(loops, best_slot_num, slot_num, best_total_hops, total_hops))
            best = au.save_au()
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_total_hops_change += 1
        else:
            au = AllocatorUnit.load_au_from_obj(best)

    # logs
    print("number of loops: {}".format(loops))
    print("number of updates for slot decrease: {}".format(cnt_slot_change))
    print("number of updates for total slot decrease: {}".format(cnt_total_hops_change))
    print("allocated rNode_id: {}".format(au.temp_allocated_rNode_dict))
    for elm in updatelog:
        print(elm)

    return AllocatorUnit.load_au_from_obj(best)
