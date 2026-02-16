import json
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .exceptions import APIError


class QuantumPortfolioClient:
    """Thin SDK wrapper around the Quantum Portfolio API."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None):
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = Request(url, method=method, headers=headers, data=body)
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8") or "{}"
                return json.loads(raw)
        except HTTPError as e:
            raw = e.read().decode("utf-8") if hasattr(e, "read") else ""
            try:
                parsed = json.loads(raw) if raw else {}
                msg = parsed.get("error") or parsed.get("message") or raw
            except Exception:
                msg = raw or str(e)
            raise APIError(e.code, msg)
        except URLError as e:
            raise APIError(0, str(e))

    # Core endpoints
    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/api/health")

    def optimize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/api/portfolio/optimize", payload)

    def optimize_batch(self, requests: List[Dict[str, Any]], stop_on_error: bool = False) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/portfolio/optimize/batch",
            {"requests": requests, "stop_on_error": stop_on_error},
        )

    def backtest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/api/portfolio/backtest", payload)

    def efficient_frontier(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/api/portfolio/efficient-frontier", payload)

    # Async jobs
    def submit_optimize_job(self, payload: Dict[str, Any], webhook_url: Optional[str] = None) -> Dict[str, Any]:
        body = {"payload": payload}
        if webhook_url:
            body["webhook_url"] = webhook_url
        return self._request("POST", "/api/jobs/optimize", body)

    def submit_backtest_job(self, payload: Dict[str, Any], webhook_url: Optional[str] = None) -> Dict[str, Any]:
        body = {"payload": payload}
        if webhook_url:
            body["webhook_url"] = webhook_url
        return self._request("POST", "/api/jobs/backtest", body)

    def get_job(self, job_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/api/jobs/{job_id}")

