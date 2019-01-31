# -*- coding: utf-8 -*-

"""Install package."""

from setuptools import setup

setup(
    name='pytest-flake8',
    version='1.0.4',
    description='pytest plugin to check FLAKE8 requirements',
    long_description=open("README.rst").read(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
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
        'flake8>=3.5',
        'pytest>=3.5',
    ],
)
