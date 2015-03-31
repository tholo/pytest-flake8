# -*- coding: utf-8 -*-

"""Install package."""

from setuptools import setup

setup(
    name='pytest-flake8',
    version='0.1',
    description='pytest plugin to check FLAKE8 requirements',
    long_description=open("README.rst").read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Topic :: Software Development",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
    ],
    license="BSD License",
    author='Thorsten Lockert',
    author_email='tholo@sigmasoft.com',
    url='https://github.com/tholo/pytest-flake8',
    py_modules=[
        'pytest_flake8',
    ],
    entry_points={
        'pytest11': ['flake8 = pytest_flake8'],
    },
    install_requires=[
        'flake8>=2.3',
        'pytest>=2.4.2',
        'pytest-cache',
    ],
)
