# Deploying to Hugging Face Spaces

This guide explains how to host the Quantum Portfolio Lab on [Hugging Face Spaces](https://huggingface.co/spaces).

## Prerequisites

- Hugging Face account
- Git

## Quick Start (from this repo)

```bash
# 1. Create a new Space at https://huggingface.co/new-space (Docker SDK)
# 2. Prepare for HF deployment
./scripts/prepare_hf_deploy.sh

# 3. Add Space as remote and push
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
git add Dockerfile
git commit -m "Deploy to Hugging Face Spaces"
git push space main

# 4. In Space Settings → Variables and secrets, add:
#    IBM_QUANTUM_TOKEN (Secret) = your token from quantum.ibm.com
#    IBM_QUANTUM_BACKEND (Variable) = simulator_stabilizer (fast) or ibm_torino (real QPU)
```

## Option A: Push This Repo to a New Space

1. **Create a new Space** at https://huggingface.co/new-space
   - Choose **Docker** as SDK
   - Name it (e.g. `quantum-portfolio-lab`)

2. **Use the HF Dockerfile**
   ```bash
   # In your quantum-hybrid-portfolio directory
   cp Dockerfile.hf Dockerfile
   ```

3. **Push to the Space**
   ```bash
   git remote add space https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
   git push space main
   ```
   Or clone the Space repo and copy files into it, then push.

## Option B: Create Space from scratch

1. Create a new Space with **Docker** SDK at https://huggingface.co/new-space

2. Clone the Space repo:
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
   cd YOUR_SPACE_NAME
   ```

3. Copy the required files:
   - All Python code (`api.py`, `serve_hf.py`, `config/`, `core/`, `services/`)
   - `frontend/` (entire folder)
   - `requirements.txt`
   - `Dockerfile.hf` → rename to `Dockerfile`
   - `huggingface/README.md` → use as `README.md` (includes HF YAML)

4. Commit and push:
   ```bash
   git add .
   git commit -m "Add Quantum Portfolio Lab"
   git push
   ```

## Space Configuration

The `README.md` for the Space must include this YAML block at the top:

```yaml
---
title: Quantum Portfolio Lab
emoji: 📊
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---
```

- **app_port: 7860** — HF Spaces expects this port by default
- **sdk: docker** — Uses the Dockerfile to build and run

## Build

HF Spaces will:

1. Run `docker build` using the Dockerfile
2. Build the React frontend (Stage 1)
3. Build the Python image with frontend artifacts (Stage 2)
4. Run `python serve_hf.py` — serves API + frontend on port 7860

## Environment Variables & Secrets

Set in **Space Settings → Variables and secrets**:

| Variable | Type | Description |
|----------|------|-------------|
| `LOG_LEVEL` | Variable | INFO, DEBUG, etc. |
| `CACHE_TTL` | Variable | Market data cache TTL (seconds) |
| `IBM_QUANTUM_TOKEN` | **Secret** | IBM Quantum API token (for QAOA on real hardware) |
| `IBM_QUANTUM_BACKEND` | Variable | Optional: `simulator_stabilizer` (fast) or `ibm_torino`, `ibm_brisbane` (real QPU) |

**IBM QAOA:** Without `IBM_QUANTUM_TOKEN`, the app falls back to classical QAOA. With the token, select **QAOA on IBM Quantum** in the objective dropdown. Real QPU runs can take 3–5+ minutes; use `simulator_stabilizer` for faster demos.

## Limits

- **CPU Spaces** — Free tier has sleep; wake on visit
- **No persistence** — Data is lost on restart (use `/data` with persistent storage upgrade if needed)
- **Timeout** — Frontend waits up to 5 min for optimizations; IBM real hardware can take longer during peak queue times

## Troubleshooting

**Build fails**
- Ensure `Dockerfile` (from Dockerfile.hf) exists at repo root
- Check `.dockerignore` does not exclude required files

**App not loading**
- Verify port 7860 in README YAML
- Check Space logs for Python errors

**API errors**
- HF Spaces may run behind a proxy; ensure CORS allows the Space URL

---

*Last updated: 2026-02*
