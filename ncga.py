import time
import random
import multiprocessing
import itertools

from deap import tools

#import networkx as nx

# my library
from galib import GA, my_multiprocessing_map

#--------------------------------------------------------------
class NCGA(GA):
    def __init__(self, seed, mate_pb=1, mutation_pb=0.5, pop_num=40, offspring_num=None, sort_method='cyclic'):
        super().__init__(seed)
        self.toolbox.register("select", tools.selSPEA2)
        self.mate_pb = mate_pb
        self.mutation_pb = mutation_pb
        self.pop_num = pop_num

        if pop_num % 2 == 0:
            self.offspring_num = pop_num
        else:
            self.offspring_num = pop_num - 1

        if sort_method in ['cyclic', 'random']:
            self.sort_method = sort_method
        else:
            ValueError("Invalid sort_method.")

    
    def run(self, exectution_time, process_num=1):
        # multiprocessing settings
        if process_num != 1:
            pool = multiprocessing.Pool(process_num)
            self.toolbox.register("map", my_multiprocessing_map, pool)

        hall_of_fame = tools.ParetoFront()
        gen = 0
        mate_pb_array = [self.mate_pb] * self.offspring_num
        mut_pb_array = [self.mutation_pb] * self.offspring_num

        # start timer
        start_time = time.time()

        # generate 0th population
        pop = self.toolbox.population(self.pop_num)

        # evaluate the population
        invalid_ind = [ind for ind in pop if not ind.fitness.valid]
        fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit

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
            if self.sort_method == 'cyclic':
                index = (gen - 1) % len(self.eval_tool.eval_list())
            elif self.sort_method == 'random':
                index = random.randrange(len(self.eval_tool.eval_list()))
            parents = sorted(pop, key=lambda ind: ind.fitness.values[index])[0:self.offspring_num]
            offsprings = list(itertools.chain.from_iterable(self.toolbox.map(self.toolbox.mate, parents[::2], parents[1::2], mate_pb_array)))

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