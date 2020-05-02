# coding=utf8
"""Unit tests for flake8 pytest plugin."""
from __future__ import print_function

import py
import pytest

pytest_plugins = ("pytester",)


def test_version():
    """Verify we can get (correct) version."""
    import pytest_flake8

    assert pytest_flake8.__version__
    assert (
        pytest_flake8.__version__.split(".")[0] >= "2"
    ), "Tests require version >= 2.0.0"


@pytest.mark.parametrize(
    "argument, value",
    [("ignore", "*.py W503"), ("max-line-length", 42), ("max-complexity", 10)],
)
def test_deprecated_cli(argument, value, testdir):
    testdir.plugins.append("pytest-flake8")
    testdir.makepyfile("class AClass:", "    pass     ", "    # too many spaces")
    tox_content = """
[pytest]
markers = flake8
"""
    tox_content += "flake8-{} = {}".format(argument, value)
    testdir.makeini(tox_content)
    with pytest.warns(DeprecationWarning):  # verify deprecated warnings are generated
        result = testdir.runpytest("--flake8")
    assert result


def test_extensions(testdir):
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
    result = testdir.runpytest("--flake8")
    result.stdout.fnmatch_lines(
        ["*collected 1*", ]
    )
    result.assert_outcomes(failed=1)


def test_ok_verbose(testdir):
    p = testdir.makepyfile(
        """
        class AClass:
            pass
    """
    )
    p = p.write(p.read() + "\n")
    result = testdir.runpytest("--flake8", "--verbose")
    result.stdout.fnmatch_lines(
        ["*test_ok_verbose*", ]
    )
    result.assert_outcomes(passed=1)


@pytest.mark.xfail("sys.platform == 'win32'")
def test_unicode_error(testdir):
    x = testdir.tmpdir.join("x.py")
    import codecs

    f = codecs.open(str(x), "w", encoding="utf8")
    f.write(
        py.builtin._totext(
            """
# coding=utf8

accent_map = {
    u'\\xc0': 'a',  # À -> a  non-ascii comment crashes it
}
""",
            "utf8",
        )
    )
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


#   ("--flake8-show-source", "", True),
#   ("--flake8-statistics", "", True),
#   ("--flake8-extensions", ".py .pyx", True)


@pytest.mark.parametrize(
    "config_line, if_present, if_absent",
    [
        (
            "ignore = E201",
            [".*ignoring.*201.*"],
            [".*201 whitespace.*", ".*501 line.*"],
        ),
        ("exclude = abc*.py", ["collected 0 items"], [".*201 whitespace.*"]),
        (
            "max-line-length = 100",
            [".*201 whitespace.*"],
            [".*201 whitespace.*", ".*501 line too long.*"],
        ),
    ],
)
def test_defer_to_f8_config(config_line, if_present, if_absent, testdir):
    """Check plugin attends to config settings for flake8 itself
       for the now-deprecated flake8-ignore, flake8-max-line-length.
       Also, since flake8-ignore ... ALL worked like [flake8] exclude,
       check plugin now honors the latter."""
    testdir.plugins = "pytest-flake8"  # force plugin to reload with tempdir as cwd
    # test file exhibits all attributes that configuration can manage
    testdir.makepyfile(
        abc_argle="""
    class Foo:
        argle = [ 2, 3, 4]
        bargle = "abcdefg" + "hijklmnop" + "hijklmnop" + "hijklmnop" + "hijklmnop" + "hijklmnop" + "hijklmnop"
        foo = "abc"
    """
    )
    tox_content = """
    [flake8]
    disable-noqa = True
    """

    # test the positive:
    testdir.makeini(tox_content + config_line + "\n")
    result = testdir.runpytest("--flake8")
    result.stdout.re_match_lines_random(if_present)

    # test the negative (config line absent)
    testdir.makeini(tox_content)
    result = testdir.runpytest("--flake8")
    result.stdout.re_match_lines_random(if_absent)
