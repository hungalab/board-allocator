import time
import random

import networkx as nx

from deap import tools
from deap import base
from deap import algorithms
from deap import creator

# my library
from allocatorunit import AllocatorUnit, App, Pair, VNode

#--------------------------------------------------------------
class GA:
    def __init__(self, seed):
        self.toolbox = base.Toolbox()

        # settings to use deap
        creator.create("Fitness", base.Fitness, weights=(TBD))
        creator.create("Individual", AllocatorUnit, fitness=creator.Fitness)

        self.

