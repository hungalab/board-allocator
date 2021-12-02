from __future__ import annotations
import time
import multiprocessing
import itertools
from typing import Optional

from deap import tools

#import networkx as nx

# my library
from galib import GA, Individual, my_multiprocessing_map, mate_or_mutate
from evaluator import Evaluator
import alns
from allocatorunit import AllocatorUnit

#----------------------------------------------------------------------------------------
class NSGA2(GA):
    def __init__(self, 
                 seed: AllocatorUnit | bytes | str, 
                 mate_pb: float = 0.7, 
                 mutation_pb: float = 0.3, 
                 archive_size: int = 40, 
                 offspring_size: Optional[int] = None):
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
    
    ##-----------------------------------------------------------------------------------
    def run(self, 
            exectution_time: float, 
            process_num: int = 1, 
            eliminate_dups:bool = True
            ) -> tools.ParetoFront:
        # multiprocessing settings
        if process_num != 1:
            pool = multiprocessing.Pool(process_num)
            self.toolbox.register("map", my_multiprocessing_map, pool)
        elif process_num == 1:
            self.toolbox.register("map", map)

        hall_of_fame = tools.ParetoFront()
        gen = 0

        # start timer
        start_time = time.time()

        # generate 0th population
        #pop = self.toolbox.population(self.pop_num)
        pop: list[Individual] 
        pop = list(self.toolbox.map(self.toolbox.individual, range(self.pop_num)))

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
        record = {eval_name: {"min": record["min"][i], 
                              "avg": record["avg"][i], "max": record["max"][i]}
                  for i, eval_name in enumerate(Evaluator.eval_list())}
        self.logbook.record(gen=0, evals=len(invalid_ind), dups='N/A', **record)

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
            offsprings: list[Individual]
            offsprings = list(itertools.chain.from_iterable(
                          map(self.toolbox.mate, parents[::2], parents[1::2], 
                              [1] * (len(parents) // 2))))

            # offsprings' mutation
            #offsprings += list(itertools.chain.from_iterable(\
            #              map(self.toolbox.mutate, pop, [1] * len(pop))))
            
            # 2-opt execution
            length = min(process_num, tournament_max_length)
            selected: list[Individual]
            selected = tools.selTournamentDCD(pop, 4 * ((length + 3) // 4) )
            selected = self.toolbox.map(alns.alns_test, selected, 
                                        [1] * length, [False] * length)
            for ind in selected:
                del ind.fitness.values
            offsprings += selected
            
            # evatuate offsprings
            invalid_ind = [ind for ind in offsprings if not ind.fitness.valid]
            fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit

            # selection
            pop += offsprings
            if eliminate_dups:
                dups = len(pop)
                pop = AllocatorUnit.unique(pop)
                dups -= len(pop)
            else:
                dups = 'N/A'
            pop = self.toolbox.select(pop, min(self.pop_num, len(pop)))

            # insert random individuals
            #rand_pop = self.toolbox.population(20 + (self.pop_num - len(pop)))
            rand_pop = list(self.toolbox.map(self.toolbox.individual, range(20 + (self.pop_num - len(pop)))))
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
            record = {eval_name: {"min": record["min"][i], "avg": record["avg"][i], "max": record["max"][i]}
                      for i, eval_name in enumerate(Evaluator.eval_list())}
            self.logbook.record(gen=gen, evals=len(invalid_ind), dups=dups, **record)

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


