from __future__ import annotations

import networkx as nx

#----------------------------------------------------------------------------------------
def mcc(graph: nx.Graph, best_slot_num: int | float = float('inf')) -> list[set[int]]:
    answer = None
    cliques = reversed(list(nx.enumerate_all_cliques(graph)))

    for clique in cliques:
        clique_node_set = set(clique)
        if -(-graph.number_of_nodes() // len(clique_node_set)) >= best_slot_num:
            break
        new_graph: nx.Graph = graph.copy()
        new_graph.remove_nodes_from(clique_node_set)
        result = mcc(new_graph, best_slot_num - 1)
        if result is not None:
            answer = [clique_node_set] + result
            best_slot_num = len(answer)
    
    if graph.number_of_nodes() < best_slot_num:
        answer = [{n} for n in graph.nodes()]

    return answer