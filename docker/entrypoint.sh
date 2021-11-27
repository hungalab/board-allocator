#!/bin/bash

USER_NAME=${LOCAL_NAME:-"user"}
GROUP_NAME=${LOCAL_GROUP:-"usergroup"}
USER_ID=${LOCAL_UID:-9001}
GROUP_ID=${LOCAL_GID:-9001}

groupadd -g $GROUP_ID $GROUP_NAME
useradd -u $USER_ID -g $GROUP_NAME -m $USER_NAME
export HOME=/home/$LOCAL_NAME

/usr/sbin/gosu $USER_NAME ln -s /usr/local/work /home/$LOCAL_NAME/work
/usr/sbin/gosu $USER_NAME ln -s /usr/local/.Xauthority $HOME/.Xauthority
cd $HOME/work
echo "Starting with `id $USER_NAME -u -n`(UID: `id $USER_NAME -u`, GID: `id $USER_NAME -g`(`id $USER_NAME -g -n`))"
echo $@
exec gosu $USER_NAME "$@"