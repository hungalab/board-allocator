from __future__ import annotations
import argparse
import os.path

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt

#----------------------------------------------------------------------------------------
def parser():
    parser = argparse.ArgumentParser(description='board allocator')
    parser.add_argument('arg', help='communication file')

    args = parser.parse_args()

    if not os.path.isfile(args.arg):
        raise FileNotFoundError("{0:s} was not found.".format(args.t))
    
    return args.arg

class _Flow:
    def __init__(self, flow_id, src, dst):
        self.flow_id = flow_id
        self.src = src
        self.dst_set = {dst}
    
    def add(self, flow_id, src, dst):
        assert self.flow_id == flow_id
        assert self.src == src
        self.dst_set.add(dst)

if __name__ == '__main__':
    comm_file = parser()
    comm_tmp = np.loadtxt(comm_file, dtype='int').tolist()

    flow_dict: dict[_Flow] = dict()

    for comm in comm_tmp:
        try:
            f:_Flow = flow_dict[comm[2]]
        except KeyError:
            flow_dict[comm[2]] = _Flow(comm[2], comm[0], comm[1])
        else:
            f.add(comm[2], comm[0], comm[1])
    
    edges = [(i, j) for i, fi in flow_dict.items() for j, fj in flow_dict.items() if i < j and ((fi.src == fj.src) or (fi.dst_set & fj.dst_set != set()))]
    graph = nx.Graph()
    graph.add_edges_from(edges)

    print("flow duplication degree: {}".format(nx.graph_clique_number(graph)))
    #plt.figure(figsize=(8.7, 5.87))
    #nx.draw(graph, labels={i:i for i in graph})
    #plt.show()

