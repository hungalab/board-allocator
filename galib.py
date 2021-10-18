import random
import copy
import collections
import numpy
from functools import partial

import networkx as nx

from deap import tools
from deap import base
from deap import creator

# my library
from allocatorunit import AllocatorUnit
from evaluator import Evaluator
import oplib

def mask_generator(sorted_vNode_id_list):
    l0, l1 = dict(), dict()
    for vNode_id in sorted_vNode_id_list:
        bit = random.randint(0, 1)
        l0[vNode_id] = bit
        l1[vNode_id] = bit ^ 1
    return l0, l1

#--------------------------------------------------------------
def cx_by_mask(parent0, parent1, mask):
    child = copy.deepcopy(parent0)

    for vNode_id, bit in mask.items():
        vNode = child.vNode_dict[vNode_id]
        if bit == 0:
            # deallocate pairs whose dst or src is changed
            for pair in vNode.send_pair_list:
                if mask[pair.dst_vNode.vNode_id] != bit:
                    oplib.pair_deallocation(child, pair.pair_id)
            
            for pair in vNode.recv_pair_list:
                if mask[pair.src_vNode.vNode_id] != bit:
                    oplib.pair_deallocation(child, pair.pair_id)
        
        elif bit == 1:
            old_rNode_id = vNode.rNode_id
            new_rNode_id = parent1.vNode_dict[vNode_id].rNode_id
            # node deallocation (update the list and dict)
            if old_rNode_id is not None:
                child.temp_allocated_rNode_dict.pop(old_rNode_id)
                child.empty_rNode_set.add(old_rNode_id)
            # temporary node allocation
            try:
                child.empty_rNode_set.remove(new_rNode_id)
            except KeyError:
                # when new_rNode_id has already been secured, release new_rNode_id
                target_vNode_id = child.temp_allocated_rNode_dict[new_rNode_id]
                child.vNode_dict[target_vNode_id].rNode_id = None
            child.temp_allocated_rNode_dict[new_rNode_id] = vNode.vNode_id
            # update rNode_id
            vNode.rNode_id = new_rNode_id

            # update pairs
            for pair in vNode.send_pair_list:
                if mask[pair.dst_vNode.vNode_id] != bit:
                    oplib.pair_deallocation(child, pair.pair_id)
                else:
                    path = parent1.pair_dict[pair.pair_id].path
                    oplib.pair_allocation(child, pair.pair_id, path)
            
            for pair in vNode.recv_pair_list:
                if mask[pair.src_vNode.vNode_id] != bit:
                    oplib.pair_deallocation(child, pair.pair_id)
                else:
                    path = parent1.pair_dict[pair.pair_id].path
                    oplib.pair_allocation(child, pair.pair_id, path)
        
        else:
            old_rNode_id = vNode.rNode_id
            vNode.rNode_id = None
            # node deallocation (update the list and dict)
            if old_rNode_id is not None:
                child.temp_allocated_rNode_dict.pop(old_rNode_id)
                child.empty_rNode_set.add(old_rNode_id)

            # send-path deallocation
            for send_pair in vNode.send_pair_list:
                if send_pair.path is not None:
                    oplib.pair_deallocation(child, send_pair.pair_id)

            # recv-path deallocation
            for recv_pair in vNode.recv_pair_list:
                if recv_pair.path is not None:
                    oplib.pair_deallocation(child, recv_pair.pair_id)

    for vNode in child.allocating_vNode_list:
        if vNode.rNode_id is None:
            oplib.random_node_allocation(child, vNode.vNode_id)
    
    for pair in child.allocating_pair_list:
        if pair.path is None:
            oplib.random_pair_allocation(child, pair.pair_id)
    
    return child


#--------------------------------------------------------------
def cx_uniform(parent0, parent1):
    if len(parent0.temp_allocated_rNode_dict) != len(parent1.temp_allocated_rNode_dict):
        raise ValueError("The number of nodes being allocated is different for each parent.")
    
    if len(parent0.allocating_pair_list) != len(parent1.allocating_pair_list):
        raise ValueError("The number of communications being allocated is different for each parent.")
    
    # make masks
    sorted_vNode_id_list = sorted(parent0.temp_allocated_rNode_dict.values())
    mask0, mask1 = mask_generator(sorted_vNode_id_list)

    ## check the duplication
    next_child0_rNode_dict = {vNode_id: parent1.vNode_dict[vNode_id].rNode_id if bit \
                                        else parent0.vNode_dict[vNode_id].rNode_id \
                              for vNode_id, bit in mask0.items()}
    counter = collections.Counter(list(next_child0_rNode_dict.values()))
    for key, count in counter.items():
        if count == 2:
            selected = random.randint(0, 1)
            current = 0
            for vNode_id, rNode_id in next_child0_rNode_dict.items():
                if rNode_id == key and current != selected:
                    mask0[vNode_id] = 2
                    current += 1
                    break
                elif rNode_id == key and current == selected:
                    current += 1
    
    next_child1_rNode_dict = {vNode_id: parent1.vNode_dict[vNode_id].rNode_id if bit \
                                        else parent0.vNode_dict[vNode_id].rNode_id \
                              for vNode_id, bit in mask1.items()}
    counter = collections.Counter(list(next_child1_rNode_dict.values()))
    for key, count in counter.items():
        if count == 2:
            selected = random.randint(0, 1)
            current = 0
            for vNode_id, rNode_id in next_child1_rNode_dict.items():
                if rNode_id == key and current != selected:
                    mask1[vNode_id] = 2
                    current += 1
                    break
                elif rNode_id == key and current == selected:
                    current += 1

    # exectute crossover
    child0 = cx_by_mask(parent0, parent1, mask0)
    child1 = cx_by_mask(parent0, parent1, mask1)
    return child0, child1

#--------------------------------------------------------------
def mut_swap(individual, mut_pb):
    if not 0 <= mut_pb <= 1 :
        raise ValueError("Specify a value between 0 and 1.")
    
    if random.random() < mut_pb:
        vNode = random.choice(individual.allocating_vNode_list)
        oplib.node_swap(individual, vNode.vNode_id)

    return individual,

#--------------------------------------------------------------
def initialization_with_solution(solution, constructor):
    return solution(constructor())

#--------------------------------------------------------------
def wrapper(func, args):
    return func(*args)

#--------------------------------------------------------------
def my_multiprocessing_map(pool, func, *iterable):
    return pool.map(partial(wrapper, func), [elements for elements in zip(*iterable)])

#--------------------------------------------------------------
class GA:
    def __init__(self, seed):
        self.toolbox = base.Toolbox()

        # create evaluation tool
        self.eval_tool = Evaluator()

        # instance settings
        creator.create("Fitness", base.Fitness, weights=self.eval_tool.weights())
        creator.create("Individual", AllocatorUnit, fitness=creator.Fitness)

        # toolbox settings
        self.toolbox.register("empty_individual", creator.Individual, None, seed)
        self.toolbox.register("individual", initialization_with_solution, \
                              oplib.generate_initial_solution, self.toolbox.empty_individual)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)
        self.toolbox.register("evaluate", self.eval_tool.evaluate)
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
        self.logbook.header = ["gen", "evals"] + self.eval_tool.eval_list()
        for eval_name in self.eval_tool.eval_list():
            self.logbook.chapters[eval_name].header = "min", "avg", "max"