from __future__ import annotations
import csv
import os
import os.path
import sys
sys.path.append(os.pardir)
import random
from functools import partial
from itertools import combinations
import networkx as nx
import matplotlib
matplotlib.use('GTK3Agg')
import matplotlib.pyplot as plt
import numpy as np
from board_allocator import BoardAllocator

TOPO_NUM = 30
NODE_NUM = 64
MAX_DEGREE = 4
SCRIPT_DIR_NAME = os.path.dirname(__file__)
MULTI_UNICAST_DIR = os.path.join(SCRIPT_DIR_NAME, 'multiple_unicast')
BROADCAST_DIR = os.path.join(SCRIPT_DIR_NAME,'broadcast')

topologies: list[nx.Graph] = list()

for i in range(TOPO_NUM):
    # make topology file
    g = nx.Graph()
    g.add_node(0)
    max_edge_num = random.randint(NODE_NUM - 1, 2 * NODE_NUM)
    loops = 0
    while True:
        # nodes whose degree is less than MAX_DEGREE
        candidates = [v for v in g.nodes if g.degree(v) < MAX_DEGREE]

        # screwed situation
        if (len(candidates) == 0) \
           or ((len(g.nodes) == NODE_NUM) and ((len(candidates) < 2) or all([g.has_edge(*e) for e in combinations(candidates, 2)]))):
            g = nx.Graph()
            g.add_node(0)
            if (loops == 100):
                max_edge_num = random.randint(NODE_NUM - 1, 2 * NODE_NUM)
                loops = 0
            else:
                loops += 1
            continue

        # add node or add edge
        if ((len(candidates) <= 2) and (len(g.nodes) != NODE_NUM)) \
           or ((len(g.nodes) * (len(g.nodes) - 1) / 2) == len(g.edges)) \
           or all([g.has_edge(*e) for e in combinations(candidates, 2)]) \
           or random.randrange((max_edge_num - len(g.edges))) < (NODE_NUM - len(g.nodes)):
            # add node
            node_id = max(g.nodes) + 1
            connect = random.choice(candidates)
            g.add_edge(connect, node_id)
        else:
            # add egde
            while True:
                edge = random.sample(candidates, 2)
                if (not g.has_edge(*edge)):
                    break
            g.add_edge(*edge)
        
        # if all nodes and edges are allocated
        if (NODE_NUM == len(g.nodes) and max_edge_num == len(g.edges)):
            if any(map(partial(nx.is_isomorphic, g), topologies)):
                g = nx.Graph()
                g.add_node(0)
                if (loops == 100):
                    max_edge_num = random.randint(NODE_NUM - 1, 2 * NODE_NUM)
                    loops = 0
                else:
                    loops += 1
            else:
                topo_list = [[vi, sorted(g[vi]).index(vj) + 1, vj, sorted(g[vj]).index(vi) + 1]
                             for vi in g.nodes
                             for vj in g[vi]
                             if vi < vj]
                topo_filename = os.path.join(SCRIPT_DIR_NAME, 'topo{0}.txt'.format(i))
                with open(topo_filename, 'w') as f:
                    writer = csv.writer(f, delimiter=' ')
                    writer.writerows(topo_list)
                topologies.append(g)
                break

for i, g in enumerate(topologies):
    print("=== topology No. {} ===".format(i))
    print("max degree: {}".format(max([d[1] for d in g.degree])))
    print("# of edges: {}".format(len(g.edges)))
    topo_tmp = np.loadtxt('topo{0}.txt'.format(i), dtype='int').tolist()
    cg = nx.Graph()
    for v0, _, v1, _ in topo_tmp:
        cg.add_edge(v0, v1)
    if not nx.is_isomorphic(g, cg):
        print("invalid!")
