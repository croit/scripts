#!/usr/bin/python3

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

import os
import time
from __helper import *

verifyCephCommand()

mon_list = getMonList()

for mon in mon_list:
	while not checkMonHealth():
		print("waiting (15s) for mon health ...")
		time.sleep(15)

	# status is now healthy
	print("compacting leveldb from mon." + mon + "... please wait, this can take hours!")
	os.system("ceph tell mon." + mon + " compact")
	time.sleep(5)



