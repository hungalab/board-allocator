#--------------------------------------------------------------
def slots(ind):
    return ind.get_slot_num()

#--------------------------------------------------------------
def hops(ind):
    return ind.get_total_communication_hops()

#--------------------------------------------------------------
def boards(ind):
    return ind.board_num_used_by_allocating_app()

#--------------------------------------------------------------
class Evaluator:
    def __init__(self):
        self.__funcs = [
            ('slots', slots, -1.0), 
            ('hops', hops, -1.0),
            ('bords', boards, -1.0)
        ]
    
    def eval_list(self):
        return [func[0] for func in self.__funcs]

    def evaluate(self, individual):
        return [func[1](individual) for func in self.__funcs]

    def weights(self):
        return tuple(func[2] for func in self.__funcs)