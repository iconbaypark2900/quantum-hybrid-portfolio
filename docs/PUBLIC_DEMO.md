# Public demo

This project is suitable as a **public, browser-based demo**: visitors can explore quantum-inspired portfolio allocation and backtesting without installing anything when you host it (for example on [Hugging Face Spaces](HUGGINGFACE_SPACES.md)).

## Audience

- **Researchers and students** who want a hands-on feel for hybrid / QUBO-style allocation vs classical baselines.
- **Conference or portfolio** visitors who need a **single URL** and a short, clear story.

## What to show in ~60 seconds

1. **Data mode** — Switch between **LIVE** (market data via the API) and **SIM** (synthetic regimes) using the header controls.
2. **Optimize** — Set tickers and dates (Live) or regime (Sim), choose an objective, run optimization.
3. **Interpret** — Holdings, performance, risk tabs; use the efficient frontier and comparison charts when available.

For full UI detail, see **[DASHBOARD_GUIDE.md](DASHBOARD_GUIDE.md)**.

## Disclaimer

**This software is for research, education, and demonstration only.** It is **not** investment, tax, or legal advice. Past performance and backtests do not guarantee future results. Market data may be delayed or incomplete. You are responsible for decisions made using this tool.

## Hosting

| Topic | Document |
|--------|----------|
| Hugging Face Spaces (Docker, port 7860) | [HUGGINGFACE_SPACES.md](HUGGINGFACE_SPACES.md) |
| HF lite venture + roadmap (tiers, phases) | [HF_VENTURE.md](HF_VENTURE.md), [HF_LITE_ROADMAP.md](HF_LITE_ROADMAP.md) |
| Local run (API + dashboard) | [GETTING_STARTED.md](GETTING_STARTED.md) |
| Root overview | [README.md](../README.md) |

## Operational expectations

- **Cold starts** — Free tier hosts may sleep; first load can be slow.
- **Rate limits** — Configure sensible limits for anonymous traffic (see `.env.example` and API guides).
- **Market data** — Live data depends on Yahoo Finance / backend; failures should degrade gracefully (cached or sample data if you implement that path).
- **Secrets** — Do not expose IBM Quantum or cloud API keys in the UI; keep them server-side or disabled in public demos.

## Related

- **[API_PRODUCT_GUIDE.md](API_PRODUCT_GUIDE.md)** — Integration patterns when exposing the API publicly.
- **[frontend/frontend-guide.md](frontend/frontend-guide.md)** / **[frontend/ui-design.md](frontend/ui-design.md)** — Frontend and UI notes for contributors.

---

*Last updated: March 2026*
