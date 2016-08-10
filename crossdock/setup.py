#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='crossdock',
    version='1.0.0',
    include_package_data=True,
    zip_safe=False,
    packages=find_packages(exclude=['tests', 'example', 'tests.*']),
    entry_points={
        'console_scripts': [
            'crossdock = crossdock.server.server:serve',
        ]
    },
    install_requires=[
        # all dependencies are included in tchannel already
    ],
)
