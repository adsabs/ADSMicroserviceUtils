# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals, division, print_function
import os
import tempfile
import unittest
from unittest import mock
import adsmutils


def _read_file(fpath):
    with open(fpath, 'r') as fi:
        return fi.read()


def _touch(path):
    with open(path, 'w'):
        pass


def _run_get_proj_home_as(caller_path):
    """Invoke _get_proj_home as if it were called from `caller_path`."""
    with mock.patch('adsmutils.inspect.getsourcefile', return_value=caller_path):
        return adsmutils._get_proj_home()


class TestGetProjHome(unittest.TestCase):

    def test_config_py_in_caller_dir_wins(self):
        """Biblib layout: pyproject.toml at repo root, config.py inside the
        package where the caller lives. PROJ_HOME resolves to the package
        directory so biblib/config.py loads. Regression test for the case
        that made the shim necessary."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, 'repo')
            pkg = os.path.join(repo, 'pkg')
            os.makedirs(pkg)
            _touch(os.path.join(repo, 'pyproject.toml'))
            _touch(os.path.join(pkg, 'config.py'))
            caller_py = os.path.join(pkg, 'app.py')
            _touch(caller_py)

            proj_home = _run_get_proj_home_as(caller_py)
            self.assertEqual(os.path.realpath(proj_home),
                             os.path.realpath(pkg))

    def test_config_py_at_repo_root(self):
        """Classic ADS layout: config.py at the repo root, caller inside the
        package. PROJ_HOME resolves to the repo root."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, 'repo')
            pkg = os.path.join(repo, 'pkg')
            os.makedirs(pkg)
            _touch(os.path.join(repo, 'pyproject.toml'))
            _touch(os.path.join(repo, 'config.py'))
            caller_py = os.path.join(pkg, 'app.py')
            _touch(caller_py)

            proj_home = _run_get_proj_home_as(caller_py)
            self.assertEqual(os.path.realpath(proj_home),
                             os.path.realpath(repo))

    def test_no_config_py_anywhere_falls_back_to_marker_dir(self):
        """No config.py anywhere: preserve the pre-existing behavior by
        returning the first directory that has a marker file. Keeps
        setup_logging's logs/ dir in the historically expected place for
        projects (like adsmutils itself) that don't ship a config.py."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, 'repo')
            pkg = os.path.join(repo, 'pkg')
            os.makedirs(pkg)
            _touch(os.path.join(repo, 'pyproject.toml'))
            caller_py = os.path.join(pkg, 'app.py')
            _touch(caller_py)

            proj_home = _run_get_proj_home_as(caller_py)
            self.assertEqual(os.path.realpath(proj_home),
                             os.path.realpath(repo))


class TestInit(unittest.TestCase):

    def test_logging(self):
        logdir = os.path.abspath(os.path.join(os.path.dirname(__file__), u'../../logs'))
        foo_log = logdir + u'/foo.bar.log'
        if os.path.exists(foo_log):
            os.remove(foo_log)
        logger = adsmutils.setup_logging(u'foo.bar')
        logger.warning(u'first')
        # If handler has stream attribute, flush it
        if hasattr(logger.handlers[0], 'stream') and logger.handlers[0].stream:
            logger.handlers[0].stream.flush()
        else:
            # concurrent-log-handler doesn't have stream attribute
            logger.handlers[0].flush()

        self.assertTrue(os.path.exists(foo_log))
        c = _read_file(foo_log)
        self.assertTrue('WARNING' in c)
        self.assertTrue('test_init.py' in c)
        self.assertTrue('first' in c)

        # now multiline message
        logger.warning(u'second\nthird')
        logger.warning(u'last')
        c = _read_file(foo_log)
        self.assertTrue(u'second\n     third' in c)

        msecs = False
        for x in c.strip().split(u'\n'):
            datestr = x.split(u' ')[0]
            if datestr != u'':
                t = adsmutils.get_date(datestr)
            if t.microsecond > 0:
                msecs = True
        self.assertTrue(msecs)

        # test json formatter
        # replace the default formatter
        for handler in logger.handlers:
            handler.formatter = adsmutils.get_json_formatter()
        logger.info(u'test json formatter')
        c = _read_file(foo_log)
        self.assertTrue(u'"message": "test json formatter"' in c)
        self.assertTrue(u'"hostname":' in c)
        self.assertTrue(u'"lineno":' in c)

        # verfiy that there was only one log handler, logging to a file
        self.assertTrue(len(logger.handlers), 1)
        # now create a logger, requesting logs be written to stdout as well
        #   so there will be two log handlers
        logger2 = adsmutils.setup_logging(name_=u'foo.bar.2', attach_stdout=True)
        self.assertTrue(len(logger2.handlers), 2)


if __name__ == '__main__':
    unittest.main()
