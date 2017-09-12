#!/usr/bin/python3

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

import os
import time
from __helper import *

verifyCephCommand()

host_list = getAllServers()

for srv in host_list:
	while not checkMonHealth() or not checkPgHealth():
		print("waiting (15s) for MON and PG health ...")
		time.sleep(15)

	# status is now healthy
	print("restarting host with ip " + srv + "... please wait!")
	os.system("""ssh -o "BatchMode yes" -o "StrictHostKeyChecking no" """ + srv + """ reboot""")
	time.sleep(120)



