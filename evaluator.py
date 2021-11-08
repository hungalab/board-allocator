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
def avg_hops(ind):
    return ind.average_hops()

#--------------------------------------------------------------
class Evaluator:
    __funcs = [
        ('avg # of slots', avg_slots, -1.0), 
        ("# of flows' edges", edges, -1.0),
        ('# of routed bords', boards, -1.0)
    ]
    
    ##---------------------------------------------------------
    @classmethod
    def eval_list(cls):
        return [func[0] for func in cls.__funcs]

    ##---------------------------------------------------------
    @classmethod
    def evaluate(cls, individual):
        return [func[1](individual) for func in cls.__funcs]

    ##---------------------------------------------------------
    @classmethod
    def weights(cls):
        return tuple(func[2] for func in cls.__funcs)