"""Tests for api.password_utils."""

import pytest

from api.password_utils import hash_password, verify_password


def test_hash_password_returns_string():
    h = hash_password("testpassword")
    assert isinstance(h, str)
    assert h.startswith("$2b$")


def test_hash_password_different_each_time():
    h1 = hash_password("same")
    h2 = hash_password("same")
    # bcrypt uses random salt, so hashes differ even for same input
    assert h1 != h2


def test_verify_password_correct():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True


def test_verify_password_incorrect():
    h = hash_password("secret123")
    assert verify_password("wrongpassword", h) is False


def test_verify_password_empty():
    h = hash_password("secret123")
    assert verify_password("", h) is False


def test_verify_password_invalid_hash():
    assert verify_password("test", "not-a-valid-hash") is False


def test_verify_password_unicode():
    h = hash_password("密码测试")
    assert verify_password("密码测试", h) is True
    assert verify_password("密码错误", h) is False
