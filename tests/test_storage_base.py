import pytest

from sonic_platform_base.sonic_storage.storage_base import StorageBase


def test_secure_erase_is_platform_dependent():
    with pytest.raises(NotImplementedError):
        StorageBase("/dev/sda").secure_erase()
