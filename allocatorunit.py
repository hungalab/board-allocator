from __future__ import annotations
import pickle
import copy
import random
from typing import Optional, Iterable

import networkx as nx

from mcc import mcc
from cpp_modules import crossing_flows, slot_allocation

#----------------------------------------------------------------------------------------
def slot_encrypt(slot_id: int) -> int:
    return -(slot_id + 1)

#----------------------------------------------------------------------------------------
def slot_decrypt(encripted_slot_id: int) -> int:
    return -(encripted_slot_id + 1)

#----------------------------------------------------------------------------------------
class Pair:
    def __init__(self, pair_id: int, src: int, dst: int, flow_id: int):
        self.pair_id = pair_id
        self.src = src
        self.dst = dst
        self.flow_id = flow_id
        self.src_vNode: Optional[VNode] = None
        self.dst_vNode: Optional[VNode] = None
        self.owner: Optional[Flow] = None
        self.path: Optional[tuple[int]] = None # using path list
        self.allocating: bool = True
    
    ##-----------------------------------------------------------------------------------
    def _hasher(self) -> int:
        '''
        This method is assumed to be used ONLY for AllocatorUnit.unique() or _hasher
        '''
        return hash((self.pair_id, self.src, self.dst, self.flow_id, self.path, self.allocating))
    
    ##-----------------------------------------------------------------------------------
    def __eq__(self, other: Pair) -> bool:
        return (self.pair_id == other.pair_id) and (self.src == other.src) \
               and (self.dst == other.dst) and (self.flow_id == other.flow_id) \
               and (self.path == other.path) \
               and (self.allocating == other.allocating)

#----------------------------------------------------------------------------------------
class Flow:
    def __init__(self, flow_id: int, pair_list: list[Pair]):
        assert flow_id >= 0
        self.flow_id = flow_id
        self.pair_list = pair_list
        self.slot_id: Optional[int] = None
        self.flow_graph: Optional[nx.DiGraph] = None
        self.allocating: bool = True
    
    ##-----------------------------------------------------------------------------------
    @property
    def cvid(self) -> int:
        return self.flow_id if self.allocating else slot_encrypt(self.slot_id)
    
    ##-----------------------------------------------------------------------------------
    @classmethod
    def is_encrypted_cvid(cls, cvid: int) -> bool:
        return cvid < 0
    
    ##-----------------------------------------------------------------------------------
    def make_flow_graph(self, None_acceptance: bool = False):
        self.flow_graph = nx.DiGraph()
        for pair in self.pair_list:
            path = pair.path
            if None_acceptance and path is None:
                continue
            nx.add_path(self.flow_graph, path)
    
    ##-----------------------------------------------------------------------------------
    def _hasher(self) -> int:
        '''
        This method is assumed to be used ONLY for AllocatorUnit.unique() or _hasher
        '''
        return hash((self.flow_id, 
                     tuple(pair._hasher() for pair in self.pair_list), 
                     self.slot_id, 
                     self.allocating))
    
    ##-----------------------------------------------------------------------------------
    def __eq__(self, other: Flow) -> bool:
        return (self.flow_id == other.flow_id) and (self.pair_list == other.pair_list) \
               and (self.slot_id == other.slot_id) and (self.allocating == other.allocating)

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
class AllocatorUnit:
    def __init__(self, seed: nx.DiGraph | AllocatorUnit | bytes | str = None):
        if isinstance(seed, nx.DiGraph):
            ## topology
            self.topology = seed # the topology for this allocator
            ## dictionaries (vNode, pair, app)
            self.vNode_dict: dict[int, VNode] = dict()
            self.flow_dict: dict[int, Flow] = dict()
            self.pair_dict: dict[int, Pair] = dict()
            self.app_dict: dict[int, App] = dict()
            ## core nodes
            self.core_nodes: set[int] = {i for i, module in seed.nodes(data="module")
                                         if module == "core"}
            self.switch_nodes: set[int] = set(seed.nodes) - self.core_nodes
            ## shortest path list
            self.st_path_table: dict[int, dict[int, tuple[tuple[int]]]] = dict() # st_path_table[src][dst] = [path0, path1, ...]

            # create st-path list
            self.st_path_table \
            = {src: 
                  {dst: 
                      tuple(
                          tuple(p[0:-1]) if seed.edges[p[-2], p[-1]]["multi_ejection"]
                          else tuple(p)
                          for p in nx.all_shortest_paths(seed, src, dst))
                   for dst in self.core_nodes if dst != src} 
               for src in self.core_nodes}
        
        elif isinstance(seed, (AllocatorUnit, bytes, str)):
            if isinstance(seed, AllocatorUnit):
                base = copy.deepcopy(seed)
            elif isinstance(seed, bytes):
                base = pickle.loads(seed)
            elif isinstance(seed, str):
                with open(seed, 'rb') as f:
                    base = pickle.load(f)

            ## topology
            self.topology = base.topology
            ## dictionaries (vNode, pair, app)
            self.vNode_dict = base.vNode_dict
            self.flow_dict = base.flow_dict
            self.pair_dict = base.pair_dict
            self.app_dict = base.app_dict
            ## core nodes
            self.core_nodes = base.core_nodes
            self.switch_nodes = base.switch_nodes
            ## shortest path list
            self.st_path_table = base.st_path_table

        else:
            raise ValueError("The argument type must be 'networkx.DiGraph', "
                             "'AllocatorUnit', 'bytes', or 'str'.")

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
        
        # disable the allocating status of pairs
        for flow in self.flow_dict.values():
            if flow.slot_id is not None:
                flow.allocating = False
                flow.make_flow_graph()

    ##-----------------------------------------------------------------------------------
    def pair_allocation(self, pair_id: int, path: tuple[int]):
        # update path
        self.pair_dict[pair_id].path = path
    
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
    
    ##-----------------------------------------------------------------------------------
    def random_node_allocation(self, vNode_id: int, with_pair_allocation: bool = True):
        # pick up an empty rNove
        map_rNode_id = random.choice(list(self.empty_rNode_set))
        self.node_allocation(vNode_id, map_rNode_id, with_pair_allocation)

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
    
    ##-----------------------------------------------------------------------------------
    def crossing_flows(self) -> set[tuple[int, int]]:
        flows = [(f.cvid, f.flow_graph.edges) for f in self.flow_dict.values()]
        return crossing_flows(flows)
    
    ##-----------------------------------------------------------------------------------
    def find_maximal_cliques_of_slot_graph(self) -> list[list[int]]:
        # construct graphs of flows in allocating
        for flow in self.flow_dict.values():
            if flow.allocating:
                flow.make_flow_graph()
        # find maximal cliques
        edges = self.crossing_flows()
        node_set = {flow.cvid for flow in self.flow_dict.values()}
        graph = nx.Graph()
        graph.add_nodes_from(node_set)
        graph.add_edges_from(edges)
        return list(nx.find_cliques(graph))

    ##-----------------------------------------------------------------------------------
    def optimal_slot_allocation(self):
        # construct graphs of flows in allocating
        for flow in self.flow_dict.values():
            if flow.allocating:
                flow.make_flow_graph()
        
        # get mcc
        edges = self.crossing_flows()
        node_set = {flow.cvid for flow in self.flow_dict.values()}
        graph = nx.Graph()
        graph.add_nodes_from(node_set)
        graph.add_edges_from(edges)
        result = mcc(graph)

        # convert mcc style (list[set[int]]) to coloring style (dict[int, int])
        coloring = {cvid: i for i, id_set in enumerate(result) for cvid in id_set}
        
       # Leave previously assigned slot_id's as they are.
        convert = {slot_id: slot_decrypt(cvid) 
                   for cvid, slot_id in coloring.items() if Flow.is_encrypted_cvid(cvid)}
        pre_convert = set(coloring.values()) - set(convert.keys())
        post_convert = set(coloring.values()) - set(convert.values())

        # sort result by the number of branches in the flow graph
        def edge_weight(s: int):
            return sum([self.flow_dict[cvid].flow_graph.number_of_edges()
                        for cvid, slot_id in coloring.items() if slot_id == s])
        pre_convert = sorted(pre_convert, key=edge_weight, reverse=True)

        for old, new in zip(pre_convert, sorted(post_convert)):
            convert[old] = new

        # assign converted slot_id
        for cvid, slot_id in coloring.items():
            if not Flow.is_encrypted_cvid(cvid):
                self.flow_dict[cvid].slot_id = convert[slot_id]
    
    ##-----------------------------------------------------------------------------------
    def greedy_slot_allocation(self, None_acceptance: bool = False):
        # construct graphs of flows in allocating
        for flow in self.flow_dict.values():
            if flow.allocating:
                flow.make_flow_graph(None_acceptance)
        
        # get coloring
        flows = [(f.cvid, f.flow_graph.edges) for f in self.flow_dict.values()]
        coloring: dict[int, int] = slot_allocation(flows)
        
        # Leave previously assigned slot_id's as they are.
        convert = {slot_id: slot_decrypt(cvid) 
                   for cvid, slot_id in coloring.items() if Flow.is_encrypted_cvid(cvid)}
        pre_convert = set(coloring.values()) - set(convert.keys())
        post_convert = set(coloring.values()) - set(convert.values())

        # sort result by the number of branches in the flow graph
        def edge_weight(s: int):
            return sum([self.flow_dict[cvid].flow_graph.number_of_edges()
                        for cvid, slot_id in coloring.items() if slot_id == s])
        pre_convert = sorted(pre_convert, key=edge_weight, reverse=True)

        for old, new in zip(pre_convert, sorted(post_convert)):
            convert[old] = new

        # assign converted slot_id
        for cvid, slot_id in coloring.items():
            if not Flow.is_encrypted_cvid(cvid):
                self.flow_dict[cvid].slot_id = convert[slot_id]
    
    ##-----------------------------------------------------------------------------------
    def get_avg_slot_num(self) -> float:
        switch2slots = {sw: 0 for sw in self.switch_nodes}
        slot_id_set = {flow.slot_id for flow in self.flow_dict.values()}
        slot_id2flow_id_list \
            = {s: [f.flow_id for f in self.flow_dict.values() if f.slot_id == s] 
               for s in slot_id_set}

        desc_slot_id_list = sorted(slot_id_set, reverse=True)
        for slot_id in desc_slot_id_list:
            flow_id_list = slot_id2flow_id_list[slot_id]
            for flow_id in flow_id_list:
                flow_graph = self.flow_dict[flow_id].flow_graph
                switches_in_flow = set(flow_graph.nodes) - self.core_nodes
                for s in [s for s in desc_slot_id_list if s >= slot_id]:
                    if s > slot_id:
                        switches_whose_slots_are_s \
                            = {switch for switch, slots in switch2slots.items()
                               if slots == s + 1}
                        if switches_in_flow & switches_whose_slots_are_s != set():
                            for sw in switches_in_flow:
                                switch2slots[sw] = s + 1
                            break
                    else:
                        for sw in switches_in_flow:
                            switch2slots[sw] = s + 1
        
        return sum(switch2slots.values()) / len(switch2slots)
    
    ##-----------------------------------------------------------------------------------
    def get_max_slot_num(self) -> int:
        return max([flow.slot_id for flow in self.flow_dict.values()]) + 1

    ##-----------------------------------------------------------------------------------
    def get_total_communication_flow_edges(self) -> int:
        return sum([flow.flow_graph.number_of_edges() 
                    for flow in self.flow_dict.values()])
    
    ##-----------------------------------------------------------------------------------
    def get_crossing_flows_num(self) -> int:
        return len(self.crossing_flows())

    ##-----------------------------------------------------------------------------------
    def board_num_to_be_routed(self) -> int:
        routed_nodes = set().union(*[pair.path for pair in self.pair_dict.values()])
        return len(routed_nodes - self.core_nodes)

    ##-----------------------------------------------------------------------------------
    def average_hops(self) -> float:
        total_hops = sum([(len(pair.path) - 2) if pair.path[-1] not in self.core_nodes 
                          else (len(pair.path) - 3)
                          for pair in self.pair_dict.values()])
        return (total_hops / len(self.pair_dict))
    
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
            print("slot_id: {}".format(flow.slot_id))
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
