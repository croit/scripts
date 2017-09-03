#!/usr/bin/python2.7

from __helper import *
import json
import re
import subprocess
import sys
import time

def executeSshCommand(host, cmd):
	# return subprocess.call(['docker', 'exec', '-it', 'croit', 'ssh', '-o', 'BatchMode yes', '-o', 'StrictHostKeyChecking no', host, cmd])
	return subprocess.call(['ssh', '-o', 'BatchMode yes', '-o', 'StrictHostKeyChecking no', host, cmd])

def executeShellCommand(cmd):
	# return subprocess.check_output(['docker', 'exec', '-it', 'croit', 'bash', '-c', cmd])
	return subprocess.check_output(['bash', '-c', cmd])

def waitForClusterHealth():
	while not checkMonHealth() or not checkPgHealth():
		print "waiting (15s) for MON and PG health ..."
		time.sleep(15)

# Verify Ceph Version
try:
	version = json.loads(executeShellCommand('ceph version -f json || exit 0'))
except ValueError:
	print "Please make sure that ceph is executable!"
	sys.exit(1)
else:
	if 'version' in version and re.search('\s((11|12).2.\d+)\s', version['version']) != None:
		print "Your Ceph version is tested and we can start the upgrade process ..."	
	else:
		print "Your Ceph version issn't working for that script, please make sure that ceph is executable and the latest kraken release."
		sys.exit(1)

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
	print "preparing server " + srv + "... please wait!"
	# update preferences
	executeSshCommand(srv, "sed -i -- 's/debian-kraken/debian-luminous/g' /etc/apt/sources.list")
	executeSshCommand(srv, "apt-get -y update && apt-get -y dist-upgrade")

# MON
for srv in mon_list:
	print "upgrading MON on " + srv + "... please wait!"
	# upgrade MON
	executeSshCommand(srv, "systemctl restart ceph-mon.target")
	if force_execute == False:
		waitForClusterHealth()

print '------ STATUS -- ceph mon feature ls --------------------------------------------'
print executeShellCommand('ceph mon feature ls')
print '---------------------------------------------------------------------------------'

# MGR
for srv in all_hosts:
	print "upgrading MGR on " + srv + "... please wait!"
	executeSshCommand(srv, "systemctl restart ceph-mgr.target")

# OSD
for srv in osd_list:
	print "upgrading OSD on " + srv + "... please wait!"
	executeSshCommand(srv, "systemctl restart ceph-osd.target")
	if force_execute == False:
		waitForClusterHealth()

print '------ STATUS -- ceph osd versions ----------------------------------------------'
print executeShellCommand('ceph osd versions')
print '---------------------------------------------------------------------------------'

# MDS
for srv in mds_list:
	print "upgrading MDS on " + srv + "... please wait!"
	executeSshCommand(srv, "systemctl restart ceph-mds.target")
	time.sleep(1)

# RGW
for srv in rgw_list:
	print "upgrading RGW on " + srv + "... please wait!"
	executeSshCommand(srv, "systemctl restart radosgw.service")


executeShellCommand('ceph osd require-osd-release luminous')
executeShellCommand('ceph osd unset noout')

print "Cluster upgrade done"

