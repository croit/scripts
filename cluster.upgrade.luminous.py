#!/usr/bin/python

from __helper import *
import subprocess

def executeSshCommand(host, cmd):
	return subprocess.call(['docker', 'exec', '-it', 'croit', 'ssh', '-o', 'BatchMode yes', '-o', 'StrictHostKeyChecking no', host, cmd])

def executeShellCommand(cmd):
	return subprocess.call(['docker', 'exec', '-it', 'croit', 'bash', '-c', cmd])


if not checkMonHealth() or not checkPgHealth():
	if raw_input('Health ERROR, are you sure to continue (y/n)? ') != 'y':
		sys.exit(1)

# prepare cluster
executeShellCommand('ceph osd set sortbitwise')
executeShellCommand('ceph osd set noout')

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

print executeShellCommand('ceph mon feature ls')

# MGR
for srv in all_hosts:
	print "upgrading MGR on " + srv + "... please wait!"
	executeSshCommand(srv, "systemctl restart ceph-mgr.target")

# OSD
for srv in osd_list:
	print "upgrading OSD on " + srv + "... please wait!"
	executeSshCommand(srv, "systemctl restart ceph-osd.target")

print executeShellCommand('ceph osd versions')

# MDS
for srv in mds_list:
	print "upgrading MDS on " + srv + "... please wait!"
	executeSshCommand(srv, "systemctl restart ceph-mds.target")

# RGW
for srv in rgw_list:
	print "upgrading RGW on " + srv + "... please wait!"
	executeSshCommand(srv, "systemctl restart radosgw.target")


executeShellCommand('ceph osd unset noout')

print "Cluster upgrade done"

