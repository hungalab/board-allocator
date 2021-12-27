import argparse
import os
import os.path
import sys
sys.path.append(os.pardir)
from datetime import datetime, timedelta, timezone

from board_allocator import BoardAllocator

SIZES = [4, 8]
METHODS = ['ALNS', 'NSGA2']
EJECTION_TYPES = ['single', 'multi']
TRIAL_NUM = 5
APPS = ['p2p', 'fft']
EXP_TIME = 3600

SCRIPT_DIR_NAME = os.path.dirname(__file__)
RESULT_DIR = os.path.join(SCRIPT_DIR_NAME,'result')

#----------------------------------------------------------------------------------------
def parser():
    parser = argparse.ArgumentParser(description='run_exp_alltoall')
    parser.add_argument('-s', help='size', nargs='+', default=SIZES, type=int)
    parser.add_argument('-m', help='method', nargs='+', default=METHODS, type=str)
    parser.add_argument('-n', help='# of traials for each configs', default=TRIAL_NUM, type=int)
    parser.add_argument('-e', help='ejection type', nargs='+', default=EJECTION_TYPES)
    parser.add_argument('-a', help='apps', nargs='+', default=APPS)

    args = parser.parse_args()

    # checking method
    for method in args.m:
        if not method.upper() in METHODS:
            raise ValueError("Invalid method: {}".format(method))

    # checking the number of trials
    if args.n <= 0:
        raise ValueError("# of trials must be greater than 0.")

    # checking ejection type
    for e in args.e:
        if not e in EJECTION_TYPES:
            raise ValueError("Invalid ejection type: {}".format(e))
    
    # checking assets
    for size in args.s:
        # for topology files
        file_name = os.path.join(SCRIPT_DIR_NAME, 'topo{0}x{0}.txt'.format(size))
        if not os.path.isfile(file_name):
            raise ValueError("{} does not exist.".format(file_name))

        # for communication files
        for app in args.a:
            file_name = os.path.join(SCRIPT_DIR_NAME, '{0}_comm{1}x{1}.txt'.format(app, size))
            if not os.path.isfile(file_name):
                raise ValueError("{} does not exist.".format(file_name))
    
    return args.s, args.m, args.n, args.e, args.a

#----------------------------------------------------------------------------------------
JST = timezone(timedelta(hours=+9))
def default_filename():
    return datetime.now(JST).strftime('%Y-%m-%d-%H%M-%S%f')

if __name__ == '__main__':
    sizes, methods, n, ejections, apps = parser()
    print('sizes: {}'.format(sizes))
    print('methods: {}'.format(methods))
    print('n: {}'.format(n))
    print('ejection type: {}'.format(ejections))
    print('apps: {}'.format(apps))

    # make directories
    if not os.path.isdir(RESULT_DIR):
        os.mkdir(RESULT_DIR)

    result_filename = os.path.join(RESULT_DIR, default_filename() + '.rpt')

    for app in apps:
        for ejection in ejections:
            for method in methods:
                for size in sizes:
                    output_list = [
                        "==============================",
                        "application: {}"               .format(app),
                        "ejection: {}-ejection"         .format(ejection),
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
                        is_multi_ejection = (ejection == 'multi')
                        traffic_file = os.path.join(SCRIPT_DIR_NAME, '{0}_comm{1}x{1}.txt'.format(app, size))

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