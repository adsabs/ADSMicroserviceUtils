# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals, division, print_function
import os
import unittest
import adsmutils


def _read_file(fpath):
    with open(fpath, 'r') as fi:
        return fi.read()


class TestInit(unittest.TestCase):

    def test_logging(self):
        logdir = os.path.abspath(os.path.join(os.path.dirname(__file__), u'../../logs'))
        foo_log = logdir + u'/foo.bar.log'
        if os.path.exists(foo_log):
            os.remove(foo_log)
        logger = adsmutils.setup_logging(u'foo.bar')
        logger.warn(u'first')
        logger.handlers[0].stream.flush()

        self.assertTrue(os.path.exists(foo_log))
        c = _read_file(foo_log)
        self.assertTrue('WARNING' in c)
        self.assertTrue('test_init.py' in c)
        self.assertTrue('first' in c)

        # now multiline message
        logger.warn(u'second\nthird')
        logger.warn(u'last')
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
