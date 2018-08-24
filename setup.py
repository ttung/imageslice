#!/usr/bin/env python

import os
import setuptools

install_requires = [line.rstrip() for line in open(os.path.join(os.path.dirname(__file__), "requirements.txt"))]

setuptools.setup(
    name="slicedimage",
    version="0.0.3",
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
