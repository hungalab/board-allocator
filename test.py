from board_allocator import BoardAllocator

from nsga2 import NSGA2

actor = BoardAllocator('fic-topo-file-cross.txt', True)
actor.load_app('cg24-tf.txt')
seed = actor.au.dumps()
nsga2 = NSGA2(seed, 0.7, 0.3, 40, None)
hall_of_fame = nsga2.run(3600, 8)