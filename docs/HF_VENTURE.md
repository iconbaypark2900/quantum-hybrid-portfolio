# Hugging Face venture — overview

This document frames the **researcher-facing Hugging Face Spaces** line as a deliberate product slice alongside the **full application** (Next.js `web/` + Flask API). It does not replace deployment runbooks; see **[HUGGINGFACE_SPACES.md](HUGGINGFACE_SPACES.md)** for Docker push steps and **[HF_LITE_ROADMAP.md](HF_LITE_ROADMAP.md)** for what we plan to build.

## Positioning

| Track | Role |
|--------|------|
| **Full app** | Complete operator workflow: ledger UI, reports, settings, integrations, production deploys (e.g. Fly / Vercel per **[FLY_DEPLOY.md](FLY_DEPLOY.md)**). |
| **HF venture** | Fast, free-tier-friendly URL for **hands-on research**: portfolio lab loop + **IBM Quantum Runtime** story without shipping the whole surface area. |

Both tracks share the **same Flask backend and domain code** (`api/`, `services/`, `methods/`, `core/`). The venture differs in **deploy artifact**, **UI depth**, and **explicitly supported routes**.

## Audience

- Researchers and students comparing classical vs quantum-inspired allocation paths.
- Conference or portfolio visitors who need a **single stable demo URL** (see **[PUBLIC_DEMO.md](PUBLIC_DEMO.md)** for the ~60 second story).

## Goals

1. **Clarity** — One obvious path: configure data mode → run optimization → interpret results; optional IBM verify / smoke-test.
2. **Trust** — Disclaimers and honest limits (cold start, timeouts, optional persistence); no implied parity with the full product.
3. **Sustainability** — Builds that fit HF Docker constraints; optional slimmer dependencies if image size or build time becomes a blocker.

## Non-goals (for the venture slice)

- Parity with every **Next.js** ledger page (reports history, full settings, admin).
- Multi-tenant product auth as the default HF experience (unless explicitly scoped later).
- Long-running batch jobs or full training pipelines on the Space (consider **Hugging Face Jobs** or external compute for that class of work).

## Success criteria (definition of done for a milestone)

- Space builds from the documented Dockerfile path and serves on **7860**.
- Documented **Tier A** behaviors in **[HF_LITE_ROADMAP.md](HF_LITE_ROADMAP.md)** work end-to-end for an anonymous visitor (within free-tier limits).
- IBM path: at minimum **verify** + **smoke-test** documented; **persisted tenant token** only if we commit to SQLite/volume semantics.

## Related documents

| Document | Purpose |
|----------|---------|
| [HF_LITE_ROADMAP.md](HF_LITE_ROADMAP.md) | Concrete deliverables, phases, in/out scope. |
| [HUGGINGFACE_SPACES.md](HUGGINGFACE_SPACES.md) | HF Docker deploy procedure. |
| [PUBLIC_DEMO.md](PUBLIC_DEMO.md) | What to show in a short demo. |
| [ibm-quantum-credentials.md](ibm-quantum-credentials.md) | Token, CRN, verify vs connect. |

---

*Living venture brief; update when scope or milestones change.*
