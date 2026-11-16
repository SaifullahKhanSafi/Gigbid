import json
import os
from cryptography.fernet import Fernet
from core import db


def cipher():
    key = os.getenv("OAUTH_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("OAUTH_ENCRYPTION_KEY must be set before connecting real accounts")
    return Fernet(key.encode())


def save_tokens(tenant, provider, tokens):
    db.put(tenant, "oauth", provider, {"ciphertext": cipher().encrypt(json.dumps(tokens).encode()).decode()})


def load_tokens(tenant, provider):
    row = db.get(tenant, "oauth", provider)
    if not row:
        return None
    return json.loads(cipher().decrypt(row["ciphertext"].encode()))
