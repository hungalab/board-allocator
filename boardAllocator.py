import argparse
import json
import sys, traceback
import os
import os.path
import shutil
import graph_tool.all as gt
import numpy as np
import collections
from collections import OrderedDict
from enum import Enum
import time
import random

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

# state of VNode
#--------------------------------------------------------------
class vNodeState(Enum):
    ALLOCATING = 1
    RUNNNING = 2
    TERMINATED = 3

#--------------------------------------------------------------
class App:
    def __init__(self, app_id, vNode_id_list, pair_id_list, communicationFile):
        self.app_id = app_id
        self.vNode_id_list = vNode_id_list # list: list of vNode_id of the App
        self.pair_id_list = pair_id_list # list: list of pair_id of the App
        self.communicationFile = communicationFile

#--------------------------------------------------------------
class Pair:
    def __init__(self, pair_id, src, dst, flow_id):
        self.pair_id = pair_id
        self.src = src
        self.dst = dst
        self.flow_id = flow_id
        self.path_id = None # using path id

#--------------------------------------------------------------
class VNode:
    def __init__(self, vNode_id, send_pair_id_list, recv_pair_id_list):
        self.vNode_id = vNode_id # int: virtualized node ID
        self.send_pair_id_list = send_pair_id_list # list: list of pair_id to be sent by this VNode
        self.recv_pair_id_list = recv_pair_id_list # list: list of pair_id to be recieved by this VNode
        self.rNode_id = None # allocated node label (label is defined in topologyFile), if the vNode is not allocated (including tmporary), the value is None

#--------------------------------------------------------------
class BoardAllocator:
    def __init__(self, topologyFile):
        # define variable
        self.topology = gt.Graph() # the topology for this allocator
        self.node_index2label = {} # dict: (index in self.topology) |-> (label in topologyFile)
        self.node_label2index = {} # dict: (label in topologyFile) |-> (index in self.topology)
        self.st_path_list = list() # 1D list: st_path_list[pathId] = [s, v0, v1, ..., t] <return value is 1D list>
        self.st_path_table = None # 2D list: st_path_table[src][dst] = [pathId0, pathId1, ...] <return value is 1D list>
        self.path_id2st = list() # 1D list: path_id2st[pathId] = (src, dst) <return value is tuple>
        self.allocating_vNode_list = list() # 1D list: the list of VNodes that are being allocated
        self.allocating_pair_list = list() # 1D list: the list of pairs that are being allocated
        self.allocating_app_list = list() # 1D list: the list of Apps that are being allocated
        self.running_vNode_list = list() # 1D list: the list of VNodes that are runnning (allocation is finished)
        self.running_pair_list = list() # 1D list: the list of pairs that are runnning (allocation is finished)
        self.running_app_list = list() # 1D list: the list of Apps that are runnning (allocation is finished)
        self.temp_allocated_rNode_list = list() # 1D list: the list of rNodes that is temporary allocated
        self.empty_rNode_list = list() # 1D list: the list of rNodes that is not allocated (not including temp_allocated_rNode_list)
        self._vNode_id = 0 # the generator of vNode_id: it is used only in generate_vNode_id() method
        self._pair_id = 0 # the generator of pair_id: it is used only in generate_pair_id() method
        self._flow_id = 0 # the generator of flow_id: it is used only in generate_flow_id() method
        self._app_id = 0 # the generator of app_id: it is used only in generate_app_id() method

        # read topology file
        topo_tmp = np.loadtxt(topologyFile, dtype='int').tolist()

        # add nodes
        list_tmp = list(r[0] for r in topo_tmp) + list(r[2] for r in topo_tmp)
        list_tmp = list(set(list_tmp))
        verticesNum = len(list_tmp) # number of vertices
        self.topology.add_vertex(verticesNum)

        # make node's dictionaries
        for i, elm in enumerate(list_tmp):
            self.node_index2label[i] = elm
            self.node_label2index[elm] = i

        # make bi-directional edges
        for elm in topo_tmp:
            self.topology.add_edge(self.node_label2index[elm[0]], self.node_label2index[elm[2]])
            self.topology.add_edge(self.node_label2index[elm[2]], self.node_label2index[elm[0]])

        # create properties
        self.topology.ep["slotNum"] = self.topology.new_ep("short") # number of slots for each edge
        self.topology.ep["flows"] = self.topology.new_ep("object") # list of slots for each edge
        for elm in self.topology.edges():
            self.topology.ep.slotNum[elm] = 0
            self.topology.ep.flows[elm] = list()
        self.topology.vp["injectionSlotNum"] = self.topology.new_vp("short") # number of slots for each injection link
        self.topology.vp["injectionFlows"] = self.topology.new_vp("object") # list of flows for each injection link
        for elm in self.topology.vertices():
            self.topology.vp.injectionSlotNum[elm] = 0
            self.topology.vp.injectionFlows[elm] = list()
        
        # create st-path list
        self.st_path_table = [[[] for _ in range(0, verticesNum)] for _ in range(0, verticesNum)]
        pathId = 0
        for src in range(0, verticesNum):
            for dst in range(0, verticesNum):
                for elm in gt.all_shortest_paths(self.topology, src, dst):
                    self.st_path_list.append(elm.tolist())
                    self.st_path_table[src][dst].append(pathId)
                    self.path_id2st.append((src, dst))
                    pathId += 1

        # draw the graph
        #gt.graph_draw(self.topology, vertex_text = self.topology.vertex_index, output="test.png")
    
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
        label2vNode_id = {elm:self.generate_vNode_id() for elm in vNode_label_list} # a dictionary for _id
        list_tmp = list(r[2] for r in comm_tmp)
        list_tmp = list(set(list_tmp))
        label2flow_id = {elm:self.generate_flow_id() for elm in list_tmp} # a dictionary for flow_id

        # convert label to id
        comm_tmp = [[label2vNode_id[elm[0]], label2vNode_id[elm[1]], label2flow_id[elm[2]]] for elm in comm_tmp]
        
        # make Pairs
        pair_id_list = list() # for making App
        for pair in comm_tmp:
            pair_id = self.generate_pair_id()
            pair_id_list.append(pair_id)
            self.allocating_pair_list.append(Pair(pair_id, pair[0], pair[1], pair[2]))

        # make App
        vNode_id_list = [label2vNode_id[elm] for elm in vNode_label_list]
        self.allocating_app_list.append(App(self.generate_app_id(), vNode_id_list, pair_id_list, communicationFile))

        # make vNodes
        for vNode_id in vNode_id_list:
            send_pair_id_list, recv_pair_id_list = list(), list()
            for pair in self.allocating_pair_list:
                if pair.src == vNode_id:
                    send_pair_id_list.append(pair.pair_id)
                elif pair.dst == vNode_id:
                    recv_pair_id_list.append(pair.pair_id)
            self.allocating_vNode_list.append(VNode(vNode_id, send_pair_id_list, recv_pair_id_list))

    ##---------------------------------------------------------
    def random_single_node_allocation(self, vNode):
        # pick up an empty rNove
        map_rNode_id = random.choice(self.empty_rNode_list)
        self.empty_rNode_list.remove(map_rNode_id)

        # temporary node allocation
        self.temp_allocated_rNode_list.append(map_rNode_id)
        vNode.rNode_id = map_rNode_id

        # temporary send-path allocation (if dst node is not allocated, the operation is not executed)
        for dst_rNode


    ##---------------------------------------------------------
    def alns(self, max_execution_time):
        p_break_path = len(self.pair_list) # probability of executing break_path()
        p_node_swap = len(self.vNode_list) # probability of executing node_swap()
        p_range = p_break_path # normalization value

        start_time = time.time()

        # genarate the initial solution
        self.generate_initial_solution()

        while True:
            # execute break_path or node_swap
            if random.randrange(p_range) < p_break_path:
                self.break_path()
            else:
                #self.node_swap()
                pass
            
            # if time is up, break the loop
            if time.time() - start_time >= max_execution_time:
                break
    
    ##---------------------------------------------------------
    def print_app(self):
        print(" ##### App ##### ")
        all_app_list = self.running_app_list + self.allocating_app_list
        for app in all_app_list:
            print("app_id: {}".format(app.app_id))
            print("vNode_id_list: {}".format(app.vNode_id_list))
            print("pair_id_list: {}".format(app.pair_id_list))
            print(" --------------------------------------------------- ")

        print("\n ##### vNode ##### ")
        all_vNode_list = self.running_vNode_list + self.allocating_vNode_list
        for vNode in all_vNode_list:
            print("vNode_id: {}".format(vNode.vNode_id))
            print("send_pair_id_list: {}".format(vNode.send_pair_id_list))
            print("recv_pair_id_list: {}".format(vNode.recv_pair_id_list))
            print(" --------------------------------------------------- ")
        
        print("\n ##### Pair ##### ")
        all_pair_list = self.running_pair_list + self.allocating_pair_list
        for pair in all_pair_list:
            print("pair_id: {}".format(pair.pair_id))
            print("src: {}".format(pair.src))
            print("dst: {}".format(pair.dst))
            print("flow_id: {}".format(pair.flow_id))
            print(" --------------------------------------------------- ")


#--------------------------------------------------------------
if __name__ == '__main__':
    args = parser()
    actor = BoardAllocator(args.t)
    actor.loadApp(args.c)
    actor.print_app()
    print(" ### OVER ### ")