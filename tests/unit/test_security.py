import hashlib
import hmac

from app.core.security import verify_github_signature


def test_verify_github_signature_accepts_valid_signature() -> None:
    secret = "top-secret"
    payload = b'{"ok": true}'
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    assert verify_github_signature(secret, payload, f"sha256={signature}")


def test_verify_github_signature_rejects_invalid_signature() -> None:
    assert not verify_github_signature("secret", b"payload", "sha256=bad")
