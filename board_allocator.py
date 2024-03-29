from __future__ import annotations
import argparse
import json
import sys
import os
import os.path
import shutil
import numpy as np
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
import random
from typing import Optional, Callable
import pickle

import networkx as nx
import matplotlib
from evaluator import Evaluator

from galib import Individual
matplotlib.use('GTK3Agg')
import matplotlib.pyplot as plt

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode, Flow
import alns
from nsga2 import NSGA2
from ncga import NCGA
from spea2 import SPEA2
import sa

# for debug
from deap import tools

sys.setrecursionlimit(100000)
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
    parser.add_argument('-me', action='store_true')

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
    return datetime.now(JST).strftime('%Y-%m-%d-%H%M-%S%f')

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
    def __init__(self, topologyFile: str, multi_ejection: bool = False):
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

        # add core nodes
        core_nodes = list(set([r[0] for r in topo_tmp] + [r[2] for r in topo_tmp]))
        core_node_num = len(core_nodes) # number of nodes
        topology.add_nodes_from([(i, {"module": "core"}) for i in range(core_node_num)])

        # label to assigned index
        self.node_index2label = {i: label for i, label in enumerate(core_nodes)}
        self.node_label2index = {value: key 
                                 for key, value in self.node_index2label.items()}
        
        # add switch nodes and edges between cores and switches
        def connecting_swicth(core_node: int):
            assert core_node < core_node_num
            return core_node_num + core_node
        topology.add_nodes_from([(i, {"module": "switch", 
                                      "adj2input_port": dict(), 
                                      "adj2output_port": dict()}) 
                                 for i in range(core_node_num, 2 * core_node_num)])
        for i in self.node_index2label.keys():
            topology.add_edge(i, connecting_swicth(i))
            topology.add_edge(connecting_swicth(i), i, multi_ejection=multi_ejection)

        # make bi-directional edges
        for core0, port0, core1, port1 in topo_tmp:
            sw0 = connecting_swicth(self.node_label2index[core0])
            sw1 = connecting_swicth(self.node_label2index[core1])
            topology.add_edge(sw0, sw1)
            topology.add_edge(sw1, sw0)
            topology.nodes[sw0]["adj2output_port"][sw1] = port0
            topology.nodes[sw1]["adj2input_port"][sw0] = port1
            topology.nodes[sw1]["adj2output_port"][sw0] = port1
            topology.nodes[sw0]["adj2input_port"][sw1] = port0
        
        ## settings for position
        #pos = {i: (-((i % core_node_num) // 4) * 4 - (i // core_node_num), ((i % core_node_num) % 4) * 4 + (i // core_node_num)) for i in range(2*core_node_num)}
        #labels = {i: self.node_index2label[i % core_node_num] for i in range(2*core_node_num)}
        # draw
        #nx.draw_networkx(topology, pos, labels=labels)
        #plt.show()
        
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
        flow2pairs = {flow_id: [Pair(self.__generate_pair_id(), p[0], p[1], flow_id) 
                              for p in comm_tmp if p[2] == flow_id]
                      for flow_id in label2flow_id.values()}
        pair_list = [pair for pairs in flow2pairs.values() for pair in pairs]

        def show_pair(pair: Pair):
            print("pair_id", pair.pair_id)
            print("src", pair.src)
            print("dst", pair.dst)
            print("flow_id", pair.flow_id)
            print("src_vNode", pair.src_vNode.rNode_id)
            print("dst_vNode", pair.dst_vNode.rNode_id)
            print("owner", pair.owner)
            print("path", pair.path)
            print("allocating", pair.allocating)

        
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
        flow_dict = {flow.flow_id: flow for flow in flow_list}
        for pair in pair_list:
            pair.src_vNode = vNode_dict[pair.src]
            pair.dst_vNode = vNode_dict[pair.dst]
            pair.owner = flow_dict[pair.flow_id]

        # print("pair_list")
        # for pair in pair_list:
        #     show_pair(pair)

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
    def alns(self, execution_time: float, for_exp: bool = False):
        self.au = alns.alns(self.au, execution_time, for_exp=for_exp)
        self.au.apply()
        return self.au

    ##-----------------------------------------------------------------------------------
    def alns_test(self, execution_time: float):
        self.au = alns.alns_test(self.au, execution_time)
        self.au.apply()
    
    ##-----------------------------------------------------------------------------------
    def alns_test2(self, execution_time: float):
        self.au = alns.alns_test2(self.au, execution_time)
        self.au.apply()

    ##-----------------------------------------------------------------------------------
    def alns_assist(self, execution_time: float):
        self.au = alns.alns_assist(self.au, execution_time)
        self.au.apply()
    
    ##-----------------------------------------------------------------------------------
    def sa(self, execution_time: float):
        self.au = sa.sa(self.au, execution_time)
        self.au.apply()
    
    ##-----------------------------------------------------------------------------------
    def nsga2(self, 
              execution_time : float, 
              process_num: int = 1, 
              mate_pb: float = 0.8, 
              mutation_pb: float = 0.2, 
              archive_size: int = 40, 
              offspring_size: Optional[int] = None, 
              for_exp: bool = False) -> tools.ParetoFront:
        seed = self.au.dumps()
        nsga2 = NSGA2(seed, mate_pb, mutation_pb, archive_size, offspring_size)
        hall_of_fame = nsga2.run(execution_time, process_num, for_exp=for_exp)

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
            index = 0
            best = hof[index].fitness.values[0] * Evaluator.weights()[0]
            for i, ind in enumerate(hof):
                ind: Individual
                score = ind.fitness.values[0] * Evaluator.weights()[0]
                if score > best:
                    index = i

        self.au: Individual = hof[index]
        self.au.apply()
        return self.au

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
    
    def show_real_flows(self):
        print("src_id, dest_id, flow_id")
        app = self.au.app_dict[0]
        for pair in app.pair_list:
            src_board_id = pair.src_vNode.rNode_id
            dst_board_id = pair.dst_vNode.rNode_id
            old_src_board_id = pair.src
            old_dst_board_id = pair.dst
            flow_id = pair.flow_id
            print(f"src: {src_board_id}, dst: {dst_board_id}, flow_id: {flow_id}")
            print(f"old_src: {old_src_board_id}, old_dst: {old_dst_board_id}, flow_id: {flow_id}")
    
    def write_real_flows(self, flow_file):
        for app_id, app in sorted(self.au.app_dict.items(), key=lambda item: item[0]):
            # flow_file_name: str = flow_file + str(app_id)
            with open(flow_file, "w") as f:
                for pair in app.pair_list:
                    src_board_id = pair.src_vNode.rNode_id
                    dst_board_id = pair.dst_vNode.rNode_id
                    old_src_board_id = pair.src
                    old_dst_board_id = pair.dst
                    flow_id = pair.flow_id
                    f.write(f"{src_board_id} {dst_board_id} {flow_id}\n")
                    print(f"src: {old_src_board_id} -> {src_board_id}, dst: {old_dst_board_id} -> {dst_board_id}, flow_id: {flow_id}")
            print(f"[INFO] Write the real flow in {flow_file}")
    
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
            print("# of slots: {}".format(self.au.get_max_slot_num()))
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
        core_node_num = len(self.au.core_nodes)
        pos = {i: (-((i % core_node_num) // 4) * 4 - (i // core_node_num), 
                   ((i % core_node_num) % 4) * 4 + (i // core_node_num)) 
               for i in self.au.topology.nodes}
        #labels = {i: self.node_index2label[i % core_node_num] for i in self.au.topology.nodes}
        ## settings for color
        used_nodes_for_app = {app.app_id: [vNode.rNode_id for vNode in app.vNode_list 
                                           if vNode.rNode_id is not None] 
                              for app in self.au.app_dict.values()}
        node_color = ['gainsboro' for i in self.au.topology.nodes]
        for app_id, used_nodes in used_nodes_for_app.items():
            for node in used_nodes:
                node_color[node] = self.app_id2vitrualizer[app_id].color
        # draw
        nx.draw_networkx(self.au.topology, pos, node_color=node_color)
        plt.savefig(path)
        plt.close()
    
    ##-----------------------------------------------------------------------------------
    def dumps(self, protocol: int = pickle.HIGHEST_PROTOCOL) -> bytes:
        return pickle.dumps(self, protocol)
    
    ##-----------------------------------------------------------------------------------
    def dump(self, file_name: str, protocol: int = pickle.HIGHEST_PROTOCOL):
        with open(file_name, 'wb') as f:
            pickle.dump(self, f, protocol)
    
    ##-----------------------------------------------------------------------------------
    @staticmethod
    def loads(obj: bytes) -> AllocatorUnit:
        return pickle.loads(obj)
    
    ##-----------------------------------------------------------------------------------
    @staticmethod
    def load(file_name: str) -> AllocatorUnit:
        with open(file_name, 'rb') as f:
            data = pickle.load(f)
        return data

#----------------------------------------------------------------------------------------
if __name__ == '__main__':
    args = parser()
    clean_dir(FIG_DIR)
    actor = BoardAllocator(args.t, args.me)
    actor.load_app(args.c)
    actor.alns_test(args.m * 60)
    
    # profiler
    #def main():
    #    actor = BoardAllocator.load('sample.pickle')
    #    actor.load_app(args.c)
    #    actor.two_opt(args.m * 60)
    #    #actor.dump('sample.pickle')
    #import cProfile
    #from pstats import SortKey
    #cProfile.run('main()', sort=SortKey.CUMULATIVE)
    
    print(" ### OVER ### ")