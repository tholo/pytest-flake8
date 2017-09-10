py.test plugin for efficiently checking PEP8 compliance 
=======================================================

Usage
-----

Install by running the command::

    pip install pytest-flake8

After installing it, when you run tests with the option::

    py.test --flake8

every file ending in ``.py`` will be discovered and checked with
flake8.

.. note::

    If optional flake8 plugins are installed, those will
    be used automatically. No provisions have been made for
    configuring these via py.test.

.. warning::

    Running flake8 tests on your project is likely to cause a number 
    of issues. The plugin allows one to configure on a per-project and
    per-file basis which errors or warnings to ignore, see
    flake8-ignore_.

.. _flake8-ignore:

Configuring FLAKE8 options per project and file
-----------------------------------------------

Maximum line length can be configured for the whole project
by adding a ``flake8-max-line-length`` option to your ``setup.cfg``
or ``tox.ini`` file like this::

    # content of setup.cfg
    [pytest]
    flake8-max-line-length = 99

Note that the default will be what naturally comes with `flake8`_
(which it turn gets its default from `pep8`_).

You may configure flake8-checking options for your project
by adding an ``flake8-ignore`` entry to your ``setup.cfg``
or ``tox.ini`` file like this::

    # content of setup.cfg
    [pytest]
    flake8-ignore = E201 E231

This would globally prevent complaints about two whitespace issues.
Rerunning with the above example will now look better::

    $ py.test -q  --flake8
    collecting ... collected 1 items
    .
    1 passed in 0.01 seconds

If you have some files where you want to specifically ignore 
some errors or warnings you can start a flake8-ignore line with 
a glob-pattern and a space-separated list of codes::

    # content of setup.cfg
    [pytest]
    flake8-ignore = 
        *.py E201
        doc/conf.py ALL

So if you have a conf.py like this::

    # content of doc/conf.py

    func (  [1,2,3]) #this line lots pep8 errors :)

then running again with the previous example will show a single
failure and it will ignore doc/conf.py alltogether::

    $ py.test --flake8 -v # verbose shows what is ignored
    ======================================= test session starts ========================================
    platform darwin -- Python 2.7.6 -- py-1.4.26 -- pytest-2.7.0 -- /Users/tholo/Source/pytest/bin/python
    cachedir: /Users/tholo/Source/pytest/src/verify/.cache
    rootdir: /Users/tholo/Source/angular/src/verify, inifile: setup.cfg
    plugins: flake8, cache
    collected 1 items

    myfile.py PASSED

    ========================================= 1 passed in 0.00 seconds =========================================

Note that doc/conf.py was not considered or imported.

Unused ignores can be found by using the ``--flake8-log-ignore-usage`` option
with a path as argument.  If the option is set, a log will be written to that
file, where each line contains, in that order, the glob, the ignore code, and
the number of messages that were suppressed by that entry.

Notes
-----

The repository of this plugin is at https://github.com/tholo/pytest-flake8

For more info on py.test see http://pytest.org

The code is partially based on Ronny Pfannschmidt's pytest-codecheckers plugin.

.. _`flake8`: https://pypi.python.org/pypi/flake8
.. _`pep8`: https://pypi.python.org/pypi/pep8
