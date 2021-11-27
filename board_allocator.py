from __future__ import annotations
import argparse
import json
import os
import os.path
import shutil
import copy
import numpy as np
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
import random
from typing import Optional, Callable

import networkx as nx
import matplotlib
matplotlib.use('GTK3Agg')
import matplotlib.pyplot as plt

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode, Flow
import alns
from nsga2 import NSGA2
from ncga import NCGA
from spea2 import SPEA2

# for debug
from deap import tools

FIG_DIR = 'figure'
#----------------------------------------------------------------------------------------
def clean_dir(path: str):
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.mkdir(path)

#----------------------------------------------------------------------------------------
def parser():
    parser = argparse.ArgumentParser(description='board allocator')
    parser.add_argument('-t', help='topology file', default='fic-topo-file-cross.txt')
    parser.add_argument('-c', help='communication partern (traffic file)', required=True)
    parser.add_argument('-s', help='', default=0, type=float)
    parser.add_argument('-m', help='', default=0, type=float)
    parser.add_argument('-ho', help='', default=0, type=float)
    parser.add_argument('--method', help='method to use', default='NSGA2')
    parser.add_argument('-p', help='# of processes to use', default=1, type=int)

    args = parser.parse_args()

    if not os.path.isfile(args.t):
        raise FileNotFoundError("{0:s} was not found.".format(args.t))

    if not os.path.isfile(args.c):
        raise FileNotFoundError("{0:s} was not found.".format(args.c))
    
    if (args.s + args.m + args.ho <= 0):
        raise ValueError("Total execution time must be greater than 0 second.")

    if args.p < 1:
        raise ValueError("The -p option must be a natural number.")
    
    return args

#----------------------------------------------------------------------------------------
JST = timezone(timedelta(hours=+9))
def now():
    return datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S (%Z)')

def default_filename():
    return datetime.now(JST).strftime('%Y-%m-%d-T%H%M-%S%f')

#----------------------------------------------------------------------------------------
class AppVirtualizer:
    def __init__(self, 
                 label2vNode_id: dict[int, int], 
                 label2flow_id: dict[int, int], 
                 communicationFile: str, 
                 color: str):
        self.label2vNode_id = label2vNode_id
        self.vNode_id2label = {value: key for key, value in self.label2vNode_id.items()}
        self.label2flow_id = label2flow_id
        self.flow_id2label = {value: key for key, value in self.label2flow_id.items()}
        self.communicationFile = communicationFile
        self.date = now()
        self.color = color

#----------------------------------------------------------------------------------------
class BoardAllocator:
    def __init__(self, topologyFile: str):
        # define variable
        ## Allocator Unit
        self.au: Optional[AllocatorUnit] = None
        ## record topology file
        self.topology_file = os.path.abspath(topologyFile)
        ## virtualization of the topology file
        self.node_index2label: dict[int, int] = {} # dict: (index in self.au.topology) |-> (label in topologyFile)
        self.node_label2index: dict[int, int] = {} # dict: (label in topologyFile) |-> (index in self.au.topology)
        ## virtualization of apps
        self.app_id2vitrualizer: dict[int, AppVirtualizer] = {} # dict: (app_id) |-> (virtualization table for app_id)
        ## id generators
        self.__vNode_id = 0 # the generator of vNode_id: it is used only in generate_vNode_id() method
        self.__pair_id = 0 # the generator of pair_id: it is used only in generate_pair_id() method
        self.__flow_id = 0 # the generator of flow_id: it is used only in generate_flow_id() method
        self.__app_id = 0 # the generator of app_id: it is used only in generate_app_id() method
        ## color pool for drawing
        self.color_pool = ['red', 'cyan', 'yellow', 'orange', 'green']

        # make topology
        topology = nx.DiGraph()

        # read topology file
        topo_tmp = np.loadtxt(topologyFile, dtype='int').tolist()

        # add nodes
        list_tmp = list(r[0] for r in topo_tmp) + list(r[2] for r in topo_tmp)
        list_tmp = list(set(list_tmp))
        verticesNum = len(list_tmp) # number of nodes
        topology.add_nodes_from(range(verticesNum))

        self.node_index2label = {i: label for i, label in enumerate(list_tmp)}
        self.node_label2index = {value: key 
                                 for key, value in self.node_index2label.items()}

        # make bi-directional edges
        for e in topo_tmp:
            topology.add_edge(self.node_label2index[e[0]], self.node_label2index[e[2]])
            topology.add_edge(self.node_label2index[e[2]], self.node_label2index[e[0]])
        
        # make allocatorunit
        self.au = AllocatorUnit(topology)

    # genaration of vNode_id: it is used only when you create a new VNode
    ##-----------------------------------------------------------------------------------
    def __generate_vNode_id(self):
        givenId = self.__vNode_id
        self.__vNode_id += 1
        return givenId
    
    # genaration of pair_id: it is used only when you create a new Pair
    ##-----------------------------------------------------------------------------------
    def __generate_pair_id(self):
        givenId = self.__pair_id
        self.__pair_id += 1
        return givenId

    # genaration of flow_id: it is used only when you find a new flow label
    ##-----------------------------------------------------------------------------------
    def __generate_flow_id(self):
        givenId = self.__flow_id
        self.__flow_id += 1
        return givenId
    
    # genaration of app_id: it is used only when you create a new App
    ##-----------------------------------------------------------------------------------
    def __generate_app_id(self):
        givenId = self.__app_id
        self.__app_id += 1
        return givenId

    ##-----------------------------------------------------------------------------------
    def load_app(self, communicationFile: str) -> bool:
        # read communication file
        comm_tmp = np.loadtxt(communicationFile, dtype='int').tolist()

        # make dictionary that convert labels to vNode_id or flow_id
        vNode_labels = {r[0] for r in comm_tmp} | {r[1] for r in comm_tmp}
        label2vNode_id = {label:self.__generate_vNode_id() for label in vNode_labels} # a dictionary for _id
        flow_labels = {r[2] for r in comm_tmp}
        label2flow_id = {label:self.__generate_flow_id() for label in flow_labels} # a dictionary for flow_id

        # convert label to id
        comm_tmp = [[label2vNode_id[p[0]], label2vNode_id[p[1]], label2flow_id[p[2]]]
                    for p in comm_tmp]
        
        # make Pairs
        flow2pairs = {flow_id: [Pair(self.__generate_pair_id(), p[0], p[1]) 
                              for p in comm_tmp if p[2] == flow_id]
                    for flow_id in label2flow_id.values()}
        pair_list = [pair for pairs in flow2pairs.values() for pair in pairs]
        
        # make Flows
        flow_list = [Flow(flow_id, pairs) for flow_id, pairs in flow2pairs.items()]

        # make vNodes
        vNode_id_list = [label2vNode_id[elm] for elm in vNode_labels]
        vNode_list = [VNode(vNode_id, 
                            [pair for pair in pair_list if pair.src == vNode_id], 
                            [pair for pair in pair_list if pair.dst == vNode_id]) 
                      for vNode_id in vNode_id_list]
        
        # set Pair.src_vNode or Pair.dst_vNode
        vNode_dict = {vNode.vNode_id: vNode for vNode in vNode_list}
        for pair in pair_list:
            pair.src_vNode = vNode_dict[pair.src]
            pair.dst_vNode = vNode_dict[pair.dst]

        # make App
        app = App(self.__generate_app_id(), vNode_list, flow_list, pair_list)
        if self.au.add_app(app):
            color = self.color_pool.pop(random.randrange(len(self.color_pool)))
            self.app_id2vitrualizer[app.app_id] \
            = AppVirtualizer(label2vNode_id, label2flow_id, \
                             os.path.abspath(communicationFile), color)
            return True
        else:
            return False
    
    ##-----------------------------------------------------------------------------------
    def remove_app(self, app_id: int):
        if app_id not in self.app_id2vitrualizer.keys():
            raise ValueError("app_id {} does not exists.".format(app_id))
        # remove from au
        self.au.remove_app(app_id)
        # restore color to color_pool
        self.color_pool.append(self.app_id2vitrualizer[app_id].color)
        # delete the virtaulizer
        del self.app_id2vitrualizer[app_id]
    
    ##-----------------------------------------------------------------------------------
    def run_optimization(self, 
                         max_execution_time: float, 
                         method: str, 
                         process_num: int = 1):
        # type: (float, str, int) -> None
        print("selected method: {}".format(method))
        if method.lower() == '2-opt':
            self.au = alns.alns2(self.au, max_execution_time)
        elif method.lower() == 'alns':
            self.au = alns.alns(self.au, max_execution_time)
        elif method.lower() == 'alns_test':
            self.au = alns.alns_test(self.au, max_execution_time)
        elif method.lower() == 'nsga2':
            seed = self.au.dumps()
            nsga2 = NSGA2(seed)
            hall_of_fame = nsga2.run(max_execution_time, process_num)
        elif method.lower() == 'ncga':
            seed = self.au.dumps()
            ncga = NCGA(seed)
            hall_of_fame = ncga.run(max_execution_time, process_num)
        elif method.lower() == 'spea2':
            seed = self.au.dumps()
            spea2 = SPEA2(seed)
            hall_of_fame = spea2.run(max_execution_time, process_num)
        else:
            raise ValueError("Invalid optimization method name.")
        
        self.au.apply()
    
    ##-----------------------------------------------------------------------------------
    def two_opt(self, execution_time: float):
        self.au = alns.alns2(self.au, execution_time)
        self.au.apply()
    
    ##-----------------------------------------------------------------------------------
    def alns(self, execution_time: float):
        self.au = alns.alns(self.au, execution_time)
        self.au.apply()
    
    ##-----------------------------------------------------------------------------------
    def nsga2(self, 
              execution_time : float, 
              process_num: int = 1, 
              mate_pb: float = 0.7, 
              mutation_pb: float = 0.3, 
              archive_size: int = 40, 
              offspring_size: Optional[int] = None) -> tools.ParetoFront:
        seed = self.au.dumps()
        nsga2 = NSGA2(seed, mate_pb, mutation_pb, archive_size, offspring_size)
        hall_of_fame = nsga2.run(execution_time, process_num)

        return hall_of_fame

    ##-----------------------------------------------------------------------------------
    def spea2(self, 
              execution_time: float, 
              process_num: int = 1, 
              mate_pb: float = 1, 
              mutation_pb: float = 0.3, 
              archive_size: int = 40, 
              offspring_size: Optional[int] = None) -> tools.ParetoFront:
        seed = self.au.dumps()
        spea2 = SPEA2(seed, mate_pb, mutation_pb, archive_size, offspring_size)
        hall_of_fame = spea2.run(execution_time, process_num)

        return hall_of_fame
    
    ##-----------------------------------------------------------------------------------
    def ncga(self, 
             execution_time: float, 
             process_num: int = 1, 
             mate_pb: float = 0.7, 
             mutation_pb: float = 0.3, 
             archive_size: int = 40, 
             offspring_size: Optional[int] = None, 
             sort_method: str = 'cyclic'):
        seed = self.au.dumps()
        ncga = NCGA(seed, mate_pb, mutation_pb, archive_size, 
                    offspring_size, sort_method)
        hall_of_fame = ncga.run(execution_time, process_num)

        return hall_of_fame

    ##-----------------------------------------------------------------------------------
    def select_from_hof(self, hof: tools.HallOfFame, index: Optional[int] = None):
        if index is None:
            pass ## select index

        return hof[index]

    ##-----------------------------------------------------------------------------------
    def show_topology_file(self):
        print(self.topology_file)

    ##-----------------------------------------------------------------------------------
    def show_apps(self, key: Callable[[int], bool] = lambda app_id: True):
        apps_book = tools.Logbook()
        apps_book.header = ['app_id', 'communication', 'date']
        for app_id, appv in sorted(self.app_id2vitrualizer.items(), key=lambda item: item[0]):
            if key(app_id):
                commfile = os.path.basename(appv.communicationFile)
                apps_book.record(app_id=app_id, communication=commfile, date=appv.date)
        
        if len(apps_book) == 0:
            print("There are no items that match the condition.")
        else:
            print(apps_book.stream)

    ##-----------------------------------------------------------------------------------
    def show_nodes(self, 
                   key: Callable[[int, int, int], bool] 
                    = lambda app_id, vNode_id, rNode_id: True):
        nodesbook = tools.Logbook()
        nodesbook.header = ['app_id', 'vNode_id', 'rNode_id']
        for app_id, app in sorted(self.au.app_dict.items(), key=lambda item: item[0]):
            def label(vNode: VNode):
                return self.app_id2vitrualizer[app_id].vNode_id2label[vNode.vNode_id]
            for vNode in sorted(app.vNode_list, key=label):
                vNode_id = self.app_id2vitrualizer[app_id].vNode_id2label[vNode.vNode_id]
                rNode_id = vNode.rNode_id
                if key(app_id, vNode_id, rNode_id):
                    nodesbook.record(app_id=app_id, vNode_id=vNode_id, rNode_id=rNode_id)
        
        if len(nodesbook) == 0:
            print("There are no items that match the condition.")
        else:
            print(nodesbook.stream)
    
    ##-----------------------------------------------------------------------------------
    def show_flows(self, 
                   key: Callable[[int, int, int], bool] 
                    = lambda app_id, flow_id, slot_id: True):
        flows_book = tools.Logbook()
        flows_book.header = ['app_id', 'flow_id', 'slot_id']
        for app_id, app in sorted(self.au.app_dict.items(), key=lambda item: item[0]):
            def label(flow: Flow):
                return self.app_id2vitrualizer[app_id].flow_id2label[flow.flow_id]
            for flow in sorted(app.flow_list, key=label):
                flow_id = self.app_id2vitrualizer[app_id].flow_id2label[flow.flow_id]
                slot_id = flow.slot_id
                if key(app_id, flow_id, slot_id):
                    flows_book.record(app_id=app_id, flow_id=flow_id, slot_id=slot_id)
        
        if len(flows_book) == 0:
            print("There are no items that match the condition.")
        else:
            print(flows_book.stream)
    
    ##-----------------------------------------------------------------------------------
    def print_result(self, fully_desplay: bool = False):
        running_vNodes = [vNode for vNode in self.au.vNode_dict.values() 
                          if vNode.rNode_id is not None]
        if len(running_vNodes) == 0:
            print("the current allocator has no running app.")
            return

        if fully_desplay:
            self.au.print_au()
        
        running_pairs = [pair for pair in self.au.pair_dict.values() 
                         if pair.path is not None]
        if len(running_pairs) != 0:
            print("# of slots: {}".format(self.au.get_max_greedy_slot_num()))
            print("average hops: {}".format(self.au.average_hops()))
            print("# of routed boards: {}".format(self.au.board_num_to_be_routed()))
        else:
            print("the current allocator has no running app with communication.")
        
        self.draw_current_node_status()
    
    ##-----------------------------------------------------------------------------------
    def draw_current_node_status(self, 
                                 path: str 
                                  = os.path.join(FIG_DIR, (default_filename()+'.png'))):
        ## settings for position
        pos = {i: (-(i // 4), i % 4) for i in self.node_index2label.keys()}
        ## settings for color
        used_nodes_for_app = {app.app_id: [vNode.rNode_id for vNode in app.vNode_list 
                                           if vNode.rNode_id is not None] 
                              for app in self.au.app_dict.values()}
        node_color = ['gainsboro' for i in self.node_index2label.keys()]
        for app_id, used_nodes in used_nodes_for_app.items():
            for node in used_nodes:
                node_color[node] = self.app_id2vitrualizer[app_id].color
        # draw
        nx.draw_networkx(self.au.topology, pos, node_color=node_color)
        plt.savefig(path)
        plt.close()

#----------------------------------------------------------------------------------------
if __name__ == '__main__':
    args = parser()
    clean_dir(FIG_DIR)
    actor = BoardAllocator(args.t)
    actor.load_app(args.c)
    actor.run_optimization(args.s + 60 * args.m + 3600 * args.ho, 'alns_test', args.p)
    actor.print_result()
    print("# of slots (optimal): {}".format(actor.au.get_optimal_slot_num()))
    
    print(" ### OVER ### ")