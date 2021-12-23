SHELL:=/bin/bash

IMAGE_NAME:=board-allocator
WORKING_DIR:=$(CURDIR)/../

DOCKER_RUN_VOLUMES:=-v $(WORKING_DIR):/usr/local/work
DOCKER_RUN_OPTIONS:=--name $(IMAGE_NAME) -it --rm
DOCKER_RUN_ENVS:= -e LOCAL_NAME=$(USER) -e LOCAL_GROUP=`id -g -n` -e LOCAL_UID=`id -u` -e LOCAL_GID=`id -g`
DOCKER_RUN_DISPLAY:= -e DISPLAY=$(DISPLAY) -v /tmp/.X11-unix:/tmp/.X11-unix -v $(HOME)/.Xauthority:/usr/local/.Xauthority --network=host

default: start

build:
	docker build -t $(IMAGE_NAME) .

start:
	docker run $(DOCKER_RUN_OPTIONS) $(DOCKER_RUN_VOLUMES) $(DOCKER_RUN_ENVS) $(DOCKER_RUN_DISPLAY) $(IMAGE_NAME)

nodisp:
	docker run $(DOCKER_RUN_OPTIONS) $(DOCKER_RUN_VOLUMES) $(DOCKER_RUN_ENVS) $(IMAGE_NAME)

exec:
	docker exec -it $(IMAGE_NAME) bash
