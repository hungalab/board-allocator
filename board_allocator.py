import argparse
import json
import sys, traceback
import os
import os.path
import shutil
import numpy as np
import collections
from collections import OrderedDict
import time
import pickle

import networkx as nx

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode
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
        topology.add_nodes_from([(i, {'injection_slot_num': 0, 'injection_pairs': set()}) for i in range(verticesNum)])

        # make node's dictionaries
        for i, label in enumerate(list_tmp):
            self.node_index2label[i] = label
            self.node_label2index[label] = i

        # make bi-directional edges
        for e in topo_tmp:
            topology.add_edge(self.node_label2index[e[0]], self.node_label2index[e[2]], slot_num = 0, pairs = set())
            topology.add_edge(self.node_label2index[e[2]], self.node_label2index[e[0]], slot_num = 0, pairs = set())
        
        # make allocatorunit
        self.au = AllocatorUnit(topology)

        # draw the graph
        #gt.graph_draw(topology, vertex_text = topology.vertex_index, output="test.png")
    
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
        
        # make Pairs
        pair_list = [Pair(self.generate_pair_id(), pair[0], pair[1], pair[2]) for pair in comm_tmp]

        # make vNodes
        vNode_list = list()
        vNode_id_list = [label2vNode_id[elm] for elm in vNode_label_list]
        for vNode_id in vNode_id_list:
            send_pair_id_list, recv_pair_id_list = list(), list()
            for pair in pair_list:
                if pair.src_vNode_id == vNode_id:
                    send_pair_id_list.append(pair.pair_id)
                elif pair.dst_vNode_id == vNode_id:
                    recv_pair_id_list.append(pair.pair_id)
            vNode_list.append(VNode(vNode_id, send_pair_id_list, recv_pair_id_list))

        # make App
        pair_id_list = [pair.pair_id for pair in pair_list]
        app = App(self.generate_app_id(), vNode_id_list, pair_id_list, communicationFile)
        self.au.add_app(app, vNode_list, pair_list)
    
    ##---------------------------------------------------------
    def run_optimization(self, max_execution_time):
        alns.alns(self.au, max_execution_time)

#--------------------------------------------------------------
if __name__ == '__main__':
    args = parser()
    actor = BoardAllocator(args.t)
    actor.load_app(args.c)
    actor.run_optimization(args.s + 60 * args.m + 3600 * args.ho)
    print(" ### OVER ### ")