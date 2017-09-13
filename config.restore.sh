#!/bin/bash

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

# adjust backup dir as needed
BACKUP_DIR="$(ls -v1d /backups/croit/* |tail -n 1)" # gets the latest backup directory
CROIT_RELEASE="croit/croit:latest"

# verify no croit container exists
CONTAINERS=$(docker container list -a --format '{{.Names}}' --no-trunc | egrep "^(croit|croit-data)$")
if [[ ! -z ${CONTAINERS} ]]
then
	# container exists
	echo "Please make sure that no docker container named 'croit' and 'croit-data' exists."
	exit 1
fi
# Verify BACKUP_DIR exists
if [[ ! -d "${BACKUP_DIR}" ]] || [[ ! -d "${BACKUP_DIR}/config" ]] || [[ ! -d "${BACKUP_DIR}/db" ]]
then
	# Backup directory contains no data
	echo "Your backup directory does not contain data. Please make sure to set the BACKUP_DIR variable."
	exit 1
fi

# Create a docker data container
docker pull ${CROIT_RELEASE}
docker create --name croit-data ${CROIT_RELEASE}

MYSQL_DATA=$(docker inspect --format='{{range .Mounts}}{{if (eq .Destination "/var/lib/mysql")}}{{.Source}}{{end}}{{end}}' croit-data)
CONFIG_DATA=$(docker inspect --format='{{range .Mounts}}{{if (eq .Destination "/config")}}{{.Source}}{{end}}{{end}}' croit-data)

[[ -z ${MYSQL_DATA}  ]] && {echo "No MySQL data directory found"} || rsync -avp --delete "${BACKUP_DIR}/db" "${MYSQL_DATA}"
[[ -z ${CONFIG_DATA} ]] && {echo "No config data directory found"} || rsync -avp --delete "${BACKUP_DIR}/config" "${CONFIG_DATA}"

echo "backup restored to data container 'croit-data', starting container croit now"
docker run --net=host --restart=always --volumes-from croit-data --name croit -d ${CROIT_RELEASE}

