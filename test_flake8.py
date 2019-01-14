# coding=utf8
"""Unit tests for flake8 pytest plugin."""
from __future__ import print_function

import py
import pytest

pytest_plugins = "pytester",


def test_version():
    """Verify we can get version."""
    import pytest_flake8
    assert pytest_flake8.__version__


class TestIgnores:

    """Test ignores."""

    @pytest.fixture
    def example(self, request):
        """Create a test file."""
        testdir = request.getfixturevalue("testdir")
        import sys
        print(testdir, file=sys.stderr)
        p = testdir.makepyfile("")
        p.write("class AClass:\n    pass\n       \n\n# too many spaces")
        return p

    def test_ignores(self, tmpdir):
        """Verify parsing of ignore statements."""
        from pytest_flake8 import Ignorer
        ignores = ["E203", "b/?.py E204 W205", "z.py ALL", "*.py E300"]
        ign = Ignorer(ignores)
        assert ign(tmpdir.join("a/b/x.py")) == "E203 E204 W205 E300".split()
        assert ign(tmpdir.join("a/y.py")) == "E203 E300".split()
        assert ign(tmpdir.join("a/z.py")) is None

    def test_default_flake8_ignores(self, testdir):
        testdir.makeini("""
            [pytest]
            markers = flake8

            [flake8]
            ignore = E203
                *.py E300
                tests/*.py ALL E203  # something
        """)
        testdir.tmpdir.ensure("xy.py")
        testdir.tmpdir.ensure("tests/hello.py")
        result = testdir.runpytest("--flake8", "-s")
        result.assert_outcomes(passed=2)
        result.stdout.fnmatch_lines([
            "*collected 2*",
            "*xy.py .*",
            "*2 passed*",
        ])

    def test_ignores_all(self, testdir):
        """Verify success when all errors are ignored."""
        testdir.makeini("""
            [pytest]
            markers = flake8
            flake8-ignore = E203
                *.py E300
                tests/*.py ALL E203 # something
        """)
        testdir.tmpdir.ensure("xy.py")
        testdir.tmpdir.ensure("tests/hello.py")
        result = testdir.runpytest("--flake8", "-s")
        result.assert_outcomes(passed=1)
        result.stdout.fnmatch_lines([
            "*collected 1*",
            "*xy.py .*",
            "*1 passed*",
        ])

    def test_w293w292(self, testdir, example):
        result = testdir.runpytest("--flake8", )
        result.stdout.fnmatch_lines([
            # "*plugins*flake8*",
            "*W293*",
            "*W292*",
        ])
        result.assert_outcomes(failed=1)

    def test_mtime_caching(self, testdir, example):
        testdir.tmpdir.ensure("hello.py")
        result = testdir.runpytest("--flake8", )
        result.stdout.fnmatch_lines([
            # "*plugins*flake8*",
            "*W293*",
            "*W292*",
        ])
        result.assert_outcomes(passed=1, failed=1)
        result = testdir.runpytest("--flake8", )
        result.stdout.fnmatch_lines([
            "*W293*",
            "*W292*",
        ])
        result.assert_outcomes(skipped=1, failed=1)
        testdir.makeini("""
            [pytest]
            flake8-ignore = *.py W293 W292 W391
        """)
        result = testdir.runpytest("--flake8", )
        result.assert_outcomes(passed=2)


def test_extensions(testdir):
    testdir.makeini("""
        [pytest]
        markers = flake8
        flake8-extensions = .py .pyx
    """)
    testdir.makefile(".pyx", """
        @cfunc
        def f():
            pass
    """)
    result = testdir.runpytest("--flake8")
    result.stdout.fnmatch_lines([
        "*collected 1*",
    ])
    result.assert_outcomes(failed=1)


def test_ok_verbose(testdir):
    p = testdir.makepyfile("""
        class AClass:
            pass
    """)
    p = p.write(p.read() + "\n")
    result = testdir.runpytest("--flake8", "--verbose")
    result.stdout.fnmatch_lines([
        "*test_ok_verbose*",
    ])
    result.assert_outcomes(passed=1)


def test_keyword_match(testdir):
    testdir.makepyfile("""
        def test_hello():
            a=[ 1,123]
            #
    """)
    result = testdir.runpytest("--flake8", "-mflake8")
    result.stdout.fnmatch_lines([
        "*E201*",
        "*1 failed*",
    ])
    result.assert_outcomes(failed=1)


@pytest.mark.xfail("sys.platform == 'win32'")
def test_unicode_error(testdir):
    x = testdir.tmpdir.join("x.py")
    import codecs
    f = codecs.open(str(x), "w", encoding="utf8")
    f.write(py.builtin._totext("""
# coding=utf8

accent_map = {
    u'\\xc0': 'a',  # À -> a  non-ascii comment crashes it
}
""", "utf8"))
    f.close()
    # result = testdir.runpytest("--flake8", x, "-s")
    # result.stdout.fnmatch_lines("*non-ascii comment*")


@pytest.mark.xfail(reason="flake8 is not properly registered as a marker")
def test_strict(testdir):
    testdir.makepyfile("")
    result = testdir.runpytest("--strict", "-mflake8")
    result.assert_outcomes(passed=1)


def test_junit_classname(testdir):
    testdir.makepyfile("")
    result = testdir.runpytest("--flake8", "--junit-xml=TEST.xml")
    junit = testdir.tmpdir.join("TEST.xml")
    with open(str(junit)) as j_file:
        j_text = j_file.read()
    result.assert_outcomes(passed=1)
    assert 'classname=""' not in j_text
