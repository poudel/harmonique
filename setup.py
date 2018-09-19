#!/usr/bin/env python
import os
from setuptools import setup


with open(os.path.join("README.md"), "r") as f:
    long_description = f.read()


def get_deps():
    with open("requirements.txt", "r") as deps:
        return deps.readlines()[1:]


setup(
    name="harmonica",
    version="0.0.1",
    description="a sad little personal static blog generator",
    long_description=long_description,
    author="Keshab Paudel",
    author_email="self@keshab.net",
    url="http://github.com/poudel/harmonica",
    py_modules=["simple_config"],
    entry_points={"console_scripts": ["harmonica=harmonica:main"]},
    install_requires=get_deps(),
    license="MIT",
    keywords="static-site blog markdown python",
)
