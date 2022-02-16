from pathlib import Path

import pytest


@pytest.fixture
def mock_py_file(testdir):
    # A python file with a single very long line
    return testdir.makepyfile(f'val = {repr("S" * 300)}')


def test_default(testdir, mock_py_file, mock_flake8_app):
    with mock_flake8_app() as mock_app:
        testdir.runpytest("--flake8", "--verbose")
    mock_app.parse_preliminary_options.assert_called_once_with([])


def test_all_legacy_ini_params(testdir, mock_py_file, mock_flake8_app):
    pytest_ini = testdir.makeini(
        """
        [pytest]
        markers = flake8
        flake8-ignore = MOCK42
        flake8-max-line-length = 1024042
        flake8-max-complexity = 999
        flake8-show-source = true
        flake8-statistics = true
        flake8-extensions = .mock-ext-42 .mock-ext-43 .py
    """
    )
    with mock_flake8_app() as mock_app:
        testdir.runpytest("--flake8", "--verbose")
    mock_app.parse_preliminary_options.assert_called_once_with(
        [
            "--config",
            str(pytest_ini),
            "--max-line-length",
            "1024042",
            "--max-complexity",
            "999",
            "--show-source",
            "--statistics",
        ]
    )


@pytest.mark.parametrize("use_relpath", [True, False])
def test_explicit_flake8_config_path(
    testdir, mock_py_file, mock_flake8_app, use_relpath
):
    flake8_config = testdir.makefile(".ini", "Custom ini confg")

    config_path = Path(flake8_config.strpath)
    if use_relpath:
        # Convert to relative path
        config_path = Path(".", config_path.name)
    else:
        config_path = config_path.resolve()

    testdir.makeini(
        f"""
        [pytest]
        markers = flake8
        flake8-config = {config_path}
    """
    )
    with mock_flake8_app() as mock_app:
        testdir.runpytest("--flake8")
    mock_app.parse_preliminary_options.assert_called_once_with(
        ["--config", flake8_config]
    )


@pytest.mark.parametrize("silence_error", [True, False])
def test_flake8_config_has_effect(testdir, mock_py_file, silence_error):
    """Check that changing values in the flake8 config actually affects its behaviour."""
    testdir.makeini(
        f"""
        [pytest]
        markers = flake8

        [flake8]
        max-line-length = {104000 if silence_error else 10}
        ignore = W292 ## ignore "no newline at end of file"
    """
    )
    test_out = testdir.runpytest("--flake8", "--verbose")
    test_out_stdout = "\n".join(test_out.stdout.lines)
    if silence_error:
        assert "FLAKE8 PASSED" in test_out_stdout
    else:
        assert "E501 line too long" in test_out_stdout
        assert "FLAKE8 FAILED" in test_out_stdout
