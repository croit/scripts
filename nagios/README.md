# Requirements

Requires python3 and pip (on Debian/Ubuntu: `apt install python3-pip`).

Run `pip3 install -r requirements.txt` to install python dependencies (might be just `pip` on other distributions)

# Running

See `./monitoring.nagios.py --help`

The script runs a specified health check on Ceph, if no health check is provided a check on the overall Ceph health is executed.

The simplest way to run this is like this:

`./monitoring.nagios.py --host localhost --user admin --pass admin`

This will map Ceph health warnings and errors to WARNING and CRITICAL service states in nagios.
You can optionally pass a specific Ceph health check as parameter to monitor on a finer granularity.
For example, it might be useful to mute the general Ceph health warning during ongoing recovery but still get alerted if an OSD fails.

## Recommended checks to monitor

Ceph offers [a lot of health checks](http://docs.ceph.com/docs/master/rados/operations/health-checks/), we've found the following to be useful with Nagios/Icinga:

```
MON_DOWN
MON_CLOCK_SKEW
OSD_DOWN
OSD_NEARFULL
OSD_FULL
OSDMAP_FLAGS
POOL_FULL
POOL_NEAR_FULL
PG_AVAILABILITY
PG_DEGRADED
PG_DAMAGED
OBJECT_UNFOUND
SLOW_OP
MDS_SLOW_METADATA_IO
FS_DEGRADED
MDS_INSUFFICIENT_STANDBY
```

