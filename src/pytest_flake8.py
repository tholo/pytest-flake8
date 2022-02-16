"""py.test plugin to test with flake8."""

import fnmatch
import logging
import os
import re

from collections import namedtuple
from contextlib import redirect_stderr, redirect_stdout
from io import BytesIO, TextIOWrapper
from pathlib import Path

import flake8.main.application
import flake8.options.config
import pytest

__version__ = "1.2.0"

logger = logging.getLogger(__name__)

HISTKEY = "flake8/mtimes"

# TODO: replace with dataclass when 3.6 support can be dropped
PytestFlake8Cache = namedtuple(
    "PytestFlake8Cache",
    [
        "enabled",
        "mtimes",
    ],
)


PytestFlake8Settings = namedtuple(
    "PytestFlake8Settings",
    [
        "enabled",
        "flake8_config",
        "flake8_exts",
        "flake8_ignore",
        "flake8_max_len",
        "flake8_max_complexity",
        "flake8_show_source",
        "flake8_statistics",
        "flake8_cache",
    ],
)


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


def pytest_configure(config: pytest.Config):
    """Start a new session."""
    if config.option.flake8:
        if hasattr(config, "cache"):
            mtimes = config.cache.get(HISTKEY, {})
        else:
            mtimes = {}

        config._flake8_settings = PytestFlake8Settings(
            enabled=True,
            flake8_config=config.getini("flake8-config"),
            flake8_exts=config.getini("flake8-extensions"),
            flake8_ignore=Ignorer(config.getini("flake8-ignore")),
            flake8_max_len=config.getini("flake8-max-line-length"),
            flake8_max_complexity=config.getini("flake8-max-complexity"),
            flake8_show_source=config.getini("flake8-show-source"),
            flake8_statistics=config.getini("flake8-statistics"),
            flake8_cache=PytestFlake8Cache(enabled=True, mtimes=mtimes),
        )
        config.addinivalue_line("markers", "flake8: Tests which run flake8.")
    else:
        config._flake8_settings = PytestFlake8Settings(
            enabled=False,
            flake8_config=None,
            flake8_exts=None,
            flake8_ignore=None,
            flake8_max_len=None,
            flake8_max_complexity=None,
            flake8_show_source=None,
            flake8_statistics=None,
            flake8_cache=None,
        )


def path_sepcific_flake8_settings(
    parent: PytestFlake8Settings, config: pytest.Config, path: Path
) -> PytestFlake8Settings:
    """Returns a copy of `parent` settings with any path-sepcific overrides."""
    overrides = {}

    if parent.flake8_config:
        orig_conifg_val = parent.flake8_config
        pytest_config = config.inipath  # may be None
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
    else:
        # flake8 config absence is explicitly requested
        active_flake8_config = None

    if active_flake8_config:
        # Ensure that the variable is of 'pathlib.Path' class
        active_flake8_config = Path(active_flake8_config)

    overrides["flake8_config"] = active_flake8_config

    return parent._replace(**overrides)


def pytest_collect_file(path, parent):
    """Filter files down to which ones should be checked."""
    pytest_config: pytest.Config = parent.config
    flake8_config: PytestFlake8Settings = pytest_config._flake8_settings
    if (not flake8_config) or (not flake8_config.enabled):
        # flake8 integration disabled
        return
    # The original `path` type is py._path.local.LocalPath, but the future is pathlib.Path
    path: Path = Path(path)
    if path.suffix not in flake8_config.flake8_exts:
        # The file extension is not to be captured
        return
    return Flake8FileCollector.from_parent(
        parent=parent,
        path=path,
        name=str(path),
        flake8_config=path_sepcific_flake8_settings(flake8_config, pytest_config, path),
    )


def pytest_unconfigure(config: pytest.Config):
    """Flush cache at end of run."""
    flake8_config: PytestFlake8Settings = config._flake8_settings
    if flake8_config.enabled and flake8_config.flake8_cache.enabled:
        config.cache.set(HISTKEY, flake8_config.flake8_cache.mtimes)


class Flake8Error(Exception):
    """indicates an error during flake8 checks.

    Attributes:
        error_count: int - number of errors
        stderr: str - flake8's stderr
        stdout: str - flake8's stdout
    """

    error_count: int = -1
    stdout: str = None
    stderr: str = None

    def __init__(self, error_count: int, stdout: str, stderr: str):
        self.error_count = error_count
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"Detected {error_count} errors.\n\n{stdout}\n{stderr}")


class Flake8FileCollector(pytest.File):

    flake8_config: PytestFlake8Settings

    def __init__(self, *args, flake8_config: PytestFlake8Settings, **kwargs):
        super().__init__(*args, **kwargs)
        self.flake8_config = flake8_config
        self.add_marker("flake8")

    def get_cache_item(self):
        # Returns (key, value) this item should have in cache
        value = ";".join(
            [
                f"mtime:{self.path.stat().st_mtime}",
                f"ignore:{self.flake8_config.flake8_ignore(self.path)}",
            ]
        )
        return (
            str(self.path.resolve()),
            value,
        )

    def setup(self):
        (my_key, exp_val) = self.get_cache_item()
        old_val = self.flake8_config.flake8_cache.mtimes.get(my_key)
        skip_message = None
        if old_val == exp_val:
            skip_message = "file(s) previously passed FLAKE8 checks"
        elif self.flake8_config.flake8_ignore.skip_file(self.path):
            skip_message = "Skipping due to flake8-ignore param"
        if skip_message:
            return pytest.skip(skip_message)

    def cache_success(self):
        """Cache the success of the test."""
        if not self.flake8_config.flake8_cache.enabled:
            return
        (my_key, exp_val) = self.get_cache_item()
        self.flake8_config.flake8_cache.mtimes[my_key] = exp_val

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(Flake8Error):
            return excinfo.value.args[0]
        return super().repr_failure(excinfo)

    def collect(self):
        return [
            Flake8Item.from_parent(parent=self, target_path=self.path, name="FLAKE8")
        ]


class Flake8Item(pytest.Item):

    parent: Flake8FileCollector
    target_path: Path = None
    flake8_config = property(lambda self: self.parent.flake8_config)

    def __init__(self, target_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.target_path = target_path

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
            found_errors = check_file(self.parent.path, self.flake8_config)
            to.flush()
            te.flush()
            out = bo.getvalue().decode("utf-8")
            err = be.getvalue().decode("utf-8")

        if found_errors:
            raise Flake8Error(found_errors, stdout=out, stderr=err)
        else:
            # update mtime only if test passed
            # otherwise failures would not be re-run next time
            self.parent.cache_success()


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
                ign = ["__ALL__"]
            if glob and "/" != os.sep and "/" in glob:
                glob = glob.replace("/", os.sep)
            ignores.append((glob, ign))

    def __call__(self, path: Path):
        l = []  # noqa: E741
        for (glob, ignlist) in self.ignores:
            if not glob or fnmatch.fnmatch(path, f"**{os.sep}{glob}"):
                if "__ALL__" in ignlist:
                    # Completely ignore the path
                    return None
                l.extend(ignlist)
        return l

    def skip_file(self, path: Path) -> bool:
        """Just a helper function for readability."""
        return self(path) is None


def check_file(path, test_config: PytestFlake8Settings):
    """Run flake8 over a single file, and return the number of failures."""
    args = []
    if test_config.flake8_config:
        args += ["--config", os.fspath(test_config.flake8_config)]
    if test_config.flake8_max_len:
        args += ["--max-line-length", test_config.flake8_max_len]
    if test_config.flake8_max_complexity:
        args += ["--max-complexity", str(test_config.flake8_max_complexity)]
    if test_config.flake8_show_source:
        args += ["--show-source"]
    if test_config.flake8_statistics:
        args += ["--statistics"]
    app = flake8.main.application.Application()

    prelim_opts, remaining_args = app.parse_preliminary_options(args)
    flake8.configure_logging(prelim_opts.verbose, prelim_opts.output_file)
    config_finder = flake8.options.config.ConfigFileFinder(
        app.program,
        prelim_opts.append_config,
        config_file=prelim_opts.config,
        ignore_config_files=prelim_opts.isolated,
    )
    app.find_plugins(config_finder)
    app.register_plugin_options()
    app.parse_configuration_and_cli(config_finder, remaining_args)

    app.options.ignore = list(test_config.flake8_ignore(path)) + list(
        app.options.ignore
    )

    app.make_formatter()  # fix this
    app.make_guide()
    app.make_file_checker_manager()
    app.run_checks([os.fspath(path)])
    app.formatter.start()
    app.report_errors()
    app.formatter.stop()
    return app.result_count
