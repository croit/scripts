#!/usr/bin/python3

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

from __helper import *
import json
import re
import subprocess
import sys
import time

print('This script will migrate your running cluster from Ceph Kraken (11.2) to Luminous (12.2)!')
print('If you have any data on your servers, please make sure to backup them before executing this script!')
if input('Do you want to upgrade the cluster (yes/no)? ') != 'yes':
	print('exiting')
	sys.exit(1)

def executeSshCommand(host, cmd):
	# return subprocess.call(['docker', 'exec', '-it', 'croit', 'ssh', '-o', 'BatchMode yes', '-o', 'StrictHostKeyChecking no', host, cmd])
	return subprocess.call(['ssh', '-o', 'BatchMode yes', '-o', 'StrictHostKeyChecking no', host, cmd])

def executeShellCommand(cmd):
	# return subprocess.check_output(['docker', 'exec', '-it', 'croit', 'bash', '-c', cmd])
	return subprocess.check_output(['bash', '-c', cmd])

def waitForClusterHealth():
	print("waiting for 15s for the cluster health...")
	time.sleep(15)
	while not checkMonHealth() or not checkPgHealth():
		print("cluster not yet healthy, checking again in 10 seconds ...")
		time.sleep(10)

# Verify Ceph Version
verifyCephCommand('\s((11|12).2.\d+)\s')

# Check if status is healthy before we start, allow forced execution for clusters with defects
force_execute = False
if not checkMonHealth() or not checkPgHealth():
	if raw_input('Health ERROR, are you sure to continue (y/n)? ') != 'y':
		sys.exit(1)
	else:
		force_execute = True

# prepare cluster
executeShellCommand('ceph osd set sortbitwise')
executeShellCommand('ceph osd set noout')
executeShellCommand("sed -i -- 's/debian-kraken/debian-luminous/g' /etc/apt/sources.list")
executeShellCommand("apt-get -y update && apt-get -y dist-upgrade")

mon_list = getServersWithService('mon')
osd_list = getServersWithService('osd')
mds_list = getServersWithService('mds')
rgw_list = getServersWithService('rgw')
all_hosts = list(set(mon_list) | set(osd_list) | set(mds_list) | set(rgw_list))

# ALL Hosts
for srv in all_hosts:
	print("preparing server " + srv + "... please wait!")
	# update preferences
	executeSshCommand(srv, "sed -i -- 's/debian-kraken/debian-luminous/g' /etc/apt/sources.list")
	executeSshCommand(srv, "apt-get -y update && apt-get -y dist-upgrade")

# MON
for srv in mon_list:
	print("upgrading MON on " + srv + "... please wait!")
	# upgrade MON
	executeSshCommand(srv, "systemctl restart ceph-mon.target")
	if force_execute == False:
		waitForClusterHealth()

print('------ STATUS -- ceph mon feature ls --------------------------------------------')
print(executeShellCommand('ceph mon feature ls'))
print('---------------------------------------------------------------------------------')

# MGR
for srv in all_hosts:
	print("upgrading MGR on " + srv + "... please wait!")
	executeSshCommand(srv, "systemctl restart ceph-mgr.target")

# OSD
for srv in osd_list:
	print("upgrading OSD on " + srv + "... please wait!")
	executeSshCommand(srv, "systemctl restart ceph-osd.target")
	if force_execute == False:
		waitForClusterHealth()

print('------ STATUS -- ceph osd versions ----------------------------------------------')
print(executeShellCommand('ceph osd versions'))
print('---------------------------------------------------------------------------------')

# MDS
for srv in mds_list:
	print("upgrading MDS on " + srv + "... please wait!")
	executeSshCommand(srv, "systemctl restart ceph-mds.target")
	time.sleep(10)

# RGW
for srv in rgw_list:
	print("upgrading RGW on " + srv + "... please wait!")
	executeSshCommand(srv, "systemctl restart ceph-radosgw.target")

# This command can only run if every OSD is upgraded, therefore it will fail on clusters with defects
try:
	executeShellCommand('ceph osd require-osd-release luminous')
except:
	print("-------------------------------------------------------------------------------------")
	print("You have at least one OSD that wasn't upgraded to luminous.")
	print("Please consider rerunning this script or rebooting all hosts to complete the upgrade.")
	print("When done, please run:")
	print("		docker exec -it croit ceph osd require-osd-release luminous")
	print("Thank you!");
	print("-------------------------------------------------------------------------------------")

executeShellCommand('ceph osd unset noout')

postRequest(API_HOST + '/cli/upgrade/luminous/update-image', auth=False)

print("\n\n")
print('-------------------------------------')
print('      cluster upgrade finished       ')
print('-------------------------------------')
print("\n\n")


