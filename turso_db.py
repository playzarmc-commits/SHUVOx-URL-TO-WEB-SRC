"""Turso (libSQL) storage over the HTTP pipeline API.

Only needs `requests` (already a dependency), so it works in Termux
without compiling any native libsql package.
All writes go through a background worker thread, so the bot's event
loop is never blocked by network calls.
"""

import json
import queue
import threading
import time

import requests

import config

TURSO_URL = str(getattr(config, "TURSO_URL", "")).strip()
TURSO_TOKEN = str(getattr(config, "TURSO_TOKEN", "")).strip()

# libsql://xyz.turso.io  ->  https://xyz.turso.io
_BASE = TURSO_URL.replace("libsql://", "https://", 1).rstrip("/")
_ENDPOINT = f"{_BASE}/v2/pipeline"
_HEADERS = {
    "Authorization": f"Bearer {TURSO_TOKEN}",
    "Content-Type": "application/json",
}

ENABLED = bool(TURSO_URL and TURSO_TOKEN)

_queue: "queue.Queue" = queue.Queue()
_worker_started = False
_lock = threading.Lock()


# ───────────────────────── low-level ─────────────────────────
def _arg(v):
    if v is None:
        return {"type": "null"}
    if isinstance(v, bool):
        return {"type": "integer", "value": str(int(v))}
    if isinstance(v, int):
        return {"type": "integer", "value": str(v)}
    return {"type": "text", "value": str(v)}


def _cell(c):
    if c is None or c.get("type") == "null":
        return None
    v = c.get("value")
    if c.get("type") == "integer":
        return int(v)
    return v


def execute_many(statements, timeout=30):
    """statements: list of (sql, args_list). Runs them in ONE HTTP request.
    Returns a list of row-lists (one per statement)."""
    reqs = [
        {"type": "execute", "stmt": {"sql": sql, "args": [_arg(a) for a in (args or [])]}}
        for sql, args in statements
    ]
    reqs.append({"type": "close"})
    r = requests.post(_ENDPOINT, headers=_HEADERS, json={"requests": reqs}, timeout=timeout)
    r.raise_for_status()
    out = []
    for res in r.json()["results"]:
        if res["type"] == "error":
            raise RuntimeError(res["error"].get("message", "Turso error"))
        if res["type"] == "ok" and res["response"]["type"] == "execute":
            result = res["response"]["result"]
            out.append([[_cell(c) for c in row] for row in result.get("rows", [])])
    return out


# ───────────────────────── background worker ─────────────────────────
def _worker():
    while True:
        statements = _queue.get()
        for attempt in range(3):
            try:
                execute_many(statements)
                break
            except Exception as e:
                print(f"⚠️ Turso write failed (try {attempt + 1}/3): {e}")
                time.sleep(2 * (attempt + 1))
        _queue.task_done()


def _ensure_worker():
    global _worker_started
    with _lock:
        if not _worker_started:
            threading.Thread(target=_worker, daemon=True).start()
            _worker_started = True


def enqueue(statements):
    """Fire-and-forget write (non-blocking)."""
    if not ENABLED:
        return
    _ensure_worker()
    _queue.put(statements)


# ───────────────────────── schema / load ─────────────────────────
def init_schema():
    execute_many([
        (
            "CREATE TABLE IF NOT EXISTS users ("
            "id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, "
            "joined TEXT, last_seen TEXT)",
            [],
        ),
        ("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)", []),
    ])


def load_all():
    """Returns (users_dict, stats_dict_or_None, force_join_list_or_None)."""
    res = execute_many([
        ("SELECT id, username, first_name, joined, last_seen FROM users", []),
        ("SELECT key, value FROM kv", []),
    ])
    users = {}
    for uid, username, first_name, joined, last_seen in res[0]:
        users[str(uid)] = {
            "id": uid,
            "username": username,
            "first_name": first_name,
            "joined": joined,
            "last_seen": last_seen,
        }
    kv = {k: v for k, v in res[1]}
    stats = json.loads(kv["stats"]) if "stats" in kv else None
    channels = json.loads(kv["force_join_channels"]) if "force_join_channels" in kv else None
    return users, stats, channels


# ───────────────────────── write helpers ─────────────────────────
_UPSERT_USER = (
    "INSERT INTO users (id, username, first_name, joined, last_seen) "
    "VALUES (?, ?, ?, ?, ?) "
    "ON CONFLICT(id) DO UPDATE SET username=excluded.username, "
    "first_name=excluded.first_name, last_seen=excluded.last_seen"
)
_UPSERT_KV = (
    "INSERT INTO kv (key, value) VALUES (?, ?) "
    "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
)


def upsert_user(u: dict):
    enqueue([(_UPSERT_USER, [u["id"], u.get("username"), u.get("first_name"),
                             u.get("joined"), u.get("last_seen")])])


def upsert_users_bulk(users: list, chunk=100):
    """Blocking bulk push (used once at startup for migration)."""
    for i in range(0, len(users), chunk):
        part = users[i:i + chunk]
        execute_many([
            (_UPSERT_USER, [u["id"], u.get("username"), u.get("first_name"),
                            u.get("joined"), u.get("last_seen")])
            for u in part
        ])


def delete_users(uids: list):
    if uids:
        enqueue([("DELETE FROM users WHERE id = ?", [int(u)]) for u in uids])


def set_kv(key: str, value):
    enqueue([(_UPSERT_KV, [key, json.dumps(value)])])
