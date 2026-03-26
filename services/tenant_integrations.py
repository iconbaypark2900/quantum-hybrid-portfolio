"""
Persist integration secrets per tenant (IBM Quantum token, Braket metadata).

Secrets are stored encrypted at rest when INTEGRATION_ENCRYPTION_KEY is set (32-byte
url-safe base64 for Fernet); otherwise stored as base64 (dev-only fallback).
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import sqlite3
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Lazy Fernet
_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet
    key = os.environ.get("INTEGRATION_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        # Accept raw 32-byte urlsafe b64 key or derive from string
        if len(key) < 32:
            key = base64.urlsafe_b64encode(
                hashlib.sha256(key.encode()).digest()
            ).decode()
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as exc:
        logger.warning("Fernet unavailable: %s", exc)
        _fernet = False
    return _fernet if _fernet is not False else None


def _enc(plain: str) -> str:
    f = _get_fernet()
    if f:
        return f.encrypt(plain.encode()).decode()
    return base64.b64encode(plain.encode()).decode()


def _dec(blob: str) -> str:
    f = _get_fernet()
    if f:
        return f.decrypt(blob.encode()).decode()
    return base64.b64decode(blob.encode()).decode()


def save_secret(
    conn_factory,
    tenant_id: str,
    provider: str,
    secret_plain: str,
    metadata: Optional[dict] = None,
) -> None:
    """Upsert secret for tenant+provider."""
    conn = conn_factory()
    try:
        cur = conn.cursor()
        meta_json = json.dumps(metadata or {})
        cur.execute(
            """
            INSERT INTO tenant_integration_secrets (tenant_id, provider, secret_enc, metadata_json, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(tenant_id, provider) DO UPDATE SET
                secret_enc = excluded.secret_enc,
                metadata_json = excluded.metadata_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (tenant_id, provider, _enc(secret_plain), meta_json),
        )
        conn.commit()
    finally:
        conn.close()


def load_secret(
    conn_factory,
    tenant_id: str,
    provider: str,
) -> Optional[tuple[str, Optional[dict]]]:
    """Return (plain_secret, metadata) or None."""
    conn = conn_factory()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT secret_enc, metadata_json FROM tenant_integration_secrets
            WHERE tenant_id = ? AND provider = ?
            """,
            (tenant_id, provider),
        )
        row = cur.fetchone()
        if not row:
            return None
        enc, meta_raw = row[0], row[1]
        meta = json.loads(meta_raw) if meta_raw else None
        return (_dec(enc), meta)
    except Exception as exc:
        logger.warning("load_secret failed: %s", exc)
        return None
    finally:
        conn.close()


def delete_secret(conn_factory, tenant_id: str, provider: str) -> None:
    conn = conn_factory()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM tenant_integration_secrets WHERE tenant_id = ? AND provider = ?",
            (tenant_id, provider),
        )
        conn.commit()
    finally:
        conn.close()


def list_tenant_ids(conn_factory) -> list[str]:
    conn = conn_factory()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT tenant_id FROM api_keys WHERE is_active = 1")
        rows = [r[0] for r in cur.fetchall() if r[0]]
        out = sorted(set(rows) | {"default"})
        return out
    except Exception:
        return ["default"]
    finally:
        conn.close()


def save_braket_metadata(
    conn_factory,
    tenant_id: str,
    metadata: dict[str, Any],
) -> None:
    """Store non-secret Braket preference JSON (credentials stay in env / IAM)."""
    conn = conn_factory()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tenant_integration_secrets (tenant_id, provider, secret_enc, metadata_json, updated_at)
            VALUES (?, 'braket', '-', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(tenant_id, provider) DO UPDATE SET
                metadata_json = excluded.metadata_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (tenant_id, json.dumps(metadata)),
        )
        conn.commit()
    finally:
        conn.close()


def load_braket_metadata(conn_factory, tenant_id: str) -> Optional[dict]:
    conn = conn_factory()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT metadata_json FROM tenant_integration_secrets
            WHERE tenant_id = ? AND provider = 'braket'
            """,
            (tenant_id,),
        )
        row = cur.fetchone()
        if not row or not row[0]:
            return None
        return json.loads(row[0])
    except Exception:
        return None
    finally:
        conn.close()
