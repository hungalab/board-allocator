import csv
import os
import os.path
import sys

from numpy import isin
sys.path.append(os.pardir)
import math
import networkx as nx
import matplotlib
matplotlib.use('GTK3Agg')
import matplotlib.pyplot as plt
from board_allocator import BoardAllocator

SIZES = [4, 8]
SCRIPT_DIR_NAME = os.path.dirname(__file__)

for N in SIZES:
    if not isinstance(N, int):
        raise TypeError("Invalid type")
    if (N <= 2) and (N & (N - 1) != 0):
        raise ValueError("Invalid value: {}".format(N))

    # make topology file
    topo_filename = os.path.join(SCRIPT_DIR_NAME, 'topo{0}x{0}.txt'.format(N))
    topo_list = [[i * N + j, di * 2 + 1, ((i + di) % N) * N + ((j + dj) % N), di * 2 + 2]
                 for i in range(N) 
                 for j in range(N) 
                 for di, dj in [(0, 1), (1, 0)]]
    with open(topo_filename, 'w') as f:
        writer = csv.writer(f, delimiter=' ')
        writer.writerows(topo_list)
    
    # draw topology
    topo_figfile = os.path.join(SCRIPT_DIR_NAME, 'topo{0}x{0}.png'.format(N))
    actor = BoardAllocator(topo_filename, True)
    core_node_num = len(actor.au.core_nodes)
    pos = {i: (-((i % core_node_num) // N) * N - (i // core_node_num), 
               ((i % core_node_num) % N) * N + (i // core_node_num)) 
           for i in actor.au.topology.nodes}
    labels = {i: '' if i < core_node_num else actor.node_index2label[i % core_node_num] for i in actor.au.topology.nodes}
    plt.figure(figsize=(8.7, 5.87))
    nx.draw_networkx(actor.au.topology, pos, labels=labels)
    plt.savefig(topo_figfile)
    plt.close()

    # make communication patterns
    p2p_comm_filename = os.path.join(SCRIPT_DIR_NAME, 'p2p_comm{0}x{0}.txt'.format(N))
    fft_comm_filename = os.path.join(SCRIPT_DIR_NAME, 'fft_comm{0}x{0}.txt'.format(N))
    p2p_comm_list = list()
    fft_comm_list = list()
    for src in range(N * N):
        p2p_comm_list.append([src, src ^ 1, src])
        for i in range(len("{:b}".format(N * N)) - 1):
            fft_comm_list.append([src, src ^ (1 << i), src])
    with open(p2p_comm_filename, 'w') as f:
        writer = csv.writer(f, delimiter=' ')
        writer.writerows(p2p_comm_list)
    with open(fft_comm_filename, 'w') as f:
        writer = csv.writer(f, delimiter=' ')
        writer.writerows(fft_comm_list)