# -*- coding: utf-8 -*-

import sys

from setuptools import find_packages
from setuptools import setup

import fastentrypoints

if not sys.version_info[0] == 3:
    sys.exit("Python 3 is required. Use: 'python3 setup.py install'")

dependencies = ["icecream", "click", "colorama"]

config = {
    "version": "0.1",
    "name": "advisory_lock",
    "url": "https://github.com/jakeogh/advisory_lock",
    "license": "ISC",
    "author": "Justin Keogh",
    "author_email": "github.com@v6y.net",
    "description": "Short explination of what it does _here_",
    "long_description": __doc__,
    "packages": find_packages(exclude=["tests"]),
    "package_data": {"advisory_lock": ["py.typed"]},
    "include_package_data": True,
    "zip_safe": False,
    "platforms": "any",
    "install_requires": dependencies,
    "entry_points": {
        "console_scripts": [
            "advisory-lock=advisory_lock.advisory_lock:cli",
        ],
    },
}

setup(**config)
