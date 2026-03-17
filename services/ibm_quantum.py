"""
IBM Quantum service — in-memory token storage and runtime service management.

qiskit-ibm-runtime is an optional dependency. All public functions degrade
gracefully if it is not installed, returning {"ok": False, "error": "..."}.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_token: Optional[str] = None
_service = None   # QiskitRuntimeService instance, lazily created on set_token()


def set_token(token: str) -> dict:
    """
    Store an IBM Quantum token and verify it by connecting to the service.

    Returns {"ok": True, "backends": [...]} on success or
            {"ok": False, "error": "..."} on failure.
    """
    global _token, _service

    token = token.strip()
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
        svc = QiskitRuntimeService(channel="ibm_quantum", token=token)
        backends = [b.name for b in svc.backends()]
    except Exception as exc:
        logger.warning("IBM Quantum token rejected: %s", exc)
        return {"ok": False, "error": str(exc)}

    with _lock:
        _token = token
        _service = svc

    logger.info(
        "IBM Quantum token accepted — %d backends available: %s",
        len(backends), backends,
    )
    return {"ok": True, "backends": backends}


def get_service():
    """Return the cached QiskitRuntimeService, or None if not configured."""
    with _lock:
        return _service


def is_configured() -> bool:
    """Return True if a valid IBM Quantum token has been set."""
    with _lock:
        return _service is not None


def get_status() -> dict:
    """
    Return connection status for the status endpoint.

    {"configured": bool, "backends": [...], "error": str (on failure)}
    """
    with _lock:
        svc = _service

    if svc is None:
        return {"configured": False, "backends": []}

    try:
        backends = [b.name for b in svc.backends()]
        return {"configured": True, "backends": backends}
    except Exception as exc:
        logger.warning("IBM Quantum status check failed: %s", exc)
        return {"configured": False, "backends": [], "error": str(exc)}


def clear_token() -> None:
    """Remove the stored token and service instance."""
    global _token, _service
    with _lock:
        _token = None
        _service = None
    logger.info("IBM Quantum token cleared")
