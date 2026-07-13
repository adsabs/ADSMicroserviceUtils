# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals, division, print_function
import testing.postgresql
from flask_testing import TestCase
from adsmutils import ADSFlask


class TestCaseDatabase(TestCase):

    postgresql_url_dict = {
        'port': 1234,
        'host': '127.0.0.1',
        'user': 'postgres',
        'database': 'test'
    }
    postgresql_url = 'postgresql://{user}@{host}:{port}/{database}' \
        .format(
            user=postgresql_url_dict['user'],
            host=postgresql_url_dict['host'],
            port=postgresql_url_dict['port'],
            database=postgresql_url_dict['database']
        )

    def create_app(self):
        '''Start the wsgi application'''
        local_config = {
            'SQLALCHEMY_DATABASE_URI': self.postgresql_url,
            'SQLALCHEMY_ECHO': False,
            'TESTING': True,
            'PROPAGATE_EXCEPTIONS': True,
            'TRAP_BAD_REQUEST_ERRORS': True
        }
        app = ADSFlask(__name__, static_folder=None, local_config=local_config)
        return app

    @classmethod
    def setUpClass(cls):
        cls.postgresql = \
            testing.postgresql.Postgresql(**cls.postgresql_url_dict)

    @classmethod
    def tearDownClass(cls):
        cls.postgresql.stop()

    def setUp(self):
        pass

    def tearDown(self):
        self.app.db.session.remove()
        self.app.db.drop_all()


class TestCase(TestCase):

    def create_app(self):
        '''Start the wsgi application'''
        local_config = {}
        app = ADSFlask(__name__, static_folder=None, local_config=local_config)
        return app
