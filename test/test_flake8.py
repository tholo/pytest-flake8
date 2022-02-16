"""Unit tests for flake8 pytest plugin."""

from pathlib import Path

import pytest


def test_version():
    """Verify we can get version."""
    import pytest_flake8

    assert pytest_flake8.__version__


@pytest.fixture
def extra_runtest_args():
    """An array of arguments that will be appended to all runpytest() calls."""
    return []


class TestIgnores:

    """Test ignores."""

    @pytest.fixture
    def example(self, request):
        """Create a test file."""
        testdir = request.getfixturevalue("testdir")
        fobj = testdir.makepyfile(test_ignores_example="")
        fobj.write("class AClass:\n    pass\n       \n\n# too many spaces")
        return fobj

    def test_ignores(self, tmpdir):
        """Verify parsing of ignore statements."""
        from pytest_flake8 import Ignorer

        ignores = ["E203", "b/?.py E204 W205", "z.py ALL", "*.py E300"]
        ign = Ignorer(ignores)
        assert ign(Path(tmpdir.join("a/b/x.py"))) == "E203 E204 W205 E300".split()
        assert ign(Path(tmpdir.join("a/y.py"))) == "E203 E300".split()
        assert ign(Path(tmpdir.join("a/z.py"))) is None

    def test_default_flake8_ignores(self, testdir, extra_runtest_args):
        testdir.makeini(
            """
            [pytest]
            markers = flake8

            [flake8]
            ignore = E203
                *.py E300
                tests/*.py ALL E203  # something
        """
        )
        testdir.tmpdir.ensure("xy.py")
        testdir.tmpdir.ensure("tests/hello.py")
        result = testdir.runpytest("--flake8", "-s", *extra_runtest_args)
        result.assert_outcomes(passed=2)
        result.stdout.fnmatch_lines(
            [
                "*collected 2*",
                "*xy.py .*",
                "*2 passed*",
            ]
        )

    def test_ignores_all(self, testdir, extra_runtest_args):
        """Verify success when all errors are ignored."""
        testdir.makeini(
            """
            [pytest]
            markers = flake8
            flake8-ignore = E203
                *.py E300
                tests/*.py ALL E203 # something
        """
        )
        testdir.tmpdir.ensure("xy.py")
        testdir.tmpdir.ensure("tests/hello.py")
        result = testdir.runpytest("--flake8", "-s", *extra_runtest_args)
        result.assert_outcomes(passed=1, skipped=1)
        result.stdout.fnmatch_lines(
            [
                r"*collected 2*",
                r"*xy.py [.]",
                r"*tests/hello.py s",
                r"*1 passed*",
            ]
        )

    def test_w293w292(self, testdir, example, extra_runtest_args):
        result = testdir.runpytest("--flake8", *extra_runtest_args)
        result.stdout.fnmatch_lines(
            [
                # "*plugins*flake8*",
                "*W293*",
                "*W292*",
            ]
        )
        result.assert_outcomes(failed=1)

    def test_mtime_caching_simple(self, testdir, extra_runtest_args):
        testdir.tmpdir.ensure("hello.py")  # empty file, should pass the check
        result = testdir.runpytest("--flake8", "-vv", *extra_runtest_args)
        result.assert_outcomes(passed=1)
        result = testdir.runpytest("--flake8", "-vv", *extra_runtest_args)
        result.assert_outcomes(skipped=1)

    def test_mtime_caching(self, testdir, example, extra_runtest_args):
        testdir.tmpdir.ensure("hello.py")
        result = testdir.runpytest("--flake8", *extra_runtest_args)
        result.stdout.fnmatch_lines(
            [
                # "*plugins*flake8*",
                "*W293*",
                "*W292*",
            ]
        )
        result.assert_outcomes(passed=1, failed=1)
        result = testdir.runpytest("--flake8", "-vv", *extra_runtest_args)
        result.stdout.fnmatch_lines(
            [
                "*W293*",
                "*W292*",
            ]
        )
        result.assert_outcomes(skipped=1, failed=1)
        testdir.makeini(
            """
            [pytest]
            flake8-ignore = *.py W293 W292 W391
        """
        )
        result = testdir.runpytest("--flake8", *extra_runtest_args)
        result.assert_outcomes(passed=2)


def test_extensions(testdir, extra_runtest_args):
    testdir.makeini(
        """
        [pytest]
        markers = flake8
        flake8-extensions = .py .pyx
    """
    )
    testdir.makefile(
        ".pyx",
        """
        @cfunc
        def f():
            pass
    """,
    )
    result = testdir.runpytest("--flake8", *extra_runtest_args)
    result.stdout.fnmatch_lines(
        [
            "*collected 1*",
        ]
    )
    result.assert_outcomes(failed=1)


def test_ok_verbose(testdir, extra_runtest_args):
    p = testdir.makepyfile(
        """
        class AClass:
            pass
    """
    )
    p = p.write(p.read() + "\n")
    result = testdir.runpytest("--flake8", "--verbose", *extra_runtest_args)
    result.stdout.fnmatch_lines(
        [
            "*test_ok_verbose*",
        ]
    )
    result.assert_outcomes(passed=1)


def test_keyword_match(testdir, extra_runtest_args):
    testdir.makepyfile(
        """
        def test_hello():
            a=[ 1,123]
            #
    """
    )
    result = testdir.runpytest("--flake8", "-mflake8", "-vv", *extra_runtest_args)
    result.stdout.fnmatch_lines(
        [
            "*E201*",
            "*1 failed*",
        ]
    )
    if pytest.__version__.startswith("7."):
        result.assert_outcomes(failed=1, deselected=1)
    else:
        # pytest v6
        result.assert_outcomes(failed=1)


def test_run_on_init_file(testdir, extra_runtest_args):
    d = testdir.mkpydir("tests")
    result = testdir.runpytest("--flake8", d / "__init__.py", *extra_runtest_args)
    result.assert_outcomes(passed=1)


@pytest.mark.xfail(reason="flake8 is not properly registered as a marker")
def test_strict(testdir, extra_runtest_args):
    testdir.makepyfile("")
    result = testdir.runpytest("--strict", "-mflake8", *extra_runtest_args)
    result.assert_outcomes(passed=1)


def test_junit_classname(testdir, extra_runtest_args):
    testdir.makepyfile("")
    result = testdir.runpytest("--flake8", "--junit-xml=TEST.xml", *extra_runtest_args)
    junit = testdir.tmpdir.join("TEST.xml")
    with open(str(junit)) as j_file:
        j_text = j_file.read()
    result.assert_outcomes(passed=1)
    assert 'classname=""' not in j_text
