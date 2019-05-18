#!/usr/bin/env python3

# Copyright (C) <2017> <martin.verges@croit.io>
#
# This software may be modified and distributed under the terms
# of the MIT license.  See the LICENSE file for details.

import logging
import requests
import re
import sys
import traceback
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from argparse import ArgumentParser
from requests.auth import HTTPBasicAuth

_log = logging.getLogger('monitoring.nagios')

VERSION = 0.3

class croit:
  args = {}
  api_auth_token = ''
  ceph_health = ''

  def __init__(self, args):
      self.args = args

  def get_data(self, url):
    request_headers = {'Content-Type':'application/json', 'Authorization':self.api_auth_token}
    return requests.get(url, headers=request_headers, verify=self.args.check_cert, timeout=15)

  def login(self):
    URL = '%s://%s:%d/api/auth/login' % (self.args.protocol, self.args.host, self.args.port)
    _log.info('POST %-50s - trying to login' % URL)
    response = requests.post(URL,
                             data='grant_type=client_credentials',
                             auth=HTTPBasicAuth(self.args.username, self.args.password),
                             headers={ 'content-type': 'application/x-www-form-urlencoded' },
                             verify=self.args.check_cert,
                             timeout=15
                            ).json()
    if 'access_token' in response:
      self.api_auth_token = response['token_type'] + ' ' + response['access_token']
      return True
    raise RuntimeError('API login failed, unable to retrieve a login token from %s' % URL)

  def status_summary(self):
    return self.get_nagios_output('%s://%s:%d/api/cluster/status/nagios' % (self.args.protocol, self.args.host, self.args.port))

  def status(self, check):
    return self.get_nagios_output('%s://%s:%d/api/cluster/status/nagios/%s' % (self.args.protocol, self.args.host, self.args.port, check))

  def get_nagios_output(self, url):
    _log.info('GET  %-50s - get the cluster status' % url)
    response = self.get_data(url)
    print(response.text)
    service_state = re.match("^\S+ (\S+)", response.text).group(1)
    if service_state == "WARNING":
      return 1
    elif service_state == "CRITICAL":
      return 2
    elif service_state == "UNKNOWN":
      return 3
    else:
      return 0


def main():
  arg_parser = ArgumentParser(description='check_croit_cluster (Version: %s)' % (VERSION))
  arg_parser.add_argument('--version', action='version', version='%s' % (VERSION))
  arg_parser.add_argument('-v', '--verbose', default=0, action='count', help='increase output verbosity (use up to 3 times)')
  arg_parser.add_argument('--timeout', default=20, type=int, help='Ceph status timeout (default 20)')
  arg_parser.add_argument('--https', default=False, action='store_true', help='use HTTPs instead of HTTP')
  arg_parser.add_argument('--check-certificate', default=False, action='store_true', help='validate TLS certificate', dest='check_cert')
  arg_parser.add_argument('--host', default='localhost', help='connect to host')
  arg_parser.add_argument('--port', type=int, help='connect to port (default=8080/443)')
  arg_parser.add_argument('--user', default='admin', help='username to authenticate', dest='username')
  arg_parser.add_argument('--pass', default='admin', help='password to authenticate', dest='password')
  arg_parser.add_argument('check', nargs='?', help='The Ceph health check to perform, defaults to the whole cluster status')
  args = arg_parser.parse_args(sys.argv[1:])
  if args.https:
    if args.port is None:
      args.port = 443
    args.protocol = 'https'
  else:
    if args.port is None:
      args.port = 8080
    args.protocol = 'http'
  api_client = croit(args)
  api_client.login()
  if args.check is None:
    return api_client.status_summary()
  else:
    return api_client.status(args.check)



if __name__ == '__main__':
  sys.exit(main())

