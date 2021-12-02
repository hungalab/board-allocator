from __future__ import annotations
import pickle
import copy
import random
from typing import Optional, Iterable
from mcc import mcc

import networkx as nx

#----------------------------------------------------------------------------------------
def slot_encrypt(slot: int) -> int:
    return -(slot + 1)

#----------------------------------------------------------------------------------------
def slot_decrypt(encripted_slot: int) -> int:
    return -(encripted_slot + 1)

#----------------------------------------------------------------------------------------
class Pair:
    def __init__(self, pair_id: int, src: int, dst: int):
        # type: (int, int, int) -> None
        self.pair_id = pair_id
        self.src = src
        self.dst = dst
        self.src_vNode: Optional[VNode] = None
        self.dst_vNode: Optional[VNode] = None
        self.path: Optional[tuple[int]] = None # using path list
        self.allocating: bool = True
    
    ##-----------------------------------------------------------------------------------
    def _hasher(self) -> int:
        '''
        This method is assumed to be used ONLY for AllocatorUnit.unique() or _hasher
        '''
        return hash((self.pair_id, self.src, self.dst, self.path, self.allocating))
    
    ##-----------------------------------------------------------------------------------
    def __eq__(self, other: Pair) -> bool:
        return (self.pair_id == other.pair_id) and (self.src == other.src) \
               and (self.dst == other.dst) and (self.path == other.path) \
               and (self.allocating == other.allocating)

#----------------------------------------------------------------------------------------
class Flow:
    def __init__(self, flow_id: Optional[int] = None, pair_list: list[Pair] = []):
        self.flow_id = flow_id
        self.pair_list = pair_list
        self.slot_id: Optional[int] = None
        self.flow_graph: Optional[nx.DiGraph] = None
    
    ##-----------------------------------------------------------------------------------
    def make_flow_graph(self, None_acceptance: bool = False):
        self.flow_graph = nx.DiGraph()
        for pair in self.pair_list:
            path = pair.path
            if None_acceptance and path is None:
                continue
            nx.add_path(self.flow_graph, path)

    ##-----------------------------------------------------------------------------------
    def merge(self, other: Flow):
        if self.flow_id is None:
            self.flow_id = slot_encrypt(other.slot_id)
        elif self.flow_id != slot_encrypt(other.slot_id):
            raise ValueError("The values of slot_id are different form each other.")
        if self.slot_id is None:
            self.slot_id = other.slot_id
        self.pair_list += other.pair_list
    
    ##-----------------------------------------------------------------------------------
    def _hasher(self) -> int:
        '''
        This method is assumed to be used ONLY for AllocatorUnit.unique() or _hasher
        '''
        return hash((self.flow_id, 
                     tuple(pair._hasher() for pair in self.pair_list), 
                     self.slot_id))
    
    ##-----------------------------------------------------------------------------------
    def __eq__(self, other: Flow) -> bool:
        return (self.flow_id == other.flow_id) and (self.pair_list == other.pair_list) \
               and (self.slot_id == other.slot_id)

#----------------------------------------------------------------------------------------
class VNode:
    def __init__(self, 
                 vNode_id: int, 
                 send_pair_list: list[Pair], 
                 recv_pair_list: list[Pair]):
        self.vNode_id = vNode_id # virtualized node ID
        self.send_pair_list = send_pair_list # list of pair to be sent by this VNode
        self.recv_pair_list = recv_pair_list # list of pair to be recieved by this VNode
        self.rNode_id: Optional[int] = None # physical node id: None means unallocated
        self.allocating: bool = True
    
    ##-----------------------------------------------------------------------------------
    @property
    def pair_list(self) -> list[Pair]:
        return self.send_pair_list + self.recv_pair_list

    ##-----------------------------------------------------------------------------------
    def _hasher(self) -> int:
        '''
        This method is assumed to be used ONLY for AllocatorUnit.unique() or _hasher
        '''
        return hash((self.vNode_id, self.rNode_id, self.allocating))
    
    ##-----------------------------------------------------------------------------------
    def __eq__(self, other: VNode) -> bool:
        return (self.vNode_id == other.vNode_id) and (self.rNode_id == other.rNode_id) \
               and (self.allocating == other.allocating)

#----------------------------------------------------------------------------------------
class App:
    def __init__(self, 
                 app_id: int, 
                 vNode_list: list[VNode], 
                 flow_list: list[Flow], 
                 pair_list: list[Pair]): 
        self.app_id = app_id
        self.vNode_list = vNode_list # list of vNodes of the App
        self.flow_list = flow_list # list of flows of the App
        self.pair_list = pair_list # list of pairs of the App
    
    ##-----------------------------------------------------------------------------------
    def _hasher(self) -> int:
        '''
        This method is assumed to be used ONLY for AllocatorUnit.unique()
        '''
        return hash((self.app_id, 
                     tuple(vNode._hasher() for vNode in self.vNode_list),
                     tuple(flow._hasher() for flow in self.flow_list), 
                     tuple(pair._hasher() for pair in self.pair_list)))
    
    ##-----------------------------------------------------------------------------------
    def __eq__(self, other: App) -> bool:
        return (self.app_id == other.app_id) \
               and (self.vNode_list == other.vNode_list) \
               and (self.flow_list == other.flow_list) \
               and (self.pair_list == other.pair_list)

#----------------------------------------------------------------------------------------
class AllocatorUnitInitializationError(Exception):
    # This class is for errors related to AllocatorUnit constructor's arguments.
    pass

#----------------------------------------------------------------------------------------
class AllocatorUnit:
    def __init__(self, 
                 topology: Optional[nx.DiGraph] = None, 
                 seed: Optional[AllocatorUnit | bytes | str] = None):
        '''
        You can use this constructor in two ways.

        1) AllocatorUnit(topology=topology, seed=None)
        Create a brand new AllocatorUnit.

        2) AllocatorUnit(topology=None, seed=seed)
        Create an AllocatorUnit from another AllocatorUnit.
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
            self.vNode_dict: dict[int, VNode] = dict()
            self.flow_dict: dict[int, Flow] = dict()
            self.pair_dict: dict[int, Pair] = dict()
            self.app_dict: dict[int, App] = dict()
            ## core nodes
            self.core_nodes: set[int] = {i for i, module in topology.nodes(data="module")
                                         if module == "core"}
            ## shortest path list
            self.st_path_table: dict[int, dict[int, tuple[tuple[int]]]] = dict() # st_path_table[src][dst] = [path0, path1, ...]
            ## slot management
            self._esc_flow_dict_for_slot_allocation = None
            self._flow_dict_for_slot_allocation_valid: bool = False

            # create st-path list
            self.st_path_table \
            = {src: 
                  {dst: 
                      tuple(
                          tuple(p[0:-1]) if topology.edges[p[-2], p[-1]]["multi_ejection"]
                          else tuple(p)
                          for p in nx.all_shortest_paths(topology, src, dst))
                   for dst in self.core_nodes if dst != src} 
               for src in self.core_nodes}
        
        elif (topology is None) and (seed is not None):
            if isinstance(seed, AllocatorUnit):
                base = copy.deepcopy(seed)
            elif isinstance(seed, bytes):
                base = pickle.loads(seed)
            elif isinstance(seed, str):
                with open(seed, 'rb') as f:
                    base = pickle.load(f)
            else:
                raise TypeError("The 2nd argument \"seed\" must be "
                                "'AllocationUnit', 'bytes', or 'str'.")

            ## topology
            self.topology = base.topology
            ## dictionaries (vNode, pair, app)
            self.vNode_dict = base.vNode_dict
            self.flow_dict = base.flow_dict
            self.pair_dict = base.pair_dict
            self.app_dict = base.app_dict
            ## core nodes
            self.core_nodes = base.core_nodes
            ## shortest path list
            self.st_path_table = base.st_path_table
            ## slot management
            self._esc_flow_dict_for_slot_allocation = base._esc_flow_dict_for_slot_allocation
            self._flow_dict_for_slot_allocation_valid = base._flow_dict_for_slot_allocation_valid

        else:
            raise AllocatorUnitInitializationError(
            "Only one of the arguments of the AllocatorUnit constructor"
            "should be specified, and the other should be None.")

    ##-----------------------------------------------------------------------------------
    @property
    def switch_nodes(self) -> set[int]:
        return set(self.topology.nodes) - self.core_nodes

    ##-----------------------------------------------------------------------------------
    @property
    def allocating_vNode_list(self) -> list[VNode]:
        return [vNode for vNode in self.vNode_dict.values() if vNode.allocating]

    ##-----------------------------------------------------------------------------------
    @property
    def allocating_pair_list(self) -> list[Pair]:
        return [pair for pair in self.pair_dict.values() if pair.allocating]
    
    ##-----------------------------------------------------------------------------------
    @property
    def temp_allocated_rNode_dict(self) -> dict[int, int]:
        return {vNode.rNode_id: vNode.vNode_id
                for vNode in self.vNode_dict.values()
                if vNode.allocating and vNode.rNode_id is not None}

    ##-----------------------------------------------------------------------------------
    @property
    def empty_rNode_set(self) -> set[int]:
        used = {vNode.rNode_id 
                for vNode in self.vNode_dict.values() if vNode.rNode_id is not None}
        return self.core_nodes - used

    ##-----------------------------------------------------------------------------------
    @property
    def _flow_dict_for_slot_allocation(self) -> dict[int, Flow]:
        return self._get_flow_dict_for_slot_allocation()

    ##-----------------------------------------------------------------------------------
    def add_app(self, app: App) -> bool:
        # check whether the app can be mapped
        if len(self.vNode_dict) + len(app.vNode_list) > self.topology.number_of_nodes():
            return False

        # add app
        self.app_dict[app.app_id] = app

        # add vNodes
        for vNode in app.vNode_list:
            self.vNode_dict[vNode.vNode_id] = vNode
        
        # add flows
        for flow in app.flow_list:
            self.flow_dict[flow.flow_id] = flow
        
        # add pairs
        for pair in app.pair_list:
            self.pair_dict[pair.pair_id] = pair
        
        return True
    
    ##-----------------------------------------------------------------------------------
    def remove_app(self, app_id: int):
        # pop app_id (remove from dict and get app)
        app = self.app_dict.pop(app_id)

        # remove vNodes
        remove_vNode_id_set = {vNode.vNode_id for vNode in app.vNode_list}
        self.vNode_dict = {vNode_id: vNode for vNode_id, vNode in self.vNode_dict.items()
                           if vNode_id not in remove_vNode_id_set}
        
        # remove vNodes
        remove_pair_id_set = {pair.pair_id for pair in app.pair_list}
        self.pair_dict = {pair_id: pair for pair_id, pair in self.pair_dict.items()
                          if pair_id not in remove_pair_id_set}
        
        # remove flows
        remove_flow_id_set = {flow.flow_id for flow in app.flow_list}
        self.flow_dict = {flow_id: flow for flow_id, flow in self.flow_dict.items()
                          if flow_id not in remove_flow_id_set}
        self._flow_dict_for_slot_allocation_valid = False

    ##-----------------------------------------------------------------------------------
    def consistenty_checker(self):
        # check for node duplication
        assigned_rNodes = [vNode.rNode_id for vNode in self.vNode_dict.values() 
                           if vNode.rNode_id is not None]
        assert sorted(assigned_rNodes) == sorted(set(assigned_rNodes))

        # check for path consistency
        for pair in self.pair_dict.values():
            src = pair.src_vNode.rNode_id
            dst = pair.dst_vNode.rNode_id
            if self.topology.has_edge(pair.path[-1], dst) \
               and (self.topology.edges[pair.path[-1], dst]["multi_ejection"]):
                dst = pair.path[-1]
            assert (pair.path[0] == src) and (pair.path[-1] == dst)
        
        return True
    
    ##-----------------------------------------------------------------------------------
    def apply(self):
        # check for allocator consistency
        self.consistenty_checker()

        # disable the allocating status of vNodes
        for vNode in self.vNode_dict.values():
            if vNode.rNode_id is not None:
                vNode.allocating = False

        # disable the allocating status of pairs
        for pair in self.pair_dict.values():
            if pair.path is not None:
                pair.allocating = False

        # apply slots and invalidate _flow_dict_for_slot_allocation_valid
        flow_id2slot_id = self.greedy_slot_allocation()
        for flow_id, slot_id in flow_id2slot_id.items():
            if flow_id >= 0:
                self.flow_dict[flow_id].slot_id = slot_id
        self._flow_dict_for_slot_allocation_valid = False

    ##-----------------------------------------------------------------------------------
    def pair_allocation(self, pair_id: int, path: tuple[int]):
        # update path
        self.pair_dict[pair_id].path = path

        # slot_list invalidation
        self._flow_dict_for_slot_allocation_valid = False
    
    ##-----------------------------------------------------------------------------------
    def random_pair_allocation(self, pair_id: int):
        # pick up src and dst rNode_id
        pair = self.pair_dict[pair_id]
        src = pair.src_vNode.rNode_id
        dst = pair.dst_vNode.rNode_id

        # pick up a path
        path = random.choice(self.st_path_table[src][dst])

        # update
        self.pair_allocation(pair_id, path)

    ##-----------------------------------------------------------------------------------
    def pair_deallocation(self, pair_id: int):
        # modify the correspond pair and abstract the path
        self.pair_dict[pair_id].path = None

        # slot_list invalidation
        self._flow_dict_for_slot_allocation_valid = False

    ##-----------------------------------------------------------------------------------
    def node_allocation(self, 
                        vNode_id: int, 
                        rNode_id: int, 
                        with_pair_allocation: bool = True):
        # temporary node allocation
        vNode = self.vNode_dict[vNode_id]
        vNode.rNode_id = rNode_id

        if with_pair_allocation:
            # temporary send-path allocation
            for send_pair in vNode.send_pair_list:
                if send_pair.dst_vNode.rNode_id is not None:
                    self.random_pair_allocation(send_pair.pair_id)

            # temporary recv-path allocation
            for recv_pair in vNode.recv_pair_list:
                if recv_pair.src_vNode.rNode_id is not None:
                    self.random_pair_allocation(recv_pair.pair_id)
        
        # slot_list invalidation
        self._flow_dict_for_slot_allocation_valid = False
    
    ##-----------------------------------------------------------------------------------
    def random_node_allocation(self, vNode_id: int):
        # pick up an empty rNove
        map_rNode_id = random.choice(list(self.empty_rNode_set))
        self.node_allocation(vNode_id, map_rNode_id)

    ##-----------------------------------------------------------------------------------
    def node_deallocation(self, vNode_id: int, with_pair_deallocation: bool = True):
        # modify the correspond vNode and abstract the rNode_id
        vNode = self.vNode_dict[vNode_id]
        vNode.rNode_id = None

        if with_pair_deallocation:
            # pair deallocation
            for pair in vNode.pair_list:
                if pair.path is not None:
                    self.pair_deallocation(pair.pair_id)
        
        self._flow_dict_for_slot_allocation_valid = False

    ##-----------------------------------------------------------------------------------
    def get_flow_dict_for_slot_allocation(self):
        return self._get_flow_dict_for_slot_allocation(True).copy()

    ##-----------------------------------------------------------------------------------
    def _get_flow_dict_for_slot_allocation(self, None_acceptance: bool = False):
        if (not self._flow_dict_for_slot_allocation_valid) or None_acceptance:
            self._flow_dict_for_slot_allocation_valid = False
            result: dict[int, Flow] = dict()
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
                flow.make_flow_graph(None_acceptance)

            if not None_acceptance:
                self._esc_flow_dict_for_slot_allocation = result
                self._flow_dict_for_slot_allocation_valid = True
            
            return result

        else:
            return self._esc_flow_dict_for_slot_allocation
    
    ##-----------------------------------------------------------------------------------
    def find_maximal_cliques_of_slot_graph(self) -> list[list[int]]:
        universe = [(i, j)
                    for i, fi in self._flow_dict_for_slot_allocation.items()
                    for j, fj in self._flow_dict_for_slot_allocation.items()
                    if i < j and 
                    nx.intersection(fi.flow_graph, fj.flow_graph).number_of_edges() != 0]
        node_set = set(self._flow_dict_for_slot_allocation.keys())
        graph = nx.Graph()
        graph.add_nodes_from(node_set)
        graph.add_edges_from(universe)
        return list(nx.find_cliques(graph))

    ##-----------------------------------------------------------------------------------
    def optimal_slot_allocation(self) -> dict[int, int]:
        universe = [(i, j)
                    for i, fi in self._flow_dict_for_slot_allocation.items()
                    for j, fj in self._flow_dict_for_slot_allocation.items()
                    if i < j and 
                    nx.intersection(fi.flow_graph, fj.flow_graph).number_of_edges() == 0]
        node_set = set(self._flow_dict_for_slot_allocation.keys())
        graph = nx.Graph()
        graph.add_nodes_from(node_set)
        graph.add_edges_from(universe)
        result = mcc(graph)
        
        existing_flow = {flow_id for id_set in result for flow_id in id_set 
                         if flow_id < 0}

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
        def edge_weight(id_set: set[int]):
            fd = self._flow_dict_for_slot_allocation
            return sum([fd[flow_id].flow_graph.number_of_edges() 
                        for flow_id in id_set])
        sorted_result = sorted(result, key=edge_weight, reverse=True)

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
    
    ##-----------------------------------------------------------------------------------
    def get_optimal_slot_num(self) -> int:
        return max(self.optimal_slot_allocation().values()) + 1
    
    ##-----------------------------------------------------------------------------------
    def greedy_slot_allocation(self) -> dict[int, int]:
        universe = [(i, j)
                    for i, fi in self._flow_dict_for_slot_allocation.items()
                    for j, fj in self._flow_dict_for_slot_allocation.items()
                    if i < j and 
                    nx.intersection(fi.flow_graph, fj.flow_graph).number_of_edges() != 0]
        node_set = set(self._flow_dict_for_slot_allocation.keys())
        graph = nx.Graph()
        graph.add_nodes_from(node_set)
        graph.add_edges_from(universe)
        coloring = nx.coloring.greedy_color(graph, strategy='saturation_largest_first')
        
        # Leave previously assigned slot_id's as they are.
        convert = dict()
        remaining_old_slot = set(coloring.values())
        exist_slot = {slot_decrypt(flow_id) 
                      for flow_id in coloring.keys() if flow_id < 0}
        remaining_new_slot = set(coloring.values()) | exist_slot
        for flow_id, slot_id in coloring.items():
            if flow_id < 0:
                decrypted_slot = slot_decrypt(flow_id)
                remaining_old_slot.remove(slot_id)
                remaining_new_slot.remove(decrypted_slot)
                convert[slot_id] = decrypted_slot
        assert len(remaining_old_slot) <= len(remaining_new_slot)

        # sort result by the number of branches in the flow graph
        def edge_weight(s: int):
            fd = self._flow_dict_for_slot_allocation
            return sum([fd[flow_id].flow_graph.number_of_edges()
                        for flow_id, slot_id in coloring.items() if slot_id == s])
        sorted_remaining_old_slot = sorted(remaining_old_slot, 
                                           key=edge_weight, reverse=True)

        for old, new in zip(sorted_remaining_old_slot, sorted(list(remaining_new_slot))):
            convert[old] = new

        for flow_id, slot_id in coloring.items():
            coloring[flow_id] = convert[slot_id]

        return coloring
    
    ##-----------------------------------------------------------------------------------
    def get_avg_greedy_slot_num(self) -> float:
        switch2slots = {n: 0 for n in self.switch_nodes}
        coloring = self.greedy_slot_allocation()
        slot_id2flow_id_list \
            = {s: [flow_id for flow_id, slot_id in coloring.items() if slot_id == s] 
                   for s in set(coloring.values())}

        desc_slot_id_list = sorted(list(set(coloring.values())), reverse=True)
        for slot_id in desc_slot_id_list:
            flow_id_list = slot_id2flow_id_list[slot_id]
            for flow_id in flow_id_list:
                flow_graph = self._flow_dict_for_slot_allocation[flow_id].flow_graph
                switches_in_flow = set(flow_graph.nodes) - self.core_nodes
                for s in [s for s in desc_slot_id_list if s >= slot_id]:
                    if s > slot_id:
                        switches_whose_slots_are_s \
                            = {switch for switch, slots in switch2slots.items()
                               if slots == s + 1}
                        if switches_in_flow & switches_whose_slots_are_s != set():
                            for node in switches_in_flow:
                                switch2slots[node] = s + 1
                            break
                    else:
                        for node in switches_in_flow:
                            switch2slots[node] = s + 1
        
        return sum(switch2slots.values()) / len(switch2slots)
    
    ##-----------------------------------------------------------------------------------
    def get_max_greedy_slot_num(self) -> int:
        return max(self.greedy_slot_allocation().values()) + 1

    ##-----------------------------------------------------------------------------------
    def get_total_communication_flow_edges(self) -> int:
        for flow in self.flow_dict.values():
            if flow.slot_id is None:
                flow.make_flow_graph()
        return sum([flow.flow_graph.number_of_edges() 
                    for flow in self.flow_dict.values()])
    
    ##-----------------------------------------------------------------------------------
    def board_num_to_be_routed(self) -> int:
        routed_nodes = set().union(*[pair.path for pair in self.pair_dict.values()])
        return len(routed_nodes - self.core_nodes)

    ##-----------------------------------------------------------------------------------
    def average_hops(self) -> float:
        total_hops = sum([len(pair.path) for pair in self.pair_dict.values()])
        return (total_hops / len(self.pair_dict)) - 2
    
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

    ##-----------------------------------------------------------------------------------
    def print_au(self):
        print(" ##### App ##### ")
        all_app_list = list(self.app_dict.values())
        for app in all_app_list:
            print("app_id: {}".format(app.app_id))
            print("vNode_id_list: {}".format([vNode.vNode_id 
                                              for vNode in app.vNode_list]))
            print("pair_id_list: {}".format([pair.pair_id for pair in app.pair_list]))
            print(" --------------------------------------------------- ")

        print("\n ##### vNode ##### ")
        all_vNode_list = list(self.vNode_dict.values())
        for vNode in all_vNode_list:
            print("vNode_id: {}".format(vNode.vNode_id))
            print("send_pair_id_list: {}".format([pair.pair_id 
                                                  for pair in vNode.send_pair_list]))
            print("recv_pair_id_list: {}".format([pair.pair_id 
                                                  for pair in vNode.recv_pair_list]))
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

    ##-----------------------------------------------------------------------------------
    def _hasher(self) -> int:
        '''
        This method is assumed to be used ONLY for AllocatorUnit.unique()
        '''
        return hash((tuple(self.topology.nodes), 
                     tuple(self.topology.edges),
                     tuple(app._hasher() for app in self.app_dict.values())))
    
    ##-----------------------------------------------------------------------------------
    @staticmethod
    def unique(units: Iterable[AllocatorUnit]) -> list[AllocatorUnit]:
        uniquer = {au._hasher(): au for au in units}
        return list(uniquer.values())
    
    ##-----------------------------------------------------------------------------------
    def __eq__(self, other: AllocatorUnit) -> bool:
        intersection = nx.intersection(self.topology, other.topology)
        return (intersection.number_of_edges() == self.topology.number_of_edges()) \
               and (intersection.number_of_nodes() == self.topology.number_of_nodes()) \
               and (self.app_dict == other.app_dict)

    ##-----------------------------------------------------------------------------------
    def __deepcopy__(self, memo) -> AllocatorUnit:
        return self.loads(self.dumps())
