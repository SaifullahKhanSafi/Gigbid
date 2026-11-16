import hashlib
import hmac
import json
import re
import secrets
import time
from contextvars import ContextVar
import jwt
from core.settings import secret

tenant_context = ContextVar("tenant", default=None)


def token(tenant, scope="user", ttl=3600, **claims):
    return jwt.encode(
        {"sub": tenant, "scope": scope, "exp": int(time.time()) + ttl, **claims}, secret(), algorithm="HS256"
    )


def decode(value, scope=None):
    payload = jwt.decode(value, secret(), algorithms=["HS256"], options={"require": ["exp", "sub", "scope"]})
    if scope and payload["scope"] != scope:
        raise ValueError("Incorrect token scope")
    return payload


def tenant():
    import os

    value = tenant_context.get() or os.getenv("GIGBID_TENANT")
    if not value:
        raise PermissionError("Authenticated tenant required")
    return value


def digest(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ":" + hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def password_matches(password, encoded):
    return hmac.compare_digest(password_hash(password, encoded.split(":")[0]), encoded)


def mask(value):
    if isinstance(value, dict):
        return {
            k: "[REDACTED]" if re.search("token|password|authorization|secret", k, re.I) else mask(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [mask(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", value)
        value = re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", "[PHONE_OR_ACCOUNT]", value)
        return value
    return value
