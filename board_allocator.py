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

import networkx as nx
import matplotlib.pyplot as plt

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode, Flow
import alns
from nsga2 import NSGA2
from ncga import NCGA
from spea2 import SPEA2

# for debug
from deap import tools
from evaluator import Evaluator

FIG_DIR = 'figure'
#--------------------------------------------------------------
def clean_dir(s):
    if os.path.isdir(s):
        shutil.rmtree(s)
    os.mkdir(s)

#--------------------------------------------------------------
def parser():
    parser = argparse.ArgumentParser(description='board allocator')
    parser.add_argument('-t', help='topology file', default='fic-topo-file-cross.txt')
    parser.add_argument('-c', help='communication partern (traffic file)', required=True)
    parser.add_argument('-s', help='', default=0, type=int)
    parser.add_argument('-m', help='', default=0, type=int)
    parser.add_argument('-ho', help='', default=0, type=int)
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

#--------------------------------------------------------------
JST = timezone(timedelta(hours=+9))
def now():
    return datetime.now(JST).strftime('%Y/%m/%d %H:%M:%S (%Z)')

def default_filename():
    return datetime.now(JST).strftime('%Y-%m-%d-T%H%M-%S%f')

#--------------------------------------------------------------
class AppVirtualizer:
    def __init__(self, label2vNode_id, label2flow_id, communicationFile, color):
        self.label2vNode_id = label2vNode_id
        self.vNode_id2label = {value: key for key, value in self.label2vNode_id.items()}
        self.label2flow_id = label2flow_id
        self.flow_id2label = {value: key for key, value in self.label2flow_id.items()}
        self.communicationFile = communicationFile
        self.date = now()
        self.color = color

#--------------------------------------------------------------
class BoardAllocator:
    def __init__(self, topologyFile):
        # define variable
        ## Allocator Unit
        self.au = None
        ## record topology file
        self.topology_file = os.path.abspath(topologyFile)
        ## virtualization of the topology file
        self.node_index2label = {} # dict: (index in self.au.topology) |-> (label in topologyFile)
        self.node_label2index = {} # dict: (label in topologyFile) |-> (index in self.au.topology)
        ## virtualization of apps
        self.app_id2vitrualizer = {} # dict: (app_id) |-> (virtualization table for app_id)
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
        self.node_label2index = {value: key for key, value in self.node_index2label.items()}

        # make bi-directional edges
        for e in topo_tmp:
            topology.add_edge(self.node_label2index[e[0]], self.node_label2index[e[2]])
            topology.add_edge(self.node_label2index[e[2]], self.node_label2index[e[0]])
        
        # make allocatorunit
        self.au = AllocatorUnit(topology)

    # genaration of vNode_id: it is used only when you create a new VNode
    ##---------------------------------------------------------
    def __generate_vNode_id(self):
        givenId = self.__vNode_id
        self.__vNode_id += 1
        return givenId
    
    # genaration of pair_id: it is used only when you create a new Pair
    ##---------------------------------------------------------
    def __generate_pair_id(self):
        givenId = self.__pair_id
        self.__pair_id += 1
        return givenId

    # genaration of flow_id: it is used only when you find a new flow label
    ##---------------------------------------------------------
    def __generate_flow_id(self):
        givenId = self.__flow_id
        self.__flow_id += 1
        return givenId
    
    # genaration of app_id: it is used only when you create a new App
    ##---------------------------------------------------------
    def __generate_app_id(self):
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
        label2vNode_id = {label:self.__generate_vNode_id() for label in vNode_label_list} # a dictionary for _id
        list_tmp = list(r[2] for r in comm_tmp)
        list_tmp = list(set(list_tmp))
        label2flow_id = {label:self.__generate_flow_id() for label in list_tmp} # a dictionary for flow_id

        # convert label to id
        comm_tmp = [[label2vNode_id[pair[0]], label2vNode_id[pair[1]], label2flow_id[pair[2]]] \
                    for pair in comm_tmp]
        flow_tmp = {flow_id: [(pair[0], pair[1]) for pair in comm_tmp if pair[2] == flow_id] \
                    for flow_id in label2flow_id.values()}
        
        # make Flows and Pairs
        pair_list = list()
        flow_list = list()
        for flow_id, flow in flow_tmp.items():
            tmp_pair_list = [Pair(self.__generate_pair_id(), pair[0], pair[1]) for pair in flow]
            flow_list.append(Flow(flow_id, tmp_pair_list))
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
        app = App(self.__generate_app_id(), vNode_list, flow_list, pair_list)
        if self.au.add_app(app):
            color = self.color_pool.pop(random.randrange(len(self.color_pool)))
            self.app_id2vitrualizer[app.app_id] \
            = AppVirtualizer(label2vNode_id, label2flow_id, \
                             os.path.abspath(communicationFile), color)
            return True
        else:
            return False
    
    ##---------------------------------------------------------
    def remove_app(self, app_id):
        if app_id not in self.app_id2vitrualizer.keys():
            raise ValueError("app_id {} does not exists.".format(app_id))
        # remove from au
        self.au.remove_app(app_id)
        # restore color to color_pool
        self.color_pool.append(self.app_id2vitrualizer[app_id].color)
        # delete the virtaulizer
        del self.app_id2vitrualizer[app_id]
    
    ##---------------------------------------------------------
    def run_optimization(self, max_execution_time, method, process_num=1):
        print("selected method: {}".format(method))
        if method.lower() == '2-opt':
            self.au = alns.alns2(self.au, max_execution_time)
        elif method.lower() == 'alns':
            self.au = alns.alns(self.au, max_execution_time)
        elif method.lower() == 'nsga2':
            seed = self.au.save_au()
            nsga2 = NSGA2(seed)
            hall_of_fame, logbook = nsga2.run(max_execution_time, process_num)
            print(logbook.stream)
            print("# of individuals in hall_of_fame: {}".format(len(hall_of_fame)))
            indbook = tools.Logbook()
            eval_name_list = Evaluator().eval_list()
            indbook.header = ['index'] + eval_name_list
            for i, ind in enumerate(hall_of_fame):
                record = {name: value for name, value in zip(eval_name_list, ind.fitness.values)}
                indbook.record(index=i, **record)
            print(indbook.stream)
        elif method.lower() == 'ncga':
            seed = self.au.save_au()
            ncga = NCGA(seed)
            hall_of_fame, logbook = ncga.run(max_execution_time, process_num)
            print(logbook.stream)
            print("# of individuals in hall_of_fame: {}".format(len(hall_of_fame)))
            indbook = tools.Logbook()
            eval_name_list = Evaluator().eval_list()
            indbook.header = ['index'] + eval_name_list
            for i, ind in enumerate(hall_of_fame):
                record = {name: value for name, value in zip(eval_name_list, ind.fitness.values)}
                indbook.record(index=i, **record)
            print(indbook.stream)
        elif method.lower() == 'spea2':
            seed = self.au.save_au()
            spea2 = SPEA2(seed)
            hall_of_fame, logbook = spea2.run(max_execution_time, process_num)
            print(logbook.stream)
            print("# of individuals in hall_of_fame: {}".format(len(hall_of_fame)))
            indbook = tools.Logbook()
            eval_name_list = Evaluator().eval_list()
            indbook.header = ['index'] + eval_name_list
            for i, ind in enumerate(hall_of_fame):
                record = {name: value for name, value in zip(eval_name_list, ind.fitness.values)}
                indbook.record(index=i, **record)
            print(indbook.stream)
        else:
            raise ValueError("Invalid optimization method name.")
        
        self.au.apply()
    
    ##---------------------------------------------------------
    def two_opt(self, execution_time):
        self.au = alns.alns2(self.au, execution_time)
        self.au.apply()

    ##---------------------------------------------------------
    def show_topology_file(self):
        print(self.topology_file)

    ##---------------------------------------------------------
    def show_apps(self, key=lambda app_id: True):
        apps_book = tools.Logbook()
        apps_book.header = ['app_id', 'communication', 'date']
        for app_id, appv in sorted(self.app_id2vitrualizer.items(), key=lambda item: item[0]):
            if key(app_id):
                apps_book.record(app_id=app_id, communication=os.path.basename(appv.communicationFile), date=appv.date)
        
        print(apps_book.stream)
        print()

    ##---------------------------------------------------------
    def show_nodes(self, key=lambda app_id, vNode_id, rNode_id: True):
        nodes_book = tools.Logbook()
        nodes_book.header = ['app_id', 'vNode_id', 'rNode_id']
        for app_id, app in sorted(self.au.app_dict.items(), key=lambda item: item[0]):
            for vNode in sorted(app.vNode_list, key=lambda vn: self.app_id2vitrualizer[app_id].vNode_id2label[vn.vNode_id]):
                vNode_id = self.app_id2vitrualizer[app_id].vNode_id2label[vNode.vNode_id]
                rNode_id = vNode.rNode_id
                if key(app_id, vNode_id, rNode_id):
                    nodes_book.record(app_id=app_id, vNode_id=vNode_id, rNode_id=rNode_id)
        
        print(nodes_book.stream)
        print()
    
    ##---------------------------------------------------------
    def show_flows(self, key=lambda app_id, flow_id, slot_id: True):
        flows_book = tools.Logbook()
        flows_book.header = ['app_id', 'flow_id', 'slot_id']
        for app_id, app in sorted(self.au.app_dict.items(), key=lambda item: item[0]):
            for flow in sorted(app.flow_list, key=lambda f: self.app_id2vitrualizer[app_id].flow_id2label[f.flow_id]):
                flow_id = self.app_id2vitrualizer[app_id].flow_id2label[flow.flow_id]
                slot_id = flow.slot_id
                if key(app_id, flow_id, slot_id):
                    flows_book.record(app_id=app_id, flow_id=flow_id, slot_id=slot_id)
        
        print(flows_book.stream)
        print()
    
    ##---------------------------------------------------------
    def print_result(self, fully_desplay=False):
        if len([vNode for vNode in self.au.vNode_dict.values() if vNode.rNode_id is not None]) == 0:
            print("the current allocator has no running app.")
            return

        if fully_desplay:
            self.au.print_au()
        
        if len([pair for pair in self.au.pair_dict.values() if pair.path is not None]) != 0:
            print("# of slots: {}".format(self.au.get_greedy_slot_num()))
            print("# of hops: {}".format(self.au.get_total_communication_hops()))
            print("# of boards to be routed: {}".format(self.au.board_num_to_be_routed()))
        else:
            print("the current allocator has no running app with communication.")
        
        self.draw_current_node_status()
    
    ##---------------------------------------------------------
    def draw_current_node_status(self, path=os.path.join(FIG_DIR, (default_filename()+'.png'))):
        ## settings for position
        pos = {i: (-(i // 4), i % 4) for i in self.node_index2label.keys()}
        ## settings for color
        used_nodes_for_app = {app.app_id: [vNode.rNode_id for vNode in app.vNode_list] for app in self.au.app_dict.values()}
        node_color = ['gainsboro' for i in self.node_index2label.keys()]
        for app_id, used_nodes in used_nodes_for_app.items():
            for node in used_nodes:
                node_color[node] = self.app_id2vitrualizer[app_id].color
        # draw
        nx.draw_networkx(self.au.topology, pos, node_color=node_color)
        plt.savefig(path)
        plt.close()

#--------------------------------------------------------------
if __name__ == '__main__':
    args = parser()
    clean_dir(FIG_DIR)
    actor = BoardAllocator(args.t)
    actor.load_app(args.c)
    #actor.run_optimization(args.s + 60 * args.m + 3600 * args.ho, args.method, args.p)
    #actor.show_apps()
    #actor.show_nodes()
    #actor.show_flows()
    actor.load_app(args.c)
    actor.run_optimization(args.s + 60 * args.m + 3600 * args.ho, args.method, args.p)
    actor.show_apps()
    actor.show_nodes()
    actor.show_flows()
    actor.print_result()
    actor.remove_app(0)
    actor.show_apps()
    actor.show_nodes()
    actor.show_flows()
    actor.print_result()
    
    print(" ### OVER ### ")