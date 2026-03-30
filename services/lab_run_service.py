"""
Lab run persistence — SQLite CRUD for durable experiment runs.

Each run captures a frozen experiment spec, execution status, and result.
Runs survive server restarts (unlike in-memory _jobs dict).
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

VALID_STATUSES = ("queued", "running", "completed", "failed")
VALID_EXECUTION_KINDS = ("lab_sync", "async_optimize", "ibm_runtime")

_db_conn_factory: Optional[Callable] = None


def set_db_conn_factory(fn: Callable) -> None:
    global _db_conn_factory
    _db_conn_factory = fn


def _conn():
    if _db_conn_factory is None:
        raise RuntimeError("lab_run_service: db_conn_factory not configured")
    return _db_conn_factory()


def ensure_table() -> None:
    conn = _conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lab_runs (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                execution_kind TEXT NOT NULL DEFAULT 'async_optimize',
                spec_json TEXT NOT NULL,
                result_json TEXT,
                error TEXT,
                external_job_id TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_lab_runs_tenant ON lab_runs(tenant_id)"
        )
        conn.commit()
        _migrate_add_payload_column(conn)
    finally:
        conn.close()


def _migrate_add_payload_column(conn) -> None:
    """Add payload_json column to persist full optimize request body (returns, covariance, tickers)."""
    try:
        cur = conn.execute("PRAGMA table_info(lab_runs)")
        cols = {row[1] for row in cur.fetchall()}
        if "payload_json" not in cols:
            conn.execute("ALTER TABLE lab_runs ADD COLUMN payload_json TEXT")
            conn.commit()
            logger.info("lab_runs: added payload_json column")
    except Exception as exc:
        logger.warning("lab_runs migrate payload_json failed: %s", exc)


_PAYLOAD_STRIP_KEYS = frozenset({"__api_key", "api_key", "password", "token"})


def sanitize_request_payload(payload: dict) -> dict:
    """Strip sensitive keys before persisting a raw optimize request payload."""
    return {k: v for k, v in payload.items() if k not in _PAYLOAD_STRIP_KEYS}


def create_run(
    tenant_id: str,
    spec: dict[str, Any],
    execution_kind: str = "async_optimize",
    *,
    request_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if execution_kind not in VALID_EXECUTION_KINDS:
        raise ValueError(f"Invalid execution_kind: {execution_kind}")
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    sanitized_payload = (
        sanitize_request_payload(request_payload)
        if request_payload is not None
        else None
    )
    row = {
        "id": run_id,
        "tenant_id": tenant_id,
        "status": "queued",
        "execution_kind": execution_kind,
        "spec_json": json.dumps(spec),
        "result_json": None,
        "error": None,
        "external_job_id": None,
        "payload_json": json.dumps(sanitized_payload) if sanitized_payload is not None else None,
        "created_at": now,
        "started_at": None,
        "finished_at": None,
    }
    conn = _conn()
    try:
        conn.execute(
            """
            INSERT INTO lab_runs (id, tenant_id, status, execution_kind,
                spec_json, result_json, error, external_job_id, payload_json,
                created_at, started_at, finished_at)
            VALUES (:id, :tenant_id, :status, :execution_kind,
                :spec_json, :result_json, :error, :external_job_id, :payload_json,
                :created_at, :started_at, :finished_at)
            """,
            row,
        )
        conn.commit()
    finally:
        conn.close()
    logger.info("run_created run_id=%s tenant=%s kind=%s", run_id, tenant_id, execution_kind)
    row["spec"] = spec
    if sanitized_payload is not None:
        row["payload"] = sanitized_payload
    return row


def update_status(
    run_id: str,
    status: str,
    *,
    result: dict | None = None,
    error: str | None = None,
    external_job_id: str | None = None,
) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    now = datetime.now(timezone.utc).isoformat()
    conn = _conn()
    try:
        fields = ["status = ?"]
        params: list[Any] = [status]
        if status == "running":
            fields.append("started_at = ?")
            params.append(now)
        if status in ("completed", "failed"):
            fields.append("finished_at = ?")
            params.append(now)
        if result is not None:
            fields.append("result_json = ?")
            params.append(json.dumps(result))
        if error is not None:
            fields.append("error = ?")
            params.append(error)
        if external_job_id is not None:
            fields.append("external_job_id = ?")
            params.append(external_job_id)
        params.append(run_id)
        conn.execute(
            f"UPDATE lab_runs SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        conn.commit()
    finally:
        conn.close()
    logger.info("run_%s run_id=%s", status, run_id)


def get_run(run_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    conn = _conn()
    try:
        conn.row_factory = _dict_factory
        if tenant_id:
            row = conn.execute(
                "SELECT * FROM lab_runs WHERE id = ? AND tenant_id = ?",
                (run_id, tenant_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM lab_runs WHERE id = ?", (run_id,)
            ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return _inflate(row)


def list_runs(tenant_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 100))
    conn = _conn()
    try:
        conn.row_factory = _dict_factory
        rows = conn.execute(
            "SELECT * FROM lab_runs WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, lim),
        ).fetchall()
    finally:
        conn.close()
    return [_inflate(r) for r in rows]


def _dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _inflate(row: dict) -> dict:
    for key in ("spec_json", "result_json", "payload_json"):
        val = row.pop(key, None)
        if key == "payload_json":
            row["payload"] = json.loads(val) if val else None
        else:
            out_key = key.replace("_json", "")
            row[out_key] = json.loads(val) if val else None
    return row
