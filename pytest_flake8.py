"""py.test plugin to test with flake8."""

import os
import re

from flake8.main import application

import py

import pytest
import warnings
import logging

__version__ = '2.0'

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
    parser.addini(
        "flake8-max-complexity",
        help="McCabe complexity threshold")
    parser.addini(
        "flake8-show-source", type="bool",
        help="show the source generate each error or warning")
    parser.addini(
        "flake8-statistics", type="bool",
        help="count errors and warnings")
    parser.addini(
        "flake8-extensions", type="args", default=[".py"],
        help="a list of file extensions, for example: .py .pyx")


def pytest_configure(config):
    """Start a new session."""
    if config.option.flake8:
        config._flake8showsource = config.getini("flake8-show-source")
        config._flake8statistics = config.getini("flake8-statistics")
        config._flake8extensions = config.getini("flake8-extensions")
        config.addinivalue_line('markers', "flake8: Tests which run flake8.")
        deprec_kwds = ["ignore", "max-line-length", "max-complexity"]
        deprec_items = []
        for d in deprec_kwds:
            if config.getini('flake8-' + d):
                deprec_items.append(d)
        if deprec_items:
            warnings.warn("pytest-flake8 2.x: Deprecated pytest-flake8 config '{}', ignoring!"
                " Use '{}' in flake8 config instead.".format(
                    "', '".join(['flake8-' + i for i in deprec_items])
                    , "', '".join(deprec_items)
                ), DeprecationWarning
            )

        if hasattr(config, 'cache'):
            config._flake8mtimes = config.cache.get(HISTKEY, {})


def pytest_sessionstart(session: pytest.Session):
    """At start of session, create flake8 session object (Application)"""
    session.config._flake8_app = application.Application()
    session.config._flake8_app.initialize(argv=[])


def pytest_sessionfinish(session: pytest.Session, exitstatus: int):
    if hasattr(session.config, "_flake8App"):
        session.config._flake8_app.report()


def pytest_collect_file(parent, path):
    """Filter files down to which ones should be checked.
    Use pytest --flake8-extensions to accept extensions, 
    but flake8 config [flake8] exclude= to skip files or directories"""
    if parent.config.option.flake8 and path.ext in (parent.config._flake8extensions):
        if parent.config._flake8_app.file_checker_manager.is_path_excluded(str(path)):
            logging.debug('Skipping file {} per flake8 exclude list.')
        else:
            return Flake8File.from_parent(parent, fspath=path)


def pytest_unconfigure(config):
    """Flush cache at end of run."""
    if hasattr(config, "_flake8mtimes"):
        config.cache.set(HISTKEY, config._flake8mtimes)


class Flake8Error(Exception):
    """ indicates an error during flake8 checks. """


class Flake8File(pytest.File):
    """Represents file, collect one flake8 test to run."""
    def collect(self):
        yield Flake8Item.from_parent(self, name="FLAKE8")


class Flake8Item(pytest.Item):
    """Represents the flake8 test run on a single file"""

    def setup(self):
        if hasattr(self.config, "_flake8mtimes"):
            flake8mtimes = self.config._flake8mtimes
        else:
            flake8mtimes = {}
        self._flake8mtime = self.fspath.mtime()
        old = flake8mtimes.get(str(self.fspath), 0)
        if old == self._flake8mtime:
            pytest.skip("file(s) previously passed FLAKE8 checks")

    def runtest(self):
        found_errors, out, err = py.io.StdCapture.call(
            run_one, str(self.fspath), self.session.config._flake8_app
        )
        if found_errors:
            raise Flake8Error(out, err)
        # update mtime only if test passed
        # otherwise failures would not be re-run next time
        if hasattr(self.config, "_flake8mtimes"):
            self.config._flake8mtimes[str(self.fspath)] = self._flake8mtime

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(Flake8Error):
            return excinfo.value.args[0]
        return super(Flake8Item, self).repr_failure(excinfo)

    def reportinfo(self):
        ignores = ""
        try:
            ignores = self.session.config._flake8_app.options.ignore
        except AttributeError:
            pass
        return (self.fspath, -1, "FLAKE8-check, ignoring [{}]".format(ignores))


def run_one(path, flake8_app):
    """Run flake8 on single file, using initialized app"""
    flake8_app.run_checks(files=[path])
    flake8_app.report_errors()
    return flake8_app.result_count
