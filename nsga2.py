import time
import random
import multiprocessing
import itertools

from deap import tools
from deap import base
from deap import algorithms
from deap import creator

#import networkx as nx

# my library
from allocatorunit import AllocatorUnit#, App, Pair, VNode, Flow
from galib import GA, Evaluator, my_multiprocessing_map

#--------------------------------------------------------------
class NSGA2(GA):
    def __init__(self, seed, mate_pb=1, mutation_pb=0.5, pop_num=40, offspring_num=None):
        super().__init__(seed)
        self.toolbox.register("select", tools.selNSGA2)
        self.mate_pb = mate_pb
        self.mutation_pb = mutation_pb
        self.pop_num = pop_num
        if offspring_num is None:
            self.offspring_num = pop_num
        elif offspring_num % 2 == 0:
            self.offspring_num = offspring_num
        else:
            ValueError("offspring_num should be an even number.")
    
    def run(self, exectution_time, process_num=1):
        # multiprocessing settings
        if process_num != 1:
            pool = multiprocessing.Pool(process_num)
            self.toolbox.register("map", my_multiprocessing_map, pool)

        hall_of_fame = tools.ParetoFront()
        gen = 0
        mut_pb_array = [self.mutation_pb] * self.offspring_num

        # start timer
        start_time = time.time()

        # generate 0th population
        pop = self.toolbox.population(self.pop_num)

        # evaluate
        invalid_ind = [ind for ind in pop if not ind.fitness.valid]
        fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

        # assign the crowding distance
        pop = self.toolbox.select(pop, len(pop))

        # update hall of fame
        hall_of_fame.update(pop)

        # record
        record = self.stats.compile(pop)
        record = {eval_name: {"min": record["min"][i], "avg": record["avg"][i], "max": record["max"][i]} \
                  for i, eval_name in enumerate(self.eval_tool.eval_list())}
        self.logbook.record(gen=0, evals=len(invalid_ind), **record)

        while time.time() - start_time < exectution_time:
            # uppdate generation number
            gen += 1

            # generate offsprings
            parents = random.choices(pop, k=self.offspring_num)
            offsprings = list(itertools.chain.from_iterable(self.toolbox.map(self.toolbox.mate, parents[::2], parents[1::2])))

            # offsprings' mutation
            self.toolbox.map(self.toolbox.mutate, offsprings, mut_pb_array)

            # delete offsprings' fitness
            for ind in offsprings:
                del ind.fitness.values
            
            # evatuate offsprings
            invalid_ind = [ind for ind in offsprings if not ind.fitness.valid]
            fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            # update hall of fame
            hall_of_fame.update(pop)

            # selection
            pop = self.toolbox.select(pop + offsprings, self.pop_num)

            # record
            record = self.stats.compile(pop)
            record = {eval_name: {"min": record["min"][i], "avg": record["avg"][i], "max": record["max"][i]} \
                      for i, eval_name in enumerate(self.eval_tool.eval_list())}
            self.logbook.record(gen=gen, evals=len(invalid_ind), **record)

        if process_num != 1:
            pool.close()
            pool.join()
    
        return hall_of_fame, self.logbook


