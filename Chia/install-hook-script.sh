#!/bin/bash
#
# this is a example hook script to use croit platform to create Chia Plots 
# please configure variables as you like and maybe change the settings of 
# the plot command according to your hardware as well 
#
# MIT Licensed, written by Martin Verges <martin.verges@croit.io>
# 

CHIA_FARMKEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CHIA_PUBKEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CHIA_TEMP=/mnt/cephfs/chia-temp/$(hostname)
CHIA_PLOTS=/mnt/cephfs/chia-plots/$(hostname)
CHIA_HOME=/mnt/cephfs/chia-home/$(hostname)
CHIA_BIN=/mnt/cephfs/chia-bin

CEPHFS_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CEPHFS_MONS=xxx.xxx.xxx.xxx.xxx,yyy.yyy.yyy.yyy,...
CEPHFS_DIR=/
CEPHFS_TARGET=/mnt/cephfs

apt-get -y update
apt-get -y install git lsb-release

if grep -qs "${CEPHFS_TARGET} " /proc/mounts; 
then
  echo "${CEPHFS_TARGET} already mounted"
else
  mkdir -p ${CEPHFS_TARGET}
  mount -t ceph -o name=chia,secret=${CEPHFS_SECRET} ${CEPHFS_MONS}:${CEPHFS_DIR} ${CEPHFS_TARGET}
fi

mkdir -p ${CHIA_TEMP}
mkdir -p ${CHIA_PLOTS}
mkdir -p ${CHIA_HOME}
[ -h ~/.chia ] || ln -s ${CHIA_HOME}/ ~/.chia

cd ${CHIA_BIN}
sh install.sh
. ./activate
chia init

echo """#!/bin/bash
cd ${CHIA_BIN}
. ./activate
cd ${CHIA_HOME}

time chia plots create -f ${CHIA_FARMKEY} -p ${CHIA_PUBKEY} --final_dir ${CHIA_PLOTS} --tmp_dir ${CHIA_TEMP} -n 4 -b 8192 --num_threads $(($(cat /proc/cpuinfo |grep ^processor|wc -l)*4))

""" > ${CHIA_HOME}/plotscript.sh
chmod +x ${CHIA_HOME}/plotscript.sh

echo """[Unit]
Description=Chia plot service
After=network-online.target local-fs.target time-sync.target remote-fs-pre.target 
Wants=network-online.target local-fs.target time-sync.target remote-fs-pre.target

[Service]
WorkingDirectory=${CHIA_HOME}
ExecStart=${CHIA_HOME}/plotscript.sh %i
Restart=always
RestartSec=30
""" > /etc/systemd/system/chia-plot@.service
systemctl daemon-reload
