"""basic web app tests."""

import app


def test_app_package_imports():
    """check app package imports."""
    assert app is not None
