try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import os


setup(name='adsmutils',
      version='0.0.1',
      packages=['adsmutils'],
      install_requires=[
          'ConcurrentLogHandler==0.9.1',
          'python-dateutil==2.6.0',
          'DateTime==4.1.1',
          'SQLAlchemy==1.1.6',
          'setuptools>=36.5.0',
          'six>=1.11.0',
          'Flask-SQLAlchemy==2.2',
          'python-json-logger==0.1.8'
      ],
  )
