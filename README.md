# board-allocator
board-allocator is a mapping tool to optimize the application mapping with the minimum number of time slots on Static Time Division Multiplexing (STDM).

This repository is based on [circuit-switch-table](https://github.com/KoibuchiLab/circuit-switch-table) and [topology-generator](https://github.com/KoibuchiLab/topology-generator) proposed in [2].

## Setup
This tool needs 
- Python3 (We recommend Python3.8~) 
- some Python libraries
- GCC which can compile C++11 programs with default settings.
We show the setup flow on `Ubuntu 22.04` and `CentOS 7` by using the `venv` module of Python3 and, also show the setup flow on a Docker container.
On other OS or versions you can use this tool.

### Ubuntu 22.04
```sh
$ sudo apt update
$ sudo apt install git gcc libgirepository1.0-dev libcairo2-dev pkg-config python3-gi python3-gi-cairo python3-dev python3-venv gir1.2-gtk-4.0

$ python3 -m venv <venv_path>
$ source <venv_path>/bin/activate
$ python3 -m pip install -U pip setuptools
$ python3 -m pip install deap matplotlib networkx pycairo PyGObject
$ cd <this_repo_path>
$ python3 setup.py install
```

### CentOS 7
```sh
$ sudo yum install -y epel-release
$ sudo yum install -y centos-release-scl
$ sudo yum group install -y "Development Tools"
$ sudo yum install -y devtoolset-7
$ sudo yum install -y rh-python38 rh-python38-python-devel 
$ sudo scl enable devtoolset-7 bash
# Check GCC version 
$ gcc --version
gcc (GCC) 7.3.1 20180303 (Red Hat 7.3.1-5)
Copyright (C) 2017 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

$ sudo scl enable rh-python38 bash
# Check Python3 version
$ python3 -V
Python 3.8.13

$ sudo yum install -y pkg-config gtk3-devel gobject-introspection-devel

$ python3 -m venv <venv_path>
$ source <venv_path>/bin/activate
$ python3 -m pip install -U pip setuptools
$ python3 -m pip install deap matplotlib networkx pycairo PyGObject
$ cd <this_repo_path>
$ python3 setup.py install
```

### Docker 
Please read [docker.md](https://github.com/hungalab/board-allocator/blob/main/docker/docker.md) in `/docker` directory.


## Artifact Evaluation
This tool experiment result is reported in [1] and [exp_random](https://github.com/hungalab/board-allocator/tree/main/exp_random) and [exp_alltoall](https://github.com/hungalab/board-allocator/tree/main/exp_alltoall) directories can help artifact evaluations of [1].

## Examples
[examples](https://github.com/hungalab/board-allocator/tree/main/examples) directory contains a example program to optimize application mapping and generate the table files of STDM switches on two types of FPGA clusters, FiC[3] and M-KUBOS cluster[4].

## cstgen.py
make switching table setting files for FiC <br>
### Usage for CLI
```
usage: cstgen.py [-h] [-t T] -c C [-s S]

cstgen

optional arguments:
  -h, --help  show this help message and exit
  -t T        topology file
  -c C        communication partern (traffic file)
  -s S        the number of slots
```
- `-c` option is mandatory. <br>
- `-t` option is not mandatory. When not specified, fic-topo-file-cross.txt is used. <br>
- `-s` option specifies the number of slots. When the specified number is less than the required number of slots, error occurs. When not specified, it will be the minimum number of slots that communication pattren requires. <br>

## Usage for library
You can use cstgen as library. Please refer https://github.com/hungalab/board-allocator/blob/master/example_for_cstgen_lib.py.
```
import cstgen

cst = cstgen.cstgen("fic-topo-file-cross.txt", "fft8.txt", 0, False)
cst.main()
cst.flowid2slotid(flow_id) #return slot id (int) corresponding flow id
cst.table(board_name) #return table (OrderedDict) corresponding board name
```


## References
[1] K. Ito, R. Yasudo and H. Amano, "Optimizing Application Mapping for Multi-FPGA Systems with Multi-ejection STDM Switches," 2022 32nd International Conference on Field-Programmable Logic and Applications (FPL), Belfast, United Kingdom, 2022, pp. 143-147 \
DOI: 10.1109/FPL57034.2022.00032

[2] Yao Hu and Michihiro Koibuchi. “Optimizing Slot Utilization and Network Topology for Communication Pattern on Circuit-Switched Parallel Computing Systems”. IEICE Transactions on Information and Systems, E102.D(2):247–260, 2019.\
DOI: 10.1587/transinf.2018EDP7225
 
[3] Musha, K., Kudoh, T., Amano, H, "Deep Learning on High Performance FPGA Switching Boards: Flow-in-Cloud", Applied Reconfigurable Computing. Architectures, Tools, and Applications. ARC 2018. \
DOI: https://doi.org/10.1007/978-3-319-78890-6_4

[4] T. Inage, K. Hironaka, K. Iizuka, K. Ito, Y. Fukushima, M. Namiki, and H. Amano, “M-KUBOS/PYNQ Cluster for multi-access edge computing,” in 2021 Ninth International Symposium on Computing and Networking (CANDAR), 2021, pp. 1–8.\
DOI: 10.1109/CANDAR53791.2021.00020
