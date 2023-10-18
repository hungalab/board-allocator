import argparse
import os
import os.path
import sys
import json
from datetime import datetime, timedelta, timezone

sys.path.append(os.pardir)
from board_allocator import BoardAllocator
import cstgen

METHODS = ['ALNS', 'NSGA2']
EJECTION_TYPES = ['single', 'multi']
EXP_TIME = 5 * 60

SCRIPT_DIR_NAME = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(SCRIPT_DIR_NAME, 'result')


#----------------------------------------------------------------------------------------
def parser():
    parser = argparse.ArgumentParser(description='run_example_board_allocator')
    parser.add_argument('-t', help='topology file path', type=str)
    parser.add_argument('-a', help='application flow file path', type=str)
    parser.add_argument('-m', help='optimization method', nargs='+', default=METHODS, type=str)
    parser.add_argument('-e', help='ejection type', nargs='+', default=EJECTION_TYPES)
    parser.add_argument('--time', help='time for optimization [s]', default=EXP_TIME, type=int)

    args = parser.parse_args()

    # checking topology file
    if not os.path.exists(args.t):
        print(f"{args.t} is not found")
        exit(1)
    # checking app flow file
    if not os.path.exists(args.a):
        print(f"{args.a} is not found")
        exit(1)
    # checking method
    for method in args.m:
        if not method.upper() in METHODS:
            raise ValueError("Invalid method: {}".format(method))
    # checking ejection type
    for e in args.e:
        if not e in EJECTION_TYPES:
            raise ValueError("Invalid ejection type: {}".format(e))

    return args.t, args.a, args.m, args.e, args.time

#----------------------------------------------------------------------------------------
def default_filename():
    JST = timezone(timedelta(hours=+9))
    return datetime.now(JST).strftime('%Y-%m-%d-%H%M-%S%f')

def show_routing():
    topology_file: str = "../fic-topo-file-cross.txt"
    app_flow_file: str = "app_flow2.txt"
    ejection: str = "single"
    is_multi_ejection: bool = (ejection == 'multi')

    allocator = BoardAllocator(topology_file, is_multi_ejection)

    # Check AllocatorUnit
    au = allocator.au
    flow_dict = au.flow_dict
    pair_dict = au.pair_dict
    shortest_path_table = au.st_path_table
    src = 1
    dst = 3
    path_list = shortest_path_table[src][dst]
    for path in path_list:
        print(path)
        """
        This shows like following.
        (1, 25, 24, 27, 3) -> 25: switch of board1, 24: switch of board0, 27: switch of board3.
        (1, 25, 26, 27, 3) -> 25: switch of board1, 26: switch of board2, 27: switch of board3.

        """

    # Check cstgen
    cst = cstgen.cstgen(topology_file, app_flow_file, 0, False)
    cst.main()
    cst_log = cst.writeLog_str
    print(cst_log)
    routing_dict: dict = cst.get_routing()
    print(routing_dict)


def main():
    topology_file, app_flow_file, methods, ejections, exp_time= parser()
    print(f"topology: {topology_file}")
    print(f"app flow: {app_flow_file}")
    print(f"methods: {methods}")
    print(f"ejection type: {ejections}")

    RESULT_DIR = os.path.join(os.getcwd(), "result")

    # make directories
    if not os.path.isdir(RESULT_DIR):
        os.mkdir(RESULT_DIR)

    result_filename = os.path.join(RESULT_DIR, default_filename() + '.log')

    for ejection in ejections:
        for method in methods:
            # optimization
            is_multi_ejection = (ejection == 'multi')

            allocator = BoardAllocator(topology_file, is_multi_ejection)
            real_flow_file = os.path.join(RESULT_DIR, f"{ejection}_{method}")
            # Show the topology of cluster
            
            allocator.load_app(app_flow_file)
            if method.upper() == 'ALNS':
                au = allocator.alns(exp_time)
            else:
                hof = allocator.nsga2(exp_time)
                au = allocator.select_from_hof(hof)
            slot_num = au.get_max_slot_num()
            print("Show the allocated nodes")
            allocator.show_nodes()
            allocator.write_real_flows(real_flow_file)
            result = f"the # of slots in {method}, {ejection} is {slot_num}\n"

            with open(result_filename, mode='a') as f:
                f.write(result)
            print(f"[INFO] Finish optimization [{method}, {ejection}]")

            cst = cstgen.cstgen(topology_file, real_flow_file, 0, False)
            cst.main()
            print("table list of m2fic00")
            table_dict = cst.table("m2fic00") #Return table (OrderedDict) corresponding board name
            print(json.dumps(table_dict, indent=2)) 
    
    print(f"[INFO] Finish all optimizations and result is in {result_filename}")

if __name__ == '__main__':
    # main()
    show_routing()