"""py.test plugin to test with flake8."""

import os
import re

from flake8.main import application

import py

import pytest

__version__ = '0.6'

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
        config._flake8ignore = Ignorer(config.getini("flake8-ignore"))
        config._flake8maxlen = config.getini("flake8-max-line-length")
        config._flake8maxcomplexity = config.getini("flake8-max-complexity")
        config._flake8showshource = config.getini("flake8-show-source")
        config._flake8statistics = config.getini("flake8-statistics")
        config._flake8exts = config.getini("flake8-extensions")
        if hasattr(config, 'cache'):
            config._flake8mtimes = config.cache.get(HISTKEY, {})


def pytest_collect_file(path, parent):
    """Filter files down to which ones should be checked."""
    config = parent.config
    if config.option.flake8 and path.ext in config._flake8exts:
        flake8ignore = config._flake8ignore(path)
        if flake8ignore is not None:
            return Flake8Item(
                path,
                parent,
                flake8ignore=flake8ignore,
                maxlength=config._flake8maxlen,
                maxcomplexity=config._flake8maxcomplexity,
                showshource=config._flake8showshource,
                statistics=config._flake8statistics)


def pytest_unconfigure(config):
    """Flush cache at end of run."""
    if hasattr(config, "_flake8mtimes"):
        config.cache.set(HISTKEY, config._flake8mtimes)


class Flake8Error(Exception):
    """ indicates an error during flake8 checks. """


class Flake8Item(pytest.Item, pytest.File):

    def __init__(self, path, parent, flake8ignore, maxlength,
                 maxcomplexity, showshource, statistics):
        super(Flake8Item, self).__init__(path, parent)
        self.add_marker("flake8")
        self.flake8ignore = flake8ignore
        self.maxlength = maxlength
        self.maxcomplexity = maxcomplexity
        self.showshource = showshource
        self.statistics = statistics

    def setup(self):
        if hasattr(self.config, "_flake8mtimes"):
            flake8mtimes = self.config._flake8mtimes
        else:
            flake8mtimes = {}
        self._flake8mtime = self.fspath.mtime()
        old = flake8mtimes.get(str(self.fspath), (0, []))
        if old == [self._flake8mtime, self.flake8ignore]:
            pytest.skip("file(s) previously passed FLAKE8 checks")

    def runtest(self):
        call = py.io.StdCapture.call
        found_errors, out, err = call(
            check_file,
            self.fspath,
            self.flake8ignore,
            self.maxlength,
            self.maxcomplexity,
            self.showshource,
            self.statistics)
        if found_errors:
            raise Flake8Error(out, err)
        # update mtime only if test passed
        # otherwise failures would not be re-run next time
        if hasattr(self.config, "_flake8mtimes"):
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


def check_file(path, flake8ignore, maxlength, maxcomplexity,
               showshource, statistics):
    """Run flake8 over a single file, and return the number of failures."""
    args = []
    if maxlength:
        args += ['--max-line-length', maxlength]
    if maxcomplexity:
        args += ['--max-complexity', maxcomplexity]
    if showshource:
        args += ['--show-source']
    if statistics:
        args += ['--statistics']
    app = application.Application()
    app.find_plugins()
    app.register_plugin_options()
    app.parse_configuration_and_cli(args)
    app.options.ignore = flake8ignore
    app.make_formatter()  # fix this
    app.make_notifier()
    app.make_guide()
    app.make_file_checker_manager()
    app.run_checks([str(path)])
    app.formatter.start()
    app.report_errors()
    # app.report_statistics()
    # app.report_benchmarks()
    app.formatter.stop()
    return app.result_count
