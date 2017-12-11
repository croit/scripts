#!/usr/bin/python3

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

import logging
import nagiosplugin
import requests
import sys
import traceback

from argparse import ArgumentParser
from requests.auth import HTTPBasicAuth
from nagiosplugin.state import Ok, Warn, Critical

_log = logging.getLogger('nagiosplugin')

VERSION = 0.1

class croit(nagiosplugin.Resource):
  args = {}
  API_AUTH_TOKEN = ''
  ceph_health = ''

  def __init__(self, args):
      self.args = args

  def api_get_data(self, url):
    request_headers = {'Content-Type':'application/json', 'Authorization':self.API_AUTH_TOKEN}
    _log.debug(' ==> REQUEST HEADERS: %s' % request_headers)
    return requests.get(url, headers=request_headers)

  def api_login(self):
    URL = '%s://%s:%s/api/auth/login' % (self.args.protocol, self.args.host, self.args.port)
    _log.info('POST %-50s - trying to login' % URL)
    response = requests.post(URL, data='grant_type=client_credentials', auth=HTTPBasicAuth(self.args.username, self.args.password), headers={ 'content-type': 'application/x-www-form-urlencoded' }).json()
    if 'access_token' in response:
      self.API_AUTH_TOKEN = response['token_type'] + ' ' + response['access_token']
      _log.debug(' ==> ACCESS_TOKEN = "%s"' % self.API_AUTH_TOKEN)
      return True
    raise RuntimeError('API login failed! unable to receive a login token from %s' % URL)

  def api_status_backend(self):
    URL = '%s://%s:%s/api/status' % (self.args.protocol, self.args.host, self.args.port)
    _log.info('GET  %-50s - get the backend status' % URL)
    response = self.api_get_data(URL)
    data = response.json()
    if response.status_code == 200 and 'status' in data and data['status'] == 'UP':
      _log.debug(' ==> got True')
      return True
    _log.debug(' ==> got False')
    return False

  def api_status_cluster(self):
    URL = '%s://%s:%s/api/cluster/status' % (self.args.protocol, self.args.host, self.args.port)
    _log.info('GET  %-50s - get the cluster status' % URL)
    response = self.api_get_data(URL)
    self.ceph_health = data = response.json()
    if response.status_code == 200:
      try:
        if data['cephLastUpdated'] >= self.args.timeout*1000:
          _log.debug(' ==> Ceph status timeout, %d ms old' % data['cephLastUpdate'])
          return False
        elif data['cephStatus']['health']['status'] == 'HEALTH_OK':
          _log.debug(' ==> reported status HEALTH_OK')
          return True
      except:
        _log.debug(' ==> got unusual json format from API')
      _log.debug(' ==> reported status is NOT OK')
      return False

  def ceph_mon_status(self):
    if self.ceph_health is not dict:
      return False
    try:
      status = self.ceph_health['cephStatus']
      if len(status['quorum_names']) < 1:
        _log.debug(' ==> no mon in quorum_names')
        return False
      for mon in status['monmap']['mons']:
        if mon.name not in status['quorum_names']:
          _log.debug(' ==> mon "%s" is not in quorum_names' % mon.name)
          return False
      return True
    except:
      _log.debug(' ==> got unusual json format from API')
      return False

  def probe(self):
    return [nagiosplugin.Metric('croit', True, context='croit'),
            nagiosplugin.Metric('croit_login', self.api_login(), context='login'),
            nagiosplugin.Metric('croit_backend', self.api_status_backend(), context='backend'),
            nagiosplugin.Metric('ceph_cluster', self.api_status_cluster(), context='ceph_cluster'),
            nagiosplugin.Metric('ceph_mon', self.ceph_mon_status(), context='ceph_mon'),
            ]

class BooleanContext(nagiosplugin.Context):
    """This context only cares about boolean values.
    You can specify using the ``critical``-parameter whether
    a False result should cause a warning or a critical error.
    """

    def __init__(self, name, critical=True,
                 fmt_metric='{name} is {value}',
                 result_cls=nagiosplugin.result.Result):
        self.critical = critical
        super().__init__(name, fmt_metric, result_cls)

    def evaluate(self, metric, resource):
        if not metric.value and self.critical:
            return self.result_cls(Critical, "NOT OK", metric)
        elif not metric.value and not self.critical:
            return self.result_cls(Warn, "NOT OK", metric)
        else:
            return self.result_cls(Ok, "OK", metric)

def main():
  arg_parser = ArgumentParser(description='check_croit_cluster (Version: %s)' % (VERSION))
  arg_parser.add_argument('--version', action='version', version='%s' % (VERSION))
  arg_parser.add_argument('-v', '--verbose', default=0, action='count', help='increase output verbosity (use up to 3 times)')
  arg_parser.add_argument('--timeout', default=20, type=int, help='Ceph status timeout (default 20)')
  arg_parser.add_argument('--https', default=False, action='store_true', help='use HTTPs instead of HTTP')
  arg_parser.add_argument('--host', default='localhost', help='connect to host')
  arg_parser.add_argument('--port', default=8080, type=int, help='connect to port')
  arg_parser.add_argument('--user', default='admin', help='username to authenticate', dest='username')
  arg_parser.add_argument('--pass', default='admin', help='password to authenticate', dest='password')
  args = arg_parser.parse_args(sys.argv[1:])
  if args.https == True:
    args.protocol = 'https'
  else:
    args.protocol = 'http'

  # API login
  check = nagiosplugin.Check(
    croit(args),
    BooleanContext('croit'),
    BooleanContext('login'),
    BooleanContext('backend'),
    BooleanContext('ceph_cluster'),
    BooleanContext('ceph_mon'),
    nagiosplugin.Summary()
  )
  check.main(verbose=args.verbose)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except:
        print('UNKNOWN - Error: %s' % (str(sys.exc_info()[1])))
        traceback.print_tb(sys.exc_info()[2])
        sys.exit(3)

