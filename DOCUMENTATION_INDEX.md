# 📚 Documentation Index

> Quick reference to all documentation in the quantum-hybrid-portfolio project

---

## 🎯 Start Here

### **New User?** → [README.md](README.md)
- Project overview and features
- Installation instructions
- Quick start example
- **Best for:** First-time users

### **Want to Run It?** → [HOW_TO_RUN.md](HOW_TO_RUN.md)
- Step-by-step running instructions
- Troubleshooting guide
- Command reference
- **Best for:** Getting the project operational

### **Need Quick Reference?** → [QUICKSTART.md](QUICKSTART.md)
- Fast setup guide
- Key features overview
- Basic usage
- **Best for:** Users who want to get started quickly

### **Exploring the Code?** → [DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md)
- Complete file-by-file reference
- Code structure explanation
- Dependency map
- **Best for:** Developers and contributors

---

## Canonical Entrypoints

| Component | Entrypoint | Notes |
|-----------|-----------|-------|
| **Backend API** | [api.py](api.py) | Flask API on port 5000; supports all objectives including HRP |
| **Frontend** | [frontend/src/App.js](frontend/src/App.js) → [EnhancedQuantumDashboard.js](frontend/src/EnhancedQuantumDashboard.js) | React app on port 3000 |

**Run the API:** `source .venv/bin/activate && python api.py`
**Run the dashboard:** `cd frontend && npm start`

> Other files such as `enhanced_api.py`, `production_api.py`, `fixed_enhanced_api.py`, `dashboard.py`, and `quantum_portfolio_dashboard.jsx` are legacy or experimental alternatives. Use `api.py` and the React app in `frontend/` for normal development and production.

---

## 📖 Documentation Files

### Root

| File | Purpose | Audience |
|------|---------|----------|
| **[README.md](README.md)** | Main project documentation and quick start | Everyone |
| **[HOW_TO_RUN.md](HOW_TO_RUN.md)** | Running instructions and troubleshooting | Users |
| **[QUICKSTART.md](QUICKSTART.md)** | Fast setup guide | Beginners |
| **[DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md)** | Complete file-by-file reference | Developers |
| **[PRODUCTION_READINESS_PLAN.md](PRODUCTION_READINESS_PLAN.md)** | Production hardening plan | Ops / DevOps |
| **[ENHANCEMENT_PLAN.md](ENHANCEMENT_PLAN.md)** | Algorithm and feature enhancement roadmap | Developers |
| **DOCUMENTATION_INDEX.md** | This file — documentation navigator | Everyone |

### docs/ folder

| File | Purpose | Audience |
|------|---------|----------|
| **[docs/README.md](docs/README.md)** | Documentation hub and quick links | Everyone |
| **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** | Installation, run steps, troubleshooting | New users |
| **[docs/DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md)** | Dashboard tabs, controls, info bubbles | End users |
| **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** | REST API endpoints, request/response | API consumers |
| **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** | System architecture, data flow | Developers |
| **[docs/HUGGINGFACE_SPACES.md](docs/HUGGINGFACE_SPACES.md)** | Deploy to Hugging Face Spaces | Ops / Deploy |
| **[docs/API_PRODUCT_GUIDE.md](docs/API_PRODUCT_GUIDE.md)** | API integration, auth, async jobs | Integrators |
| **docs/openapi.yaml** | OpenAPI 3.0 spec (served at `/api/docs/openapi`) | API consumers |

---

## 🗺️ Documentation Map

```
📚 Documentation
│
├── 🌟 README.md ────────────────┐
├── 🚀 HOW_TO_RUN.md ────────────┤
├── ⚡ QUICKSTART.md ─────────────┤  Root
├── 📂 DIRECTORY_GUIDE.md ───────┤
├── 📚 DOCUMENTATION_INDEX.md ───┘  (you are here)
│
└── 📁 docs/
    ├── README.md ─────────────────── Documentation hub
    ├── GETTING_STARTED.md ─────────── Install & run
    ├── DASHBOARD_GUIDE.md ─────────── Dashboard user guide
    ├── API_REFERENCE.md ───────────── API endpoints
    ├── ARCHITECTURE.md ────────────── System architecture
    └── API_PRODUCT_GUIDE.md ───────── API integration
```

---

## 🎓 Learning Path

### **Level 1: Getting Started**
1. Read [README.md](README.md) - Overview
2. Follow [QUICKSTART.md](QUICKSTART.md) - Setup
3. Run `python quick_test.py` - Verify

### **Level 2: Using the System**
1. Read [HOW_TO_RUN.md](HOW_TO_RUN.md) - Commands
2. Run `python examples/basic_qsw_example.py` - Example
3. Explore `notebooks/01_qsw_exploration.ipynb` - Interactive

### **Level 3: Understanding the Code**
1. Read [DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md) - Structure
2. Study `core/quantum_inspired/quantum_walk.py` - Main algorithm
3. Review `tests/test_quantum_walk.py` - Test cases

### **Level 4: Contributing**
1. Review [README.md](README.md) Contributing section
2. Study [DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md) Modification Guide
3. Make changes, test, submit PR

---

## 🔍 Find Information By Topic

### **Installation**
- [README.md - Quick Start](README.md#-quick-start)
- [HOW_TO_RUN.md - Installation](HOW_TO_RUN.md)
- [QUICKSTART.md - Installation](QUICKSTART.md)

### **Running Examples**
- [README.md - Running Examples](README.md#-running-examples)
- [HOW_TO_RUN.md - What You Can Run](HOW_TO_RUN.md#-what-you-can-run)
- `examples/basic_qsw_example.py`

### **Configuration**
- [README.md - Configuration](README.md#-configuration)
- [DIRECTORY_GUIDE.md - Configuration](DIRECTORY_GUIDE.md#️-configuration-config)
- `config/qsw_config.py`

### **Testing**
- [README.md - Testing](README.md#-testing)
- [HOW_TO_RUN.md - Troubleshooting](HOW_TO_RUN.md#-troubleshooting)
- [DIRECTORY_GUIDE.md - Tests](DIRECTORY_GUIDE.md#-tests-tests)

### **Algorithm Details**
- [README.md - How It Works](README.md#-how-it-works)
- [DIRECTORY_GUIDE.md - Core Implementation](DIRECTORY_GUIDE.md#-core-implementation-core)
- `core/quantum_inspired/` source files

### **File Descriptions**
- [DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md) - Complete reference

### **Performance Metrics**
- [README.md - Performance](README.md#-performance)
- `validation/chang_validation.py`

### **Troubleshooting**
- [HOW_TO_RUN.md - Troubleshooting](HOW_TO_RUN.md#-troubleshooting)

---

## 📝 Documentation Standards

### **When to Update Documentation:**
- ✅ Adding new features
- ✅ Changing setup process
- ✅ Modifying file structure
- ✅ Fixing bugs that affect usage
- ✅ Adding new dependencies

### **Which File to Update:**
- **Features/Setup changed** → Update README.md
- **New commands/running steps** → Update HOW_TO_RUN.md
- **Files added/removed** → Update DIRECTORY_GUIDE.md
- **Quick reference needs updating** → Update QUICKSTART.md

### **Documentation Checklist:**
- [ ] Accurate (reflects current code)
- [ ] Complete (covers all cases)
- [ ] Clear (easy to understand)
- [ ] Examples included
- [ ] Updated date at bottom

---

## 🌐 External Resources

### **Git Repository**
- **URL:** https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio
- **Issues:** https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/issues
- **PRs:** https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/pulls

### **Related Research**
- Chang et al. (2025) - "Quantum Stochastic Walks for Portfolio Optimization"
- Markowitz (1952) - "Portfolio Selection"
- Nielsen & Chuang - "Quantum Computation and Quantum Information"

### **Dependencies Documentation**
- [NumPy](https://numpy.org/doc/)
- [Pandas](https://pandas.pydata.org/docs/)
- [NetworkX](https://networkx.org/documentation/)
- [SciPy](https://docs.scipy.org/)
- [yfinance](https://pypi.org/project/yfinance/)

---

## 🆘 Quick Help

### **I want to...**

**...understand what this project does**
→ Read [README.md](README.md)

**...install and run it**
→ Follow [HOW_TO_RUN.md](HOW_TO_RUN.md)

**...get started quickly**
→ Check [QUICKSTART.md](QUICKSTART.md)

**...understand the code structure**
→ Study [DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md)

**...find a specific file**
→ Search [DIRECTORY_GUIDE.md](DIRECTORY_GUIDE.md)

**...contribute to the project**
→ See [README.md - Contributing](README.md#-contributing)

**...report a bug**
→ Open an [issue](https://github.com/Quantum-Global-Group/quantum-hybrid-portfolio/issues)

**...understand the algorithm**
→ Read [README.md - How It Works](README.md#-how-it-works)

**...use the dashboard**
→ Read [docs/DASHBOARD_GUIDE.md](docs/DASHBOARD_GUIDE.md)

**...call the API**
→ Read [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

**...understand the architecture**
→ Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 📊 Documentation Stats

```
Total Documentation: ~40K+ words
Root files: 5+ markdown files
docs/ folder: 7 documentation files
Coverage: Installation, dashboard, API, architecture
Last Updated: 2026-02
```

---

## 🔄 Documentation Maintenance

**Owned by:** Quantum Global Group  
**Review Frequency:** With each major release  
**Update Trigger:** Code changes affecting usage

**To Report Doc Issues:**
1. Open GitHub issue
2. Tag with `documentation` label
3. Reference specific file/section

---

**💡 Tip:** Bookmark this file! It's your map to all project documentation.

---

**Version:** 0.2.0  
**Last Updated:** 2026-02  
**Maintainer:** Quantum Global Group
