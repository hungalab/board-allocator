import pickle

import networkx as nx

#--------------------------------------------------------------
def slot_encrypt(slot):
    return -(slot + 1)

#--------------------------------------------------------------
def slot_decrypt(encripted_slot):
    return -(encripted_slot + 1)

#--------------------------------------------------------------
class App:
    def __init__(self, app_id, vNode_list, flow_list, pair_list):
        self.app_id = app_id
        self.vNode_list = vNode_list # list: list of vNodes of the App
        self.flow_list = flow_list # list: list of flows of the App
        self.pair_list = pair_list # list: list of pairs of the App

#--------------------------------------------------------------
class Pair:
    def __init__(self, pair_id, src, dst):
        self.pair_id = pair_id
        self.src = src
        self.dst = dst
        self.src_vNode = None
        self.dst_vNode = None
        self.path = None # using path list

#--------------------------------------------------------------
class Flow:
    def __init__(self, flow_id=None, pair_list=[]):
        self.flow_id = flow_id
        self.pair_list = pair_list
        self.slot_id = None
        self.flow_graph = None
    
    def make_flow_graph(self):
        self.flow_graph = nx.DiGraph()
        for pair in self.pair_list:
            path = pair.path
            nx.add_path(self.flow_graph, path)

    def merge(self, other):
        if self.flow_id is None:
            self.flow_id = slot_encrypt(other.slot_id)
        elif self.flow_id != slot_encrypt(other.slot_id):
            raise ValueError("The values of slot_id are different form each other.")
        if self.slot_id is None:
            self.slot_id = other.slot_id
        self.pair_list += other.pair_list

#--------------------------------------------------------------
class VNode:
    def __init__(self, vNode_id, send_pair_list, recv_pair_list):
        self.vNode_id = vNode_id # int: virtualized node ID
        self.send_pair_list = send_pair_list # list: list of pair to be sent by this VNode
        self.recv_pair_list = recv_pair_list # list: list of pair to be recieved by this VNode
        self.rNode_id = None # allocated node label (label is defined in topologyFile), 
                             # if the vNode is not allocated (including tmporary), the value is None

#--------------------------------------------------------------
class AllocatorUnitInitializationError(Exception):
    # This class is for errors related to AllocatorUnit constructor's arguments.
    pass

#--------------------------------------------------------------
class AllocatorUnit:
    def __init__(self, topology=None, seed=None):
        '''
        You can use this constructor in two ways.

        1) AllocatorUnit(topology=topology, seed=None)
        Create a brand new AllocatorUnit.

        2) AllocatorUnit(topology=None, seed=seed)
        Create an allocator unit with some applications (already in place or to be allocated).
        The 2nd argument "seed" can take 
            i)   a bytes object in which AllocatorUnit has been serialized by pickle, 
            ii)  a file in which the serialized bytes object has been saved by pickle, 
            iii) or AllocatorUnit.

        Note: AllocatorUnit(topology=topology, seed=seed) 
        and AllocationUnit(topology=None, seed=None)
        raise Error.
        '''
        if (topology is not None) and (seed is None):
            ## topology
            self.topology = topology # the topology for this allocator
            ## dictionaries (vNode, pair, app)
            self.vNode_dict = dict()
            self.flow_dict = dict()
            self.pair_dict = dict()
            self.app_dict = dict()
            ## allocating object lists
            self.allocating_vNode_list = list() # 1D list: the list of VNodes that are being allocated
            self.allocating_pair_list = list() # 1D list: the list of pairs that are being allocated
            ## manage the real node
            self.temp_allocated_rNode_dict = dict() # 1D dict: rNode_id |-> vNode_id
            self.empty_rNode_set = set(range(nx.number_of_nodes(self.topology))) # the set of rNodes that is not allocated (not including temp_allocated_rNode_dict)
            ## shortest path list
            self.st_path_table = None # 2D list: st_path_table[src][dst] = [path0, path1, ...] <return value is 1D list of path(1D list)>
            ## slot management
            self.flow_dict_for_slot_allocation = None 
            self.flow_dict_for_slot_allocation_valid = False

            # create st-path list
            node_num = nx.number_of_nodes(self.topology)
            self.st_path_table = [[[] for _ in range(0, node_num)] for _ in range(0, node_num)]
            for src in range(0, node_num):
                for dst in range(0, node_num):
                    for path in nx.all_shortest_paths(self.topology, src, dst):
                        self.st_path_table[src][dst].append([path[0]] + path)
        
        elif (topology is None) and (seed is not None):
            if isinstance(seed, AllocatorUnit):
                base = copy.deepcopy(seed)
            elif isinstance(seed, bytes):
                base = pickle.loads(seed)
            elif isinstance(seed, str):
                with open(seed, 'rb') as f:
                    base = pikcle.load(f)
            else:
                raise TypeError("The 2nd argument \"seed\" must be 'AllocationUnit', 'bytes', or 'str'.")

            ## topology
            self.topology = base.topology
            ## dictionaries (vNode, pair, app)
            self.vNode_dict = base.vNode_dict
            self.flow_dict = base.flow_dict
            self.pair_dict = base.pair_dict
            self.app_dict = base.app_dict
            ## allocating object lists
            self.allocating_vNode_list = base.allocating_vNode_list
            self.allocating_pair_list = base.allocating_pair_list
            ## manage the real node
            self.temp_allocated_rNode_dict = base.temp_allocated_rNode_dict
            self.empty_rNode_set = base.empty_rNode_set
            ## shortest path list
            self.st_path_table = base.st_path_table
            ## slot management
            self.flow_dict_for_slot_allocation = base.flow_dict_for_slot_allocation
            self.flow_dict_for_slot_allocation_valid = base.flow_dict_for_slot_allocation_valid

        else:
            raise AllocatorUnitInitializationError( \
            "Only one of the arguments of the AllocatorUnit constructor" \
            "should be specified, and the other should be None.")

    ##---------------------------------------------------------
    def add_app(self, app):
        # check whether the app can be mapped
        if len(self.vNode_dict) + len(app.vNode_list) > nx.number_of_nodes(self.topology):
            return False

        # add app
        self.app_dict[app.app_id] = app

        # add vNodes
        for vNode in app.vNode_list:
            self.vNode_dict[vNode.vNode_id] = vNode
            self.allocating_vNode_list.append(vNode)
        
        # add flows
        for flow in app.flow_list:
            self.flow_dict[flow.flow_id] = flow
        
        # add pairs
        for pair in app.pair_list:
            self.pair_dict[pair.pair_id] = pair
            self.allocating_pair_list.append(pair)
        
        return True
    
    ##---------------------------------------------------------
    def remove_app(self, app_id):
        # pop app_id (remove from dict and get app)
        app = self.app_dict.pop(app_id)

        # remove vNodes
        remove_vNode_id_set = {vNode.vNode_id for vNode in app.vNode_list}
        self.vNode_dict = {vNode_id: vNode for vNode_id, vNode in self.vNode_dict.items() \
                           if vNode_id not in remove_vNode_id_set}
        self.allocating_vNode_list = [vNode for vNode in self.allocating_vNode_list \
                                      if vNode.vNode_id not in remove_vNode_id_set]
        
        # remove vNodes
        remove_pair_id_set = {pair.pair_id for pair in app.pair_list}
        self.pair_dict = {pair_id: pair for pair_id, pair in self.pair_dict.items() \
                          if pair_id not in remove_pair_id_set}
        self.allocating_pair_list = [pair for pair in self.allocating_pair_list \
                                     if pair.pair_id not in remove_pair_id_set]
        
        # remove flows
        remove_flow_id_set = {flow.flow_id for flow in app.flow_list}
        self.flow_dict = {flow_id: flow for flow_id, flow in self.flow_dict.items() \
                          if flow_id not in remove_flow_id_set}
        self.flow_dict_for_slot_allocation_valid = False
    
    ##---------------------------------------------------------
    def apply(self):
        assert len(self.allocating_vNode_list) == len(self.temp_allocated_rNode_dict)

        # flush allocating lists
        self.allocating_vNode_list = list()
        self.allocating_pair_list = list()

        # apply rNode to corresponding vNode and flush temp_allocated_rNode_dict
        for rNode_id, vNode_id in self.temp_allocated_rNode_dict.items():
            self.vNode_dict[vNode_id].rNode_id = rNode_id
        self.temp_allocated_rNode_dict = dict()

        # apply slots and invalidate flow_dict_for_slot_allocation_valid
        flow_id2slot_id = self.greedy_slot_allocation()
        for flow_id, slot_id in flow_id2slot_id.items():
            if flow_id >= 0:
                self.flow_dict[flow_id].slot_id = slot_id
        self.flow_dict_for_slot_allocation_valid = False

    ##---------------------------------------------------------
    def set_flow_dict_for_slot_allocation(self):
        if not self.flow_dict_for_slot_allocation_valid:
            result = dict()
            for flow in self.flow_dict.values():
                if flow.slot_id is not None:
                    try:
                        result[slot_encrypt(flow.slot_id)].merge(flow)
                    except KeyError:
                        result[slot_encrypt(flow.slot_id)] = Flow()
                        result[slot_encrypt(flow.slot_id)].merge(flow)
                else:
                    result[flow.flow_id] = flow

            for flow in result.values():
                flow.make_flow_graph()

            self.flow_dict_for_slot_allocation = result
            self.flow_dict_for_slot_allocation_valid = True

    ##---------------------------------------------------------
    def optimal_slot_allocation(self):
        from mcc import mcc
        from graphillion import GraphSet
        self.set_flow_dict_for_slot_allocation()
        universe = [(i, j) \
                    for i, fi in self.flow_dict_for_slot_allocation.items() \
                    for j, fj in self.flow_dict_for_slot_allocation.items() \
                    if i < j and nx.number_of_edges(nx.intersection(fi.flow_graph, fj.flow_graph)) == 0]
        if universe == []:
            return len(self.flow_dict_for_slot_allocation)
        node_set = set(self.flow_dict_for_slot_allocation.keys())
        GraphSet.set_universe(universe)
        result = mcc(len(node_set), node_set)
        
        existing_flow = {flow_id for id_set in result for flow_id in id_set if flow_id < 0}

        # convert a list of sets to a dict
        result_dict = dict()
        used_slot = set()
        # Assign slot_id that has already been assigned
        for id_set in result:
            common_set = id_set & existing_flow
            assert 0 <= len(common_set) <= 1
            if len(common_set) == 1:
                slot_id = slot_decrypt(common_set.pop())
                used_slot.add(slot_id)
                for flow_id in id_set:
                    result_dict[flow_id] = slot_id
        
        # sort result by the number of branches in the flow graph
        sorted_result = sorted(result, \
                               key=lambda id_set: \
                                sum([nx.number_of_edges(flow_dict_for_slot_allocation[flow_id].flow_graph) \
                                    for flow_id in id_set]))

        # assign the other slot_id
        slot_id = 0
        for id_set in sorted_result:
            while slot_id in used_slot:
                slot_id += 1
            if len(id_set & existing_flow) == 0:
                used_slot.add(slot_id)
                for flow_id in id_set:
                    result_dict[flow_id] = slot_id
                slot_id += 1

        return result_dict
    
    ##---------------------------------------------------------
    def get_optimal_slot_num(self):
        return max(self.optimal_slot_allocation().values()) + 1
    
    ##---------------------------------------------------------
    def greedy_slot_allocation(self):
        self.set_flow_dict_for_slot_allocation()
        universe = [(i, j) \
                    for i, fi in self.flow_dict_for_slot_allocation.items() \
                    for j, fj in self.flow_dict_for_slot_allocation.items() \
                    if i < j and nx.number_of_edges(nx.intersection(fi.flow_graph, fj.flow_graph)) != 0]
        node_set = set(self.flow_dict_for_slot_allocation.keys())
        graph = nx.Graph()
        graph.add_nodes_from(node_set)
        graph.add_edges_from(universe)
        coloring = nx.coloring.greedy_color(graph, strategy='saturation_largest_first')
        
        # Leave previously assigned slot_id's as they are.
        convert = dict()
        remaining_old_slot = set(coloring.values())
        remaining_new_slot = set(coloring.values()) | set(range(slot_decrypt(min(coloring.keys())) + 1))
        for flow_id, slot_id in coloring.items():
            if flow_id < 0:
                decrypted_slot = slot_decrypt(flow_id)
                remaining_old_slot.remove(slot_id)
                remaining_new_slot.remove(decrypted_slot)
                convert[slot_id] = decrypted_slot
        assert len(remaining_old_slot) <= len(remaining_new_slot)

        # sort result by the number of branches in the flow graph
        sorted_remaining_old_slot = sorted(remaining_old_slot, \
                                           key=lambda s: \
                                            sum([nx.number_of_edges(self.flow_dict_for_slot_allocation[flow_id].flow_graph) \
                                                 for flow_id, slot_id in coloring.items() if slot_id == s]))
        for old, new in zip(sorted_remaining_old_slot, sorted(list(remaining_new_slot))):
            convert[old] = new

        for flow_id, slot_id in coloring.items():
            coloring[flow_id] = convert[slot_id]

        return coloring
    
    ##---------------------------------------------------------
    def get_avg_greedy_slot_num(self):
        rNode_id2slots = {rNode_id: 0 for rNode_id in self.topology.nodes}
        coloring = self.greedy_slot_allocation()
        slot_id2flow_id_list = {s: [flow_id for flow_id, slot_id in coloring.items() if slot_id == s] \
                                    for s in set(coloring.values())}

        desc_slot_id_list = sorted(list(set(coloring.values())), reverse=True)
        for slot_id in desc_slot_id_list:
            flow_id_list = slot_id2flow_id_list[slot_id]
            for flow_id in flow_id_list:
                flow_graph = self.flow_dict_for_slot_allocation[flow_id].flow_graph
                nodes_in_flow = set(flow_graph.nodes)
                for s in [s for s in desc_slot_id_list if s >= slot_id]:
                    if s > slot_id:
                        rNodes_whose_slots_are_s = {rNode_id for rNode_id, slots in rNode_id2slots.items() \
                                                    if slots == s + 1}
                        if nodes_in_flow & rNodes_whose_slots_are_s != set():
                            for node in nodes_in_flow:
                                rNode_id2slots[node] = s + 1
                            break
                    else:
                        for node in nodes_in_flow:
                            rNode_id2slots[node] = s + 1
        
        return sum(rNode_id2slots.values()) / len(rNode_id2slots)
    
    ##---------------------------------------------------------
    def get_max_greedy_slot_num(self):
        return max(self.greedy_slot_allocation().values()) + 1

    ##---------------------------------------------------------
    def get_total_communication_flow_edges(self):
        self.set_flow_dict_for_slot_allocation()
        return sum([nx.number_of_edges(flow.flow_graph) for flow in self.flow_dict.values()])
    
    ##---------------------------------------------------------
    def board_num_to_be_routed(self):
        return len(set().union(*[pair.path for pair in self.pair_dict.values()]))

    ##---------------------------------------------------------
    def average_hops(self):
        return (sum([len(pair.path) for pair in self.pair_dict.values()]) / len(self.pair_dict)) - 2
    
    ##---------------------------------------------------------
    def save_au(self, file_name=None, protocol=pickle.HIGHEST_PROTOCOL):
        if file_name is None:
            return pickle.dumps(self, protocol)
        else:
            with open(file_name, 'wb') as f:
                pickle.dump(self, f, protocol)
    
    ##---------------------------------------------------------
    @classmethod
    def load_au_from_obj(cls, obj):
        return pickle.loads(obj)
    
    ##---------------------------------------------------------
    @classmethod
    def load_au_from_file(cls, file_name):
        with open(file_name, 'rb') as f:
            data = pickle.load(f)
        return data

    ##---------------------------------------------------------
    def print_au(self):
        print(" ##### App ##### ")
        all_app_list = list(self.app_dict.values())
        for app in all_app_list:
            print("app_id: {}".format(app.app_id))
            print("vNode_id_list: {}".format([vNode.vNode_id for vNode in app.vNode_list]))
            print("pair_id_list: {}".format([pair.pair_id for pair in app.pair_list]))
            print(" --------------------------------------------------- ")

        print("\n ##### vNode ##### ")
        all_vNode_list = list(self.vNode_dict.values())
        for vNode in all_vNode_list:
            print("vNode_id: {}".format(vNode.vNode_id))
            print("send_pair_id_list: {}".format([pair.pair_id for pair in vNode.send_pair_list]))
            print("recv_pair_id_list: {}".format([pair.pair_id for pair in vNode.recv_pair_list]))
            print("rNode_id: {}".format(vNode.rNode_id))
            print(" --------------------------------------------------- ")
        
        print("\n ##### Flow ##### ")
        all_flow_list = list(self.flow_dict.values())
        for flow in all_flow_list:
            print("flow_id: {}".format(flow.flow_id))
            print("pair_id_list: {}".format([pair.pair_id for pair in flow.pair_list]))
            print(" --------------------------------------------------- ")

        print("\n ##### Pair ##### ")
        all_pair_list = list(self.pair_dict.values())
        for pair in all_pair_list:
            print("pair_id: {}".format(pair.pair_id))
            print("src: {}".format(pair.src_vNode.vNode_id))
            print("dst: {}".format(pair.dst_vNode.vNode_id))
            print("path: {}".format(pair.path))
            print(" --------------------------------------------------- ")
    
    ##---------------------------------------------------------
    def __eq__(self, other):
        for vNode_id in self.vNode_dict.keys():
            if self.vNode_dict[vNode_id].rNode_id != other.vNode_dict[vNode_id].rNode_id:
                return False
        
        for pair_id in self.pair_dict.keys():
            if self.pair_dict[pair_id].path != other.pair_dict[pair_id].path:
                return False
        
        return True

    ##---------------------------------------------------------
    def __deepcopy__(self, memo):
        return pickle.loads(pickle.dumps(self, pickle.HIGHEST_PROTOCOL))
