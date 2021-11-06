import time
import random
import multiprocessing
import itertools

from deap import tools

#import networkx as nx

# my library
from galib import GA, my_multiprocessing_map, mate_or_mutate

#--------------------------------------------------------------
class NSGA2(GA):
    def __init__(self, seed, mate_pb=0.7, mutation_pb=0.3, archive_size=40, \
                 offspring_size=None):
        super().__init__(seed)
        self.toolbox.register("select", tools.selNSGA2)
        self.mate_pb = mate_pb
        self.mutation_pb = mutation_pb
        self.pop_num = archive_size
        if offspring_size is None:
            self.offspring_size = archive_size - (archive_size % 4)
        elif offspring_size % 4 == 0:
            self.offspring_size = offspring_size
        else:
            raise ValueError("offspring_size must be a multiple of 4.")
    
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
        mate_pb_array = [self.mate_pb] * (self.offspring_size //2)
        mut_pb_array = [self.mutation_pb] * self.offspring_size
        mate_array = [self.toolbox.mate] * (self.offspring_size // 2)
        mutate_array = [self.toolbox.mutate] * (self.offspring_size // 2)

        # start timer
        start_time = time.time()

        # generate 0th population
        pop = self.toolbox.population(self.pop_num)

        # evaluate the population
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

            # binary tournament selection
            parents = list()
            tournament_max_length = len(pop) - (len(pop) % 4)
            max_loop_index = self.offspring_size // tournament_max_length
            for i in range(max_loop_index + 1):
                if i != max_loop_index:
                    length = tournament_max_length
                else:
                    length = self.offspring_size - (tournament_max_length * max_loop_index)
                parents += tools.selTournamentDCD(pop, length)
            

            #offsprings = list(itertools.chain.from_iterable(
            #              map(mate_or_mutate, mate_array, mutate_array, 
            #                  parents[::2], parents[1::2], mate_pb_array)))
            
            offsprings = list(itertools.chain.from_iterable(\
                          map(self.toolbox.mate, parents[::2], parents[1::2], [1] * (len(parents) // 2))))

            # offsprings' mutation
            offsprings += list(itertools.chain.from_iterable(\
                          map(self.toolbox.mutate, pop, [1] * len(pop))))
            
            # evatuate offsprings
            invalid_ind = [ind for ind in offsprings if not ind.fitness.valid]
            fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            # selection
            pop = self.toolbox.select(pop + offsprings, self.pop_num)

            # insert random individuals
            rand_pop = self.toolbox.population(20)
            fitnesses = self.toolbox.map(self.toolbox.evaluate, rand_pop)
            for ind, fit in zip(rand_pop, fitnesses):
                ind.fitness.values = fit
            rand_pop = self.toolbox.select(rand_pop, len(rand_pop))
            pop += rand_pop
            invalid_ind += rand_pop

            # update hall of fame
            hall_of_fame.update(pop)

            # record
            record = self.stats.compile(pop)
            record = {eval_name: {"min": record["min"][i], "avg": record["avg"][i], "max": record["max"][i]} \
                      for i, eval_name in enumerate(self.eval_tool.eval_list())}
            self.logbook.record(gen=gen, evals=len(invalid_ind), **record)

        if process_num != 1:
            pool.close()
            pool.join()

        print(self.logbook.stream)
        print("# of individuals in hall_of_fame: {}".format(len(hall_of_fame)))
        indbook = tools.Logbook()
        indbook.header = ['index'] + self.eval_tool.eval_list()
        for i, ind in enumerate(hall_of_fame):
            record = {name: value for name, value in zip(self.eval_tool.eval_list(), ind.fitness.values)}
            indbook.record(index=i, **record)
        print(indbook.stream)
    
        return hall_of_fame


