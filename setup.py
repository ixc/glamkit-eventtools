#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
 
setup(
    name='glamkit-eventtools',
    version='1.0.0a1',
    description='An event management app for Django.',
    author='Greg Turner',
    author_email='greg@interaction.net.au',
    url='http://github.com/glamkit/glamkit-eventtools',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    classifiers=['Development Status :: 4 - Beta',
                 'Environment :: Web Environment',
                 'Framework :: Django',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: BSD License',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python',
                 'Topic :: Utilities'],
    install_requires=['setuptools', 'vobject==0.8.1c', 'python-dateutil==1.5', 'django-mptt>=0.5'],
    license='BSD',
    test_suite = "eventtools.tests",
)

# also requires libraries in REQUIREMENTS.txt
# pip install -r REQUIREMENTS.txt
