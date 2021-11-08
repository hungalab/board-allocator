import time
import random
import multiprocessing
import itertools

from deap import tools

#import networkx as nx

# my library
from galib import GA, my_multiprocessing_map
from evaluator import Evaluator

#--------------------------------------------------------------
class NCGA(GA):
    SORT_METHOD_LIST = ['cyclic', 'random']

    def __init__(self, seed, mate_pb=1, mutation_pb=0.5, archive_size=40, \
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
            raise ValueError("offspring_size must be a multiple of 2.")

        if sort_method in NCGA.SORT_METHOD_LIST:
            self.sort_method = sort_method
        else:
            raise ValueError("Invalid sort_method.")

    ##---------------------------------------------------------
    def run(self, exectution_time, process_num=1):
        # multiprocessing settings
        if process_num != 1:
            pool = multiprocessing.Pool(process_num)
            self.toolbox.register("map", my_multiprocessing_map, pool)
        elif process_num == 1:
            self.toolbox.register("map", map)

        hall_of_fame = tools.ParetoFront()
        gen = 0
        mate_pb_array = [self.mate_pb] * (self.offspring_size // 2)
        mut_pb_array = [self.mutation_pb] * self.offspring_size

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
                  for i, eval_name in enumerate(Evaluator.eval_list())}
        self.logbook.record(gen=0, evals=len(invalid_ind), **record)

        while time.time() - start_time < exectution_time:
            # uppdate generation number
            gen += 1

            # generate offsprings
            if self.sort_method == 'cyclic':
                index = (gen - 1) % len(Evaluator.eval_list())
            elif self.sort_method == 'random':
                index = random.randrange(len(Evaluator.eval_list()))
            parents = sorted(pop, key=lambda ind: ind.fitness.values[index])[0:self.offspring_size]
            offsprings = list(itertools.chain.from_iterable(\
                          map(self.toolbox.mate, parents[::2], parents[1::2], mate_pb_array)))

            # offsprings' mutation
            offsprings = list(itertools.chain.from_iterable(\
                          map(self.toolbox.mutate, offsprings, mut_pb_array)))
            
            # evatuate offsprings
            invalid_ind = [ind for ind in offsprings if not ind.fitness.valid]
            fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            # selection
            pop = self.toolbox.select(pop + offsprings, self.pop_num)

            ## insert random individuals
            #rand_pop = self.toolbox.population(20)
            #fitnesses = self.toolbox.map(self.toolbox.evaluate, rand_pop)
            #for ind, fit in zip(rand_pop, fitnesses):
            #    ind.fitness.values = fit
            #pop += rand_pop
            #invalid_ind += rand_pop

            # update hall of fame
            hall_of_fame.update(pop)

            # record
            record = self.stats.compile(pop)
            record = {eval_name: {"min": record["min"][i], "avg": record["avg"][i], "max": record["max"][i]} \
                      for i, eval_name in enumerate(Evaluator.eval_list())}
            self.logbook.record(gen=gen, evals=len(invalid_ind), **record)

        if process_num != 1:
            pool.close()
            pool.join()
        
        print(self.logbook.stream)
        print("# of individuals in hall_of_fame: {}".format(len(hall_of_fame)))
        indbook = tools.Logbook()
        indbook.header = ['index'] + Evaluator.eval_list()
        for i, ind in enumerate(hall_of_fame):
            record = {name: value for name, value in zip(Evaluator.eval_list(), ind.fitness.values)}
            indbook.record(index=i, **record)
        print(indbook.stream)
    
        return hall_of_fame