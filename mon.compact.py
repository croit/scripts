#!/usr/bin/python

import os
from __helper import *

mon_list = getMonList()

for mon in mon_list:
	while not checkMonHealth():
		print "waiting (15s) for mon health ..."
		sleep(15)

	# status is now healthy
	print "compacting leveldb from mon." + mon + "... please wait, this can take hours!"
	os.system("ceph tell mon." + mon + " compact")
	sleep(5)



