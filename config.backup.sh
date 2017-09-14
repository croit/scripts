#!/bin/bash

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

# verify that the croit container exists
CONTAINER=$(docker container list -a --format '{{.Names}}' --no-trunc | egrep "^croit$")
if [[ -z ${CONTAINER} ]]
then
    # container does not exists
    echo "Please make sure that a docker container named 'croit' exists."
    exit 1
fi

# adjust backup dir as needed
BACKUP_DIR="/backups/croit/$(date +%s)"

echo "Starting backup to ${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}/"

# we need to gather the directorys while the docker container runs
MYSQL_DATA=$(docker inspect --format='{{range .Mounts}}{{if (eq .Destination "/var/lib/mysql")}}{{.Source}}{{end}}{{end}}' croit)
CONFIG_DATA=$(docker inspect --format='{{range .Mounts}}{{if (eq .Destination "/config")}}{{.Source}}{{end}}{{end}}' croit)
RELEASE=$(docker inspect --format='{{.Config.Image}}' croit)

# Shutdown container befor creating backup
docker stop croit

# Database backup
echo "create database backup from ${MYSQL_DATA}"
[[ -z ${MYSQL_DATA} ]] && {echo "No MySQL/MariaDB data directory found"} || tar czf "${BACKUP_DIR}/db.tgz" -C "${MYSQL_DATA}" .

# configuration backup
echo "create config backup from ${CONFIG_DATA}"
[[ -z ${CONFIG_DATA} ]] && {echo "No croit config data directory found"} || tar czf "${BACKUP_DIR}/config.tgz" -C "${CONFIG_DATA}" .

# save the container release tag
echo "backup based on a container with tags ${RELEASE}"
[[ -z ${RELEASE} ]] && {echo "Unable to detect the container release tags"} || echo ${RELEASE} > "${BACKUP_DIR}/release"

# Start the container again
docker start croit


