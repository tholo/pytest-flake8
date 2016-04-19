"""py.test plugin to test with flake8."""

import os
import re

from flake8.engine import get_style_guide

import py

import pytest

__version__ = '0.2'

HISTKEY = "flake8/mtimes"


def pytest_addoption(parser):
    """Hook up additional options."""
    group = parser.getgroup("general")
    group.addoption(
        '--flake8', action='store_true',
        help="perform some flake8 sanity checks on .py files")
    parser.addini(
        "flake8-ignore", type="linelist",
        help="each line specifies a glob pattern and whitespace "
             "separated FLAKE8 errors or warnings which will be ignored, "
             "example: *.py W293")
    parser.addini(
        "flake8-max-line-length",
        help="maximum line length")


def pytest_configure(config):
    """Start a new session."""
    if config.option.flake8:
        config._flake8ignore = Ignorer(config.getini("flake8-ignore"))
        config._flake8maxlen = config.getini("flake8-max-line-length")
        config._flake8mtimes = config.cache.get(HISTKEY, {})


def pytest_collect_file(path, parent):
    """Filter files down to which ones should be checked."""
    config = parent.config
    if config.option.flake8 and path.ext == '.py':
        flake8ignore = config._flake8ignore(path)
        if flake8ignore is not None:
            return Flake8Item(path, parent, flake8ignore, config._flake8maxlen)


def pytest_unconfigure(config):
    """Flush cache at end of run."""
    if hasattr(config, "_flake8mtimes"):
        config.cache.set(HISTKEY, config._flake8mtimes)


class Flake8Error(Exception):
    """ indicates an error during flake8 checks. """


class Flake8Item(pytest.Item, pytest.File):

    def __init__(self, path, parent, flake8ignore, maxlength):
        super(Flake8Item, self).__init__(path, parent)
        self.add_marker("flake8")
        self.flake8ignore = flake8ignore
        self.maxlength = maxlength

    def setup(self):
        flake8mtimes = self.config._flake8mtimes
        self._flake8mtime = self.fspath.mtime()
        old = flake8mtimes.get(str(self.fspath), (0, []))
        if old == [self._flake8mtime, self.flake8ignore]:
            pytest.skip("file(s) previously passed FLAKE8 checks")

    def runtest(self):
        call = py.io.StdCapture.call
        found_errors, out, err = call(
            check_file, self.fspath, self.flake8ignore, self.maxlength)
        if found_errors:
            raise Flake8Error(out, err)
        # update mtime only if test passed
        # otherwise failures would not be re-run next time
        self.config._flake8mtimes[str(self.fspath)] = (self._flake8mtime,
                                                       self.flake8ignore)

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(Flake8Error):
            return excinfo.value.args[0]
        return super(Flake8Item, self).repr_failure(excinfo)

    def reportinfo(self):
        if self.flake8ignore:
            ignores = "(ignoring %s)" % " ".join(self.flake8ignore)
        else:
            ignores = ""
        return (self.fspath, -1, "FLAKE8-check%s" % ignores)


class Ignorer:
    def __init__(self, ignorelines, coderex=re.compile("[EW]\d\d\d")):
        self.ignores = ignores = []
        for line in ignorelines:
            i = line.find("#")
            if i != -1:
                line = line[:i]
            try:
                glob, ign = line.split(None, 1)
            except ValueError:
                glob, ign = None, line
            if glob and coderex.match(glob):
                glob, ign = None, line
            ign = ign.split()
            if "ALL" in ign:
                ign = None
            if glob and "/" != os.sep and "/" in glob:
                glob = glob.replace("/", os.sep)
            ignores.append((glob, ign))

    def __call__(self, path):
        l = []
        for (glob, ignlist) in self.ignores:
            if not glob or path.fnmatch(glob):
                if ignlist is None:
                    return None
                l.extend(ignlist)
        return l


def check_file(path, flake8ignore, maxlength):
    """Run flake8 over a single file, and return the number of failures."""
    if maxlength:
        flake8_style = get_style_guide(
            parse_argv=False, paths=['--max-line-length', maxlength])
    else:
        flake8_style = get_style_guide(parse_argv=False)
    options = flake8_style.options

    if options.install_hook:
        from flake8.hooks import install_hook
        install_hook()

    return flake8_style.input_file(str(path), expected=flake8ignore)
