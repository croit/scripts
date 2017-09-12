#!/usr/bin/python3

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

# python constants are nonexisting, but here we go
API_HOST					= 'http://localhost:8080/api'
API_URL_CLI_STATUS  		= API_HOST + '/cli/status'
API_URL_CLI_SERVERS 		= API_HOST + '/cli/servers'
#API_URL_CLI_SERVICES 		= API_HOST + '/cli/services'
API_URL_LOGIN	 			= API_HOST + '/auth/login'
API_URL_LOGIN_TOKEN_INFO 	= API_HOST + '/auth/token-info'
API_URL_DISKS_ALL			= API_HOST + '/servers/%d/disks'
API_URL_DISKS				= API_HOST + '/servers/%d/disks/%d'
API_URL_DISK_WIPE			= API_HOST + '/servers/%d/disks/%d/wipe'
API_URL_CREATE_MON			= API_HOST + '/cluster/create/mons'
API_URL_SERVERS				= API_HOST + '/servers'
API_URL_SERVER_SERVICES_MON	= API_HOST + '/servers/%d/services/mon'
API_URL_TASK				= API_HOST + '/tasks/%d'

import json
import os
import re
import requests
import shutil
import subprocess
import sys
import time
from requests.auth import HTTPBasicAuth

# API token cache
api_auth_token = ''

def verifyCephCommand(require_version=None): # Regular Expression '\s((11|12).2.\d+)\s'
	if shutil.which('ceph') == None:
		print("Please make sure that Ceph is executable!")
		sys.exit(1)

	if require_version == None:
		# no version check
		return True
	else:
		output = subprocess.check_output(['ceph', 'version', '-f', 'json'])
		version = json.loads(output.decode('utf8'))
		if 'version' in version and re.search(require_version, version['version']) != None:
			return True
		else:
			print("Your Ceph version issn't working for that script.")
			sys.exit(1)



def adminLogin():
	global API_URL_LOGIN, api_auth_token
	payload = "grant_type=client_credentials"
	headers = { 'content-type': "application/x-www-form-urlencoded" }
	response = requests.post(API_URL_LOGIN, data=payload, auth=HTTPBasicAuth('admin', 'admin'), headers=headers).json()
	if 'access_token' in response and 'access_token' in response:
		api_auth_token = response['token_type'] + ' ' + response['access_token']
		writeTokenFile(api_auth_token)
		return api_auth_token
	else:
		username = input("Username: ")
		password = input("Password: ")
		response = requests.post(API_URL_LOGIN, data=payload, auth=HTTPBasicAuth(username, password), headers=headers).json()
		if 'access_token' in response and 'access_token' in response:
			api_auth_token = response['token_type'] + ' ' + response['access_token']
			writeTokenFile(api_auth_token)
			return api_auth_token
		else:
			return False

def checkLoginToken():
	global API_URL_CLI_STATUS, api_auth_token
	if api_auth_token == '':
		# try to load the token from file
		loadTokenFile()
	if api_auth_token == '':
		# no token therefore invalid
		return False
	else:
		# verify token
		r = requests.get(API_URL_LOGIN_TOKEN_INFO, headers={'Content-Type':'application/json', 'Authorization': api_auth_token})
		if r.status_code == 200:
			return True
		else:
			return False
	
def writeTokenFile(token):
	with open(".api_token", "w") as token_file:
		token_file.write(token.strip())
	return token_file.close()
	

def loadTokenFile():
	global api_auth_token
	if os.path.isfile(".api_token"):
		try:
			token_file = open(".api_token", "r")
		except(IOError, OSError, Failure) as e:
			return False
		else:
			try:
				ret = token_file.readline()
				api_auth_token = ret.strip()
				return api_auth_token
			finally:
				token_file.close()
	return False
	
def getRequestHeaders(auth=True):
	request_headers = {'Content-Type':'application/json'}
	if auth == True:
		request_headers['Authorization'] = loadTokenFile()
	return request_headers
	
def patchDisk(server_id, disk_id, data, wait=True):
	global API_URL_DISKS
	r = patchRequest(API_URL_DISKS % (server_id, disk_id), data)
	if r.status_code == 200:
		if wait:
			task = r.json()
			if 'id' in task and waitForTask(task['id']):
				return True
			else:
				print('patchDisk failed while waiting for the task to complete')
				return False
		else:
			return True

	elif r.status_code == 204:
		return True

	print('patchDisk failed with status_code %d' % r.status_code)
	return False

def createJournal(server_id, disk_id, count):
	return patchDisk(server_id, disk_id, {"role":"journal", "partitions": count})

def createMon(server_id, disk_id, ip=False):
	print('server #%d disk #%d createing MON' % (server_id, disk_id))
	if patchDisk(server_id, disk_id, {"role":"mon"}) and waitDiskState(server_id, disk_id, 'mon'):
		return createMonService(server_id, ip)
	else:
		return False

def createOsd(server_id, disk_id, journal_disk_id=None, wait=True):
	print('server #%d disk #%d createing OSD' % (server_id, disk_id))
	if journal_disk_id == None:
		return patchDisk(server_id, disk_id, {"role":"osd"}, wait)
	else:
		return patchDisk(server_id, disk_id, {"role":"osd", "journalDisk": journal_disk_id}, wait)

def deleteRequest(url, data={}, auth=True):
	return requests.delete(url, json=data, headers=getRequestHeaders(auth))
	
def patchRequest(url, data={}, auth=True):
	return requests.patch(url, json=data, headers=getRequestHeaders(auth))

def postRequest(url, data={}, auth=True):
	return requests.post(url, json=data, headers=getRequestHeaders(auth))

def getRequest(url, auth=True):
	return requests.get(url, headers=getRequestHeaders(auth))

def getServers():
	global API_URL_SERVERS
	r = getRequest(API_URL_SERVERS)
	if r.status_code == 200:
		return r.json()
	else:
		return False

def createMonService(server_id, ip=False):
	global API_URL_CREATE_MON, API_URL_SERVER_SERVICES_MON
	r = getRequest(API_URL_CREATE_MON)
	if r.status_code == 200:
		services = r.json()	
		if type(services) is list and len(services)>0:
			for service in services:
				if 'id' in service and 'ips' in service and len(service['ips'])>0 and service['id'] == server_id:
					if ip == False:
						task = postRequest(API_URL_SERVER_SERVICES_MON % server_id, {"ip": service['ips'][0]}).json()
					else:
						task = postRequest(API_URL_SERVER_SERVICES_MON % server_id, {"ip": ip}).json()

					if 'id' in task and waitForTask(task['id']):
						return True
					else:
						return False
	else:
		print('service returned errors - status %d' % r.status_code)
		return False


def wipeDisk(server_id, disk_id, serial, wait=True):
	global API_URL_DISK_WIPE
	print('server #%d wiping disk #%d' % (server_id, disk_id))
	deleteRequest(API_URL_DISK_WIPE % (server_id, disk_id), {"serial": serial})
	if wait:
		return waitDiskState(server_id, disk_id, 'unassigned')
	else:
		return True


def waitDiskState(server_id, disk_id, state, timeout=15):
	global API_URL_DISKS_ALL
	starttime = int(time.time())
	while True:
		disks = getRequest(API_URL_DISKS_ALL % server_id).json()
		if type(disks) is list and len(disks)>0:
			for disk in disks:
				if 'id' in disk and 'server' in disk and 'role' in disk and disk['id'] == disk_id and disk['server'] == server_id and disk['role'] == state:
					return True
		if int(time.time()) - starttime > timeout:
			print(disks)
			print('Waiting for the DISK timed out. Unable to get the status of disk #%d to reach %s!' % (disk_id, state))
			return False
		time.sleep(1)


def waitForTask(task_id):
	global API_URL_TASK
	errors = 0
	starttime = int(time.time())
	while True:
		time.sleep(1)
		task = getRequest(API_URL_TASK % task_id).json()
		if 'done' in task and 'id' in task and 'name' in task and task['done'] == True:
			return True
		elif 'done' in task and task['done'] == False:
			print('waiting for task #%d to complete' % task_id)
		elif int(time.time()) - starttime > 30:
			# Task timeout to prevent it from hanging forever
			print('Task %d (%s) timeout, something seems to block the task from completing' % (task_id, task['name']))
			return False
		else:
			errors += 1
			if errors >= 5:
				print('Task %d cannot be found' % task_id)
				return False


def checkMonHealth():
	global API_URL_CLI_STATUS
	response_json = __CallCliApi(API_URL_CLI_STATUS)
	
	count_max = 0
	count_cur = 0
	if 'cephStatus' in response_json and response_json['cephStatus'] is dict and 'monmap' in response_json['cephStatus'] and 'mons' in response_json['cephStatus']['monmap']:
		count_max = len(response_json['cephStatus']['monmap']['mons'])
	if 'cephStatus' in response_json and response_json['cephStatus'] is dict and 'quorum' in response_json['cephStatus']:
		count_cur = len(response_json['cephStatus']['quorum'])

	if count_cur != count_max:
		return False
	else:
		return True


def checkPgHealth():
	global API_URL_CLI_STATUS
	response_json = __CallCliApi(API_URL_CLI_STATUS)
	
	if 'cephStatus' in response_json and response_json['cephStatus'] is dict and 'pgmap' in response_json['cephStatus'] and 'pgs_by_state' in response_json['cephStatus']['pgmap']:
		pgstates = response_json['cephStatus']['pgmap']['pgs_by_state']
		for element in pgstates:
			if 'state_name' in element and element['state_name'] != 'active+clean':
				return False;
	return True;


# service can be 'mon', 'osd', 'mds', 'nfs', 'rgw'
def getServersWithService(service='mon'):
	global API_URL_CLI_SERVERS
	response_json = __CallCliApi(API_URL_CLI_SERVERS)
	ip_list = []
	for element in response_json:
		if service == 'osd':
			if 'osds' in element and element['osds'] > 0 and 'ip' in element:
				ip_list.append(element['ip'])
		else:
			if service == 'nfs': service = 'cephfs_nfs_gateway'
			if service == 'rgw': service = 'radosgw'
			if 'services' in element and service in element['services'] and element['services'][service] > 0:
				ip_list.append(element['ip'])
	return ip_list


def getMonList():
	global API_URL_CLI_STATUS
	response_json = __CallCliApi(API_URL_CLI_STATUS)
	mon_list = []
	if 'cephStatus' in response_json and 'monmap' in response_json['cephStatus'] and 'mons' in response_json['cephStatus']['monmap']:
		response_mon = response_json['cephStatus']['monmap']['mons']
		for element in response_mon:
			if 'name' in element:
				mon_list.append(element['name'])
		return mon_list
	else:
		print("mons not found in status response from ", API_URL_CLI_STATUS)
		return False


def getAllServers():
	global API_URL_CLI_SERVERS
	response_json = __CallCliApi(API_URL_CLI_SERVERS)
	ip_list = []
	for element in response_json:
		if 'ip' in element:
			ip_list.append(element['ip'])
	return ip_list


def __CallCliApi(url):
	r = requests.get(url)
	return r.json()
	

