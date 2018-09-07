#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os

import unittest
import json
import inspect
from mock import patch

import adsmutils
from base import TestCaseDatabase

class TestAdsUtils(unittest.TestCase):
    """
    Tests the appliction's methods
    """
    def setUp(self):
        unittest.TestCase.setUp(self)


    def tearDown(self):
        unittest.TestCase.tearDown(self)


    def test_load_config(self):
        with patch('adsmutils.load_module') as load_module:
            c = adsmutils.load_config()
            f = os.path.abspath(os.path.join(os.path.dirname(inspect.getsourcefile(adsmutils)), '..'))
            self.assertEquals((f + '/config.py',),
                              load_module.call_args_list[0][0])
            self.assertEquals((f + '/local_config.py',),
                              load_module.call_args_list[1][0])
            self.assertEqual(c['PROJ_HOME'], f)

        with patch('adsmutils.load_module') as load_module:
            adsmutils.load_config('/tmp')
            self.assertEquals(('/tmp/config.py',),
                              load_module.call_args_list[0][0])
            self.assertEquals(('/tmp/local_config.py',),
                              load_module.call_args_list[1][0])


    def test_load_module(self):
        f = os.path.abspath(os.path.join(os.path.dirname(inspect.getsourcefile(adsmutils)), './tests/config_sample.py'))
        x = adsmutils.load_module(f)
        self.assertEquals(x, {'FOO': {'bar': ['baz', 1]}})

    def test_update_from_env(self):
        os.environ["FOO"] = "2"
        os.environ["BAR"] = "False"
        os.environ["ADSWS_TEST_BAR"] = "True"
        conf = {'FOO': 1, 'BAR': False}
        adsmutils.conf_update_from_env("adsws.test", conf)
        self.assertEquals(conf, {'FOO': 2, 'BAR': True})


    def test_setup_logging(self):
        with patch('adsmutils.ConcurrentRotatingFileHandler') as cloghandler:
            adsmutils.setup_logging('app')
            f = os.path.abspath(os.path.join(os.path.abspath(__file__), '../../..'))
            self.assertEqual("call(backupCount=10, encoding=u'UTF-8', filename=u'{filename}/logs/app.log', maxBytes=10485760, mode=u'a')".format(filename=f),
                             str(cloghandler.call_args))


    def test_get_date(self):
        """Check we always work with UTC dates"""

        d = adsmutils.get_date()
        self.assertTrue(d.tzname() == 'UTC')

        d1 = adsmutils.get_date('2009-09-04T01:56:35.450686Z')
        self.assertTrue(d1.tzname() == 'UTC')
        self.assertEqual(d1.isoformat(), '2009-09-04T01:56:35.450686+00:00')

        d2 = adsmutils.get_date('2009-09-03T20:56:35.450686-05:00')
        self.assertTrue(d2.tzname() == 'UTC')
        self.assertEqual(d2.isoformat(), '2009-09-04T01:56:35.450686+00:00')

        d3 = adsmutils.get_date('2009-09-03T20:56:35.450686')
        self.assertTrue(d3.tzname() == 'UTC')
        self.assertEqual(d3.isoformat(), '2009-09-03T20:56:35.450686+00:00')


from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy as sa

class TestDBUtils(TestCaseDatabase):
    def test_utcdatetime_type(self):
        
        base = declarative_base()
        class Test(base):
            __tablename__ = 'testdate'
            id = sa.Column(sa.Integer, primary_key=True)
            created = sa.Column(adsmutils.UTCDateTime, default=adsmutils.get_date)
            updated = sa.Column(adsmutils.UTCDateTime)
        base.metadata.bind = self.app.db.session.get_bind()
        base.metadata.create_all()
        
        with self.app.session_scope() as session:
            session.add(Test())
            m = session.query(Test).first()
            assert m.created
            assert m.created.tzname() == 'UTC'
            assert '+00:00' in str(m.created)
            
            current = adsmutils.get_date('2018-09-07T20:22:02.249389+00:00')
            m.updated = current
            session.commit()
            
            m = session.query(Test).first()
            assert str(m.updated) == str(current)
        
if __name__ == '__main__':
    unittest.main()
