#!/usr/bin/python3

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

# SETTINGS #
MAIN_INTERFACE={"interfaceName":"ens19","ip":"10.0.0.2"}
PXE_NETWORK={"ip":"10.0.0.0","netmask":"24","gateway":"","poolStart":"10.0.0.101","poolEnd":"10.0.0.199","type":"other","description":""}
MON_DISK='/dev/sda'
MON_MAX_COUNT=5
OSD_DISKS=['/dev/vda','/dev/vdb','/dev/vdc','/dev/vdd']
JOURNAL_DISK='/dev/sdb'
JOURNAL_COUNT=len(OSD_DISKS)
API_HOST='http://localhost:8080/api'
############


import requests
import sys
import time
from __helper import *

print('This script will install a clean and fresh cluster and wipe all data in the process!')
print('If you have any data on your servers, please make sure to backup them before executing this script!')
if input('Do you want to install the cluster (yes/no)? ') != 'yes':
	print('breaking up')
	sys.exit(1)

if not checkLoginToken():
	if not adminLogin():
		print("Admin login failed, no auth token available!")
		sys.exit(1)

# Start the basic configuration of the Cluster
print('STEP 1: installing the cluster')
status = getRequest(API_HOST + '/status').json()
if 'doSetup' in status and status['doSetup'] == True:
	postRequest(API_HOST + '/setup/main-ip', MAIN_INTERFACE)
	postRequest(API_HOST + '/networks', PXE_NETWORK)
	print("-----------------------------------")
	print("-- please start your servers now --")
	print("-----------------------------------")

	# WAIT FOR SERVERS
	servers = getServers()
	while not (type(servers) is list and len(servers)>0 and 'id' in servers[0]):
		servers = getServers()
		time.sleep(2)


	# CREATE THE MON
	mon_ready = False
	print('found a server, waiting for harddisk detection')
	while not mon_ready:
		disks = getRequest(API_HOST + '/servers/%d/disks' % servers[0]['id']).json()
		if type(disks) is list and len(disks)>0:
			for disk in disks:
				if 'id' in disk and 'path' in disk and disk['path'] == MON_DISK:
					if 'role' in disk and disk['role'] == 'mon':
						mon_ready = True
						break
					elif 'role' in disk and disk['role'] == 'unassigned':
						print('server and disk was found and prepared, installing MON')
						patchDisk(servers[0]['id'], disk['id'], {"role":"mon"})
						if waitDiskState(servers[0]['id'], disk['id'], 'mon'):
							print('disk is now set to MON')
					elif 'role' in disk and disk['role'] not in ['unassigned', 'deleting', 'mon']:
						print('disk state = %s' % disk['role'])
						wipeDisk(servers[0]['id'], disk['id'], disk['serial'])
						if waitDiskState(servers[0]['id'], disk['id'], 'unassigned'):
							print('disk is now clean')

	# create the cluster
	print('creating the cluster environment,...')
	task = postRequest(API_HOST + '/cluster/create', {"mons":[{"server":servers[0]['id'],"ip":servers[0]['ip']}]}).json()
	if 'id' in task and waitForTask(task['id']):
		print("--------------------------------------")
		print("-- a basic cluster is now installed --")
		print("--------------------------------------")
	else:
		print(task)
		print("cluster might be installed, but backend did not provide a working task, please check")
		sys.exit(1)

# Cluster is installed, do additional configuration

# OSD PREPARATION
print('STEP 2: installing OSD services')
changeList = []
servers = getServers()
for server in servers:
	disks = getRequest(API_HOST + '/servers/%d/disks' % server['id']).json()
	if type(disks) is list and len(disks)>0:
		# to speed up this script, we do execute a lot of wipe command async
		for disk in disks:
			if 'id' in disk and 'role' in disk and disk['role'] == 'other' and 'path' in disk and disk['path'] not in [JOURNAL_DISK] + [MON_DISK]:
				wipeDisk(server['id'], disk['id'], disk['serial'], False)
				changeList.append({"server_id": server['id'], "id": disk['id']})

# wait until all disks are done
for lastDisk in changeList:
	waitDiskState(lastDisk['server_id'], lastDisk['id'], 'unassigned', 30)

changeList = []
for server in servers:
	journal_disk_id = None
	disks = getRequest(API_HOST + '/servers/%d/disks' % server['id']).json()
	if type(disks) is list and len(disks)>0:
		# prepare the journal disks
		for disk in disks:
			if 'id' in disk and 'path' in disk and disk['path'] == JOURNAL_DISK:
				journal_disk_id = disk['id']
				print('server #%d disk #%d (%s) will be a journal' % (server['id'], disk['id'], disk['path']))
				if 'role' in disk and disk['role'] not in ['unassigned', 'journal']:
					wipeDisk(server['id'], disk['id'], disk['serial'])
				if disk['role'] == 'unassigned':
					createJournal(server['id'], disk['id'], JOURNAL_COUNT)

		# install the disk as an OSD
		for disk in disks:
			if 'id' in disk and 'path' in disk and disk['path'] in OSD_DISKS:
				if 'role' in disk and disk['role'] == 'osd':
					print('server #%d disk %d (%s) is already used as an OSD' % (server['id'], disk['id'], disk['path']))
				else:
					if disk['role'] != 'unassigned':
						wipeDisk(server['id'], disk['id'], disk['serial'])
					createOsd(server['id'], disk['id'], journal_disk_id, False)
					changeList.append({"server_id": server['id'], "id": disk['id']})

# wait until all disks are done
for lastDisk in changeList:
	waitDiskState(lastDisk['server_id'], lastDisk['id'], 'osd', 600)

		
# INSTALL ADDITIONAL MONs
print('STEP 3: installing MON services')
servers = getServers()
for server in servers:
	disks = getRequest(API_HOST + '/servers/%d/disks' % server['id']).json()
	if type(disks) is list and len(disks)>0:
		for disk in disks:
			mon_list = getServersWithService('mon')
			if mon_list.count >= MON_MAX_COUNT:
				print('maximum count (%d/%d) of MON services reached' % (mon_list.count, MON_MAX_COUNT))
			else:
				if 'id' in disk and 'path' in disk and disk['path'] == MON_DISK:
					if 'role' in disk and disk['role'] == 'mon':
						print('server #%d disk #%d (%s) is already used for MON' % (server['id'], disk['id'], disk['path']))
						createMonService(server['id'])
					else:
						if disk['role'] != 'unassigned':
							wipeDisk(server['id'], disk['id'], disk['serial'])
						createMon(server['id'], disk['id'])


# TODO: CRUSH MAP
# TODO: install additional services (rgw, nfs, ...)
