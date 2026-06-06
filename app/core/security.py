import hashlib
import hmac


def verify_github_signature(secret: str, payload: bytes, signature_header: str | None) -> bool:
    if not signature_header:
        return False

    try:
        algorithm, signature = signature_header.split("=", maxsplit=1)
    except ValueError:
        return False

    if algorithm != "sha256":
        return False

    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
