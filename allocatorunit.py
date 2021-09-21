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
        self.rNode_id = None # allocated node label (label is defined in topologyFile), if the vNode is not allocated (including tmporary), the value is None

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
class AllocatorUnit:
    def __init__(self, topology):
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
        self.empty_rNode_list = list() # 1D list: the list of rNodes that is not allocated (not including temp_allocated_rNode_dict)
        ## shortest path list
        self.st_path_table = None # 2D list: st_path_table[src][dst] = [path0, path1, ...] <return value is 1D list of path(1D list)>
        ## slot management
        self.slot_list = None # 1D list: the lists of Slot

        # create st-path list
        node_num = nx.number_of_nodes(self.topology)
        self.st_path_table = [[[] for _ in range(0, node_num)] for _ in range(0, node_num)]
        for src in range(0, node_num):
            for dst in range(0, node_num):
                for path in nx.all_shortest_paths(self.topology, src, dst):
                    self.st_path_table[src][dst].append([path[0]] + path)

    ##---------------------------------------------------------
    def add_app(self, app):
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
    
    ##---------------------------------------------------------
    def slot_allocation(self):
        # make flow_graphs
        for flow in self.flow_dict.values():
            flow.make_flow_graph()

        # sort by the number of edges for each flow_graph
        flow_list = sorted(list(self.flow_dict.values()), key=lambda x: nx.number_of_edges(x.flow_graph))
        
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
        
        return len(self.slot_list)

    
    ##---------------------------------------------------------
    def get_total_communication_hops(self):
        return sum([nx.number_of_edges(slot.graph) for slot in self.slot_list])
    
    ##---------------------------------------------------------
    def save_au(self, file_name=None, protocol=pickle.HIGHEST_PROTOCOL):
        if file_name == None:
            return pickle.dumps(self, protocol)
        else:
            with open(file_name, 'wb') as f:
                pickle.dump(self, f, protocol)
    
    ##---------------------------------------------------------
    @classmethod
    def load_au(cls, obj=None, file_name=None):
        if (obj != None) and (file_name == None):
            return pickle.loads(obj)
        elif (obj == None) and (file_name != None):
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
            print("flow_id: {}".format(pair.flow_id))
            print(" --------------------------------------------------- ")