import argparse
import os
import os.path
import sys
sys.path.append(os.pardir)
from datetime import datetime, timedelta, timezone

from board_allocator import BoardAllocator

TOPO_NUM = 30
METHODS = ['ALNS', 'NSGA2']
EJECTION_TYPES = ['single', 'multi']
APPS = ['a2a', 'fft', 'fork']
APP_SIZE = 16
EXP_TIME = 3600

SCRIPT_DIR_NAME = os.path.dirname(__file__)
RESULT_DIR = os.path.join(SCRIPT_DIR_NAME,'result')

#----------------------------------------------------------------------------------------
def parser():
    parser = argparse.ArgumentParser(description='run_exp_alltoall')
    parser.add_argument('-t', help='# of topologies', default=TOPO_NUM, type=int)
    parser.add_argument('-m', help='method', nargs='+', default=METHODS, type=str)
    parser.add_argument('-e', help='ejection type', nargs='+', default=EJECTION_TYPES)
    parser.add_argument('-a', help='apps', nargs='+', default=APPS)

    args = parser.parse_args()

    # checking topologies
    if args.t <= 0:
        raise ValueError("# of trials must be greater than 0.")
    for i in range(args.t):
        file_name = os.path.join(SCRIPT_DIR_NAME, 'topo{0}.txt'.format(i))
        if not os.path.isfile(file_name):
            raise ValueError("{} does not exist.".format(file_name))

    # checking method
    for method in args.m:
        if not method.upper() in METHODS:
            raise ValueError("Invalid method: {}".format(method))

    # checking ejection type
    for e in args.e:
        if not e in EJECTION_TYPES:
            raise ValueError("Invalid ejection type: {}".format(e))

    # for communication files
    for app in args.a:
        file_name = os.path.join(SCRIPT_DIR_NAME, '{0}_{1}.txt'.format(app, APP_SIZE))
        if not os.path.isfile(file_name):
            raise ValueError("{} does not exist.".format(file_name))
    
    return args.t, args.m, args.e, args.a

#----------------------------------------------------------------------------------------
JST = timezone(timedelta(hours=+9))
def default_filename():
    return datetime.now(JST).strftime('%Y-%m-%d-%H%M-%S%f')

if __name__ == '__main__':
    topo_num, methods, ejections, apps = parser()
    print('# of topologies: {}'.format(topo_num))
    print('methods: {}'.format(methods))
    print('ejection type: {}'.format(ejections))
    print('apps: {}'.format(apps))

    # make directories
    if not os.path.isdir(RESULT_DIR):
        os.mkdir(RESULT_DIR)

    result_filename = os.path.join(RESULT_DIR, default_filename() + '.rpt')

    for app in apps:
        for ejection in ejections:
            for method in methods:
                for i in range(topo_num):
                    output_list = [
                        "==============================",
                        "application: {}"               .format(app),
                        "ejection: {}-ejection"         .format(ejection),
                        "optimization method: {}"       .format(method),
                        "topology id: {}"               .format(i),
                        "==============================\n"
                    ]
                    for line in output_list:
                        print(line)
                    with open(result_filename, mode='a') as f:
                        f.write('\n'.join(output_list))

                    # optimization
                    topology_file = os.path.join(SCRIPT_DIR_NAME, 'topo{0}.txt'.format(i))
                    is_multi_ejection = (ejection == 'multi')
                    traffic_file = os.path.join(SCRIPT_DIR_NAME, '{0}_{1}.txt'.format(app, APP_SIZE))

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