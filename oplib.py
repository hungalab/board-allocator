from __future__ import annotations
import random
import copy
from typing import Optional
import networkx as nx

from allocatorunit import AllocatorUnit, Pair

#----------------------------------------------------------------------------------------
def generate_initial_solution(au: AllocatorUnit) -> AllocatorUnit:
    # copy au
    au = copy.deepcopy(au)

    # allocate rNodes
    for vNode in au.allocating_vNode_list:
        if vNode.rNode_id is None:
            au.random_node_allocation(vNode.vNode_id)

    return au

#----------------------------------------------------------------------------------------
def initialize_by_assist(au: AllocatorUnit, _ = None) -> AllocatorUnit:
    for vNode in au.allocating_vNode_list:
        assert vNode.rNode_id is None
    for pair in au.allocating_pair_list:
        assert pair.path is None

    au = copy.deepcopy(au)
    
    # make temporary flow dict
    au.flow_dict_for_slot_allocation_valid = False
    au.set_flow_dict_for_slot_allocation(None_acceptance=True)
    fd = au.flow_dict_for_slot_allocation.copy()

    # node allocation
    for vNode in au.allocating_vNode_list:
        vNode.rNode_id = random.choice(list(au.empty_rNode_set))
    
    # make a list of pairs with their flow_id
    pairs = [(pair, flow.flow_id) 
             for flow in au.flow_dict.values() if flow.slot_id is None 
             for pair in flow.pair_list]
    
    # sort by the number of hops
    def pair_hops(item: tuple[Pair, int]) -> int:
        src = item[0].src_vNode.rNode_id
        dst = item[0].dst_vNode.rNode_id
        return len(au.st_path_table[src][dst][0])
    pairs.sort(key=pair_hops)

    for pair, flow_id in pairs:
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id

        # calculate score for each path
        result = dict()
        for path in au.st_path_table[src][dst]:
            au.pair_allocation(pair.pair_id, path)
            fd[flow_id].make_flow_graph(True)
            fg = fd[flow_id].flow_graph
            score = [(nx.intersection(fg, f.flow_graph).number_of_edges() != 0) 
                      and (i != flow_id) 
                     for i, f in fd.items()].count(True)
            result[path] = (score, fg.number_of_edges())

        # select the best path
        best_score = min(result.values(), key=lambda item: item[0])[0]
        best = {path: score for path, score in result.items() if score[0] == best_score}
        best_score = min(best.values(), key=lambda item: item[1])[1]
        best = [path for path, score in best.items() if score[1] == best_score]
        path = random.choice(best)

        # apply the best path
        au.pair_allocation(pair.pair_id, path)
        fd[flow_id].make_flow_graph(True)
    
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
    
    return au

#----------------------------------------------------------------------------------------
def break_a_maximal_clique_and_repair(au: AllocatorUnit) -> AllocatorUnit:
    au = copy.deepcopy(au)

    # find maximal cliques (size >= 2)
    au.set_flow_dict_for_slot_allocation()
    fd = au.flow_dict_for_slot_allocation.copy()
    universe = [(i, j)
                for i, fi in fd.items()
                for j, fj in fd.items()
                if i < j and 
                nx.intersection(fi.flow_graph, fj.flow_graph).number_of_edges() != 0]
    node_set = set(fd.keys())
    graph = nx.Graph()
    graph.add_nodes_from(node_set)
    graph.add_edges_from(universe)
    maximals = [c for c in nx.find_cliques(graph) if len(c) > 1]

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
    break_pairs = [(pair, flow_id) for flow_id in selected if flow_id >= 0 for pair in fd[flow_id].pair_list]
    break_pairs.sort(key=lambda item: len(item[0].path))

    # pair deallocation
    for pair, _ in break_pairs:
        au.pair_deallocation(pair.pair_id)
    
    # reconstruct fd's flow graphs
    for flow_id in selected:
        fd[flow_id].make_flow_graph(None_acceptance=True)
    
    for pair, flow_id in break_pairs:
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id
        result = dict()

        # calculate score for each path
        for path in au.st_path_table[src][dst]:
            au.pair_allocation(pair.pair_id, path)
            fd[flow_id].make_flow_graph(None_acceptance=True)
            fg = fd[flow_id].flow_graph
            score = [(nx.intersection(fg, f.flow_graph).number_of_edges() != 0) 
                      and (i != flow_id) 
                     for i, f in fd.items()].count(True)
            result[path] = (score, fg.number_of_edges())
        
        # select the best path
        best_score = min(result.values(), key=lambda item: item[0])[0]
        best = {path: score for path, score in result.items() if score[0] == best_score}
        best_score = min(best.values(), key=lambda item: item[1])[1]
        best = [path for path, score in best.items() if score[1] == best_score]
        path = random.choice(best)

        # apply the best path
        au.pair_allocation(pair.pair_id, path)
        fd[flow_id].make_flow_graph(True)
    
    return au