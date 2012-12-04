#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
 
setup(
    name='glamkit-eventtools',
    version='0.6.0',
    description='An event management app for Django.',
    author='The Interaction Consoritum',
    author_email='admins@interaction.net.au',
    url='http://github.com/ixc/glamkit-eventtools',
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
    install_requires=[
        'python-dateutil==1.5',
        'django-countries==1.0.3',
        'vobject==0.8.1c'
    ],
    license='BSD',
    test_suite = "eventtools.tests",
)
