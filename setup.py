#!/usr/bin/env python

import os
import setuptools
import sys

install_requires = [line.rstrip() for line in open(os.path.join(os.path.dirname(__file__), "requirements.txt"))]

if sys.version_info >= (3, 4):
    # Remove the dependency on enum34
    # on platforms that have it natively.
    install_requires.remove("enum34")

setuptools.setup(
    name="slicedimage",
    version="0.0.2",
    description="Library to access sliced imaging data",
    author="Tony Tung",
    author_email="ttung@chanzuckerberg.com",
    license="MIT",
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    entry_points={
        'console_scripts': "slicedimage=slicedimage.cli.main:main"
    }
)
