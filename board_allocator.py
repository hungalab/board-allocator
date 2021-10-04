import argparse
import json
import sys, traceback
import os
import os.path
import shutil
import numpy as np
import collections
from collections import OrderedDict

import networkx as nx
import matplotlib.pyplot as plt

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode, Flow
import alns

##---------------------------------------------------------
def parser():
    parser = argparse.ArgumentParser(description='board allocator')
    parser.add_argument('-t', help='topology file', default='fic-topo-file-cross.txt')
    parser.add_argument('-c', help='communication partern (traffic file)', required=True)
    parser.add_argument('-s', help='', default=0, type=int)
    parser.add_argument('-m', help='', default=0, type=int)
    parser.add_argument('-ho', help='', default=0, type=int)

    args = parser.parse_args()

    if not os.path.isfile(args.t):
        print("Error: {0:s} was not found.".format(args.t), sys.stderr)
        sys.exit(1)
    
    if not os.path.isfile(args.c):
        print("Error: {0:s} was not found.".format(args.c), sys.stderr)
        sys.exit(2)
    
    if (args.s + args.m + args.ho <= 0):
        print("Error: Total execution time must be greater than 0 second.".format(args.c), sys.stderr)
        sys.exit(3)
    
    return args

#--------------------------------------------------------------
class BoardAllocator:
    def __init__(self, topologyFile):
        # define variable
        ## Allocator Unit
        self.au = None
        ## virtualization of the topology file
        self.node_index2label = {} # dict: (index in self.au.topology) |-> (label in topologyFile)
        self.node_label2index = {} # dict: (label in topologyFile) |-> (index in self.au.topology)
        ## id generators
        self.__vNode_id = 0 # the generator of vNode_id: it is used only in generate_vNode_id() method
        self.__pair_id = 0 # the generator of pair_id: it is used only in generate_pair_id() method
        self.__flow_id = 0 # the generator of flow_id: it is used only in generate_flow_id() method
        self.__app_id = 0 # the generator of app_id: it is used only in generate_app_id() method

        # make topology
        topology = nx.DiGraph()

        # read topology file
        topo_tmp = np.loadtxt(topologyFile, dtype='int').tolist()

        # add nodes
        list_tmp = list(r[0] for r in topo_tmp) + list(r[2] for r in topo_tmp)
        list_tmp = list(set(list_tmp))
        verticesNum = len(list_tmp) # number of nodes
        topology.add_nodes_from(range(verticesNum))

        # make node's dictionaries
        for i, label in enumerate(list_tmp):
            self.node_index2label[i] = label
            self.node_label2index[label] = i

        # make bi-directional edges
        for e in topo_tmp:
            topology.add_edge(self.node_label2index[e[0]], self.node_label2index[e[2]])
            topology.add_edge(self.node_label2index[e[2]], self.node_label2index[e[0]])
        
        # make allocatorunit
        self.au = AllocatorUnit(topology)

    # genaration of vNode_id: it is used only when you create a new VNode
    ##---------------------------------------------------------
    def generate_vNode_id(self):
        givenId = self.__vNode_id
        self.__vNode_id += 1
        return givenId
    
    # genaration of pair_id: it is used only when you create a new Pair
    ##---------------------------------------------------------
    def generate_pair_id(self):
        givenId = self.__pair_id
        self.__pair_id += 1
        return givenId

    # genaration of flow_id: it is used only when you find a new flow label
    ##---------------------------------------------------------
    def generate_flow_id(self):
        givenId = self.__flow_id
        self.__flow_id += 1
        return givenId
    
    # genaration of app_id: it is used only when you create a new App
    ##---------------------------------------------------------
    def generate_app_id(self):
        givenId = self.__app_id
        self.__app_id += 1
        return givenId

    ##---------------------------------------------------------
    def load_app(self, communicationFile):
        # read communication file
        comm_tmp = np.loadtxt(communicationFile, dtype='int').tolist()

        # make dictionary that convert labels to vNode_id or flow_id
        list_tmp = list(r[0] for r in comm_tmp) + list(r[1] for r in comm_tmp)
        vNode_label_list = list(set(list_tmp))
        label2vNode_id = {label:self.generate_vNode_id() for label in vNode_label_list} # a dictionary for _id
        list_tmp = list(r[2] for r in comm_tmp)
        list_tmp = list(set(list_tmp))
        label2flow_id = {label:self.generate_flow_id() for label in list_tmp} # a dictionary for flow_id

        # convert label to id
        comm_tmp = [[label2vNode_id[pair[0]], label2vNode_id[pair[1]], label2flow_id[pair[2]]] for pair in comm_tmp]
        flow_tmp = [[] for _ in label2flow_id]
        for pair in comm_tmp:
            flow_tmp[pair[2]].append((pair[0], pair[1]))
        
        # make Flows and Pairs
        pair_list = list()
        flow_list = list()
        for i, flow in enumerate(flow_tmp):
            tmp_pair_list = [Pair(self.generate_pair_id(), pair[0], pair[1]) for pair in flow]
            flow_list.append(Flow(i, tmp_pair_list))
            pair_list += tmp_pair_list

        # make vNodes
        vNode_list = list()
        vNode_id_list = [label2vNode_id[elm] for elm in vNode_label_list]
        for vNode_id in vNode_id_list:
            send_pair_list, recv_pair_list = list(), list()
            for pair in pair_list:
                if pair.src == vNode_id:
                    send_pair_list.append(pair)
                elif pair.dst == vNode_id:
                    recv_pair_list.append(pair)
            vNode_list.append(VNode(vNode_id, send_pair_list, recv_pair_list))
        
        # set Pair.src_vNode or Pair.dst_vNode
        for pair in pair_list:
            for vNode in vNode_list:
                if pair.src == vNode.vNode_id:
                    pair.src_vNode = vNode
                elif pair.dst == vNode.vNode_id:
                    pair.dst_vNode = vNode

        # make App
        app = App(self.generate_app_id(), vNode_list, flow_list, pair_list, communicationFile)
        self.au.add_app(app)
    
    ##---------------------------------------------------------
    def run_optimization(self, max_execution_time):
        self.au = alns.alns(self.au, max_execution_time)
    
    ##---------------------------------------------------------
    def print_result(self):
        print("nunber of slots: {}".format(self.au.slot_allocation()))
        node_num = nx.number_of_nodes(self.au.topology)
        used_node = set(self.au.temp_allocated_rNode_dict.keys())
        pos = {}
        for i in range(node_num):
            pos[i] = (i // 4, i % 4)
        node_color = list()
        for i in range(node_num):
            if i in used_node:
                node_color.append('red')
            else:
                node_color.append('cyan')
        nx.draw_networkx(self.au.topology, pos, node_color=node_color)
        plt.show()

#--------------------------------------------------------------
if __name__ == '__main__':
    args = parser()
    actor = BoardAllocator(args.t)
    actor.load_app(args.c)
    actor.run_optimization(args.s + 60 * args.m + 3600 * args.ho)
    actor.print_result()
    print(" ### OVER ### ")