import argparse
import os
import os.path
import sys
sys.path.append(os.pardir)
from datetime import datetime, timedelta, timezone

from board_allocator import BoardAllocator

SIZES = [3, 4, 5, 6, 7, 8]
METHODS = ['ALNS', 'NSGA2']
EXP_TIME = 3600
TRIAL_NUM = 5
CONFIGS = ['single_unicast', 'multi_unicast', 'multi_broadcast']

EJECTION_TYPES = ['single', 'multi']
CASTING_TYPES = ['unicast', 'broadcast']
SCRIPT_DIR_NAME = os.path.dirname(__file__)
MULTI_UNICAST_DIR = os.path.join(SCRIPT_DIR_NAME, 'multiple_unicast')
BROADCAST_DIR = os.path.join(SCRIPT_DIR_NAME,'broadcast')
RESULT_DIR = os.path.join(SCRIPT_DIR_NAME,'result')

class Config:
    def __init__(self, ejection, casting):
        if not ejection in EJECTION_TYPES:
            raise ValueError("Invalid ejection type: {}".format(ejection))
        if not casting in CASTING_TYPES:
            raise ValueError("Invalid ejection type: {}".format(casting))
        self.ejection = ejection
        self.casting = casting

#----------------------------------------------------------------------------------------
def parser():
    parser = argparse.ArgumentParser(description='run_exp_alltoall')
    parser.add_argument('-s', help='size', nargs='+', default=SIZES, type=int)
    parser.add_argument('-m', help='method', nargs='+', default=METHODS, type=str)
    parser.add_argument('-n', help='# of traials for each configs', default=TRIAL_NUM, type=int)
    parser.add_argument('-c', help='ejection type and way to cast', nargs='+', default=CONFIGS)

    args = parser.parse_args()

    # checking method
    for method in args.m:
        if not method.upper() in METHODS:
            raise ValueError("Invalid method: {}".format(method))

    # checking the number of trials
    if args.n <= 0:
        raise ValueError("# of trials must be greater than 0.")

    # checking ejection and casting configs
    configs: list[Config] = list()
    for config in args.c:
        c = config.split('_')
        if len(c) != 2:
            raise ValueError("Invalid expression: {}".format(config))
        configs.append(Config(*c))
    
    # checking assets
    for size in args.s:
        # for topology files
        file_name = os.path.join(SCRIPT_DIR_NAME, 'topo{0}x{0}.txt'.format(size))
        if not os.path.isfile(file_name):
            raise ValueError("{} does not exist.".format(file_name))

        # for communication files
        for config in configs:
            if config.casting == 'broadcast':
                file_name = os.path.join(BROADCAST_DIR, 'comm{0}x{0}.txt'.format(size))
            else:
                file_name = os.path.join(MULTI_UNICAST_DIR, 'comm{0}x{0}.txt'.format(size))
            if not os.path.isfile(file_name):
                raise ValueError("{} does not exist.".format(file_name))

    
    return args.s, args.m, args.n, configs

#----------------------------------------------------------------------------------------
JST = timezone(timedelta(hours=+9))
def default_filename():
    return datetime.now(JST).strftime('%Y-%m-%d-%H%M-%S%f')

if __name__ == '__main__':
    sizes, methods, n, configs = parser()
    print('sizes: {}'.format(sizes))
    print('methods: {}'.format(methods))
    print('n: {}'.format(n))
    print('configs: {}'.format(['{}_{}'.format(c.ejection, c.casting) for c in configs]))

    # make directories
    if not os.path.isdir(RESULT_DIR):
        os.mkdir(RESULT_DIR)

    result_filename = os.path.join(RESULT_DIR, default_filename() + '.rpt')

    for config in configs:
        for method in methods:
            for size in sizes:
                output_list = [
                    "==============================",
                    "ejection: {}-ejection"         .format(config.ejection),
                    "casting: {}"                   .format("multiple-unicast" if config.casting == 'unicast' else config.casting),
                    "optimization method: {}"       .format(method),
                    "size: {0}x{0}"                 .format(size),
                    "==============================\n"
                ]
                for line in output_list:
                    print(line)
                with open(result_filename, mode='a') as f:
                    f.write('\n'.join(output_list))
                
                for i in range(n):
                    print("---------- {}-th ----------".format(i))

                    # optimization
                    topology_file = os.path.join(SCRIPT_DIR_NAME, 'topo{0}x{0}.txt'.format(size))
                    is_multi_ejection = (config.ejection == 'multi')
                    if config.casting == 'broadcast':
                        traffic_file = os.path.join(BROADCAST_DIR, 'comm{0}x{0}.txt'.format(size))
                    else:
                        traffic_file = os.path.join(MULTI_UNICAST_DIR, 'comm{0}x{0}.txt'.format(size))

                    allocator = BoardAllocator(topology_file, is_multi_ejection)
                    allocator.load_app(traffic_file)
                    if method.upper() == 'ALNS':
                        au = allocator.alns(EXP_TIME, for_exp=True)
                    else:
                        hof = allocator.nsga2(EXP_TIME, for_exp=True)
                        au = allocator.select_from_hof(hof)
                    slot_num = au.get_max_slot_num()

                    with open(result_filename, mode='a') as f:
                        f.write("{}th, {}\n".format(i, slot_num))
                    
                print("\n")
                with open(result_filename, mode='a') as f:
                    f.write("\n")


