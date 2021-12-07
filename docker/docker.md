# Dokcer Support
You can execute board-allocator in a virtual environment with docker.

## Usage
Basic operations are described in the Makefile.
### make build
- Build docker image.
### make start
- run the docker image
- mount the parent directory and below under the virtual environment
- create a user with your local pc's user id and group id (i.e. the owner of the file added/edited in the container will be the same as when executed on the local pc)
### make runwdisp
- enable X forwarding
- other is same as "make start"