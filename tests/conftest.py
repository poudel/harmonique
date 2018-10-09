import os
import pytest


@pytest.fixture
def example():
    print(os.path.curdir())
    return os.path.curdir()
