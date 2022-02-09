from __future__ import annotations
from typing import Callable

from allocatorunit import AllocatorUnit

#----------------------------------------------------------------------------------------
def avg_slots(ind: AllocatorUnit) -> float:
    return ind.get_avg_slot_num()

#----------------------------------------------------------------------------------------
def max_slots(ind: AllocatorUnit) -> int:
    return ind.get_max_slot_num()

#----------------------------------------------------------------------------------------
def edges(ind: AllocatorUnit) -> int:
    return ind.get_total_communication_flow_edges()

#----------------------------------------------------------------------------------------
def boards(ind: AllocatorUnit) -> int:
    return ind.board_num_to_be_routed()

#----------------------------------------------------------------------------------------
def avg_hops(ind: AllocatorUnit) -> float:
    return ind.average_hops()

#----------------------------------------------------------------------------------------
class Evaluator:
    __funcs: list[tuple[str, Callable[[AllocatorUnit], float | int], float]] = [
        ('# of slots', max_slots, -1.0), 
        ("# of flows' edges", edges, -1.0),
        ('# of routed bords', boards, -1.0)
    ]
    
    ##-----------------------------------------------------------------------------------
    @classmethod
    def eval_list(cls) -> list[str]:
        return [func[0] for func in cls.__funcs]

    ##-----------------------------------------------------------------------------------
    @classmethod
    def evaluate(cls, individual: AllocatorUnit) -> list[float | int]:
        return [func[1](individual) for func in cls.__funcs]

    ##-----------------------------------------------------------------------------------
    @classmethod
    def weights(cls) -> tuple[float]:
        return tuple(func[2] for func in cls.__funcs)