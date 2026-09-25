"""SQLite-backed knowledge store: connection, migrations, transactions, audit.

Why SQLite (stdlib ``sqlite3``) and not a new database service
--------------------------------------------------------------
Visable's production backend has no database today (see
docs/ai/WAYMAKER_KNOWLEDGE_PLATFORM.md §Storage). SQLite gives the knowledge
layer real relational integrity — foreign keys, CHECK constraints, partial
unique indexes, triggers, transactions — with zero new dependencies and no new
infrastructure. The schema is written in the portable subset so a PostgreSQL
port is mechanical once one exists.

Durability contract
-------------------
* ``WAYMAKER_KNOWLEDGE_DB`` sets the database path. On Railway it must point at
  a mounted volume for operator edits to survive a redeploy.
* ``:memory:`` is supported (tests; last-resort fallback).
* If the configured path cannot be opened, the store falls back to an
  in-memory database and reports ``durable=False`` so the operator UI can say
  so. Runtime answers keep working because the seed is re-applied.

Thread-safety: one connection guarded by an ``RLock``. Knowledge writes are
rare operator actions; reads are cached by the retrieval layer.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

logger = logging.getLogger("paradiso.knowledge")

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = _BACKEND_DIR / "var" / "knowledge" / "waymaker_knowledge.sqlite3"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def stable_hash(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def configured_db_path() -> str:
    return os.environ.get("WAYMAKER_KNOWLEDGE_DB", "").strip() or str(DEFAULT_DB_PATH)


class KnowledgeStore:
    """A migrated SQLite database plus transaction and audit helpers."""

    def __init__(self, path: Optional[str] = None):
        self.requested_path = path or configured_db_path()
        self._lock = threading.RLock()
        self.durable = True
        self.open_error = ""
        self.conn = self._open(self.requested_path)
        self.apply_migrations()

    # -- connection -----------------------------------------------------------
    def _open(self, path: str) -> sqlite3.Connection:
        if path == ":memory:":
            self.durable = False
            return self._connect(":memory:")
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            return self._connect(path)
        except (OSError, sqlite3.Error) as exc:  # read-only FS, bad path, ...
            logger.warning("knowledge_store_open_failed path_configured=%s error=%s — using in-memory store",
                           bool(os.environ.get("WAYMAKER_KNOWLEDGE_DB")), type(exc).__name__)
            self.durable = False
            self.open_error = type(exc).__name__
            return self._connect(":memory:")

    @staticmethod
    def _connect(path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if path != ":memory:":
            with contextlib.suppress(sqlite3.Error):
                conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    # -- migrations -------------------------------------------------------------
    def apply_migrations(self) -> List[str]:
        """Apply pending ``migrations/NNNN_*.sql`` in order. Returns applied ids.

        Additive only. A migration whose checksum changed after being applied is
        a hard error: applied migrations are immutable history.
        """
        applied: List[str] = []
        with self._lock:
            self.conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " version TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)"
            )
            done = {r["version"]: r["checksum"] for r in self.conn.execute("SELECT * FROM schema_migrations")}
            for path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
                sql = path.read_text(encoding="utf-8")
                checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
                version = path.stem
                if version in done:
                    if done[version] != checksum:
                        raise RuntimeError(f"applied migration {version} was modified (checksum mismatch)")
                    continue
                self.conn.execute("BEGIN IMMEDIATE")
                try:
                    for statement in _split_sql(sql):
                        self.conn.execute(statement)
                    self.conn.execute(
                        "INSERT INTO schema_migrations(version, checksum, applied_at) VALUES (?,?,?)",
                        (version, checksum, utc_now()),
                    )
                    self.conn.execute("COMMIT")
                except Exception:
                    self.conn.execute("ROLLBACK")
                    raise
                applied.append(version)
                logger.info("knowledge_migration_applied version=%s", version)
        return applied

    def schema_version(self) -> str:
        row = self.one("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1")
        return row["version"] if row else ""

    # -- queries ----------------------------------------------------------------
    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """All-or-nothing unit of work (BEGIN IMMEDIATE ... COMMIT/ROLLBACK).

        Nested use joins the outer transaction.
        """
        with self._lock:
            if self.conn.in_transaction:
                yield self.conn
                return
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self.conn
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
            else:
                self.conn.execute("COMMIT")

    def one(self, sql: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        with self._lock:
            return self.conn.execute(sql, tuple(params)).fetchone()

    def all(self, sql: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        with self._lock:
            return list(self.conn.execute(sql, tuple(params)).fetchall())

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self.conn.execute(sql, tuple(params))

    def revision(self) -> str:
        """A cheap token that changes whenever knowledge-relevant rows change.

        Used as the retrieval cache key, so a publish invalidates cached answers
        without any explicit cache plumbing.
        """
        row = self.one(
            "SELECT (SELECT COUNT(*) FROM audit_log) AS a,"
            " (SELECT COALESCE(MAX(at), '') FROM audit_log) AS b,"
            " (SELECT COUNT(*) FROM knowledge_facts) AS c"
        )
        return f"{row['a']}:{row['b']}:{row['c']}" if row else "0"

    # -- audit --------------------------------------------------------------------
    def audit(
        self,
        *,
        actor: str,
        actor_kind: str,
        entity_type: str,
        entity_id: str,
        action: str,
        reason: str = "",
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
    ) -> str:
        audit_id = new_id("aud")
        self.execute(
            "INSERT INTO audit_log(audit_id, at, actor, actor_kind, entity_type, entity_id, action,"
            " reason, before_json, after_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (audit_id, utc_now(), actor, actor_kind, entity_type, entity_id, action, reason or "",
             json.dumps(before or {}, ensure_ascii=False, sort_keys=True),
             json.dumps(after or {}, ensure_ascii=False, sort_keys=True)),
        )
        return audit_id


def _split_sql(sql: str) -> List[str]:
    """Split a migration into statements, keeping trigger bodies intact."""
    statements: List[str] = []
    buf: List[str] = []
    in_trigger = False
    for raw in sql.splitlines():
        line = raw.split("--", 1)[0] if not raw.strip().startswith("--") else ""
        if not line.strip():
            continue
        buf.append(line)
        upper = line.strip().upper()
        if upper.startswith("CREATE TRIGGER"):
            in_trigger = True
        if in_trigger:
            if upper.endswith("END;"):
                statements.append("\n".join(buf))
                buf, in_trigger = [], False
            continue
        if line.rstrip().endswith(";"):
            statements.append("\n".join(buf))
            buf = []
    if buf and "".join(buf).strip():
        statements.append("\n".join(buf))
    return [s for s in statements if s.strip() and not s.strip().upper().startswith("PRAGMA")]


def row_dict(row: Optional[sqlite3.Row], *, json_fields: Sequence[str] = ()) -> Dict[str, Any]:
    if row is None:
        return {}
    out = dict(row)
    for key in json_fields:
        if key in out and isinstance(out[key], str):
            try:
                out[key] = json.loads(out[key])
            except ValueError:
                pass
    return out
