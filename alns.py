import time
import random
import copy

# my library
import oplib
from allocatorunit import AllocatorUnit

#----------------------------------------------------------------------------------------
def alns(au: AllocatorUnit, 
         max_execution_time: float, 
         enable_log: bool = True) -> AllocatorUnit:
    # probability changer
    p_range = min(2, len(au.allocating_vNode_list)) + 1 # normalization value

    loops = 0
    cnt_slot_change = 0
    cnt_total_hops_change = 0
    updatelog = list()

    start_time = time.time()

    # genarate the initial solution
    best = oplib.generate_initial_solution(au)
    best_slot_num = best.get_avg_slot_num()
    best_total_hops = best.get_total_communication_flow_edges()
    print("{:>6}th loop: slots: {}, "
                             "hops: {}".format(loops, best_slot_num, 
                                                      best_total_hops))

    while time.time() - start_time < max_execution_time:
        loops += 1

        # break and repair
        if random.random() < (1 - ((time.time() - start_time) / max_execution_time)):
            target_node_num = random.randrange(1, p_range)
            au = oplib.break_and_repair(best, target_node_num)
        else:
            au = oplib.break_and_repair2(best)

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

#----------------------------------------------------------------------------------------
def alns_only_pairs(au: AllocatorUnit, 
                    max_execution_time: float, 
                    enable_log: bool = True) -> AllocatorUnit:
    # probability changer
    p_range = min(2, len(au.allocating_vNode_list)) + 1 # normalization value

    loops = 0
    cnt_slot_change = 0
    cnt_total_hops_change = 0
    updatelog = list()

    start_time = time.time()

    # genarate the initial solution
    best = oplib.generate_initial_solution(au)
    best_slot_num = best.get_avg_slot_num()
    best_total_hops = best.get_total_communication_flow_edges()

    while time.time() - start_time < max_execution_time:
        loops += 1

        # break and repair
        target_pair_num = random.randrange(1, len(au.allocating_pair_list))
        au = oplib.break_and_repair(best, target_pair_num, target='pair')

        # evaluation
        slot_num = au.get_avg_slot_num()
        total_hops = au.get_total_communication_flow_edges()
        if slot_num < best_slot_num:
            updatelog.append("{:>6}th loop: update for slot decrease (slots: {} -> {}, "
                             "hops: {} -> {})".format(loops, best_slot_num, slot_num, 
                                                      best_total_hops, total_hops))
            best = au
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_slot_change += 1
        elif (slot_num == best_slot_num) and (total_hops < best_total_hops):
            updatelog.append("{:>6}th loop: update for total hops decrease "
                             "(slots: {} -> {}, hops: {} -> {})"
                             .format(loops, best_slot_num, slot_num, 
                                     best_total_hops, total_hops))
            best = au
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_total_hops_change += 1

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

#----------------------------------------------------------------------------------------
def alns2(au: AllocatorUnit, 
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
            updatelog.append("{:>6}th loop: update for slot decrease (slots: {} -> {}, "
                             "hops: {} -> {})".format(loops, best_slot_num, slot_num, 
                                                      best_total_hops, total_hops))
            best = au
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_slot_change += 1
        elif (slot_num == best_slot_num) and (total_hops < best_total_hops):
            updatelog.append("{:>6}th loop: update for total hops decrease "
                             "(slots: {} -> {}, hops: {} -> {})"
                             .format(loops, best_slot_num, slot_num, 
                                     best_total_hops, total_hops))
            best = au
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_total_hops_change += 1

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

#----------------------------------------------------------------------------------------
def alns_test(au: AllocatorUnit, 
          max_execution_time: float, 
          enable_log: bool = True) -> AllocatorUnit:
    # variables for log
    loops = 0
    cnt_slot_change = 0
    cnt_total_hops_change = 0
    updatelog = list()

    # start timer
    start_time = time.time()

    # genarate the initial solution
    if all([pair.path is None for pair in au.allocating_pair_list] 
           + [vNode.rNode_id is None for vNode in au.allocating_vNode_list]):
        best = oplib.initialize_by_assist(au)
    else:
        best = copy.deepcopy(au)
    best_slot_num = best.get_avg_slot_num()
    best_total_hops = best.get_total_communication_flow_edges()
    maximals = best.find_maximal_cliques_of_slot_graph()
    best_clieque_size = len(max(maximals, key=len))
    maximals = [c for c in maximals if len(c) == best_clieque_size]
    best_max_clieque_size_num = len(maximals)
    if enable_log:
        print("# of slots: {}, clique size: {}, # of max clieques: {}, # of edges: {}"
              .format(best_slot_num, best_clieque_size, best_max_clieque_size_num, best_total_hops))

    while time.time() - start_time < max_execution_time:
        loops += 1
        
        # execute node_swap
        au = oplib.break_a_maximal_clique_and_repair(best)
        
        # evaluation
        slot_num = au.get_avg_slot_num()
        total_hops = au.get_total_communication_flow_edges()
        if slot_num < best_slot_num:
            updatelog.append("{:>6}th loop: update for slot decrease (slots: {} -> {}, "
                             "hops: {} -> {})".format(loops, best_slot_num, slot_num, 
                                                      best_total_hops, total_hops))
            best = au
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_slot_change += 1
        elif (slot_num == best_slot_num) and (total_hops < best_total_hops):
            updatelog.append("{:>6}th loop: update for total hops decrease "
                             "(slots: {} -> {}, hops: {} -> {})"
                             .format(loops, best_slot_num, slot_num, 
                                     best_total_hops, total_hops))
            best = au
            best_slot_num = slot_num
            best_total_hops = total_hops
            cnt_total_hops_change += 1

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

#----------------------------------------------------------------------------------------
def alns_test2(au: AllocatorUnit, 
          max_execution_time: float, 
          enable_log: bool = True) -> AllocatorUnit:
    # variables for log
    loops = 0
    cnt_slot_change = 0
    cnt_total_hops_change = 0
    updatelog = list()

    # start timer
    start_time = time.time()

    # genarate the initial solution
    if all([pair.path is None for pair in au.allocating_pair_list] 
           + [vNode.rNode_id is None for vNode in au.allocating_vNode_list]):
        best = oplib.initialize_by_assist(au)
    else:
        best = copy.deepcopy(au)
    best_slot_num = best.get_avg_slot_num()
    best_total_hops = best.get_total_communication_flow_edges()
    maximals = best.find_maximal_cliques_of_slot_graph()
    best_clieque_size = len(max(maximals, key=len))
    maximals = [c for c in maximals if len(c) == best_clieque_size]
    best_max_clieque_size_num = len(maximals)
    if enable_log:
        print("# of slots: {}, clique size: {}, # of max clieques: {}, # of edges: {}"
              .format(best_slot_num, best_clieque_size, best_max_clieque_size_num, best_total_hops))

    while time.time() - start_time < max_execution_time:
        loops += 1
        au = oplib.break_a_maximal_clique_and_repair(best)
        slot_num = au.get_avg_slot_num()
        total_hops = au.get_total_communication_flow_edges()
        #print("# of slots: {}, # of flows' edges: {}".format(slot_num, total_hops))
        maximals = au.find_maximal_cliques_of_slot_graph()
        clieque_size = len(max(maximals, key=len))
        maximals = [c for c in maximals if len(c) == clieque_size]
        max_clieque_size_num = len(maximals)

        if slot_num < best_slot_num:
            best = au
            best_slot_num = slot_num
            best_clieque_size = clieque_size
            best_max_clieque_size_num = max_clieque_size_num
            best_total_hops = total_hops
            if enable_log:
                print("'# of slots: {}', clique size: {}, # of max clieques: {}, # of edges: {}"
                      .format(best_slot_num, best_clieque_size, best_max_clieque_size_num, best_total_hops))
        elif slot_num == best_slot_num and (clieque_size < best_clieque_size):
            best = au
            best_slot_num = slot_num
            best_clieque_size = clieque_size
            best_max_clieque_size_num = max_clieque_size_num
            best_total_hops = total_hops
            if enable_log:
                print("# of slots: {}, 'clique size: {}', # of max clieques: {}, # of edges: {}"
                      .format(best_slot_num, best_clieque_size, best_max_clieque_size_num, best_total_hops))
        elif slot_num == best_slot_num and (clieque_size == best_clieque_size) and (max_clieque_size_num < best_max_clieque_size_num):
            best = au
            best_slot_num = slot_num
            best_clieque_size = clieque_size
            best_max_clieque_size_num = max_clieque_size_num
            best_total_hops = total_hops
            if enable_log:
                print("# of slots: {}, clique size: {}, '# of max clieques: {}', # of edges: {}"
                      .format(best_slot_num, best_clieque_size, best_max_clieque_size_num, best_total_hops))
        elif slot_num == best_slot_num and (clieque_size == best_clieque_size) and (max_clieque_size_num == best_max_clieque_size_num) and (total_hops < best_total_hops):
            best = au
            best_slot_num = slot_num
            best_clieque_size = clieque_size
            best_max_clieque_size_num = max_clieque_size_num
            best_total_hops = total_hops
            if enable_log:
                print("# of slots: {}, clique size: {}, # of max clieques: {}, '# of edges: {}'"
                      .format(best_slot_num, best_clieque_size, best_max_clieque_size_num, best_total_hops))

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

#----------------------------------------------------------------------------------------
def alns_assist(au: AllocatorUnit, 
          max_execution_time: float, 
          enable_log: bool = True) -> AllocatorUnit:
    # variables for log
    loops = 0
    cnt_slot_change = 0
    cnt_total_hops_change = 0
    updatelog = list()

    # start timer
    start_time = time.time()

    # genarate the initial solution
    if all([pair.path is None for pair in au.allocating_pair_list] 
           + [vNode.rNode_id is None for vNode in au.allocating_vNode_list]):
        best = oplib.initialize_by_avg_slot_assist(au)
    else:
        best = copy.deepcopy(au)
    best_slot_num = best.get_avg_slot_num()
    best_total_hops = best.get_total_communication_flow_edges()
    if enable_log:
        print("# of slots: {}, # of edges: {}"
              .format(best_slot_num, best_total_hops))

    while time.time() - start_time < max_execution_time:
        loops += 1
        au = oplib.break_nodes_and_repair(best)
        slot_num = au.get_avg_slot_num()
        total_hops = au.get_total_communication_flow_edges()

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
        
        #loops += 1
        #
        ## execute node_swap
        #au = break_and_repair_a_maximal_clique(best)
        #
        ## evaluation
        #slot_num = au.get_avg_slot_num()
        #total_hops = au.get_total_communication_flow_edges()
        #if slot_num < best_slot_num:
        #    updatelog.append("{:>6}th loop: update for slot decrease (slots: {} -> {}, "
        #                     "hops: {} -> {})".format(loops, best_slot_num, slot_num, 
        #                                              best_total_hops, total_hops))
        #    best = au
        #    best_slot_num = slot_num
        #    best_total_hops = total_hops
        #    cnt_slot_change += 1
        #elif (slot_num == best_slot_num) and (total_hops < best_total_hops):
        #    updatelog.append("{:>6}th loop: update for total hops decrease "
        #                     "(slots: {} -> {}, hops: {} -> {})"
        #                     .format(loops, best_slot_num, slot_num, 
        #                             best_total_hops, total_hops))
        #    best = au
        #    best_slot_num = slot_num
        #    best_total_hops = total_hops
        #    cnt_total_hops_change += 1

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
