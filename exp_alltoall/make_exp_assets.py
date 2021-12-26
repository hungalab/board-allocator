import csv
import os
import os.path
import sys
sys.path.append(os.pardir)
import networkx as nx
import matplotlib
matplotlib.use('GTK3Agg')
import matplotlib.pyplot as plt
from board_allocator import BoardAllocator

SIZES = [3, 4, 5, 6, 7, 8]
SCRIPT_DIR_NAME = os.path.dirname(__file__)
MULTI_UNICAST_DIR = os.path.join(SCRIPT_DIR_NAME, 'multiple_unicast')
BROADCAST_DIR = os.path.join(SCRIPT_DIR_NAME,'broadcast')

# make directories
if not os.path.isdir(MULTI_UNICAST_DIR):
    os.mkdir(MULTI_UNICAST_DIR)
if not os.path.isdir(BROADCAST_DIR):
    os.mkdir(BROADCAST_DIR)

for N in SIZES:
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
    ucomm_filename = os.path.join(MULTI_UNICAST_DIR, 'comm{0}x{0}.txt'.format(N))
    bcomm_filename = os.path.join(BROADCAST_DIR, 'comm{0}x{0}.txt'.format(N))
    ucomm_list = list()
    bcomm_list = list()
    flow_id = 0
    for src in range(N * N):
        for dst in range(N * N):
            if src != dst:
                ucomm_list.append([src, dst, flow_id])
                bcomm_list.append([src, dst, src])
                flow_id += 1
    with open(ucomm_filename, 'w') as f:
        writer = csv.writer(f, delimiter=' ')
        writer.writerows(ucomm_list)
    with open(bcomm_filename, 'w') as f:
        writer = csv.writer(f, delimiter=' ')
        writer.writerows(bcomm_list)
