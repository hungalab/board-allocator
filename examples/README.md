# Example of board allocator

This directory contains a example program to optimize application mapping and generate the table files of STDM switches on FiC and M-KUBOS cluster.
This optimization method are published as [1].

## Run board allocator and cstgen
cstgen is a tool developed by Koibuchi lab at NII [2].
This example runs board allocator to determine which four boards are used in FiC for executing FFT and generate the table files of STDM switches on FiC.

### How to run
Simply, just run the shell script as following.

`$ ./run.sh`

This script executes a python script. 

`$ python3 run_allocator.py -t ../fic-topo-file-cross.txt -a fft4_app_flow.txt -e single --time 60`

`-t` arg is the system topology file and in this example, we assume FiC as the system. \
`-a` arg is the application flow file which represents the flow of an application.
In this example, we use FFT on 4boards as the target application.\
`-e` arg is the type of ejection refered in [3] and usually we specify `single` option.\
`--time` arg means the time for optimization and in this command we can search 60 minutes.

### Output of this example

This example create `/result` and `/output` directory.
In `/result` directory, there is a log file of optimization flow and `/output` directory contains the table files of 24 FiC-SW boards(board0.json ~ board23.json) which can be configured from `ficmgr`.

## References
[1] K. Ito, R. Yasudo and H. Amano, "Optimizing Application Mapping for Multi-FPGA Systems with Multi-ejection STDM Switches," 2022 32nd International Conference on Field-Programmable Logic and Applications (FPL), Belfast, United Kingdom, 2022, pp. 143-147 \
DOI: 10.1109/FPL57034.2022.00032

[2] Yao Hu and Michihiro Koibuchi. “Optimizing Slot Utilization and Network Topology for Communication Pattern on Circuit-Switched Parallel Computing Systems”. IEICE Transactions on Information and Systems, E102.D(2):247–260, 2019.\
DOI: 10.1587/transinf.2018EDP7225
 
[3] Kohei Ito, Kensuke Iizuka, Kazuei Hironaka, Yao Hu, Michihiro Koibuchi, and Hideharu Amano. “Improving the Performance of Circuit-Switched Interconnection Network for a Multi-FPGA System”. IEICE　Transactions on Information and Systems, E104.D(12):2029–2039, 2021. \
DOI: 10.1587/transinf.2021PAP0002
