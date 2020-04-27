pytest plugin for efficiently checking PEP8 compliance 
======================================================

.. image:: https://img.shields.io/pypi/v/pytest-flake8.svg
    :target: https://pypi.python.org/pypi/pytest-flake8

.. image:: https://img.shields.io/pypi/pyversions/pytest-flake8.svg
    :target: https://pypi.python.org/pypi/pytest-flake8

.. image:: https://img.shields.io/pypi/implementation/pytest-flake8.svg
    :target: https://pypi.python.org/pypi/pytest-flake8

.. image:: https://img.shields.io/pypi/status/pytest-flake8.svg
    :target: https://pypi.python.org/pypi/pytest-flake8

.. image:: https://travis-ci.org/tholo/pytest-flake8.svg?branch=master
    :target: https://travis-ci.org/tholo/pytest-flake8

.. image:: https://img.shields.io/github/issues/tholo/pytest-flake8.svg
    :target: https://github.com/tholo/pytest-flake8/issues

.. image:: https://img.shields.io/github/issues-pr/tholo/pytest-flake8.svg
    :target: https://github.com/tholo/pytest-flake8/pulls

Usage
-----

Install by running the command::

    pip install pytest-flake8

After installing it, when you run tests with the option::

    pytest --flake8 [--flake8-exts=.py...] [--flake8-statistics] [--flake8-show-source]

*.py files will be discovered and checked with flake8, subject to
flake8's configuration for excluding files and ignoring errors.

.. note::

    All configuration of flake8 and its plugins is done through [flake8] configuration files.
    Note that these have different pattern matching rules than pytest.


Notes
-----

The repository of this plugin is at https://github.com/bobhy/pytest-flake8

For more info on `pytest`_ see http://pytest.org

The code is based on Thorsten Lockert's V1 implementation 
and Ronny Pfannschmidt's `pytest-codecheckers`_ plugin.

.. _`pytest`: http://pytest.org
.. _`flake8`: https://pypi.python.org/pypi/flake8
.. _`pycodestyle`: https://pypi.python.org/pypi/pycodestyle
.. _`pytest-codecheckers`: https://pypi.python.org/pypi/pytest-codecheckers
