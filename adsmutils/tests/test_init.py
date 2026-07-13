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
        logdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logs'))
        foo_log = logdir + '/foo.bar.log'
        if os.path.exists(foo_log):
            os.remove(foo_log)
        logger = adsmutils.setup_logging('foo.bar')
        logger.warning('first')
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
        logger.warning('second\nthird')
        logger.warning('last')
        c = _read_file(foo_log)
        self.assertTrue('second\n     third' in c)

        msecs = False
        for x in c.strip().split('\n'):
            datestr = x.split(' ')[0]
            if datestr != '':
                t = adsmutils.get_date(datestr)
            if t.microsecond > 0:
                msecs = True
        self.assertTrue(msecs)

        # test json formatter
        # replace the default formatter
        for handler in logger.handlers:
            handler.formatter = adsmutils.get_json_formatter()
        logger.info('test json formatter')
        c = _read_file(foo_log)
        self.assertTrue('"message": "test json formatter"' in c)
        self.assertTrue('"hostname":' in c)
        self.assertTrue('"lineno":' in c)

        # verfiy that there was only one log handler, logging to a file
        self.assertTrue(len(logger.handlers), 1)
        # now create a logger, requesting logs be written to stdout as well
        #   so there will be two log handlers
        logger2 = adsmutils.setup_logging(name_='foo.bar.2', attach_stdout=True)
        self.assertTrue(len(logger2.handlers), 2)


if __name__ == '__main__':
    unittest.main()
