import argparse
import json
import sys, traceback
import os
import os.path
import shutil
import numpy as np
import collections
from collections import OrderedDict
import copy

OUTPUT_DIR = "output"
TABLE_FILE_NAME = "board"
FLOW_FILE_NAME = "flow"
LOG_FILE_NAME = "log"
TABLE_FILE = OUTPUT_DIR + "/" + TABLE_FILE_NAME
FLOW_FILE = OUTPUT_DIR + "/" + FLOW_FILE_NAME
LOG_FILE = OUTPUT_DIR + "/" + LOG_FILE_NAME

# FiC board list
MK1_LIST = ["fic00", "fic01", "fic02", "fic03",
            "fic04", "fic05", "fic06", "fic07",
            "fic08", "fic09", "fic10", "fic11"]
MK2_LIST = ["m2fic00", "m2fic01", "m2fic02", "m2fic03",
            "m2fic04", "m2fic05", "m2fic06", "m2fic07",
            "m2fic08", "m2fic09", "m2fic10", "m2fic11"]
FIC_LIST = MK1_LIST + MK2_LIST

#--------------------------------------------------------------
class Tree:
    def __init__(self, node_num):
        self.matrix = [[0] * (node_num + 1) for i in range(node_num + 1)]
        self.path_list = list()
        self.weight = 0

#--------------------------------------------------------------
class Flow:
    def __init__(self, id, ID):
        self.pairs_id = list()
        self.id = id
        self.channels = list()
        self.ID = ID

#--------------------------------------------------------------
class Pair:
    def __init__(self, src, dst, h_src, h_dst):
        self.src = src
        self.dst = dst
        self.h_src = h_src
        self.h_dst = h_dst
        self.pair_id = None
        self.flow_id = -1
        self.ID = -1
        self.Valid = False
        self.hops = -1
        self.channels = list()

#--------------------------------------------------------------
class Cross_Paths:
    def __init__(self):
        self.pair_index = list()
        self.flow_index = list()
        self.assigned_list = list()
        self.assigned_dst_list = list()
        self.Valid = False
        self.routing_table = list()

#--------------------------------------------------------------
def cleanDir(s):
    if os.path.isdir(s):
        shutil.rmtree(s)
    os.mkdir(s)

#--------------------------------------------------------------
def minDistance(dist:list, sptSet:list, V:int):
    min_value = 10000
    min_list = list()

    for v in range(0, V):
        if (not sptSet[v]) and (dist[v] < min_value):
            min_value = dist[v]
            min_list = [v]
        elif (not sptSet[v]) and (dist[v] == min_value):
            min_list.append(v)

    return min_list

#--------------------------------------------------------------
def printPath(parent:list, j:int, src:int, dst:int, pair_paths:list, V:int, path:list):
    if parent[j] == []:
        if j == src:
            path.reverse()
            pair_paths[src * V + dst].append(path)
        return

    path.append(j)
    
    for p in parent[j]:
        printPath(parent, p, src, dst, pair_paths, V, copy.deepcopy(path))

#--------------------------------------------------------------
def printSolution(V:int, parent:list, src:int, pair_paths:list):
    for i in range(0, V):
        if i != src:
            dst = i
            printPath(parent, i, src, dst, pair_paths, V, list())

#--------------------------------------------------------------
def dijkstra(V:int, graph:list, src:int, pair_paths:list):
    dist = [10000] * V
    sptSet = [False] * V
    parent = [list() for i in range(0, V)]

    dist[src] = 0

    for count in range(0, V - 1):
        u_list = minDistance(dist, sptSet, V)

        for u in u_list:
            sptSet[u] = True

            for v in range(0, V):
                if (not sptSet[v]) and graph[u * V + v] and (dist[u] + graph[u * V + v] < dist[v]):
                    parent[v].append(u)
                    dist[v] = dist[u] + graph[u * V + v]
                elif (not sptSet[v]) and graph[u * V + v] and (dist[u] + graph[u * V + v] == dist[v]):
                    parent[v].append(u)
    
    printSolution(V, parent, src, pair_paths)

#--------------------------------------------------------------
class cstgen:
    def __init__(self, topology_file, comm_partern_file, maxSlots, isSlotLimited):
        self.topology_file = topology_file
        self.comm_partern_file = comm_partern_file
        self.maxSlots = maxSlots
        self.isSlotLimited = isSlotLimited
        self.Host_Num = 1
        self.topo_file = None
        self.topo_sws_uni = None
        self.switch_num = 0
        self.degree = 0
        self.ports = None
        self.ports_p_sw = None
        self.Crossing_Paths = None
        self.Switch_Topo = None #length: self.ports
        self.ct = None
        self.hops = None
        self.pairs = None
        self.flows = None
        self.max_cp = float('inf')
        self.isInit_writeLog = True
        self.writeLog_str = ""
        self.isInit_writeFlow = None
        self.lane_num = 1
        self.tableList = list()
        self.pair_paths = None
        self.tree_list = list()

    ##---------------------------------------------------------
    def writeLog(self, s):
        if self.isInit_writeLog:
            f = open(LOG_FILE, 'w')
        else:
            f = open(LOG_FILE, 'a')
        f.write(s)
        f.close()
        self.isInit_writeLog = False

    ##---------------------------------------------------------
    def writeFlow(self, flow:int, s):
        file_name = "{0:s}{1:d}".format(FLOW_FILE, flow)
        if self.isInit_writeFlow[flow]:
            f = open(file_name, 'w')
        else:
            f = open(file_name, 'a')
        f.write(s)
        f.close()
        self.isInit_writeFlow[flow] = False

    ##---------------------------------------------------------
    def readTopologyFile(self):
        self.topo_file = np.loadtxt(self.topology_file, dtype='int').tolist()
        topo_sws_dup = list(r[0] for r in self.topo_file) + list(r[2] for r in self.topo_file) #duplicate
        self.topo_sws_uni = list(set(topo_sws_dup)) #unique
        self.switch_num = len(self.topo_sws_uni)
        self.degree = max(collections.Counter(topo_sws_dup).values())
        self.ports = ((self.switch_num - 1) + 1 + 2 * self.Host_Num) * self.switch_num
        self.ports_p_sw = ((self.switch_num - 1) + 1 + 2 * self.Host_Num)

    ##---------------------------------------------------------
    def searchSPT(self):
        self.Switch_Topo = [-1] * self.ports

        # create topology list
        for topo_elm in self.topo_file:
            i0 = self.topo_sws_uni.index(topo_elm[0])
            connect_sw0 = topo_elm[2]
            connect_port0 = topo_elm[1]
            k0 = self.topo_sws_uni.index(connect_sw0)
            self.Switch_Topo[i0 * self.ports_p_sw + k0] = connect_port0
            i1 = self.topo_sws_uni.index(topo_elm[2])
            connect_sw1 = topo_elm[0]
            connect_port1 = topo_elm[3]
            k1 = self.topo_sws_uni.index(connect_sw1)
            self.Switch_Topo[i1 * self.ports_p_sw + k1] = connect_port1
        
        # create graph (0: not connect, 1: connect)
        V = self.switch_num
        graph = list()
        for i in range(0, V * V):
            if self.Switch_Topo[(i // V) * self.ports_p_sw + (i % V)] == -1:
                graph.append(0)
            else:
                graph.append(1)

        # dijsktra
        self.pair_paths = [[] for i in range(0, V * V)]
        for i in range(0, V):
            dijkstra(V, graph, i, self.pair_paths)
        
        #for src in range(V):
        #    for dst in range(V):
        #        print("====src: {}, dst: {}====".format(src, dst))
        #        for elm in self.pair_paths[src * V + dst]:
        #            print(elm)
        #exit(0) #for debug

    ##---------------------------------------------------------
    def raedCommunicationPatern(self):
        self.comm_list = np.loadtxt(self.comm_partern_file, dtype='int').tolist()

    # return values: 
    ##---------------------------------------------------------
    def routing(self, pair_path:list):
        V = self.switch_num
        isOutOfBounds = False
        Crossing_Paths = [Cross_Paths() for i in range(0, self.ports)]
        pairs = list()
        flows = list()
        hops = 0
        ct = 0

        for comm in self.comm_list:
            h_src = comm[0]
            src = h_src // self.Host_Num
            h_dst = comm[1]
            dst = h_dst // self.Host_Num
            flowid = comm[2]

            pairs.append(Pair(src, dst, h_src, h_dst))
            try:
                src_index = self.topo_sws_uni.index(src)
            except ValueError:
                print("Error: src number ({0}) is wrong.".format(h_src), sys.stderr)
                self.writeLog_str += "Error: src number ({0}) is wrong.".format(h_src)
                self.writeLog(self.writeLog_str)
                sys.exit(3)
            try:
                dst_index = self.topo_sws_uni.index(dst)
            except ValueError:
                print("Error: dst number ({0}) is wrong.".format(h_dst), sys.stderr)
                self.writeLog_str += "Error: dst number ({0}) is wrong.".format(h_dst)
                self.writeLog(self.writeLog_str)
                sys.exit(4)

            #localhost(h_src) --> src
            t = src_index * self.ports_p_sw + (self.switch_num - 1) + 1 + h_src % self.Host_Num
            Crossing_Paths[t].pair_index.append(ct)
            pairs[ct].channels.append(t)
            pairs[ct].pair_id = ct
            pairs[ct].flow_id = flowid
            f = Flow(flowid, -1)
            f.pairs_id.append(ct)
            f.channels.append(t)
            flows.append(f)
            Crossing_Paths[t].flow_index.append(flowid)
            pairs[ct].hops = len(pair_path[src_index * V + dst_index]) + 1
            hops += pairs[ct].hops

            #src --> dst
            i = 0
            for pair_elm in pair_path[src_index * V + dst_index]:
                if i == 0:
                    t = src_index * self.ports_p_sw + pair_elm
                else:
                    t = pre_pair_elm * self.ports_p_sw + pair_elm
                Crossing_Paths[t].pair_index.append(ct)
                pairs[ct].channels.append(t)
                flows[len(flows) - 1].channels.append(t)
                Crossing_Paths[t].flow_index.append(flowid)
                pre_pair_elm = pair_elm
                i += 1
            
            #dst --> localhost(h_dst)
            t = dst_index * self.ports_p_sw + (self.switch_num - 1) + 1 + self.Host_Num + h_dst % self.Host_Num
            Crossing_Paths[t].pair_index.append(ct)
            pairs[ct].channels.append(t)
            flows[len(flows) - 1].channels.append(t)
            Crossing_Paths[t].flow_index.append(flowid)

            ct += 1

        # merge the elements of flows whose flow_id is same
        flows.sort(key=lambda x: x.id)
        pre_flow_id = -1
        new_flows = list()
        for f in flows:
            flowid = f.id
            if pre_flow_id != flowid:
                new_flows.append(f)
            else:
                new_flows[len(new_flows) - 1].pairs_id += f.pairs_id
                new_flows[len(new_flows) - 1].channels += f.channels
            pre_flow_id = flowid
        flows = new_flows

        return isOutOfBounds, Crossing_Paths, pairs, flows, hops, ct

    # return values: max_cp, flows, Crossing_Paths, pairs
    ##---------------------------------------------------------
    def slotAlloc(self, Crossing_Paths, pairs, flows):
        # erase duplicates
        for elm in Crossing_Paths:
            elm.flow_index = list(set(elm.flow_index))
        for f in flows:
            f.channels = list(set(f.channels))

        # slot allocation
        ID_max = 0
        max_id = 0
        tmp_max_cp_elm = max(Crossing_Paths, key=lambda x: len(x.flow_index))
        tmp_max_cp = len(tmp_max_cp_elm.flow_index)
        max_cp = 0
        for elm in Crossing_Paths:
            if tmp_max_cp > max_cp:
                max_cp = tmp_max_cp
                elm = tmp_max_cp_elm
            path_ct = 0
            while path_ct < len(elm.flow_index):
                t = elm.flow_index[path_ct]
                valid = True
                for i in flows[t].pairs_id:
                    if not pairs[i].Valid:
                        valid = False
                        break
                if valid:
                    path_ct += 1
                    continue
                
                id_tmp = 0
                NG_ID = False

                #NEXT_ID_FLOW
                while True:
                    s_ct = 0
                    while (s_ct < len(flows[t].channels)) and (not NG_ID):
                        i = flows[t].channels[s_ct]
                        try:
                            find_index = Crossing_Paths[i].assigned_list.index(id_tmp)
                        except ValueError:
                            pass
                        else:
                            NG_ID = True

                        s_ct += 1
                    if NG_ID:
                        id_tmp += 1
                        NG_ID = False
                    else:
                        break

                flows[t].ID = id_tmp
                if id_tmp > ID_max:
                    ID_max = id_tmp
                
                a_ct = 0
                while a_ct < len(flows[t].channels):
                    tmp_j = flows[t].channels[a_ct]
                    Crossing_Paths[tmp_j].assigned_list.append(id_tmp)
                    t = elm.flow_index[path_ct]
                    for n in flows[t].pairs_id:
                        Crossing_Paths[tmp_j].assigned_dst_list.append(pairs[n].h_dst)
                    a_ct += 1
                
                for n in flows[t].pairs_id:
                    pairs[n].Valid = True
                if max_id <= id_tmp:
                    max_id = id_tmp + 1
                
                path_ct += 1
            elm.Valid = True

        # reassing slot # in ascending order based on flow id
        slots = list()
        for flowid in range(0, len(flows)):
            if not (flows[flowid].ID in slots):
                slots.append(flows[flowid].ID)
        for flowid in range(0, len(flows)):
            for n in range(0, len(slots)):
                if flows[flowid].ID == slots[n]:
                    flows[flowid].ID = n
                    break
        
        return ID_max + 1

    ##---------------------------------------------------------
    def findBestSolution(self):
        V = self.switch_num

        #abstruct the required pair_path
        pair_paths_for_comm_list = [[[]] for i in range(0, V * V)]
        for comm in self.comm_list:
            src = comm[0]
            dst = comm[1]
            flowid = comm[2]
            if len(self.tree_list) <= flowid:
                self.tree_list.append([Tree(V)])
            
            new_list = list()
            for p_tree in self.tree_list[flowid]:
                for elm in self.pair_paths[src * V + dst]:
                    # update the tree object
                    tree = copy.deepcopy(p_tree)
                    parent = src
                    tree.matrix[parent][V] = 1
                    for child in elm:
                        if tree.matrix[parent][child] == 0:
                            tree.matrix[parent][child] = 1
                            tree.weight += 1
                        parent = child
                    path = [src] + elm
                    tree.path_list.append(path)

                    # append the tree object
                    new_list.append(tree)

            # update the list
            self.tree_list[flowid] = new_list
        
        for elm in self.tree_list:
            elm.sort(key=lambda x: x.weight)

        # for debug --------------------------------------------------
        print("matrix:")
        for elm in self.tree_list[0][0].matrix:
            print(elm)
        print("paths:")
        for elm in self.tree_list[0][0].path_list:
            print(elm)
        print("weight: {}".format(self.tree_list[0][0].weight))

        i = 0
        tmp = 1
        for elm in self.tree_list:
            print("flowid {}: # of trees = {}".format(i, len(elm)))
            tmp *= len(elm)
            i += 1
        
        i = 0
        for elm in self.tree_list[0]:
            print("index {}: weight = {}".format(i, elm.weight))
            i += 1
        exit(0)
        #-------------------------------------------------------------
        
        #generate the combination
        isbegin = True
        for elm in pair_paths_for_comm_list:
            if isbegin:
                pair_path_list = [copy.deepcopy(elm)]
                isbegin = False
            else:
                next_pair_path_list = list()
                for p in pair_path_list:
                    for e in elm:
                        tmp = copy.deepcopy(p)
                        tmp.append(e)
                        next_pair_path_list.append(tmp)
                pair_path_list = next_pair_path_list
        
        #search for the combination
        for pair_path in pair_path_list:
            isOutOfBounds, Crossing_Paths, pairs, flows, hops, ct = self.routing(pair_path)
            if isOutOfBounds:
                continue
            max_cp = self.slotAlloc(Crossing_Paths, pairs, flows)
            if max_cp < self.max_cp:
                self.Crossing_Paths = Crossing_Paths
                self.pairs = pairs
                self.flows = flows
                self.hops = hops
                self.ct = ct
                self.max_cp = max_cp
        
        self.isInit_writeFlow = [True] * len(self.flows)

    # required values: pairs, Crossing_Paths, flows, max_cp
    ##---------------------------------------------------------
    def showPath(self):
        self.writeLog_str += " === # of slots === \n"
        self.writeLog_str += "{}\n".format(self.max_cp)
        if not self.isSlotLimited:
            slots = self.max_cp
        elif self.isSlotLimited and (self.max_cp <= self.maxSlots):
            slots = self.maxSlots
        else:
            print("Error: # of slots is larger than the specified value.", sys.stderr)
            self.writeLog_str += "Error: # of slots is larger than the specified value."
            self.writeLog(self.writeLog_str)
            sys.exit(8)

        for elm_cp in self.Crossing_Paths:
            ID_array = [-1] * len(elm_cp.pair_index)
            for elm_pi in elm_cp.pair_index:
                ID_array.append(self.pairs[elm_pi].ID)
            ID_array.sort()
            k = 0
            error = False
            while (k + 1 < len(ID_array)) and (not error):
                if (ID_array[k] == ID_array[k + 1]) and (ID_array[k] != -1):
                    error = True
                k += 1
            if error:
                print("Error: Slot # collision is occured.", sys.stderr)
                self.writeLog_str += "Error: Slot # collision is occured."
                self.writeLog(self.writeLog_str)
                sys.exit(5)
        
        port = 0
        self.writeLog_str += " === Number of slots === \n"
        self.writeLog_str += " SW0, SW1, SW2, SW3, ..., out, in\n"

        self.writeLog_str += " SW {:2d}:".format(port // self.ports_p_sw)
        for elm_cp in self.Crossing_Paths:
            if len(self.flows) == 0:
                self.writeLog_str += " {}".format(len(elm_cp.pair_index))
            else:
                self.writeLog_str += " {}".format(len(elm_cp.flow_index))
            port += 1
            if port % self.ports_p_sw == 0:
                self.writeLog_str += "\n"
                if port != self.ports_p_sw * self.switch_num:
                    self.writeLog_str += " SW {:2d}:".format(port // self.ports_p_sw)

        for elm_cp in self.Crossing_Paths:
            elm_cp.Valid = True
        
        self.writeLog_str += " === The number of paths on this application ===\n"
        self.writeLog_str += "{0} (all-toall cases: {1})\n".format(self.ct, (self.switch_num * self.Host_Num) * (self.switch_num * self.Host_Num - 1))
        self.writeLog_str += " === The average hops ===\n"
        self.writeLog_str += "{}\n".format(self.hops / self.ct)
        
        self.writeLog_str += " === Routing path for each node pair ===\n"
        for current_pair in self.pairs:
            slot_num = self.flows[current_pair.flow_id].ID

            self.writeLog_str += " Pair ID {0} (Flow ID {1}): \n".format(current_pair.pair_id, current_pair.flow_id)
            self.writeFlow(current_pair.flow_id, "{0} {1} {2}\n".format(current_pair.src, current_pair.dst, slot_num))

            try:
                src_index = self.topo_sws_uni.index(current_pair.src)
            except ValueError:
                print("Error: src number ({0}) is wrong.".format(current_pair.src), sys.stderr)
                self.writeLog_str += "Error: src number ({0}) is wrong.".format(current_pair.src)
                self.writeLog(self.writeLog_str)
                sys.exit(6)
        
            try:
                dst_index = self.topo_sws_uni.index(current_pair.dst)
            except ValueError:
                print("Error: dst number ({0}) is wrong.".format(current_pair.dst), sys.stderr)
                self.writeLog_str += "Error: dst number ({0}) is wrong.".format(current_pair.dst)
                self.writeLog(self.writeLog_str)
                sys.exit(7)
        
            for j in range(1, len(current_pair.channels)):
                input_port = 0
                output_port = 0
                if j == 1:
                    target_sw = current_pair.src
                    output_port = self.Switch_Topo[current_pair.channels[j]]
                    self.writeLog_str += "   SW {0:d} (port {1:d}->{2:d}) - [slot {3:d}] -> ".format(target_sw, input_port, output_port, slot_num)
                elif j == len(current_pair.channels) - 1:
                    target_sw = current_pair.dst
                    input_port = self.Switch_Topo[dst_index * self.ports_p_sw + current_pair.channels[j - 1] // self.ports_p_sw]
                    self.writeLog_str += "SW {0:d} (port {1:d}->{2:d})".format(target_sw, input_port, output_port)
                else:
                    target_sw = current_pair.channels[j] // self.ports_p_sw
                    output_port = self.Switch_Topo[current_pair.channels[j]]
                    input_port = self.Switch_Topo[target_sw * self.ports_p_sw + current_pair.channels[j - 1] // self.ports_p_sw]
                   
                    self.writeLog_str += "SW {0:d} (port {1:d}->{2:d}) - [slot {3:d}] -> ".format(self.topo_sws_uni[target_sw], input_port, output_port, slot_num)

                self.Crossing_Paths[current_pair.channels[j]].routing_table.append(input_port)
                self.Crossing_Paths[current_pair.channels[j]].routing_table.append(slot_num)
                self.Crossing_Paths[current_pair.channels[j]].routing_table.append(current_pair.h_src)
                self.Crossing_Paths[current_pair.channels[j]].routing_table.append(current_pair.h_dst)
                self.Crossing_Paths[current_pair.channels[j]].routing_table.append(current_pair.pair_id)
            self.writeLog_str += "\n"
        
        self.writeLog_str += " === Port information for each switch === \n"
        for i in range(0, self.switch_num):
            self.writeLog_str += " SW {} : \n".format(self.topo_sws_uni[i])
            tablesetdict = OrderedDict()
            tablesetdict["slots"] = slots
            tablesetdict["ports"] = self.degree + 1
            tablesetdict["switches"] = self.lane_num # for multi-lane
            tablesetdict["table"] = OrderedDict()

            for lane_id in range(0, self.lane_num):
                lane_str = "switch{}".format(lane_id)
                tablesetdict["table"][lane_str] = OrderedDict()
                slot_occupied = False
                index = self.ports_p_sw * i + (self.switch_num - 1) + 2 * self.Host_Num
                
                #port 0
                tablesetdict["table"][lane_str]["port0"] = OrderedDict()
                for s in range(0, slots):
                    slot_str = "slot{}".format(s)
                    if len(self.Crossing_Paths[index].routing_table) > 0:
                        for j in range(0, len(self.Crossing_Paths[index].routing_table), 5):
                            if self.Crossing_Paths[index].routing_table[j + 1] == s: 
                                tablesetdict["table"][lane_str]["port0"][slot_str] = self.Crossing_Paths[index].routing_table[j]
                                slot_occupied = True
                                self.writeLog_str += "      Port {}".format(self.Crossing_Paths[index].routing_table[j])
                                self.writeLog_str += " (Slot {}".format(self.Crossing_Paths[index].routing_table[j + 1])
                                self.writeLog_str += ") --> Port 0 (Slot {}".format(self.Crossing_Paths[index].routing_table[j + 1])
                                self.writeLog_str += "), from node {}".format(self.Crossing_Paths[index].routing_table[j + 2])
                                self.writeLog_str += " to node {}".format(self.Crossing_Paths[index].routing_table[j + 3])
                                self.writeLog_str += " (Pair ID {}".format(self.Crossing_Paths[index].routing_table[j + 4])
                                self.writeLog_str += ",Flow ID {})\n".format(self.pairs[self.Crossing_Paths[index].routing_table[j + 4]].flow_id)
                    if not slot_occupied:
                        tablesetdict["table"][lane_str]["port0"][slot_str] = self.degree + 1
                    slot_occupied = False

                for n in range(1, self.degree + 1):
                    port_str = "port{}".format(n)
                    tablesetdict["table"][lane_str][port_str] = OrderedDict()
                    for op in range(0, (self.switch_num - 1) + 1):
                        index = self.ports_p_sw * i + op
                        out_port = self.Switch_Topo[index]
                        if (out_port == n):
                            for s in range(0, slots):
                                slot_str = "slot{}".format(s)
                                temp_ip = list()
                                if len(self.Crossing_Paths[index].routing_table) > 0:
                                    for j in range(0, len(self.Crossing_Paths[index].routing_table), 5):
                                        if self.Crossing_Paths[index].routing_table[j + 1] == s:
                                            input_port = self.Crossing_Paths[index].routing_table[j]
                                            if not (input_port in temp_ip):
                                                tablesetdict["table"][lane_str][port_str][slot_str] = input_port
                                                temp_ip.append(input_port)

                                            slot_occupied = True
                                            self.writeLog_str += "      Port {}".format(input_port)
                                            self.writeLog_str += " (Slot {}".format(self.Crossing_Paths[index].routing_table[j + 1])
                                            self.writeLog_str += ") --> Port {0} (Slot {1}".format(out_port, self.Crossing_Paths[index].routing_table[j + 1])
                                            self.writeLog_str += "), from node {}".format(self.Crossing_Paths[index].routing_table[j + 2])
                                            self.writeLog_str += " to node {}".format(self.Crossing_Paths[index].routing_table[j + 3])
                                            self.writeLog_str += " (Pair ID {}".format(self.Crossing_Paths[index].routing_table[j + 4])
                                            self.writeLog_str += ",Flow ID {})\n".format(self.pairs[self.Crossing_Paths[index].routing_table[j + 4]].flow_id)

                                if not slot_occupied:
                                    tablesetdict["table"][lane_str][port_str][slot_str] = self.degree + 1
                                slot_occupied = False
            
            #register table
            self.tableList.append(tablesetdict)
            #write json file
            json_file_name = "{0:s}{1:d}.json".format(TABLE_FILE, self.topo_sws_uni[i])
            wf = open(json_file_name, 'w')
            json.dump(tablesetdict, wf, indent=4)
            wf.close()

        #write log if it is successful
        self.writeLog(self.writeLog_str)

    ##---------------------------------------------------------
    def main(self):
        cleanDir(OUTPUT_DIR)
        #topofile
        #comm_file
        self.readTopologyFile()
        self.searchSPT()
        self.raedCommunicationPatern()
        self.findBestSolution()
        self.showPath()

    ##---------------------------------------------------------
    def flowid2slotid(self, flowid:int):
        return self.flows[flowid].ID

    ##---------------------------------------------------------
    def table(self, board:str):
        index = self.topo_sws_uni.index(FIC_LIST.index(board))
        return self.tableList[index]

#--------------------------------------------------------------
class cstgenCaller:
    def __init__(self):
        self.args = None
        self.isSlotLimited = False
    
    ##---------------------------------------------------------
    def argparse(self):
        parser = argparse.ArgumentParser(description='cstgen')

        parser.add_argument('-t', help='topology file', default='fic-topo-file-cross.txt')
        parser.add_argument('-c', help='communication partern (traffic file)', required=True)
        parser.add_argument('-s', help='the number of slots', type=int)

        self.args = parser.parse_args()

        if not os.path.isfile(self.args.t):
            print("Error: {0:s} was not found.".format(self.args.t), sys.stderr)
            sys.exit(1)
        
        if not os.path.isfile(self.args.c):
            print("Error: {0:s} was not found.".format(self.args.c), sys.stderr)
            sys.exit(2)
        
        if self.args.s is not None:
            self.isSlotLimited = True

    ##---------------------------------------------------------
    def main(self):
        self.argparse()
        actor = cstgen(self.args.t, self.args.c, self.args.s, self.isSlotLimited)
        actor.main()
        print(" !!! Routing tables for each sw are saved to output/ !!!")
        print(" ### OVER ###")

#--------------------------------------------------------------
if __name__ == '__main__':
    obj = cstgenCaller()
    obj.main()