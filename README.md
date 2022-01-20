pytest plugin for efficiently checking PEP8 compliance
===============

[![Version](https://img.shields.io/pypi/v/pytest-flake8-v2.svg)](https://pypi.python.org/pypi/pytest-flake8-v2)
[![PyPi](https://img.shields.io/pypi/status/pytest-flake8-v2.svg)](https://pypi.python.org/pypi/pytest-flake8-v2)
[![CI](https://github.com/VRGhost/pytest-flake8/actions/workflows/main.yml/badge.svg)](https://github.com/VRGhost/pytest-flake8/actions/workflows/main.yml)
[![Issues](https://img.shields.io/github/issues/VRGhost/pytest-flake8.svg)](https://github.com/VRGhost/pytest-flake8/issues)
[![PRs](https://img.shields.io/github/issues-pr/VRGhost/pytest-flake8.svg)](https://github.com/VRGhost/pytest-flake8/pulls)

Usage
=====

Install by running the command:

    pip install pytest-flake8-v2

After installing it, when you run tests with the option:

    pytest --flake8

every file ending in `.py` will be discovered and checked with flake8.

###### Note

If optional flake8 plugins are installed, those will be used
automatically. No provisions have been made for configuring these via
[pytest](http://pytest.org).


###### Warning


Running flake8 tests on your project is likely to cause a number of
issues. The plugin allows one to configure on a per-project and per-file
basis which errors or warnings to ignore, see
[flake8-ignore](#flake8-ignore).


Configuring FLAKE8 options per project and file
===============================================

###### Flake8 config file

Flake8-pytest automatically sets flake8 config file to match pytest config file path.
This means that you can configure flake8 by adding a `[flake8]` section to the pytests' config.

    #
    [pytest]
    markers = flake8

    [flake8]
    max-line-length = 71
    ignore = W292 ; ignore "no newline at end of file"

You can override this default by using `flake8-config` parameter

    [pytest]
    flake8-config = ./pytest.ini

If path relative, than it is treated as relative to pytests' config file.

###### Misc

Maximum line length can be configured for the whole project by adding a
`flake8-max-line-length` option to your `setup.cfg` or `tox.ini` file
like this:

    # content of setup.cfg
    [tool:pytest]
    flake8-max-line-length = 99

Note that the default will be what naturally comes with
[flake8](https://pypi.python.org/pypi/flake8) (which it turn gets its
default from [pycodestyle](https://pypi.python.org/pypi/pycodestyle)).

You may configure flake8-checking options for your project by adding an
`flake8-ignore` entry to your `setup.cfg` or `tox.ini` file like this:

    # content of setup.cfg
    [tool:pytest]
    flake8-ignore = E201 E231

This would globally prevent complaints about two whitespace issues.
Rerunning with the above example will now look better:

    $ pytest -q  --flake8
    collecting ... collected 1 items
    .
    1 passed in 0.01 seconds

If you have some files where you want to specifically ignore some errors
or warnings you can start a flake8-ignore line with a glob-pattern and a
space-separated list of codes:

    # content of setup.cfg
    [tool:pytest]
    flake8-ignore = 
        *.py E201
        doc/conf.py ALL

So if you have a conf.py like this:

    # content of doc/conf.py

    func (  [1,2,3]) #this line lots PEP8 errors :)

then running again with the previous example will show a single failure
and it will ignore doc/conf.py alltogether:

    $ pytest --flake8 -v # verbose shows what is ignored
    ======================================= test session starts ========================================
    platform darwin -- Python 2.7.6 -- py-1.4.26 -- pytest-2.7.0 -- /Users/tholo/Source/pytest/bin/python
    cachedir: /Users/tholo/Source/pytest/src/verify/.cache
    rootdir: /Users/tholo/Source/angular/src/verify, inifile: setup.cfg
    plugins: flake8, cache
    collected 1 items

    myfile.py PASSED

    ========================================= 1 passed in 0.00 seconds =========================================

Note that doc/conf.py was not considered or imported.

FAQs
====

All the flake8 tests are skipping!
----------------------------------

This is by design. Clean flake8 results are cached and, unless the file
is modified, not tested again.

You can run with `pytest --cache-clear --flake8` to override this.

Notes
=====

The repository of this plugin is at
<https://github.com/VRGhost/pytest-flake8>

For more info on [pytest](http://pytest.org) see <http://pytest.org>

The code is partially based on Ronny Pfannschmidt\'s
[pytest-codecheckers](https://pypi.python.org/pypi/pytest-codecheckers)
plugin.
