"""Format `/api/portfolio/optimize` JSON for Gradio Markdown / Dataframe."""
from __future__ import annotations

import json
from typing import Any

# Tickers aligned with `web/src/lib/defaultUniverse.ts` and smoke presets
PRESET_MAG7_JPM = "AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA,JPM"
PRESET_DEFAULT_10 = "AAPL,MSFT,GOOGL,AMZN,NVDA,JPM,JNJ,PG,V,UNH"


def _pct(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{100.0 * float(x):.2f}%"


def _num(x: Any, nd: int = 4) -> str:
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return "—"


def format_session_strip(
    objective: str,
    mode_label: str,
    n_universe: int,
    weight_min: float,
    weight_max: float,
) -> str:
    obj = (objective or "hybrid").replace("_", " ").title()
    return (
        f"`SESSION` **{obj}** · {n_universe} tickers ({mode_label}) · "
        f"wt {weight_min:.3f}–{weight_max:.2f}"
    )


def format_optimize_result(body: Any) -> dict[str, Any]:
    """
    Returns keys: ok, err, kpi_html, holdings_headers, holdings_rows,
    sector_headers, sector_rows, perf_md, risk_md, raw_json
    """
    out: dict[str, Any] = {
        "ok": False,
        "err": "",
        "kpi_html": "",
        "holdings_headers": ["Name", "Sector", "Weight %"],
        "holdings_rows": [],
        "sector_headers": ["Sector", "Weight %"],
        "sector_rows": [],
        "perf_md": "",
        "risk_md": "",
        "sensitivity_md": "",
        "raw_json": "",
    }
    if body is None:
        out["err"] = "Empty response"
        out["kpi_html"] = '<p class="ql-lite-err">Empty response</p>'
        return out
    if isinstance(body, str):
        out["err"] = body[:2000]
        out["raw_json"] = body[:8000]
        out["kpi_html"] = f'<p class="ql-lite-err">{body[:500]}</p>'
        return out
    if not isinstance(body, dict):
        out["err"] = "Unexpected response type"
        out["raw_json"] = json.dumps(body, default=str, indent=2)[:8000]
        return out

    out["raw_json"] = json.dumps(body, indent=2, default=str)

    # HTTP / Flask error shapes (success payload has weights / sharpe_ratio / holdings)
    if "status" in body and "body" in body:
        inner = body.get("body")
        out["err"] = json.dumps(inner, indent=2) if isinstance(inner, (dict, list)) else str(inner)[:4000]
        out["kpi_html"] = f'<pre class="ql-lite-err">{out["err"][:3000]}</pre>'
        return out
    if "error" in body and "sharpe_ratio" not in body and "weights" not in body:
        err = body.get("error")
        out["err"] = json.dumps(err, indent=2) if not isinstance(err, str) else err
        out["kpi_html"] = f'<pre class="ql-lite-err">{out["err"][:3000]}</pre>'
        return out

    sharpe = body.get("sharpe_ratio")
    exp_ret = body.get("expected_return")
    vol = body.get("volatility")
    n_active = body.get("n_active")
    rm = body.get("risk_metrics") or {}
    var_95 = rm.get("var_95")

    kpi = f"""
<div class="ql-lite-kpi">
  <div class="ql-lite-kpi-card"><span class="ql-lite-kpi-label">Sharpe</span><span class="ql-lite-kpi-val">{_num(sharpe, 3)}</span></div>
  <div class="ql-lite-kpi-card ql-lite-accent"><span class="ql-lite-kpi-label">E[R]</span><span class="ql-lite-kpi-val">{_pct(exp_ret)}</span></div>
  <div class="ql-lite-kpi-card"><span class="ql-lite-kpi-label">Vol</span><span class="ql-lite-kpi-val">{_pct(vol)}</span></div>
  <div class="ql-lite-kpi-card"><span class="ql-lite-kpi-label">Active</span><span class="ql-lite-kpi-val">{int(n_active) if n_active is not None else '—'}</span></div>
  <div class="ql-lite-kpi-card ql-lite-var"><span class="ql-lite-kpi-label">VaR (95%)</span><span class="ql-lite-kpi-val">{_pct(var_95)}</span></div>
</div>
"""
    out["kpi_html"] = kpi
    out["ok"] = True

    holdings = body.get("holdings") or []
    rows = []
    for h in holdings:
        if not isinstance(h, dict):
            continue
        w = float(h.get("weight", 0))
        rows.append([h.get("name", ""), h.get("sector", ""), round(100.0 * w, 2)])
    rows.sort(key=lambda r: -r[2])
    out["holdings_rows"] = rows

    sectors = body.get("sector_allocation") or []
    srows = []
    for s in sectors:
        if isinstance(s, dict):
            w = float(s.get("weight", 0))
            srows.append([s.get("sector", ""), round(100.0 * w, 2)])
    srows.sort(key=lambda r: -r[1])
    out["sector_rows"] = srows

    benchmarks = body.get("benchmarks") or {}
    if benchmarks:
        lines = ["| Benchmark | Sharpe | E[R] | Vol |", "|---|---:|---:|---:|"]
        for name, b in benchmarks.items():
            if not isinstance(b, dict):
                continue
            lines.append(
                f"| {name} | {_num(b.get('sharpe'), 3)} | {_pct(b.get('expected_return'))} | {_pct(b.get('volatility'))} |"
            )
        out["perf_md"] = "**Benchmarks (classical references)**\n\n" + "\n".join(lines)
    else:
        out["perf_md"] = "*No benchmark block in response (classical fallbacks may be unavailable).*"

    risk_lines = [
        f"- **Annualized volatility:** {_pct(vol)}  (√(w′Σw))",
        f"- **VaR (95%, normal approx.):** {_pct(var_95)}",
        f"- **Active positions (above floor):** {n_active}",
        "",
        "**Sector allocation** — see table on Portfolio tab or rows below.",
    ]
    if srows:
        risk_lines.append("")
        risk_lines.append("| Sector | Weight % |")
        risk_lines.append("|---:|---:|")
        for name, wt in srows:
            risk_lines.append(f"| {name} | {wt:.2f} |")
    out["risk_md"] = "\n".join(risk_lines)

    out["sensitivity_md"] = (
        "**Sensitivity (lite)**\n\n"
        "Full marginal analysis lives in the Next.js app. "
        "Here, re-run **Portfolio Lab** with different `weight_min` / `maxWeight` / regime / objective "
        "to compare scenarios side-by-side (export raw JSON below if needed)."
    )

    return out
