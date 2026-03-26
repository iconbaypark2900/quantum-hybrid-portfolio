"""
IBM Quantum service — per-tenant in-memory service cache + SQLite persistence.

qiskit-ibm-runtime is an optional dependency. All public functions degrade
gracefully if it is not installed, returning {"ok": False, "error": "..."}.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def resolve_tenant(explicit: Optional[str] = None) -> str:
    """Resolve tenant for IBM: explicit > static API_KEY + X-Tenant-Id > g.tenant_id > default."""
    if explicit:
        return explicit
    try:
        import os

        from flask import g, has_request_context, request

        if has_request_context():
            api_key = os.getenv("API_KEY", "")
            client_key = request.headers.get("X-API-Key", "")
            if api_key and client_key == api_key:
                h = (request.headers.get("X-Tenant-Id") or "").strip()
                if h:
                    return h
            tid = getattr(g, "tenant_id", None)
            if tid and tid not in ("anonymous", None, ""):
                return str(tid)
    except Exception:
        pass
    return "default"

_lock = threading.Lock()
# tenant_id -> (QiskitRuntimeService | None, token str)
_services: dict[str, tuple[Optional[object], Optional[str]]] = {}

_db_conn_factory: Optional[Callable[[], object]] = None


def set_db_conn_factory(fn: Callable[[], object]) -> None:
    """Called from api.py to enable persistence."""
    global _db_conn_factory
    _db_conn_factory = fn


def _persist_token(tenant_id: str, token: str) -> None:
    if not _db_conn_factory:
        return
    try:
        from services import tenant_integrations as ti

        ti.save_secret(_db_conn_factory, tenant_id, "ibm", token)
    except Exception as exc:
        logger.warning("IBM token persist failed: %s", exc)


def _load_token(tenant_id: str) -> Optional[str]:
    if not _db_conn_factory:
        return None
    try:
        from services import tenant_integrations as ti

        row = ti.load_secret(_db_conn_factory, tenant_id, "ibm")
        return row[0] if row else None
    except Exception as exc:
        logger.warning("IBM token load failed: %s", exc)
        return None


def _clear_persisted(tenant_id: str) -> None:
    if not _db_conn_factory:
        return
    try:
        from services import tenant_integrations as ti

        ti.delete_secret(_db_conn_factory, tenant_id, "ibm")
    except Exception as exc:
        logger.warning("IBM token delete failed: %s", exc)


def set_token(tenant_id: str, token: str) -> dict:
    """
    Store an IBM Quantum API token for tenant_id and verify connectivity.

    Returns {"ok": True, "backends": [...]} on success or
            {"ok": False, "error": "..."} on failure.
    """
    token = (token or "").strip()
    if not token:
        return {"ok": False, "error": "Token is empty"}

    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError:
        return {
            "ok": False,
            "error": "qiskit-ibm-runtime is not installed. "
            "Run: pip install qiskit qiskit-ibm-runtime",
        }

    try:
        svc = QiskitRuntimeService(channel="ibm_quantum_platform", token=token)
        backends = [b.name for b in svc.backends()]
    except Exception as exc:
        logger.warning("IBM Quantum token rejected: %s", exc)
        return {"ok": False, "error": str(exc)}

    with _lock:
        _services[tenant_id] = (svc, token)

    _persist_token(tenant_id, token)

    logger.info(
        "IBM Quantum token accepted tenant=%s — %d backends: %s",
        tenant_id,
        len(backends),
        backends,
    )
    return {"ok": True, "backends": backends}


def ensure_loaded(tenant_id: str) -> None:
    """Lazy-load token from DB into memory if missing (no duplicate persist)."""
    with _lock:
        if tenant_id in _services and _services[tenant_id][0] is not None:
            return
    tok = _load_token(tenant_id)
    if not tok:
        return
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError:
        return
    try:
        svc = QiskitRuntimeService(channel="ibm_quantum_platform", token=tok)
        with _lock:
            _services[tenant_id] = (svc, tok)
    except Exception as exc:
        logger.warning("IBM lazy load failed tenant=%s: %s", tenant_id, exc)


def get_service(tenant_id: Optional[str] = None):
    """Return cached QiskitRuntimeService for tenant (Flask g if omitted), or None."""
    tid = resolve_tenant(tenant_id)
    ensure_loaded(tid)
    with _lock:
        t = _services.get(tid)
        return t[0] if t else None


def is_configured(tenant_id: Optional[str] = None) -> bool:
    tid = resolve_tenant(tenant_id)
    ensure_loaded(tid)
    with _lock:
        t = _services.get(tid)
        return t is not None and t[0] is not None


def get_status(tenant_id: str) -> dict:
    """
    Return connection status for tenant_id.

    {"configured": bool, "backends": [...], "tenant_id": str, "error": str?}
    """
    ensure_loaded(tenant_id)
    with _lock:
        t = _services.get(tenant_id)
        svc = t[0] if t else None

    if svc is None:
        return {
            "configured": False,
            "backends": [],
            "tenant_id": tenant_id,
        }

    try:
        backends = [b.name for b in svc.backends()]
        return {"configured": True, "backends": backends, "tenant_id": tenant_id}
    except Exception as exc:
        logger.warning("IBM Quantum status check failed: %s", exc)
        return {
            "configured": False,
            "backends": [],
            "tenant_id": tenant_id,
            "error": str(exc),
        }


def clear_token(tenant_id: str) -> None:
    """Remove token for tenant from memory and DB."""
    with _lock:
        if tenant_id in _services:
            del _services[tenant_id]
    _clear_persisted(tenant_id)
    logger.info("IBM Quantum token cleared tenant=%s", tenant_id)


def _runtime_job_to_dict(job: Any) -> dict[str, Any]:
    """Extract JSON-friendly fields from a qiskit-ibm-runtime RuntimeJob (V2)."""
    row: dict[str, Any] = {}
    try:
        jid = job.job_id()
        row["job_id"] = str(jid)
    except Exception:
        row["job_id"] = None

    try:
        st = job.status()
        row["status"] = st if isinstance(st, str) else str(st)
    except Exception as exc:
        row["status"] = None
        row["status_error"] = str(exc)

    try:
        b = job.backend()
        if b is not None:
            row["backend"] = getattr(b, "name", None) or str(b)
        else:
            row["backend"] = None
    except Exception:
        row["backend"] = None

    try:
        cd = job.creation_date
        if isinstance(cd, datetime):
            row["created"] = cd.isoformat()
        elif cd is not None:
            row["created"] = str(cd)
        else:
            row["created"] = None
    except Exception:
        row["created"] = None

    try:
        u = job.usage()
        row["usage_seconds"] = float(u) if u is not None else None
    except Exception:
        row["usage_seconds"] = None

    try:
        inst = job.instance
        row["instance"] = inst if isinstance(inst, str) else None
    except Exception:
        row["instance"] = None

    try:
        pid = getattr(job, "primitive_id", None)
        if pid is not None:
            row["program_id"] = str(pid)
    except Exception:
        pass

    return row


def list_runtime_workloads(tenant_id: str, *, limit: int = 20) -> dict:
    """
    List recent IBM Quantum Runtime jobs for the tenant's stored API token.

    Requires qiskit-ibm-runtime. Uses QiskitRuntimeService.jobs(limit=...).

    Returns a stable dict for the API layer:
        ok, configured, workloads (list of dicts), tenant_id, error (optional).
    """
    lim = max(1, min(int(limit), 100))

    try:
        from qiskit_ibm_runtime import QiskitRuntimeService  # noqa: F401
    except ImportError:
        return {
            "ok": False,
            "configured": False,
            "workloads": [],
            "tenant_id": tenant_id,
            "error": "qiskit-ibm-runtime is not installed. "
            "Run: pip install qiskit qiskit-ibm-runtime",
        }

    ensure_loaded(tenant_id)
    with _lock:
        t = _services.get(tenant_id)
        svc = t[0] if t else None

    if svc is None:
        return {
            "ok": False,
            "configured": False,
            "workloads": [],
            "tenant_id": tenant_id,
            "error": "IBM Quantum not configured for this tenant",
        }

    try:
        jobs = svc.jobs(limit=lim, descending=True)
        workloads = [_runtime_job_to_dict(j) for j in jobs]
        return {
            "ok": True,
            "configured": True,
            "workloads": workloads,
            "tenant_id": tenant_id,
        }
    except Exception as exc:
        logger.warning("IBM Quantum workloads list failed tenant=%s: %s", tenant_id, exc)
        return {
            "ok": False,
            "configured": True,
            "workloads": [],
            "tenant_id": tenant_id,
            "error": str(exc),
        }
