#!/usr/bin/env python

"""
Python WebDAV Server.

This is an example implementation of a DAVserver using the DAV package.

"""

from __future__ import absolute_import
from __future__ import print_function
import getopt
import sys
import os
import logging

from six.moves.BaseHTTPServer import HTTPServer
from six.moves.socketserver import ThreadingMixIn

from pywebdav.server.fileauth import DAVAuthHandler
from pywebdav.server.fshandler import FilesystemHandler

from pywebdav import __version__, __author__

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger('pywebdav')


LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def runserver(
        port=8008, host='localhost',
        directory='/tmp',
        verbose=False,
        noauth=False,
        user='',
        password='',
        handler=DAVAuthHandler,
        server=ThreadedHTTPServer):

    directory = directory.strip()
    directory = directory.rstrip('/')
    host = host.strip()

    if not os.path.isdir(directory):
        os.makedirs(directory)
        # log.error('%s is not a valid directory!' % directory)
        # return sys.exit(233)

    # basic checks against wrong hosts
    if host.find('/') != -1 or host.find(':') != -1:
        log.error('Malformed host %s' % host)
        return sys.exit(233)

    # no root directory
    if directory == '/':
        log.error('Root directory not allowed!')
        sys.exit(233)

    # dispatch directory and host to the filesystem handler
    # This handler is responsible from where to take the data
    handler.IFACE_CLASS = FilesystemHandler(
        directory, 'http://%s:%s/' % (host, port), verbose)

    # put some extra vars
    handler.verbose = verbose
    if noauth:
        log.warning('Authentication disabled!')
        handler.DO_AUTH = False

    log.info('Serving data from %s' % directory)

    if handler._config.DAV.getboolean('lockemulation') is False:
        log.info('Deactivated LOCK, UNLOCK (WebDAV level 2) support')

    handler.IFACE_CLASS.mimecheck = True
    if handler._config.DAV.getboolean('mimecheck') is False:
        handler.IFACE_CLASS.mimecheck = False
        log.info(
            "Disabled mimetype sniffing "
            "(All files will have type application/octet-stream)")

    if handler._config.DAV.baseurl:
        log.info('Using %s as base url for PROPFIND requests' %
                 handler._config.DAV.baseurl)
    handler.IFACE_CLASS.baseurl = handler._config.DAV.baseurl

    # initialize server on specified port
    runner = server((host, port), handler)
    print(('Listening on %s (%i)' % (host, port)))

    try:
        runner.serve_forever()
    except KeyboardInterrupt:
        log.info('Killed by user')


usage = """PyWebDAV server (version %s)
Standalone WebDAV server

Make sure to activate LOCK, UNLOCK using parameter -J if you want
to use clients like Windows Explorer or Mac OS X Finder that expect
LOCK working for write support.

Usage: ./server.py [OPTIONS]
Parameters:
    -c, --config    Specify a file where configuration is specified. In this
                    file you can specify options for a running server.
                    For an example look at the config.ini in this directory.
    -D, --directory Directory where to serve data from
                    The user that runs this server must have permissions
                    on that directory. NEVER run as root!
                    Default directory is /tmp
    -B, --baseurl   Behind a proxy pywebdav needs to generate other URIs for
                    PROPFIND. If you are experiencing problems with links or
                    such when behind a proxy then just set this to a sensible
                    default (e.g. http://dav.domain.com). Make sure that you
                    include the protocol.
    -H, --host      Host where to listen on (default: localhost)
    -P, --port      Port to bind server to  (default: 8008)
    -u, --user      Username for authentication
    -p, --password  Password for given user
    -n, --noauth    Pass parameter if server should not ask for authentication
                    This means that every user has access
    -m, --mysql     Pass this parameter if you want MySQL based authentication.
                    If you want to use MySQL then the usage of a configuration
                    file is mandatory.
    -J, --nolock    Deactivate LOCK and UNLOCK mode (WebDAV Version 2).
    -M, --nomime    Deactivate mimetype sniffing. Sniffing is based on magic
                    numbers detection but can be slow under heavy load. If you
                    are experiencing speed problems try to use this parameter.
    -v, --verbose   Be verbose.
    -l, --loglevel  Select the log level : DEBUG, INFO, WARNING, ERROR, CRITICAL
                    Default is WARNING
    -h, --help      Show this screen

Please send bug reports and feature requests to %s
""" % (__version__, __author__)


def setupDummyConfig(**kw):

    class DummyConfigDAV:
        def __init__(self, **kw):
            self.__dict__.update(**kw)

        def getboolean(self, name):
            return (str(getattr(self, name, 0))
                    in ('1', "yes", "true", "on", "True"))

    class DummyConfig:
        DAV = DummyConfigDAV(**kw)

    return DummyConfig()


def run():
    verbose = False
    directory = '/tmp'
    port = 8008
    host = 'localhost'
    noauth = False
    user = ''
    password = ''
    daemonize = False
    daemonaction = 'start'
    counter = 0
    mysql = False
    lockemulation = True
    http_response_use_iterator = True
    chunked_http_response = True
    configfile = ''
    mimecheck = True
    loglevel = 'warning'
    baseurl = ''

    # parse commandline
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'P:D:H:u:p:nvhmJi:c:Ml:TB:',
                                   ['host=', 'port=', 'directory=', 'user=',
                                    'password=', 'noauth', 'help', 'verbose',
                                    'config=', 'nolock', 'nomime', 'loglevel'
                                    'baseurl='])
    except getopt.GetoptError as e:
        print(usage)
        print('>>>> ERROR: %s' % str(e))
        sys.exit(2)

    for o, a in opts:
        if o in ['-M', '--nomime']:
            mimecheck = False

        if o in ['-J', '--nolock']:
            lockemulation = False

        if o in ['-c', '--config']:
            configfile = a

        if o in ['-D', '--directory']:
            directory = a

        if o in ['-H', '--host']:
            host = a

        if o in ['-P', '--port']:
            port = a

        if o in ['-v', '--verbose']:
            verbose = True

        if o in ['-l', '--loglevel']:
            loglevel = a.lower()

        if o in ['-h', '--help']:
            print(usage)
            sys.exit(2)

        if o in ['-n', '--noauth']:
            noauth = True

        if o in ['-u', '--user']:
            user = a

        if o in ['-p', '--password']:
            password = a

    # This feature are disabled because they are unstable
    http_request_use_iterator = 0

    conf = None

    _dc = {'verbose': verbose,
           'directory': directory,
           'port': port,
           'host': host,
           'noauth': noauth,
           'user': user,
           'password': password,
           'daemonize': daemonize,
           'daemonaction': daemonaction,
           'counter': counter,
           'lockemulation': lockemulation,
           'mimecheck': mimecheck,
           'chunked_http_response': chunked_http_response,
           'http_request_use_iterator': http_request_use_iterator,
           'http_response_use_iterator': http_response_use_iterator,
           'baseurl': baseurl
           }

    conf = setupDummyConfig(**_dc)

    if verbose and (LEVELS[loglevel] > LEVELS['info']):
        loglevel = 'info'

    logging.getLogger().setLevel(LEVELS[loglevel])

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)

    if not noauth and not user:
        print(usage)
        print('>> ERROR: No parameter specified!', file=sys.stderr)
        print('>> Example: davserver -D /tmp -n', file=sys.stderr)
        sys.exit(3)

    if isinstance(port, str):
        port = int(port.strip())

    log.info('chunked_http_response feature %s' %
             (conf.DAV.getboolean('chunked_http_response') and 'ON' or 'OFF'))
    log.info('http_request_use_iterator feature %s' %
             (conf.DAV.getboolean('http_request_use_iterator') and 'ON' or 'OFF'))
    log.info('http_response_use_iterator feature %s' % (
        conf.DAV.getboolean('http_response_use_iterator') and 'ON' or 'OFF'))

    handler = DAVAuthHandler
    # injecting options
    handler._config = conf

    runserver(port, host, directory, verbose, noauth, user, password,
              handler=handler)


if __name__ == '__main__':
    run()
