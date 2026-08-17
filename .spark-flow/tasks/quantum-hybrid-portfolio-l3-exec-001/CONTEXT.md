        # CONTEXT: quantum-hybrid-portfolio-l3-exec-001

        ## Snapshot

        - Captured: 2026-05-31T00:54:59
        - Repo: `/home/iconbaypark2900/quantumGlobalGroup/quantum-hybrid-portfolio`
        - Branch: `main`

        ## Git status

        ```text
        M .spark-flow/memory/ASSESSMENT.md
 M .spark-flow/memory/PROJECT_PHASE.md
 M .spark-flow/memory/current_state.md
 M .spark-flow/memory/decisions.md
 M .spark-flow/memory/project_phase.json
?? .spark-flow/README.md
?? .spark-flow/current
?? .spark-flow/project_profile.yaml
?? .spark-flow/tasks/
?? docs/LIAISON_PROJECT_BRIEF.md
        ```

        ## Project metadata files

        - `frontend/package.json`
- `web/.next/dev/build/package.json`
- `web/.next/dev/package.json`
- `.venv/lib/python3.12/site-packages/pandas/pyproject.toml`
- `.venv/lib/python3.12/site-packages/stevedore/example/pyproject.toml`
- `.venv/lib/python3.12/site-packages/stevedore/example2/pyproject.toml`
- `pyproject.toml`
- `requirements.txt`
- `docker-compose.yml`

        ## README excerpt

        ```markdown
        ---
title: Quantum Portfolio Lab
emoji: 📊
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# Quantum Hybrid Portfolio

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Quantum-inspired portfolio optimization running on classical hardware.**

This project implements quantum-inspired portfolio optimization: hybrid pipelines, QUBO+SA, VQE, and classical methods, delivering robust allocations without requiring quantum hardware.

## Key Features

- **Hybrid 3-Stage Pipeline** — Screening, quantum-inspired selection, optimization (Buonaiuto/Herman 2025)
- **QUBO + Simulated Annealing** — Discrete optimization (Orús et al. 2019)
- **VQE PauliTwoDesign** — Variational quantum eigensolver-inspired weights (Scientific Reports 2023)
- **Multiple Optimization Objectives** — Equal weight, Markowitz, Min Variance, HRP, Target Return
- **Hybrid Quantum-Classical Workflows** — VQE for risk, QAOA for optimization, TensorFlow Quantum integration
- **Interactive Dashboard** — React-based frontend with real-time optimization and backtesting
- **REST API** — Full-featured API with rate limiting, caching, and Prometheus metrics

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Run Quick Test

```bash
python quick_test.py
```

### 4. Start the API

```bash
python -m api
```

The API runs at **http://localhost:5000**

- Health check: http://localhost:5000/api/health
- OpenAPI docs: http://localhost:5000/api/docs/openapi

### 5. Launch Dashboard

**Next.js (primary):**

```bash
cd web
npm install
npm run dev
```

Dashboard opens at **http://localhost:3042** (configured via `NEXT_WEB_PORT`; defaults to 3042 to avoid conflicts with the API on 5000).

**CRA (legacy, archived):** The original React dashboard in `frontend/` is retained for reference. To run it: `cd frontend && npm install && npm start` (http://localhost:3000).

### Public demo

To **host** a browser-only demo or understand disclaimers and limits, see **[docs/PUBLIC_DEMO.md](docs/PUBLIC_DEMO.md)**. Deploying to Hugging Face Spaces: **[docs/HUGGINGFACE_SPACES.md](docs/HUGGINGFACE_SPACES.md)**.

## Documentation
        ```

        ## Source of truth

        This file is the durable context snapshot for the current task. Chat history is not the source of truth.
