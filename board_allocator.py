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

import graph_tool.all as gt

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode

##---------------------------------------------------------
def parser():
    parser = argparse.ArgumentParser(description='board allocator')
    parser.add_argument('-t', help='topology file', default='fic-topo-file-cross.txt')
    parser.add_argument('-c', help='communication partern (traffic file)', required=True)

    args = parser.parse_args()

    if not os.path.isfile(args.t):
        print("Error: {0:s} was not found.".format(args.t), sys.stderr)
        sys.exit(1)
    
    if not os.path.isfile(args.c):
        print("Error: {0:s} was not found.".format(args.c), sys.stderr)
        sys.exit(2)
    
    return args

#--------------------------------------------------------------
class App:
    def __init__(self, app_id, vNode_list, pair_list, communicationFile):
        self.app_id = app_id
        self.vNode_list = vNode_list # list: list of vNode of the App
        self.pair_list = pair_list # list: list of pair of the App
        self.communicationFile = communicationFile

#--------------------------------------------------------------
class Pair:
    def __init__(self, pair_id, src, dst, flow_id):
        self.pair_id = pair_id
        self.src = src
        self.src_vNode = None
        self.dst = dst
        self.dst_vNode = None
        self.flow_id = flow_id
        self.path_id = None # using path list

#--------------------------------------------------------------
class VNode:
    def __init__(self, vNode_id, send_pair_list, recv_pair_list):
        self.vNode_id = vNode_id # int: virtualized node ID
        self.send_pair_list = send_pair_list # list: list of pair to be sent by this VNode
        self.recv_pair_list = recv_pair_list # list: list of pair to be recieved by this VNode
        self.rNode_id = None # allocated node label (label is defined in topologyFile), if the vNode is not allocated (including tmporary), the value is None

#--------------------------------------------------------------
class AllocatorUnit:
    def __init__(self):
        ## topology
        self.topology = gt.Graph() # the topology for this allocator
        ## allocating object lists
        self.allocating_vNode_list = list() # 1D list: the list of VNodes that are being allocated
        self.allocating_pair_list = list() # 1D list: the list of pairs that are being allocated
        self.allocating_app_list = list() # 1D list: the list of Apps that are being allocated
        ## runnning (allocated) object list
        self.running_vNode_list = list() # 1D list: the list of VNodes that are runnning (allocation is finished)
        self.running_pair_list = list() # 1D list: the list of pairs that are runnning (allocation is finished)
        self.running_app_list = list() # 1D list: the list of Apps that are runnning (allocation is finished)
        ## manage the real node
        self.temp_allocated_rNode_list = list() # 1D list: the list of rNodes that is temporary allocated
        self.empty_rNode_list = list() # 1D list: the list of rNodes that is not allocated (not including temp_allocated_rNode_list)

#--------------------------------------------------------------
class BoardAllocator:
    def __init__(self, topologyFile):
        # define variable
        ## Allocator Unit
        self.au = None
        ## virtualization of the topology file
        self.node_index2label = {} # dict: (index in self.au.topology) |-> (label in topologyFile)
        self.node_label2index = {} # dict: (label in topologyFile) |-> (index in self.au.topology)
        ## shortest path list
        self.st_path_table = None # 2D list: st_path_table[src][dst] = [path0, path1, ...] <return value is 1D list of path(1D list)>
        ## id generators
        self._vNode_id = 0 # the generator of vNode_id: it is used only in generate_vNode_id() method
        self._pair_id = 0 # the generator of pair_id: it is used only in generate_pair_id() method
        self._flow_id = 0 # the generator of flow_id: it is used only in generate_flow_id() method
        self._app_id = 0 # the generator of app_id: it is used only in generate_app_id() method

        # make topology
        topology = gt.Graph()

        # read topology file
        topo_tmp = np.loadtxt(topologyFile, dtype='int').tolist()

        # add nodes
        list_tmp = list(r[0] for r in topo_tmp) + list(r[2] for r in topo_tmp)
        list_tmp = list(set(list_tmp))
        verticesNum = len(list_tmp) # number of vertices
        topology.add_vertex(verticesNum)

        # make node's dictionaries
        for i, label in enumerate(list_tmp):
            self.node_index2label[i] = label
            self.node_label2index[label] = i

        # make bi-directional edges
        for e in topo_tmp:
            topology.add_edge(self.node_label2index[e[0]], self.node_label2index[e[2]])
            topology.add_edge(self.node_label2index[e[2]], self.node_label2index[e[0]])

        # create st-path list
        self.st_path_table = [[[] for _ in range(0, verticesNum)] for _ in range(0, verticesNum)]
        for src in range(0, verticesNum):
            for dst in range(0, verticesNum):
                for paths in gt.all_shortest_paths(topology, src, dst):
                    self.st_path_table[src][dst].append(paths.tolist())
        
        # make allocatorunit
        self.au = AllocatorUnit(topology)

        # draw the graph
        #gt.graph_draw(topology, vertex_text = topology.vertex_index, output="test.png")
    
    # genaration of vNode_id: it is used only when you create a new VNode
    ##---------------------------------------------------------
    def generate_vNode_id(self):
        givenId = self._vNode_id
        self._vNode_id += 1
        return givenId
    
    # genaration of pair_id: it is used only when you create a new Pair
    ##---------------------------------------------------------
    def generate_pair_id(self):
        givenId = self._pair_id
        self._pair_id += 1
        return givenId

    # genaration of flow_id: it is used only when you find a new flow label
    ##---------------------------------------------------------
    def generate_flow_id(self):
        givenId = self._flow_id
        self._flow_id += 1
        return givenId
    
    # genaration of app_id: it is used only when you create a new App
    ##---------------------------------------------------------
    def generate_app_id(self):
        givenId = self._app_id
        self._app_id += 1
        return givenId

    ##---------------------------------------------------------
    def loadApp(self, communicationFile):
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
        app = App(self.generate_app_id(), vNode_list, pair_list, communicationFile)
        self.au.add_app(app, vNode_list, pair_list)

#--------------------------------------------------------------
if __name__ == '__main__':
    args = parser()
    actor = BoardAllocator(args.t)
    actor.load_app(args.c)
    print(" ### OVER ### ")