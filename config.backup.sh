#!/bin/bash

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

# adjust backup dir as needed
BACKUP_DIR=/backups/croit/$(date +%s)

MYSQL_DATA=$(docker inspect --format='{{range .Mounts}}{{if (eq .Destination "/var/lib/mysql")}}{{.Source}}{{end}}{{end}}' croit)
CONFIG_DATA=$(docker inspect --format='{{range .Mounts}}{{if (eq .Destination "/config")}}{{.Source}}{{end}}{{end}}' croit)

docker stop croit
mkdir -p "${BACKUP_DIR}/config"
mkdir -p "${BACKUP_DIR}/db"
cp -r "${MYSQL_DATA}" "${BACKUP_DIR}/db"
cp -r "${CONFIG_DATA}" "${BACKUP_DIR}/config"
docker start croit


