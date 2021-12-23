import time
import random
import copy
import math

# my library
import oplib
from allocatorunit import AllocatorUnit

#----------------------------------------------------------------------------------------
def sa(au: AllocatorUnit, 
          max_execution_time: float, 
          enable_log: bool = True) -> AllocatorUnit:
    # probability changer
    p_range = 2 # normalization value

    # variables for log
    loops = 0
    cnt_slot_change = 0
    cnt_total_hops_change = 0
    updatelog = list()

    # start timer
    start_time = time.time()
    T = 100.0
    t = T

    # genarate the initial solution
    best = oplib.generate_initial_solution(au)
    best_slot_num = best.get_avg_slot_num()
    best_total_hops = best.get_total_communication_flow_edges()

    while time.time() - start_time < max_execution_time:
        loops += 1

        # execute node_swap
        au = oplib.node_swap(best)

        # evaluation
        slot_num = au.get_avg_slot_num()
        total_hops = au.get_total_communication_flow_edges()
        if slot_num < best_slot_num:
            print("{:>6}th loop: update for slot decrease (slots: {} -> {}, "
                             "hops: {} -> {})".format(loops, best_slot_num, slot_num, 
                                                      best_total_hops, total_hops))
            best = au
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_slot_change += 1
        elif (slot_num == best_slot_num) and (total_hops < best_total_hops):
            print("{:>6}th loop: update for total hops decrease "
                             "(slots: {} -> {}, hops: {} -> {})"
                             .format(loops, best_slot_num, slot_num, 
                                     best_total_hops, total_hops))
            best = au
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_total_hops_change += 1
        elif random.random() < math.exp(-((slot_num - best_slot_num) + abs(total_hops - best_total_hops) * (0.1 ** max(len(str(total_hops)), len(str(best_total_hops)))))/ t):
            print("{:>6}th loop: transition by probability "
                             "(slots: {} -> {}, hops: {} -> {})"
                             .format(loops, best_slot_num, slot_num, 
                                     best_total_hops, total_hops))
            best = au
            best_slot_num = slot_num
            best_total_hops = total_hops

        t = t * 0.99
        if t < 0.000000001:
            print("break by temperature")
            break


    # logs
    if enable_log:
        print("# of loops: {}".format(loops))
        print("# of updates for slot decrease: {}".format(cnt_slot_change))
        print("# of updates for total slot decrease: {}".format(cnt_total_hops_change))
        print("# of slots: {}".format(best.get_max_slot_num()))
        print("# of routed boards: {}".format(best.board_num_to_be_routed()))
        print("allocated rNode_id: {}".format(best.temp_allocated_rNode_dict))
        for elm in updatelog:
            print(elm)

    return best