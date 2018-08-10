"""
Contains useful functions and utilities that are not neccessarily only useful
for this module. But are also used in differing modules insidide the same
project, and so do not belong to anything specific.
"""

from __future__ import absolute_import, unicode_literals
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import load_only as _load_only
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from flask_sqlalchemy import SQLAlchemy
import os
import logging
import imp
import sys
import time
import socket
import json
import ast
from dateutil import parser, tz
from datetime import datetime
import inspect
from cloghandler import ConcurrentRotatingFileHandler
from flask import Flask
from pythonjsonlogger import jsonlogger
from logging import Formatter
import flask
import requests

local_zone = tz.tzlocal()
utc_zone = tz.tzutc()

TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%S.%fZ"

def _get_proj_home(extra_frames=0):
    """Get the location of the caller module; then go up max_levels until
    finding requirements.txt"""

    frame = inspect.stack()[2+extra_frames]
    module = inspect.getsourcefile(frame[0])
    if not module:
        raise Exception("Sorry, wasnt able to guess your location. Let devs know about this issue.")
    d = os.path.dirname(module)
    x = d
    max_level = 3
    while max_level:
        f = os.path.abspath(os.path.join(x, 'requirements.txt'))
        if os.path.exists(f):
            return x
        x = os.path.abspath(os.path.join(x, '..'))
        max_level -= 1
    sys.stderr.write("Sorry, cant find the proj home; returning the location of the caller: %s\n" % d)
    return d



def get_date(timestr=None):
    """
    Always parses the time to be in the UTC time zone; or returns
    the current date (with UTC timezone specified)

    :param: timestr
    :type: str or None

    :return: datetime object with tzinfo=tzutc()
    """
    if timestr is None:
        return datetime.utcnow().replace(tzinfo=utc_zone)

    if isinstance(timestr, datetime):
        date = timestr
    else:
        date = parser.parse(timestr)

    if 'tzinfo' in repr(date): #hack, around silly None.encode()...
        date = date.astimezone(utc_zone)
    else:
        # this depends on current locale, for the moment when not
        # timezone specified, I'll treat them as UTC (however, it
        # is probably not correct and should work with an offset
        # but to that we would have to know which timezone the
        # was created)

        #local_date = date.replace(tzinfo=local_zone)
        #date = date.astimezone(utc_zone)

        date = date.replace(tzinfo=utc_zone)

    return date



def load_config(proj_home=None, extra_frames=0, app_name=None):
    """
    Loads configuration from config.py and also from local_config.py

    :param: proj_home - str, location of the home - we'll always try
        to load config files from there. If the location is empty,
        we'll inspect the caller and derive the location of its parent
        folder.
    :param: extra_frames - int, number of frames to look back; default
        is 2, which is good when the load_config() is called directly,
        but when called from inside classes, we need to add extra more

    :return dictionary
    """
    conf = {}

    if proj_home is not None:
        proj_home = os.path.abspath(proj_home)
        if not os.path.exists(proj_home):
            raise Exception('{proj_home} doesnt exist'.format(proj_home=proj_home))
    else:
        proj_home = _get_proj_home(extra_frames=extra_frames)


    if proj_home not in sys.path:
        sys.path.append(proj_home)

    conf['PROJ_HOME'] = proj_home

    conf.update(load_module(os.path.join(proj_home, 'config.py')))
    conf.update(load_module(os.path.join(proj_home, 'local_config.py')))
    conf_update_from_env(app_name or conf.get('SERVICE', ''), conf)

    return conf

def conf_update_from_env(app_name, conf):
    app_name = app_name.replace(".", "_").upper()
    for key in conf.keys():
        specific_app_key = "_".join((app_name, key))
        if specific_app_key in os.environ:
            # Highest priority: variables with app_name as prefix
            _replace_value(conf, key, os.environ[specific_app_key])
        elif key in os.environ:
            _replace_value(conf, key, os.environ[key])

def _replace_value(conf, key, new_value):
    logging.info("Overwriting constant '%s' old value '%s' with new value '%s' from environment", key, conf[key], new_value)
    try:
        w = json.loads(new_value)
        conf[key] = w
    except:
        try:
            # Interpret numbers, booleans, etc...
            conf[key] = ast.literal_eval(new_value)
        except:
            # String
            conf[key] = new_value


def load_module(filename):
    """
    Loads module, first from config.py then from local_config.py

    :return dictionary
    """

    filename = os.path.join(filename)
    d = imp.new_module('config')
    d.__file__ = filename
    try:
        with open(filename) as config_file:
            exec(compile(config_file.read(), filename, 'exec'), d.__dict__)
    except IOError as e:
        pass
    res = {}
    from_object(d, res)
    return res


def setup_logging(name_, level=None, proj_home=None, attach_stdout=False):
    """
    Sets up generic logging to file with rotating files on disk

    :param: name_: the name of the logfile (not the destination!)
    :param: level: the level of the logging DEBUG, INFO, WARN
    :param: proj_home: optional, starting dir in which we'll
            check for (and create) 'logs' folder and set the
            logger there
    :return: logging instance
    """

    if level is None:
        config = load_config(extra_frames=1, proj_home=proj_home, app_name=name_)
        level = config.get('LOGGING_LEVEL', 'INFO')

    level = getattr(logging, level)

    logfmt = u'%(asctime)s %(msecs)03d %(levelname)-8s [%(process)d:%(threadName)s:%(filename)s:%(lineno)d] %(message)s'
    datefmt = u'%Y-%m-%dT%H:%M:%S.%fZ' # ISO 8601
    #formatter = logging.Formatter(fmt=logfmt, datefmt=datefmt)

    formatter = MultilineMessagesFormatter(fmt=logfmt, datefmt=datefmt)
    formatter.multiline_marker = ''
    formatter.multiline_fmt = '     %(message)s'

    formatter.converter = time.gmtime
    logging_instance = logging.getLogger(name_)
    logging_instance.propagate = False # logging messages are not passed to the handlers of ancestor loggers (i.e., gunicorn)

    if proj_home:
        proj_home = os.path.abspath(proj_home)
        fn_path = os.path.join(proj_home, 'logs')
    else:
        fn_path = os.path.join(_get_proj_home(), 'logs')

    if not os.path.exists(fn_path):
        os.makedirs(fn_path)

    fn = os.path.join(fn_path, '{0}.log'.format(name_.split('.log')[0]))
    rfh = ConcurrentRotatingFileHandler(filename=fn,
                                        maxBytes=10485760,
                                        backupCount=10,
                                        mode='a',
                                        encoding='UTF-8')  # 10MB file
    rfh.setFormatter(formatter)
    logging_instance.handlers = []
    logging_instance.addHandler(rfh)
    logging_instance.setLevel(level)

    if attach_stdout:
        stdout = logging.StreamHandler(sys.stdout)
        stdout.formatter = get_json_formatter()
        logging_instance.addHandler(stdout)

    return logging_instance


def from_object(from_obj, to_obj):
    """Updates the values from the given object.  An object can be of one
    of the following two types:

    Objects are usually either modules or classes.
    Just the uppercase variables in that object are stored in the config.

    :param obj: an import name or object
    """
    for key in dir(from_obj):
        if key.isupper():
            to_obj[key] = getattr(from_obj, key)




class ADSFlask(Flask):
    """ADS Flask worker; used by all the microservice applications.

    This class should be instantiated outside app.py

    """

    def __init__(self, app_name, *args, **kwargs):
        """
        :param: app_name - string, name of the application (can be anything)
        :keyword: local_config - dict, configuration that should be applied
            over the default config (that is loaded from config.py and local_config.py)
        """
        proj_home = None
        if 'proj_home' in kwargs:
            proj_home = kwargs.pop('proj_home')
        self._config = load_config(extra_frames=1, proj_home=proj_home, app_name=app_name)
        if not proj_home:
            proj_home = self._config.get('PROJ_HOME', None)

        local_config = None
        if 'local_config' in kwargs:
            local_config = kwargs.pop('local_config')
            if local_config:
                self._config.update(local_config) #our config

        Flask.__init__(self, app_name, *args, **kwargs)
        self.config.update(self._config)
        self._logger = setup_logging(app_name, proj_home=proj_home,
                                     level=self._config.get('LOGGING_LEVEL', 'INFO'),
                                     attach_stdout=self._config.get('LOG_STDOUT', False))

        self.db = None

        if self._config.get('SQLALCHEMY_DATABASE_URI', None):
            self.db = SQLAlchemy(self)

        # HTTP connection pool
        # - The maximum number of retries each connection should attempt: this
        #   applies only to failed DNS lookups, socket connections and connection timeouts,
        #   never to requests where data has made it to the server. By default,
        #   requests does not retry failed connections.
        # http://docs.python-requests.org/en/latest/api/?highlight=max_retries#requests.adapters.HTTPAdapter
        self.client = requests.Session()
        http_adapter = requests.adapters.HTTPAdapter(pool_connections=self._config.get('REQUESTS_POOL_CONNECTIONS', 10), pool_maxsize=self._config.get('REQUESTS_POOL_MAXSIZE', 1000), max_retries=self._config.get('REQUESTS_POOL_RETRIES', 3), pool_block=False)
        self.client.mount('http://', http_adapter)
        self.before_request_funcs.setdefault(None, []).append(self._before_request)

    def _before_request(self):
        if flask.has_request_context():
            # New request will contain also key information from the original request
            forward_headers = {}
            forward_headers["X-Original-Uri"] = flask.request.headers.get('X-Original-Uri', "-")
            forward_headers["X-Original-Forwarded-For"] = flask.request.headers.get('X-Original-Forwarded-For', "-")
            forward_headers["X-Forwarded-For"] = flask.request.headers.get('X-Forwarded-For', "-")
            forward_headers["X-Forwarded-Authorization"] = flask.request.headers.get('X-Forwarded-Authorization', flask.request.headers.get('Authorization', "-"))
            forward_headers["X-Amzn-Trace-Id"] = flask.request.headers.get('X-Amzn-Trace-Id', "-")
            self.client.headers.update(forward_headers)

    def _get_callers_module(self):
        frame = inspect.stack()[2]
        m = inspect.getmodule(frame[0])
        if m.__name__ == '__main__':
            parts = m.__file__.split(os.path.sep)
            return '%s.%s' % (parts[-2], parts[-1].split('.')[0])
        return m.__name__


    def close_app(self):
        """Closes the app"""
        self.db = None
        self.logger = None


    @contextmanager
    def session_scope(self):
        """Provides a transactional session - ie. the session for the
        current thread/work of unit.

        Use as:

            with session_scope() as session:
                o = ModelObject(...)
                session.add(o)
        """

        if self.db is None:
            raise Exception('DB not initialized properly, check: SQLALCHEMY_URL')

        # create local session (optional step)
        s = self.db.session()

        try:
            yield s
            s.commit()
        except:
            s.rollback()
            raise
        finally:
            s.close()



class MultilineMessagesFormatter(logging.Formatter):

    def format(self, record):
        """
        This is mostly the same as logging.Formatter.format except for adding spaces in front
        of the multiline messages.
        """
        s = logging.Formatter.format(self, record)

        if '\n' in s:
            return '\n     '.join(s.split('\n'))
        else:
            return s

    def formatTime(self, record, datefmt=None):
        """logging uses time.strftime which doesn't understand
        how to add microsecs. datetime understands that. so we
        have to work around the old time.strftime here."""
        if datefmt:
            datefmt = datefmt.replace('%f', '%03d' % (record.msecs))
            return logging.Formatter.formatTime(self, record, datefmt)
        else:
            return logging.Formatter.formatTime(self, record, datefmt) # default ISO8601


class JsonFormatter(jsonlogger.JsonFormatter, object):
    converter = time.gmtime

    def __init__(self,
                 fmt="%(asctime) %(name) %(processName) %(filename)  %(funcName) %(levelname) %(lineno) %(module) %(threadName) %(message)",
                 datefmt=TIMESTAMP_FMT,
                 extra={}, *args, **kwargs):
        self._extra = extra
        jsonlogger.JsonFormatter.__init__(self, fmt=fmt, datefmt=datefmt, *args, **kwargs)

    def add_fields(self, log_record, record, message_dict):
        super(JsonFormatter, self).add_fields(log_record, record, message_dict)
        if flask.has_request_context():
            # Log key fields that gnunicorn logs too
            log_record["X-Original-Uri"] = flask.request.headers.get('X-Original-Uri', "-")
            log_record["X-Original-Forwarded-For"] = flask.request.headers.get('X-Original-Forwarded-For', "-")
            log_record["X-Forwarded-For"] = flask.request.headers.get('X-Forwarded-For', "-")
            log_record["X-Forwarded-Authorization"] = flask.request.headers.get('X-Forwarded-Authorization', "-")
            log_record["Authorization"] = flask.request.headers.get('Authorization', "-")
            log_record["X-Amzn-Trace-Id"] = flask.request.headers.get('X-Amzn-Trace-Id', "-")
            log_record["cookie"] = "; ".join(["{}={}".format(k, v) for k, v in flask.request.cookies.iteritems()])

    def process_log_record(self, log_record):
        # Enforce the presence of a timestamp
        if "asctime" in log_record:
            log_record["timestamp"] = log_record["asctime"]
        else:
            log_record["timestamp"] = datetime.utcnow().strftime(TIMESTAMP_FMT)
            log_record["asctime"] = log_record["timestamp"]

        if self._extra is not None:
            for key, value in self._extra.items():
                log_record[key] = value
        return super(JsonFormatter, self).process_log_record(log_record)

    def formatException(self, ei):
        if ei and not isinstance(ei, tuple):
            ei = sys.exc_info()
        r = jsonlogger.JsonFormatter.formatException(self, ei)
        return r

    def formatTime(self, record, datefmt=None):
        """logging uses time.strftime which doesn't understand
        how to add microsecs. datetime understands that. so we
        have to work around the old time.strftime here."""
        if datefmt:
            datefmt = datefmt.replace('%f', '%03d' % (record.msecs))
            return Formatter.formatTime(self, record, datefmt)
        else:
            return Formatter.formatTime(self, record, datefmt)  # default ISO8601

    def format(self, record):
        return jsonlogger.JsonFormatter.format(self, record)

class GunicornJsonFormatter(JsonFormatter, object):

    def __init__(self,*args, **kwargs):
        internal_kwargs = {"extra": {"hostname": socket.gethostname()}}
        internal_kwargs.update(kwargs)
        JsonFormatter.__init__(self, *args, **internal_kwargs)

    def add_fields(self, log_record, record, message_dict):
        super(GunicornJsonFormatter, self).add_fields(log_record, record, message_dict)
        # Log key fields that the flask microservice logs too
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['msecs'] = record.msecs
        # Extract JSON message
        try:
            msg = json.loads(record.message)
        except ValueError, e:
            pass
        else:
            leftovers = {}
            for key, value in msg.iteritems():
                # Make sure we do not overwrite an existing key
                # and we do not use "message" since it will be overwritten
                if key != "message" and key not in log_record:
                    log_record[key] = value
                else:
                    leftovers[key] = value
            log_record['_leftovers'] = json.dumps(leftovers)

    def process_log_record(self, log_record):
        if '_leftovers' in log_record:
            # Remove already extracted JSON message keys and leave only
            # the keys that could not be extracted (if any)
            log_record['message'] = log_record['_leftovers']
            del log_record['_leftovers']
        return super(GunicornJsonFormatter, self).process_log_record(log_record)

def get_json_formatter(logfmt=u'%(asctime)s,%(msecs)03d %(levelname)-8s [%(process)d:%(threadName)s:%(filename)s:%(lineno)d] %(message)s',
                       datefmt=TIMESTAMP_FMT):
    return JsonFormatter(logfmt, datefmt, extra={"hostname": socket.gethostname()})


