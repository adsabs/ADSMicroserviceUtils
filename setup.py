import os
from subprocess import Popen, PIPE

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup, find_packages

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
    long_description = ""

with open('requirements.txt') as f:
    required = f.read().splitlines()

def get_git_version(default="v0.0.1"):
    try:
        p = Popen(['git', 'describe', '--tags'], stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        line = line.strip()
        return line.decode('utf-8')
    except:
        return default

setup(
    author="NASA/SAO ADS",
    name='adsmutils',
    classifiers=[
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    description='ADS Microservice Utils',
    include_package_data=True,
    install_requires=required,
    license='MIT',
    long_description=long_description,
    url='https://github.com/adsabs/ADSMicroserviceUtils',
    packages=find_packages(),
    platforms='any',
    version=get_git_version(default="v0.0.1"),
    zip_safe=False,
)

