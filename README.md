# board-allocator
This repository is based on https://github.com/KoibuchiLab/circuit-switch-table and https://github.com/KoibuchiLab/topology-generator.

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
