import hashlib
import uuid
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from core import db
from core.security import token, decode, password_hash, password_matches
from apps.api.schemas.models import Session

bearer = HTTPBearer(auto_error=False)


def identity(email):
    return hashlib.sha256(email.strip().casefold().encode()).hexdigest()


def register(email, password):
    key = identity(email)
    from mcp_servers.marketplace.adapters.local_sim import lock

    with db.connection() as c:
        lock(c, "register:" + key)
        if db.get("authentication", "user", key, c):
            raise HTTPException(409, "Email already registered")
        uid = uuid.uuid4().hex
        db.put("authentication", "user", key, {"id": uid, "password": password_hash(password)}, c)
        db.put(
            uid,
            "settings",
            "profile",
            {
                "persona": "ml",
                "floor_rate": 20,
                "weekly_connects": 100,
                "saved_search": "",
                "scheduled_scouting": False,
                "autonomy": "suggest",
            },
            c,
        )
    return session(uid)


def session(uid):
    jti = uuid.uuid4().hex
    db.put(uid, "session", jti, {"id": jti, "active": True})
    return Session(access_token=token(uid, "user", ttl=86400, jti=jti), user_id=uid)


def login(email, password):
    user = db.get("authentication", "user", identity(email))
    if not user or not password_matches(password, user["password"]):
        raise HTTPException(401, "Invalid credentials")
    return session(user["id"])


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    try:
        if not credentials:
            raise ValueError()
        data = decode(credentials.credentials, "user")
        if not (db.get(data["sub"], "session", data["jti"]) or {}).get("active"):
            raise ValueError()
        return data["sub"]
    except Exception:
        raise HTTPException(401, "Sign in to continue") from None
