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
    def __init__(self, seed, mate_pb=1, mutation_pb=0.3, archive_size=40, \
                 offspring_size=None, sort_method='cyclic'):
        super().__init__(seed)
        self.toolbox.register("select", tools.selSPEA2)
        self.mate_pb = mate_pb
        self.mutation_pb = mutation_pb
        self.pop_num = archive_size

        if offspring_size is None:
            self.offspring_size = archive_size - (archive_size % 2)
        elif offspring_size % 2 == 0:
            self.offspring_size = self.offspring_size
        else:
            ValueError("offspring_size must be a multiple of 2.")

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
        mate_pb_array = [self.mate_pb] * self.offspring_size
        mut_pb_array = [self.mutation_pb] * (self.pop_num + self.offspring_size)

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
            parents = sorted(pop, key=lambda ind: ind.fitness.values[index])[0:self.offspring_size]
            offsprings = list(itertools.chain.from_iterable(\
                          self.toolbox.map(self.toolbox.mate, parents[::2], parents[1::2], mate_pb_array)))

            # mutation
            pop = pop + offsprings
            pop = list(itertools.chain.from_iterable(\
                   self.toolbox.map(self.toolbox.mutate, pop, mut_pb_array)))
            
            # evatuate offsprings
            invalid_ind = [ind for ind in pop if not ind.fitness.valid]
            fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            # update hall of fame
            hall_of_fame.update(pop)

            # selection
            pop = self.toolbox.select(pop, self.pop_num)

            # record
            record = self.stats.compile(pop)
            record = {eval_name: {"min": record["min"][i], "avg": record["avg"][i], "max": record["max"][i]} \
                      for i, eval_name in enumerate(self.eval_tool.eval_list())}
            self.logbook.record(gen=gen, evals=len(invalid_ind), **record)

        if process_num != 1:
            pool.close()
            pool.join()
    
        return hall_of_fame, self.logbook