import contextlib
import unittest.mock

import pytest

pytest_plugins = ("pytester",)


@pytest.fixture
def mock_flake8_app():
    """Returns a context that temporarily mocks pytest application.

    This binding is made a context because mocking the pytest app
    causes side effect in this (pytest-flake8's) test suite
    while the context exits.
    """
    import flake8.main.application

    @contextlib.contextmanager
    def mock_app_ctx():
        orig_cls = flake8.main.application.Application
        with unittest.mock.patch.object(
            flake8.main.application, "Application", spec=orig_cls
        ) as mock_app_cls:
            mock_flake8_app = mock_app_cls.return_value
            mock_flake8_app.program = "mock_flake8"
            mock_flake8_app.formatter = unittest.mock.MagicMock(name="mock_formatter")
            mock_flake8_app.result_count = 42
            mock_flake8_app.options = unittest.mock.Mock(name="mock_flake8_options")

            prelim_opts_mock = unittest.mock.MagicMock(name="prelim_opts_mock")
            prelim_opts_mock.append_config = []

            mock_flake8_app.parse_preliminary_options.return_value = (
                prelim_opts_mock,
                unittest.mock.MagicMock(name="remaining_args_mock"),
            )
            yield mock_flake8_app

    return mock_app_ctx
