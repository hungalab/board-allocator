import networkx as nx
import pickle

from allocatorunit import AllocatorUnit, App, Pair, VNode, Flow

#--------------------------------------------------------------
if __name__ == '__main__':
    au = AllocatorUnit.load_au_from_file('sample.pickle')
    flows = au.flow_dict

    print("---matrix---")
    mcc_mat = [[1 if nx.number_of_edges(nx.intersection(fi.flow_graph, fj.flow_graph)) == 0 else 0 for fj in flows.values()] for fi in flows.values()]
    cp_mat = [[1 if nx.number_of_edges(nx.intersection(fi.flow_graph, fj.flow_graph)) != 0 else 0 for fj in flows.values()] for fi in flows.values()]
    for i in cp_mat:
        print(i)
    print()


    cp_universe = [(i, j) for i, fi in flows.items() for j, fj in flows.items() if i < j and nx.number_of_edges(nx.intersection(fi.flow_graph, fj.flow_graph)) != 0]
    universe = [(i, j) for i, fi in flows.items() for j, fj in flows.items() if i < j and nx.number_of_edges(nx.intersection(fi.flow_graph, fj.flow_graph)) == 0]
    node_set = set(flows.keys())
    node_num = len(node_set)
    print("# of nodes: {}".format(node_num))
    print("node: {}".format(node_set))
    #print(universe)

    graph = nx.Graph()
    graph.add_nodes_from(node_set)
    graph.add_edges_from(cp_universe)
    coloring = nx.coloring.greedy_color(graph)
    print(coloring)
    print(len(set(coloring.values())))

    #print("\n--- slot allocation---")
    #GraphSet.set_universe(universe)
    #result = mcc(node_num, node_set)
    #print(result)

    print("-- exp ---")
    #result = GraphSet.cliques(2)
    #print(len(result))
    #for i in result:
    #    print(i)
    #print("###")
    #print(setset._obj2int)
    #GraphSet.set_universe([(0, 5), (1, 5), (1, 6), (1, 3), (2, 4), (2, 5), (4, 6), (5, 6), (5, 7)])
    #k = 2
    #degree_constraints = {pickle.dumps(v, protocol=0): (0, k, k - 1) for v in node_set}
    #graph = [(pickle.dumps(e[0], protocol=0), (pickle.dumps(e[1], protocol=0))) for e in universe]
    #print(graph)
    #result0 = _graphillion._graphs(graph=graph, vertex_groups=[], degree_constraints=degree_constraints, num_edges=(k * (k - 1) // 2, k * (k - 1) // 2 + 1, 1), num_comps=-1, no_loop=False, search_space=None, linear_constraints=None)
    #print(len(result0))
    #print(GraphSet(result0))
    #for i in result0:
    #    print(i)
    #print("###")
    #result = result.excluding(1)
    #print(len(result))
    #for i in result:
    #    print(i)
    #for i in reversed(range(2, node_num)):
    #    cliques = GraphSet.cliques(i)
    #    print("# of {}-cliques: {}".format(i, len(cliques)))
    #    for clique in cliques:
    #        clique_node_set = set().union(*[set(edge) for edge in clique])
    #        for k in reversed(range(2, len(clique_node_set) + 1)):
    #            vertex_groups = [[], list(set().union(*[set(edge) for edge in clique]))]
    #            degree_constraints = {v: range(0, k, k - 1) for GraphSet._vertices}
    #            num_edges = k * (k - 1) // 2
    #            GraphSet.graphs(vertex_groups=vertex_groups, degree_constraints=degree_constraints, num_edges=num_edges)