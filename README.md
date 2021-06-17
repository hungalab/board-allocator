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
`-c` option is mandatory. <br>
`-t` option is not mandatory. When not specified, fic-topo-file-cross.txt is used. <br>
You can specify the number of slots by `-s` option. When not specified, it will be the minimum number o slots that can meet the condition of the traffic file. <br>

## Usage for library
