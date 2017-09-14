#!/bin/bash

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

# adjust backup dir as needed
BACKUP_DIR="$(ls -v1d /backups/croit/* |tail -n 1)" # gets the latest backup directory
CROIT_RELEASE="$(cat ${BACKUP_DIR}/release)"
[[ -z ${CROIT_RELEASE} ]] && CROIT_RELEASE="croit:latest"

# verify no croit container exists
CONTAINERS=$(docker container list -a --format '{{.Names}}' --no-trunc | egrep "^(croit|croit-data)$")
if [[ ! -z ${CONTAINERS} ]]
then
	# container exists
	echo "Please make sure that no docker container named 'croit' and 'croit-data' exists."
	exit 1
fi
# Verify BACKUP_DIR exists
if [[ ! -d "${BACKUP_DIR}" ]] || [[ ! -f "${BACKUP_DIR}/config.tgz" ]] || [[ ! -f "${BACKUP_DIR}/db.tgz" ]]
then
	# Backup directory contains no data
	echo "Your backup directory does not contain data. Please make sure to set the BACKUP_DIR variable."
	exit 1
fi

echo "Restoring Backup from ${BACKUP_DIR}"
echo "with container release version ${CROIT_RELEASE}"

# Create a docker data container
docker pull ${CROIT_RELEASE}
docker create --name croit-data ${CROIT_RELEASE}

# Database restore
MYSQL_DATA=$(docker inspect --format='{{range .Mounts}}{{if (eq .Destination "/var/lib/mysql")}}{{.Source}}{{end}}{{end}}' croit-data)
echo "Restoring MySQL/MariaDB"
echo "Source      = ${BACKUP_DIR}/db.tgz"
echo "Destination = ${MYSQL_DATA}"
[[ -z ${MYSQL_DATA}  ]] && {echo "No MySQL/MariaDB data directory found"} || tar xf "${BACKUP_DIR}/db.tgz" -C "${MYSQL_DATA}"

# Configuration restore
CONFIG_DATA=$(docker inspect --format='{{range .Mounts}}{{if (eq .Destination "/config")}}{{.Source}}{{end}}{{end}}' croit-data)
echo "Restoring croit config"
echo "Source      = ${BACKUP_DIR}/config.tgz"
echo "Destination = ${CONFIG_DATA}"
[[ -z ${CONFIG_DATA} ]] && {echo "No config data directory found"} || tar xf "${BACKUP_DIR}/config.tgz" -C "${CONFIG_DATA}"

echo "backup restored to data container 'croit-data', starting container croit now"
docker run --net=host --restart=always --volumes-from croit-data --name croit -d ${CROIT_RELEASE}

