from cpp_modules import crossing_flows, crossings_for_a_flow, slot_allocation

import networkx as nx

flows = [(0, {(0, 1), (0, 2)}), (1, {(0, 1), (1, 2)}), (2, {(1, 2)}), (3, {(0, 1)}), (0, {(1, 2)}), (4, {(3, 4), (0, 1)})]

print("===Checking crossing_flows===")
correct = {(0, 1), (0, 3), (1, 2), (1, 3), (1, 0), (2, 0)}

result = crossing_flows(flows)

if (result == correct):
    print("Successed!")
else:
    print("Failed.")
    print("result: {}, correct: {}".format(result, correct))
print()

print("===Checking crossing_flows===")
index = 1
correct = len({e[0] if e[1] == index else e[1] for e in correct if e[0] == index or e[1] == index})

result = crossings_for_a_flow(flows[index], flows)

if (result == correct):
    print("Successed!")
else:
    print("Failed.")
    print("result: {}, correct: {}".format(result, correct))
print()

print("===Checking slot alllocation===")
edges = crossing_flows(flows)
nodes = {v for f in flows for e in f[1] for v in e}
graph = nx.Graph()
graph.add_nodes_from(nodes)
graph.add_edges_from(edges)
correct = nx.coloring.greedy_color(graph, strategy='largest_first')

result = slot_allocation(flows)
print(result)

if (result == correct):
    print("Successed!")
else:
    print("Failed.")
    print("result: {}, correct: {}".format(result, correct))
print()