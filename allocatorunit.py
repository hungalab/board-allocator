import sys, traceback
import pickle

import networkx as nx

#--------------------------------------------------------------
class App:
    def __init__(self, app_id, vNode_list, flow_list, pair_list, communicationFile):
        self.app_id = app_id
        self.vNode_list = vNode_list # list: list of vNodes of the App
        self.flow_list = flow_list # list: list of flows of the App
        self.pair_list = pair_list # list: list of pairs of the App
        self.communicationFile = communicationFile

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
    def __init__(self, flow_id, pair_list):
        self.flow_id = flow_id
        self.pair_list = pair_list
        self.slot_id = None
        self.flow_graph = None
    
    def make_flow_graph(self):
        self.flow_graph = nx.DiGraph()
        for pair in self.pair_list:
            path = pair.path
            nx.add_path(self.flow_graph, path)

#--------------------------------------------------------------
class VNode:
    def __init__(self, vNode_id, send_pair_list, recv_pair_list):
        self.vNode_id = vNode_id # int: virtualized node ID
        self.send_pair_list = send_pair_list # list: list of pair to be sent by this VNode
        self.recv_pair_list = recv_pair_list # list: list of pair to be recieved by this VNode
        self.rNode_id = None # allocated node label (label is defined in topologyFile), 
                             # if the vNode is not allocated (including tmporary), the value is None

#--------------------------------------------------------------
class Slot:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.flow_list = list()
    
    def can_combine_and_do(self, flow):
        intersection = nx.intersection(self.graph, flow.flow_graph)
        if nx.number_of_edges(intersection) == 0:
            self.graph = nx.compose(self.graph, flow.flow_graph)
            self.flow_list.append(flow)
            return True
        else:
            return False

#--------------------------------------------------------------
class AllocatorUnitInitializationError(Exception):
    # This class is for errors related to AllocatorUnit constructor arguments.
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
            self.allocating_app_list = list() # 1D list: the list of Apps that are being allocated
            ## runnning (allocated) object list
            self.running_vNode_list = list() # 1D list: the list of VNodes that are runnning (allocation is finished)
            self.running_pair_list = list() # 1D list: the list of pairs that are runnning (allocation is finished)
            self.running_app_list = list() # 1D list: the list of Apps that are runnning (allocation is finished)
            ## manage the real node
            self.temp_allocated_rNode_dict = dict() # 1D dict: rNode_id |-> vNode_id
            self.empty_rNode_set = set(range(nx.number_of_nodes(self.topology))) # the set of rNodes that is not allocated (not including temp_allocated_rNode_dict)
            ## shortest path list
            self.st_path_table = None # 2D list: st_path_table[src][dst] = [path0, path1, ...] <return value is 1D list of path(1D list)>
            ## slot management
            self.slot_list = None # 1D list: the lists of Slot
            self.slot_valid = False

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
            self.allocating_app_list = base.allocating_app_list
            ## runnning (allocated) object list
            self.running_vNode_list = base.running_vNode_list
            self.running_pair_list = base.running_pair_list
            self.running_app_list = base.running_app_list
            ## manage the real node
            self.temp_allocated_rNode_dict = base.temp_allocated_rNode_dict
            self.empty_rNode_set = base.empty_rNode_set
            ## shortest path list
            self.st_path_table = base.st_path_table
            ## slot management
            self.slot_list = base.slot_list
            self.slot_valid = base.slot_valid

        else:
            raise AllocatorUnitInitializationError( \
            "Only one of the arguments of the AllocatorUnit constructor \
            should be specified, and the other should be None.")

    ##---------------------------------------------------------
    def add_app(self, app):
        # check whether the app can be mapped
        if len(self.running_vNode_list) + len(app.vNode_list) > nx.number_of_nodes(self.topology):
            return False

        # add app
        self.app_dict[app.app_id] = app
        self.allocating_app_list.append(app)

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
    def slot_allocation(self):
        if not self.slot_valid:
        # make flow_graphs
            for flow in self.flow_dict.values():
                flow.make_flow_graph()

            # sort by the number of edges for each flow_graph
            flow_list = sorted(list(self.flow_dict.values()), \
                               key=lambda x: nx.number_of_edges(x.flow_graph))

            # allocation by greedy
            self.slot_list = [Slot()]
            for flow in flow_list:
                allocated = False
                for slot in self.slot_list:
                    if slot.can_combine_and_do(flow):
                        allocated = True
                        break

                if allocated:
                    continue

                new_slot = Slot()
                new_slot.can_combine_and_do(flow)
                self.slot_list.append(new_slot)
        
        self.slot_valid = True

        return pickle.loads(pickle.dumps(self.slot_list, pickle.HIGHEST_PROTOCOL))

    ##---------------------------------------------------------
    def get_slot_num(self):
        self.slot_allocation()
        return len(self.slot_list)
    
    ##---------------------------------------------------------
    def get_total_communication_hops(self):
        self.slot_allocation()
        return sum([nx.number_of_edges(slot.graph) for slot in self.slot_list])
    
    ##---------------------------------------------------------
    def board_num_used_by_allocating_app(self):
        return len(set().union(*[pair.path for pair in self.allocating_pair_list]))
    
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
    def __deepcopy__(self, memo):
        return pickle.loads(pickle.dumps(self, pickle.HIGHEST_PROTOCOL))