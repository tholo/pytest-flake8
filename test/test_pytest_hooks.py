"""Test pytest hook configuration."""


def test_pytest_ordering(testdir):
    """Flake8 tests should be executed at the end of all other tests.

    (Just my personal preference, but, you know, I'm the maintainer.)
    """
    testdir.makepyfile(
        test_pytest_ordering_src="""
        def test_pass():
            assert (1 + 1) == 2

        def test_fail():
            assert 42 is False

        ################### this comment is definetly pep8-incompatible

    """
    )
    result = testdir.runpytest("--flake8", "-vv")
    result.assert_outcomes(passed=1, failed=2)
    result.stdout.fnmatch_lines(
        [
            "*collected 3*",
            "*::test_pass PASSED*",
            "*::test_fail FAILED*",
            "*::FLAKE8 FAILED*",
        ]
    )


def test_pytest_ordering_early_escape(testdir):
    """Flake8 tests should be executed at the end of all other tests.

    (Just my personal preference, but, you know, I'm the maintainer.)
    """
    testdir.makepyfile(
        test_pytest_ordering_src="""
        def test_pass():
            assert (1 + 1) == 2

        def test_fail():
            assert 42 is False

        ################### this comment is definetly pep8-incompatible

    """
    )
    result = testdir.runpytest("--flake8", "-x", "-vv")
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(
        [
            "*collected 3*",
            "*::test_pass PASSED*",
            "*::test_fail FAILED*",
        ]
    )
