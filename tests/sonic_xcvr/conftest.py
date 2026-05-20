from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _no_sleep():
    with patch("time.sleep"):
        yield
