from __future__ import annotations

from graphillion import GraphSet

#----------------------------------------------------------------------------------------
def mcc(previsous_clique_number: int, 
        rest_nodes: set[int], 
        best_slot_num: int | float = float('inf')):
    #print("{}, {}, {}".format(previsous_clique_number, rest_nodes, best_slot_num))
    answer = None
    tmp_best = best_slot_num

    for k in reversed(range(2, previsous_clique_number + 1)):
        if -(-len(rest_nodes) // k) >= tmp_best:
            break
        degree_constraints = {v: range(0, k, k - 1) if v in rest_nodes else 0 
                              for v in GraphSet._vertices}
        num_edges = k * (k - 1) // 2
        cliques = GraphSet.graphs(degree_constraints=degree_constraints, 
                                  num_edges=num_edges)
        for clique in cliques:
            clique_node_set = set().union(*[set(edge) for edge in clique])
            result = mcc(k, rest_nodes - clique_node_set, tmp_best - 1)
            if result is not None:
                answer = [clique_node_set] + result
                tmp_best = len(result) + 1

    if len(rest_nodes) < tmp_best:
        answer = [{elm} for elm in rest_nodes]

    return answer