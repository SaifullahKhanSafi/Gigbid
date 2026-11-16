"""Small tenant-scoped document repository; SQLite locally, Postgres in Compose."""

from contextlib import contextmanager
import json
import os
import sqlite3
import time
import uuid
from core.settings import RUNTIME


@contextmanager
def connection():
    url = os.getenv("DATABASE_URL")
    if url:
        import psycopg
        from psycopg.rows import dict_row

        conn = psycopg.connect(url, row_factory=dict_row)
    else:
        conn = sqlite3.connect(os.getenv("GIGBID_DB", str(RUNTIME / "app.sqlite3")), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute(conn, sql, args=()):
    return conn.execute(sql.replace("?", "%s") if os.getenv("DATABASE_URL") else sql, args)


def initialize():
    with connection() as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS documents (tenant TEXT NOT NULL, kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL, updated DOUBLE PRECISION NOT NULL, PRIMARY KEY(tenant,kind,id))"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS audit (id TEXT PRIMARY KEY, tenant TEXT NOT NULL, trace TEXT NOT NULL, body TEXT NOT NULL, created DOUBLE PRECISION NOT NULL)"
        )


def put(tenant, kind, key, body, conn=None):
    if conn is None:
        with connection() as c:
            return put(tenant, kind, key, body, c)
    execute(
        conn,
        "INSERT INTO documents(tenant,kind,id,body,updated) VALUES(?,?,?,?,?) ON CONFLICT(tenant,kind,id) DO UPDATE SET body=excluded.body, updated=excluded.updated",
        (tenant, kind, key, json.dumps(body), time.time()),
    )
    return body


def get(tenant, kind, key, conn=None):
    if conn is None:
        with connection() as c:
            return get(tenant, kind, key, c)
    row = execute(conn, "SELECT body FROM documents WHERE tenant=? AND kind=? AND id=?", (tenant, kind, key)).fetchone()
    return json.loads(row["body"]) if row else None


def scan(tenant, kind, conn=None):
    if conn is None:
        with connection() as c:
            return scan(tenant, kind, c)
    rows = execute(
        conn, "SELECT body FROM documents WHERE tenant=? AND kind=? ORDER BY updated DESC", (tenant, kind)
    ).fetchall()
    return [json.loads(r["body"]) for r in rows]


def delete(tenant, kind, key):
    with connection() as c:
        execute(c, "DELETE FROM documents WHERE tenant=? AND kind=? AND id=?", (tenant, kind, key))


def audit(tenant, trace, event):
    from core.security import mask

    with connection() as c:
        execute(
            c,
            "INSERT INTO audit(id,tenant,trace,body,created) VALUES(?,?,?,?,?)",
            (uuid.uuid4().hex, tenant, trace, json.dumps(mask(event)), time.time()),
        )


initialize()
