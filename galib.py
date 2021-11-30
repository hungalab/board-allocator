from __future__ import annotations
import random
import copy
import collections
from re import I
import numpy
from functools import partial
import multiprocessing
from typing import Callable, Iterable, Any

from deap import tools
from deap import base
from deap import creator

# my library
from allocatorunit import AllocatorUnit
from evaluator import Evaluator
import oplib

#----------------------------------------------------------------------------------------
class Fitness(base.Fitness):
    weights = Evaluator.weights()

#----------------------------------------------------------------------------------------
class Individual(AllocatorUnit):
    def __init__(self, seed: AllocatorUnit | bytes | str):
        super().__init__(None, seed)
        self.fitness = Fitness()

#----------------------------------------------------------------------------------------
def mask_generator(sorted_vNode_id_list: list[int]
                   ) -> tuple[dict[int, int], dict[int, int]]:
    l0, l1 = dict(), dict()
    for vNode_id in sorted_vNode_id_list:
        bit = random.randint(0, 1)
        l0[vNode_id] = bit
        l1[vNode_id] = bit ^ 1
    return l0, l1

#----------------------------------------------------------------------------------------
def cx_by_mask(parent0: Individual, parent1: Individual, mask: dict[int, int]
               ) -> tuple[Individual]:
    child = copy.deepcopy(parent0)

    # node inheritance
    for vNode_id, bit in mask.items():
        # inherit from parent1
        if bit == 1:
            # update rNode_id
            child.node_allocation(vNode_id, parent1.vNode_dict[vNode_id].rNode_id, False)

        # inherit nothing
        elif bit != 0:
            child.node_deallocation(vNode_id, False)

    # path inheritance
    for pair_id, pair in {pair.pair_id: pair
                          for vNode_id in mask.keys() 
                          for pair in child.vNode_dict[vNode_id].pair_list}.items():
        src_bit = mask[pair.src_vNode.vNode_id]
        dst_bit = mask[pair.dst_vNode.vNode_id]

        # inherit from parent1
        if src_bit == dst_bit == 1:
            child.pair_allocation(pair_id, parent1.pair_dict[pair_id].path)
        
        # inherit nothing
        elif not (src_bit == dst_bit == 0):
            child.pair_deallocation(pair_id)
            

    # allocate unallocated vNodes
    for vNode in child.allocating_vNode_list:
        if vNode.rNode_id is None:
            child.random_node_allocation(vNode.vNode_id)

    # allocate unallocated pairs
    for pair in child.allocating_pair_list:
        if pair.path is None:
            child.random_pair_allocation(pair.pair_id)

    # delete the fitness
    del child.fitness.values

    # flow_dict_for_slot_allocation_valid invalidation
    child.flow_dict_for_slot_allocation_valid = False
    
    return child,


#----------------------------------------------------------------------------------------
def cx_uniform(parent0: Individual, parent1: Individual, mate_pb: float = 1.0
               ) -> tuple[Individual, Individual]:
    if len(parent0.temp_allocated_rNode_dict) != len(parent1.temp_allocated_rNode_dict):
        raise ValueError("The number of nodes being allocated is "
                         "different for each parent.")
    
    if len(parent0.allocating_pair_list) != len(parent1.allocating_pair_list):
        raise ValueError("The number of communications being allocated is "
                         "different for each parent.")
    
    if not 0 <= mate_pb <= 1 :
        raise ValueError("Specify a value between 0 and 1.")
    
    if random.random() < mate_pb:
        # make masks
        sorted_vNode_id_list = sorted(parent0.temp_allocated_rNode_dict.values())
        mask0, mask1 = mask_generator(sorted_vNode_id_list)
        parent = [parent0, parent1]
        invalid_value = 2 # Not 0 or 1

        # check the duplication
        next_child0_rNode_dict = {vNode_id: parent[bit].vNode_dict[vNode_id].rNode_id
                                  for vNode_id, bit in mask0.items()}
        counter = collections.Counter(list(next_child0_rNode_dict.values()))
        for key, count in counter.items():
            if count == 2:
                selected = random.randint(0, 1)
                current = 0
                for vNode_id, rNode_id in next_child0_rNode_dict.items():
                    if rNode_id == key and current != selected:
                        mask0[vNode_id] = invalid_value
                        current += 1
                        break
                    elif rNode_id == key and current == selected:
                        current += 1

        next_child1_rNode_dict = {vNode_id: parent[bit].vNode_dict[vNode_id].rNode_id
                                  for vNode_id, bit in mask1.items()}
        counter = collections.Counter(list(next_child1_rNode_dict.values()))
        for key, count in counter.items():
            assert count <= 2
            if count == 2:
                selected = random.randint(0, 1)
                current = 0
                for vNode_id, rNode_id in next_child1_rNode_dict.items():
                    if rNode_id == key and current != selected:
                        mask1[vNode_id] = invalid_value
                        current += 1
                        break
                    elif rNode_id == key and current == selected:
                        current += 1

        # exectute crossover
        child0, = cx_by_mask(parent0, parent1, mask0)
        child1, = cx_by_mask(parent0, parent1, mask1)

    else:
        child0 = copy.deepcopy(parent0)
        child1 = copy.deepcopy(parent1)

    return child0, child1

#----------------------------------------------------------------------------------------
def mut_swap(individual: Individual, mut_pb: float = 1.0) -> tuple[Individual]:

    if not 0 <= mut_pb <= 1 :
        raise ValueError("Specify a value between 0 and 1.")
    
    ind = copy.deepcopy(individual)
    
    if random.random() < mut_pb:
        oplib.node_swap(ind)
        del ind.fitness.values

    return ind,
    
#----------------------------------------------------------------------------------------
def wrapper(func: Callable[..., Any], args: Iterable) -> Any:
    return func(*args)

#----------------------------------------------------------------------------------------
def my_multiprocessing_map(pool: multiprocessing.Pool, 
                           func: Callable[..., Any], 
                           *iterable: Iterable) -> list:
    return pool.map(partial(wrapper, func), [elements for elements in zip(*iterable)])

#----------------------------------------------------------------------------------------
def mate_and_mutate(mate: Callable[[Individual, Individual, float], 
                                   tuple[Individual, Individual]], 
                    mutate: Callable[[Individual, float], tuple[Individual]], 
                    parent0: Individual, 
                    parent1: Individual, 
                    mate_pb: float, 
                    mut_pb: float
                    ) -> tuple[Individual, Individual]:
    child0, child1 = mate(parent0, parent1, mate_pb)
    child0, = mutate(child0, mut_pb)
    child1, = mutate(child1, mut_pb)
    return child0, child1

#----------------------------------------------------------------------------------------
def mate_or_mutate(mate: Callable[[Individual, Individual, float], 
                                   tuple[Individual, Individual]], 
                   mutate: Callable[[Individual, float], tuple[Individual]], 
                   parent0: Individual, 
                   parent1: Individual, 
                   mate_pb: float
                   ) -> tuple[Individual, Individual]:
    if random.random() <= mate_pb:
        child0, child1 = mate(parent0, parent1, 1)
    else:
        child0, = mutate(parent0, 1)
        child1, = mutate(parent1, 1)

    return child0, child1

#----------------------------------------------------------------------------------------
class GA:
    def __init__(self, seed: AllocatorUnit | bytes | str):
        self.toolbox = base.Toolbox()

        # toolbox settings
        self.toolbox.register("empty_individual", Individual, seed)
        self.__ind_seed = self.toolbox.empty_individual()
        self.toolbox.register("individual", oplib.initialize_by_assist, self.__ind_seed)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register("evaluate", Evaluator.evaluate)
        self.toolbox.register("mate", cx_uniform)
        self.toolbox.register("mutate", mut_swap)
        self.toolbox.register("select", tools.selTournamentDCD)

        # statistics settings
        self.stats = tools.Statistics(key=lambda ind: ind.fitness.values)
        self.stats.register("avg", numpy.mean, axis=0)
        self.stats.register("min", numpy.min, axis=0)
        self.stats.register("max", numpy.max, axis=0)

        # logbook settings
        self.logbook = tools.Logbook()
        self.logbook.header = ["gen", "evals", "dups"] + Evaluator.eval_list()
        for eval_name in Evaluator.eval_list():
            self.logbook.chapters[eval_name].header = "min", "avg", "max"