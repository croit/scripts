#!/usr/bin/python

# python constants are nonexisting, but here we go
API_URL_STATUS  	= 'http://localhost:8080/api/cli/status'
API_URL_SERVERS 	= 'http://localhost:8080/api/cli/servers'
API_URL_SERVICES 	= 'http://localhost:8080/api/cli/services'

import json
import requests

def checkMonHealth():
	global API_URL_STATUS
	response_json = __callApi(API_URL_STATUS)
	
	count_max = 0
	count_cur = 0
	if 'cephStatus' in response_json and 'monmap' in response_json['cephStatus'] and 'mons' in response_json['cephStatus']['monmap']:
		count_max = len(response_json['cephStatus']['monmap']['mons'])
	if 'cephStatus' in response_json and 'quorum' in response_json['cephStatus']:
		count_cur = len(response_json['cephStatus']['quorum'])

	if count_cur != count_max:
		return False
	else:
		return True


def checkPgHealth():
	global API_URL_STATUS
	response_json = __callApi(API_URL_STATUS)
	
	if 'cephStatus' in response_json and 'pgmap' in response_json['cephStatus'] and 'pgs_by_state' in response_json['cephStatus']['pgmap']:
		pgstates = response_json['cephStatus']['pgmap']['pgs_by_state']
		for element in pgstates:
			if 'state_name' in element and element['state_name'] != 'active+clean':
				return False;
	return True;


# service can be 'mon', 'osd', 'mds', 'nfs', 'rgw'
def getServersWithService(service='mon'):
	global API_URL_SERVERS
	response_json = __callApi(API_URL_SERVERS)
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
	global API_URL_STATUS
	response_json = __callApi(API_URL_STATUS)
	mon_list = []
	if 'cephStatus' in response_json and 'monmap' in response_json['cephStatus'] and 'mons' in response_json['cephStatus']['monmap']:
		response_mon = response_json['cephStatus']['monmap']['mons']
		for element in response_mon:
			if 'name' in element:
				mon_list.append(element['name'])
		return mon_list
	else:
		print "mons not found in status response from " + API_URL_STATUS
		return False


def getAllServers():
	global API_URL_SERVERS
	response_json = __callApi(API_URL_SERVERS)
	ip_list = []
	for element in response_json:
		if 'ip' in element:
			ip_list.append(element['ip'])
	return ip_list


def __callApi(url):
	r = requests.get(url)
	return r.json()
	

