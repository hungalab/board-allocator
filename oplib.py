from __future__ import annotations
import random
import copy
from typing import Optional
import networkx as nx

from allocatorunit import AllocatorUnit, Pair, Flow
from cpp_modules import crossings_for_a_flow

#----------------------------------------------------------------------------------------
def generate_initial_solution(au: AllocatorUnit, _ = None) -> AllocatorUnit:
    # copy au
    au = copy.deepcopy(au)

    # allocate rNodes
    for vNode in au.allocating_vNode_list:
        if vNode.rNode_id is None:
            au.random_node_allocation(vNode.vNode_id)
    
    # slot allocation
    au.greedy_slot_allocation()

    return au

#----------------------------------------------------------------------------------------
def initialize_by_assist(au: AllocatorUnit, _ = None) -> AllocatorUnit:
    for vNode in au.allocating_vNode_list:
        assert vNode.rNode_id is None
    for pair in au.allocating_pair_list:
        assert pair.path is None

    au = copy.deepcopy(au)

    # node allocation
    for vNode in au.allocating_vNode_list:
        au.random_node_allocation(vNode.vNode_id, False)
    
    # make a list of pairs with their flow_id
    pairs = [(pair, flow.flow_id) 
             for flow in au.flow_dict.values() if flow.allocating
             for pair in flow.pair_list]
    
    # sort by the number of hops
    def pair_hops(item: tuple[Pair, int]) -> int:
        src = item[0].src_vNode.rNode_id
        dst = item[0].dst_vNode.rNode_id
        return len(au.st_path_table[src][dst][0])
    pairs.sort(key=pair_hops)

    # reconstruct flow graphs
    for flow in au.flow_dict.values():
        if flow.allocating:
            flow.make_flow_graph(None_acceptance=True)

    for pair, flow_id in pairs:
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id

        # calculate score for each path
        result = dict()
        for path in au.st_path_table[src][dst]:
            au.pair_allocation(pair.pair_id, path)
            au.flow_dict[flow_id].make_flow_graph(True)
            fg = au.flow_dict[flow_id].flow_graph
            #score = len({f.cvid for i, f in au.flow_dict.items()
            #             if (fg.edges & f.flow_graph.edges != set())
            #             and (i != flow_id)})
            flows = [(f.cvid, f.flow_graph.edges) for f in au.flow_dict.values()]
            score = crossings_for_a_flow((flow_id, fg.edges), flows)
            result[path] = (score, fg.number_of_edges())

        # select the best path
        best_score = min(result.values(), key=lambda item: item[0])[0]
        best = {path: score for path, score in result.items() if score[0] == best_score}
        best_score = min(best.values(), key=lambda item: item[1])[1]
        best = [path for path, score in best.items() if score[1] == best_score]
        path = random.choice(best)

        # apply the best path
        au.pair_allocation(pair.pair_id, path)
        au.flow_dict[flow_id].make_flow_graph(True)
    
    # slot allocation
    au.greedy_slot_allocation()
    
    return au

#----------------------------------------------------------------------------------------
def update_all_paths_of_a_random_node(au: AllocatorUnit) -> AllocatorUnit:
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

    # slot allocation
    au.greedy_slot_allocation()

    return au

#----------------------------------------------------------------------------------------
def node_swap(au: AllocatorUnit, 
              target_vNode_id: Optional[int] = None
              ) -> AllocatorUnit: 
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

    # slot allocation
    au.greedy_slot_allocation()

    return au

#----------------------------------------------------------------------------------------
def break_and_repair(au: AllocatorUnit, 
                     target_num: int, 
                     target: str='node'
                     ) -> AllocatorUnit:
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
    
    # slot allocation
    au.greedy_slot_allocation()
    
    return au

#----------------------------------------------------------------------------------------
def break_a_maximal_clique_and_repair(au: AllocatorUnit) -> AllocatorUnit:
    au = copy.deepcopy(au)

    # find maximal cliques (size >= 2)
    maximals = [c for c in au.find_maximal_cliques_of_slot_graph() if len(c) > 1]

    # select one of maximal cliques
    #for i in range(len(node_set)):
    #    print("{}-clieque: {}".format(i, len([c for c in maximals if len(c) == i])))

    #size2maximals = {size: [c for c in maximals if len(c) == size] 
    #                  for size in range(len(node_set))}
    #maximals = list()
    #unditected = set(node_set)
    #for size in range(len(node_set)):
    #    maximals += size2maximals[size]
    #    detected = set().union(*size2maximals[size])
    #    unditected -= detected
    #    if unditected == set():
    #        break
    selected = random.choice(maximals)

    # make a list of pairs with their flow_id and sort it by # of hops
    break_pairs = [(pair, cvid) 
                   for cvid in selected if not Flow.is_encrypted_cvid(cvid)
                   for pair in au.flow_dict[cvid].pair_list]
    break_pairs.sort(key=lambda item: len(item[0].path))

    # pair deallocation
    for pair, _ in break_pairs:
        au.pair_deallocation(pair.pair_id)
    
    # reconstruct selected nodes' flow graphs
    for cvid in selected:
        if not Flow.is_encrypted_cvid(cvid):
            au.flow_dict[cvid].make_flow_graph(None_acceptance=True)
    
    print(len(break_pairs))
    lolololo = 0
    for pair, flow_id in break_pairs:
        print(lolololo)
        lolololo += 1
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id
        result = dict()

        # calculate score for each path
        for path in au.st_path_table[src][dst]:
            au.pair_allocation(pair.pair_id, path)
            au.flow_dict[flow_id].make_flow_graph(None_acceptance=True)
            fg = au.flow_dict[flow_id].flow_graph
            score = len({f.cvid for i, f in au.flow_dict.items()
                         if (fg.edges & f.flow_graph.edges != set())
                         and (i != flow_id)})
            result[path] = (score, fg.number_of_edges())
        
        # select the best path
        best_score = min(result.values(), key=lambda item: item[0])[0]
        best = {path: score for path, score in result.items() if score[0] == best_score}
        best_score = min(best.values(), key=lambda item: item[1])[1]
        best = [path for path, score in best.items() if score[1] == best_score]
        path = random.choice(best)

        # apply the best path
        au.pair_allocation(pair.pair_id, path)
        au.flow_dict[flow_id].make_flow_graph(True)
    
    # slot allocation
    au.greedy_slot_allocation()
    
    return au

#----------------------------------------------------------------------------------------
def break_and_repair2(au: AllocatorUnit) -> AllocatorUnit:
    au = copy.deepcopy(au)

    selected_flow = random.choice([flow for flow in au.flow_dict.values() if flow.allocating])

    # make a list of pairs with their flow_id and sort it by # of hops
    pairs = random.sample(selected_flow.pair_list, len(selected_flow.pair_list))
    random.shuffle(pairs)
    def pair_hops(pair: Pair) -> int:
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id
        return len(au.st_path_table[src][dst][0])
    pairs.sort(key=pair_hops)

    # pair deallocation
    for pair in pairs:
        au.pair_deallocation(pair.pair_id)
    
    # reconstruct selected nodes' flow graphs
    selected_flow.make_flow_graph(None_acceptance=True)
    
    for pair in pairs:
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id
        result = dict()

        # calculate score for each path
        for path in au.st_path_table[src][dst]:
            au.pair_allocation(pair.pair_id, path)
            selected_flow.make_flow_graph(None_acceptance=True)
            fg = selected_flow.flow_graph
            score = len({f.cvid for i, f in au.flow_dict.items()
                         if (fg.edges & f.flow_graph.edges != set())
                         and (i != selected_flow.flow_id)})
            result[path] = (score, fg.number_of_edges())
        
        # select the best path
        best_score = min(result.values(), key=lambda item: item[0])[0]
        best = {path: score for path, score in result.items() if score[0] == best_score}
        best_score = min(best.values(), key=lambda item: item[1])[1]
        best = [path for path, score in best.items() if score[1] == best_score]
        path = random.choice(best)

        # apply the best path
        au.pair_allocation(pair.pair_id, path)
        selected_flow.make_flow_graph(True)
    
    # slot allocation
    au.greedy_slot_allocation()
    
    return au

#----------------------------------------------------------------------------------------
def initialize_by_avg_slot_assist(au: AllocatorUnit, _ = None) -> AllocatorUnit:
    for vNode in au.allocating_vNode_list:
        assert vNode.rNode_id is None
    for pair in au.allocating_pair_list:
        assert pair.path is None

    au = copy.deepcopy(au)

    # node allocation
    for vNode in au.allocating_vNode_list:
        au.random_node_allocation(vNode.vNode_id, with_pair_allocation=False)
    
    # make a list of pairs with their flow_id
    pairs = au.allocating_pair_list

    # sorted by hop count
    random.shuffle(pairs)
    def pair_hops(pair: Pair) -> int:
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id
        return len(au.st_path_table[src][dst][0])
    pairs.sort(key=pair_hops)
    
    for pair in pairs:
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id
        result = dict()

        # calculate score for each path
        for path in au.st_path_table[src][dst]:
            au.pair_allocation(pair.pair_id, path)
            au.greedy_slot_allocation(True)
            score = au.get_avg_slot_num()
            result[path] = (score, pair.owner.flow_graph.number_of_edges())
        
        # select the best path
        best_score = min(result.values(), key=lambda item: item[0])[0]
        best = {path: score for path, score in result.items() if score[0] == best_score}
        best_score = min(best.values(), key=lambda item: item[1])[1]
        best = [path for path, score in best.items() if score[1] == best_score]
        path = random.choice(best)

        # apply the best path
        au.pair_allocation(pair.pair_id, path)
    
    # slot allocation
    au.greedy_slot_allocation()
    
    return au

#----------------------------------------------------------------------------------------
def break_nodes_and_repair(au: AllocatorUnit) -> AllocatorUnit:
    au = copy.deepcopy(au)

    # select vNodes to be broken
    selected_vNodes = random.sample(au.allocating_vNode_list, random.randint(1, len(au.allocating_vNode_list)))

    # node deallocation
    for vNode in selected_vNodes:
        au.node_deallocation(vNode.vNode_id)

    # make a list of broken pairs
    broken_pairs = {pair.pair_id
                   for vNode in selected_vNodes
                   for pair in au.vNode_dict[vNode.vNode_id].pair_list}
    broken_pairs = [au.pair_dict[pair_id] for pair_id in broken_pairs]
    
    # pair deallocation
    for pair in broken_pairs:
        au.pair_deallocation(pair.pair_id)
    
    # randomly node allocation
    for vNode in selected_vNodes:
        au.random_node_allocation(vNode.vNode_id, with_pair_allocation=False)

    # sorted by hop count
    random.shuffle(broken_pairs)
    def pair_hops(pair: Pair) -> int:
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id
        return len(au.st_path_table[src][dst][0])
    broken_pairs.sort(key=pair_hops)
    
    for pair in broken_pairs:
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id
        result = dict()

        # calculate score for each path
        for path in au.st_path_table[src][dst]:
            au.pair_allocation(pair.pair_id, path)
            au.greedy_slot_allocation(True)
            score = au.get_avg_slot_num()
            result[path] = (score, pair.owner.flow_graph.number_of_edges())
        
        # select the best path
        best_score = min(result.values(), key=lambda item: item[0])[0]
        best = {path: score for path, score in result.items() if score[0] == best_score}
        best_score = min(best.values(), key=lambda item: item[1])[1]
        best = [path for path, score in best.items() if score[1] == best_score]
        path = random.choice(best)

        # apply the best path
        au.pair_allocation(pair.pair_id, path)
    
    # slot allocation
    au.greedy_slot_allocation()
    
    return au