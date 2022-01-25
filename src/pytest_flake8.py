"""py.test plugin to test with flake8."""

import logging
import os
import re

from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, TextIOWrapper
from pathlib import Path

import pytest

from flake8.main import application
from flake8.options import config

__version__ = "1.1.2"

logger = logging.getLogger(__name__)

HISTKEY = "flake8/mtimes"


def is_pytest_version(release: str, major: str = r"\d*"):
    return re.match(rf"^(?:{release})[.](?:{major})([.].*)?$", pytest.__version__)


def pytest_addoption(parser):
    """Hook up additional options."""
    group = parser.getgroup("general")
    group.addoption(
        "--flake8",
        action="store_true",
        help="perform some flake8 sanity checks on .py files",
    )
    group.addoption(
        "--no-flake8",
        action="store_false",
        dest="flake8",
        help="Disable flake8 integration",
    )
    parser.addini(
        "flake8-ignore",
        type="linelist",
        help="each line specifies a glob pattern and whitespace "
        "separated FLAKE8 errors or warnings which will be ignored, "
        "example: *.py W293",
    )
    parser.addini("flake8-max-line-length", help="maximum line length")
    parser.addini("flake8-max-complexity", help="McCabe complexity threshold")
    parser.addini(
        "flake8-show-source",
        type="bool",
        help="show the source generate each error or warning",
    )
    parser.addini("flake8-statistics", type="bool", help="count errors and warnings")
    parser.addini(
        "flake8-extensions",
        type="args",
        default=[".py"],
        help="a list of file extensions, for example: .py .pyx",
    )
    parser.addini(
        "flake8-config",
        default="__PYTEST_INI__",
        type=None,
        help="Path to the flake8 config file. (Default is the path to the pytest.ini)",
    )


def pytest_configure(config):
    """Start a new session."""
    if config.option.flake8:
        config._flake8ignore = Ignorer(config.getini("flake8-ignore"))
        config._flake8maxlen = config.getini("flake8-max-line-length")
        config._flake8maxcomplexity = config.getini("flake8-max-complexity")
        config._flake8showshource = config.getini("flake8-show-source")
        config._flake8statistics = config.getini("flake8-statistics")
        config._flake8exts = config.getini("flake8-extensions")
        config._flake8config = config.getini("flake8-config")
        config.addinivalue_line("markers", "flake8: Tests which run flake8.")
        if hasattr(config, "cache"):
            config._flake8mtimes = config.cache.get(HISTKEY, {})


def pytest_collect_file(path, parent):
    """Filter files down to which ones should be checked."""
    config = parent.config
    if (not config.option.flake8) or (path.ext not in config._flake8exts):
        # Flake8 integration is either disabled or the extension is not listed
        #  in the flake8-extensions array
        return

    active_flake8_config = None
    if config._flake8config:
        orig_conifg_val = config._flake8config
        if is_pytest_version("6", "0"):
            pytest_config = Path(config.inifile) if config.inifile else None
        else:
            pytest_config = config.inipath  # may be None
        active_flake8_config = None
        if orig_conifg_val == "__PYTEST_INI__":
            active_flake8_config = pytest_config
        else:
            orig_conifg_val = Path(orig_conifg_val)
            if not orig_conifg_val.is_absolute() and pytest_config:
                # Assume that the flake8-config is relative to the pytests' config
                active_flake8_config = pytest_config.parent.joinpath(orig_conifg_val)
            elif orig_conifg_val.exists():
                active_flake8_config = orig_conifg_val
            else:
                logger.warning(
                    f"Flake8 config file {active_flake8_config!r} does not exist."
                )
                active_flake8_config = None

    # raise Exception([orig_conifg_val, pytest_config, active_flake8_config])
    if active_flake8_config:
        active_flake8_config = active_flake8_config.resolve()

    flake8ignore = config._flake8ignore(path)
    if flake8ignore is not None:
        if is_pytest_version("6"):
            out_item = Flake8Item.from_parent(parent, fspath=path, name=path)
        else:
            assert is_pytest_version("[789]"), "pytest 7+"
            out_item = Flake8Item.from_parent(
                parent=parent, path=Path(path), name=str(path)
            )

        out_item.flake8ignore = flake8ignore
        out_item.maxlength = config._flake8maxlen
        out_item.maxcomplexity = config._flake8maxcomplexity
        out_item.showshource = config._flake8showshource
        out_item.statistics = config._flake8statistics
        out_item.config_file = active_flake8_config
        return out_item


def pytest_unconfigure(config):
    """Flush cache at end of run."""
    if hasattr(config, "_flake8mtimes"):
        config.cache.set(HISTKEY, config._flake8mtimes)


class Flake8Error(Exception):
    """indicates an error during flake8 checks."""


class Flake8Item(pytest.Item, pytest.File):
    def __init__(self, *args, **kwargs):
        kwargs.pop("fspath", None)
        super().__init__(*args, **kwargs)
        self._nodeid += "::FLAKE8"
        self.add_marker("flake8")

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
        with BytesIO() as bo, TextIOWrapper(
            bo, encoding="utf-8"
        ) as to, BytesIO() as be, TextIOWrapper(
            be, encoding="utf-8"
        ) as te, redirect_stdout(
            to
        ), redirect_stderr(
            te
        ):
            found_errors = check_file(
                self.fspath,
                self.config_file,
                self.flake8ignore,
                self.maxlength,
                self.maxcomplexity,
                self.showshource,
                self.statistics,
            )
            to.flush()
            te.flush()
            out = bo.getvalue().decode("utf-8")
            err = be.getvalue().decode("utf-8")

        if found_errors:
            raise Flake8Error(out, err)
        # update mtime only if test passed
        # otherwise failures would not be re-run next time
        if hasattr(self.config, "_flake8mtimes"):
            self.config._flake8mtimes[str(self.fspath)] = (
                self._flake8mtime,
                self.flake8ignore,
            )

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

    def collect(self):
        return iter((self,))


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


def check_file(
    path, config_file, flake8ignore, maxlength, maxcomplexity, showshource, statistics
):
    """Run flake8 over a single file, and return the number of failures."""
    args = []
    if config_file:
        args += ["--config", os.fspath(config_file)]
    if maxlength:
        args += ["--max-line-length", maxlength]
    if maxcomplexity:
        args += ["--max-complexity", maxcomplexity]
    if showshource:
        args += ["--show-source"]
    if statistics:
        args += ["--statistics"]
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
    if hasattr(app, "make_notifier"):
        # removed in flake8 3.7+
        app.make_notifier()
    app.make_guide()
    app.make_file_checker_manager()
    app.run_checks([str(path)])
    app.formatter.start()
    app.report_errors()
    app.formatter.stop()
    return app.result_count
