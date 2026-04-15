"""HTTP helpers for Gradio lite — same Flask API as Next.js `web/`."""
from __future__ import annotations

from typing import Any

import requests

OPT_TIMEOUT = 300.0
IBM_TIMEOUT = 180.0


def unwrap_envelope(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload and "meta" in payload:
        return payload.get("data")
    return payload


def build_headers(api_key: str, tenant_id: str) -> dict[str, str]:
    h: dict[str, str] = {"Content-Type": "application/json"}
    if api_key.strip():
        h["X-API-Key"] = api_key.strip()
    tid = tenant_id.strip()
    if tid:
        h["X-Tenant-Id"] = tid
    return h


def api_request(
    method: str,
    base: str,
    path: str,
    api_key: str,
    tenant_id: str,
    json_body: dict | None = None,
    timeout: float = 60.0,
) -> tuple[bool, Any]:
    url = f"{base.rstrip('/')}{path}"
    try:
        r = requests.request(
            method,
            url,
            headers=build_headers(api_key, tenant_id),
            json=json_body,
            timeout=timeout,
        )
        try:
            body = r.json()
        except Exception:
            body = r.text[:8000]
        if r.status_code >= 400:
            return False, {"status": r.status_code, "body": body}
        return True, unwrap_envelope(body)
    except requests.RequestException as e:
        return False, str(e)


def fetch_objective_ids(base: str, api_key: str, tenant_id: str) -> list[str]:
    ok, body = api_request("GET", base, "/api/config/objectives", api_key, tenant_id, timeout=30.0)
    if not ok:
        return [
            "hybrid",
            "markowitz",
            "min_variance",
            "hrp",
            "qubo_sa",
            "qaoa",
            "vqe",
            "hybrid_qaoa",
        ]
    objs = (body or {}).get("objectives") or []
    ids = [o.get("id") for o in objs if isinstance(o, dict) and o.get("id")]
    return ids or ["hybrid"]


def fetch_tenants(base: str, api_key: str, tenant_id: str) -> list[tuple[str, str]]:
    """Return [(id, label), ...] for dropdown."""
    ok, body = api_request("GET", base, "/api/config/tenants", api_key, tenant_id, timeout=30.0)
    if not ok:
        return [("default", "Default")]
    rows = (body or {}).get("tenants") or []
    out: list[tuple[str, str]] = []
    for t in rows:
        if isinstance(t, dict) and t.get("id"):
            tid = str(t["id"])
            label = str(t.get("label") or tid)
            out.append((tid, label))
    return out or [("default", "Default")]


def ibm_workloads(base: str, api_key: str, tenant_id: str, limit: int = 20) -> tuple[bool, Any]:
    return api_request(
        "GET",
        base,
        f"/api/config/ibm-quantum/workloads?limit={limit}",
        api_key,
        tenant_id,
        timeout=60.0,
    )
