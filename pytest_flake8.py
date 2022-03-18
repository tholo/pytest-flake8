"""py.test plugin to test with flake8."""

import os
import re
from contextlib import redirect_stdout, redirect_stderr
from io import BytesIO, TextIOWrapper

from flake8.main import application
from flake8.options import config

import pytest

__version__ = '1.1.1'

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
        "flake8-max-doc-length",
        help="maximum doc line length")
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
        config._flake8maxdoclen = config.getini("flake8-max-doc-length")
        config._flake8maxcomplexity = config.getini("flake8-max-complexity")
        config._flake8showsource = config.getini("flake8-show-source")
        config._flake8statistics = config.getini("flake8-statistics")
        config._flake8exts = config.getini("flake8-extensions")
        config.addinivalue_line('markers', "flake8: Tests which run flake8.")
        if hasattr(config, 'cache'):
            config._flake8mtimes = config.cache.get(HISTKEY, {})


def pytest_collect_file(file_path, path, parent):
    """Filter files down to which ones should be checked."""
    config = parent.config
    if config.option.flake8 and file_path.suffix in config._flake8exts:
        flake8ignore = config._flake8ignore(path)
        if flake8ignore is not None:
            item = Flake8File.from_parent(
                parent, path=file_path,
                flake8ignore=flake8ignore,
                maxlength=config._flake8maxlen,
                maxdoclength=config._flake8maxdoclen,
                maxcomplexity=config._flake8maxcomplexity,
                showsource=config._flake8showsource,
                statistics=config._flake8statistics)
            return item


def pytest_unconfigure(config):
    """Flush cache at end of run."""
    if hasattr(config, "_flake8mtimes"):
        config.cache.set(HISTKEY, config._flake8mtimes)


class Flake8Error(Exception):
    """ indicates an error during flake8 checks. """


class Flake8File(pytest.File):

    def __init__(self, *k,
                 flake8ignore=None, maxlength=None, maxdoclength=None,
                 maxcomplexity=None, showsource=None, statistics=None,
                 **kw):
        super().__init__(*k, **kw)
        self.flake8ignore = flake8ignore
        self.maxlength = maxlength
        self.maxdoclength = maxdoclength
        self.maxcomplexity = maxcomplexity
        self.showsource = showsource
        self.statistics = statistics

    def collect(self):
        return [Flake8Item.from_parent(self, name="flake-8")]


class Flake8Item(pytest.Item):

    def __init__(self, *k, **kwargs):
        super().__init__(*k, **kwargs)
        self._nodeid += "::FLAKE8"
        self.add_marker("flake8")
        self.flake8ignore = self.parent.flake8ignore
        self.maxlength = self.parent.maxlength
        self.maxdoclength = self.parent.maxdoclength
        self.maxcomplexity = self.parent.maxcomplexity
        self.showsource = self.parent.showsource
        self.statistics = self.parent.statistics

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
        with BytesIO() as bo, TextIOWrapper(bo, encoding='utf-8') as to, \
             BytesIO() as be, TextIOWrapper(be, encoding='utf-8') as te, \
             redirect_stdout(to), redirect_stderr(te):
            found_errors = check_file(
                self.fspath,
                self.flake8ignore,
                self.maxlength,
                self.maxdoclength,
                self.maxcomplexity,
                self.showsource,
                self.statistics
            )
            to.flush()
            te.flush()
            out = bo.getvalue().decode('utf-8')
            err = be.getvalue().decode('utf-8')

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
    def __init__(self, ignorelines, coderex=re.compile(r"[EW]\d\d\d")):
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
        l = []  # noqa: E741
        for (glob, ignlist) in self.ignores:
            if not glob or path.fnmatch(glob):
                if ignlist is None:
                    return None
                l.extend(ignlist)
        return l


def check_file(path, flake8ignore, maxlength, maxdoclenght, maxcomplexity,
               showsource, statistics):
    """Run flake8 over a single file, and return the number of failures."""
    args = []
    if maxlength:
        args += ['--max-line-length', maxlength]
    if maxdoclenght:
        args += ['--max-doc-length', maxdoclenght]
    if maxcomplexity:
        args += ['--max-complexity', maxcomplexity]
    if showsource:
        args += ['--show-source']
    if statistics:
        args += ['--statistics']
    app = application.Application()
    prelim_opts, remaining_args = app.parse_preliminary_options(args)
    config_finder = config.ConfigFileFinder(
        app.program,
        prelim_opts.append_config,
        config_file=prelim_opts.config,
        ignore_config_files=prelim_opts.isolated,
    )
    app.find_plugins(config_finder)
    app.register_plugin_options()
    app.parse_configuration_and_cli(config_finder, remaining_args)
    if flake8ignore:
        app.options.ignore = flake8ignore
    app.make_formatter()  # fix this
    app.make_guide()
    app.make_file_checker_manager()
    app.run_checks([str(path)])
    app.formatter.start()
    app.report_errors()
    app.formatter.stop()
    return app.result_count
