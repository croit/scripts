#!/usr/bin/python

import os
import time
from __helper import *

host_list = getAllServers()

for srv in host_list:
	while not checkMonHealth():
		print "waiting (15s) for mon health ..."
		time.sleep(15)

	# status is now healthy
	print "restarting host with ip " + srv + "... please wait!"
	os.system("""ssh -o "BatchMode yes" -o "StrictHostKeyChecking no" """ + srv + """ reboot""")
	time.sleep(120)



