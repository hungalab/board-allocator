#--------------------------------------------------------------
def avg_slots(ind):
    return ind.get_avg_greedy_slot_num()

#--------------------------------------------------------------
def max_slots(ind):
    return ind.get_max_greedy_slot_num()

#--------------------------------------------------------------
def edges(ind):
    return ind.get_total_communication_flow_edges()

#--------------------------------------------------------------
def boards(ind):
    return ind.board_num_to_be_routed()

#--------------------------------------------------------------
class Evaluator:
    def __init__(self):
        self.__funcs = [
            ('slots(avg)', avg_slots, -1.0), 
            ('slots(max)', max_slots, -1.0), 
            ('edges', edges, -1.0),
            ('bords', boards, -1.0)
        ]
    
    def eval_list(self):
        return [func[0] for func in self.__funcs]

    def evaluate(self, individual):
        return [func[1](individual) for func in self.__funcs]

    def weights(self):
        return tuple(func[2] for func in self.__funcs)