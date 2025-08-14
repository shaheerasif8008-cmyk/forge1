from __future__ import annotations

from testing_app.core.signing import sign_bytes, verify_bytes


def test_sign_and_verify() -> None:
    data = b"hello"
    sig = sign_bytes(data)
    assert verify_bytes(data, sig) is True
    assert verify_bytes(b"bye", sig) is False


