#!/usr/bin/python

import os
import time
from __helper import *

host_list = getAllServers()

for srv in host_list:
	while not checkMonHealth() or not checkPgHealth():
		print "waiting (15s) for MON and PG health ..."
		time.sleep(15)

	# status is now healthy
	print "restarting host with ip " + srv + "... please wait!"
	os.system("""ssh -o "BatchMode yes" -o "StrictHostKeyChecking no" """ + srv + """ reboot""")
	time.sleep(120)



