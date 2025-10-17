# 🚀 How to Run the Quantum Hybrid Portfolio Project

## Quick Start (3 Commands)

```bash
# 1. Navigate to project
cd /home/roc/quantumGlobalGroup/quantum-hybrid-portfolio

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Run any of the examples below
```

---

## 📋 What You Can Run

### 1️⃣ **Run Unit Tests** (Fastest - ~1 second)
```bash
python -m pytest tests/test_quantum_walk.py -v
```

**What it does:** Tests core functionality  
**Time:** < 1 second  
**Output:** Shows 7 tests passing ✓

---

### 2️⃣ **Run Basic Example** (Medium - ~10 seconds)
```bash
python examples/basic_qsw_example.py
```

**What it does:**
- Downloads real S&P 500 stock data (30 stocks, 3 years)
- Runs QSW optimization
- Shows portfolio allocation and metrics
- Asks if you want to run validation (press Enter or Ctrl+C to skip)

**Time:** ~10 seconds (data download + optimization)  
**Output:** Portfolio with Sharpe ratio, returns, weights

**Press Ctrl+C** when it says "Press Enter to run validation" if you just want quick results.

---

### 3️⃣ **Run Full Validation** (Slowest - ~30 seconds)
```bash
python examples/basic_qsw_example.py
# Then press Enter when prompted
```

**What it does:**
- Runs basic example (above)
- Then runs Chang et al. validation suite:
  - 50 iterations of Sharpe improvement testing
  - 12 months of turnover analysis
  - 20 parameter sensitivity tests
  - Regime adaptation testing
- Generates performance report

**Time:** ~30-60 seconds  
**Output:** 
- Validation metrics vs. research claims
- `chang_validation_report.png` (chart)

---

### 4️⃣ **Run Phase 1 Verification** (Diagnostic - ~20 seconds)
```bash
python tests/phase1.py
```

**What it does:**
- Runs 5 diagnostic tests on the fixes
- Compares QSW vs classical optimization
- Shows what's working and what needs improvement

**Time:** ~20 seconds  
**Output:** Test results with ✓/✗ for each fix

---

### 5️⃣ **Interactive Jupyter Notebooks**
```bash
jupyter lab
```

**What it does:**
- Opens Jupyter in browser
- Navigate to `notebooks/` folder
- Open `01_qsw_exploration.ipynb` or `02_chang_validation.ipynb`

**Time:** Interactive  
**Output:** Step-by-step exploration

---

## 🔧 Troubleshooting

### Error: "ModuleNotFoundError"
**Solution:**
```bash
# Make sure you're in the right directory
cd /home/roc/quantumGlobalGroup/quantum-hybrid-portfolio

# Make sure venv is activated (you should see (.venv) in prompt)
source .venv/bin/activate

# Reinstall the package
pip install -e .
```

---

### Error: "No module named 'core.quantum_inspired.quantum_walk'"
**Solution:** Files were deleted. Restore from git:
```bash
git restore core/quantum_inspired/quantum_walk.py \
            core/quantum_inspired/evolution_dynamics.py \
            core/quantum_inspired/stability_enhancer.py
```

---

### Error: yfinance download issues
**Solution:** Internet/API issues. The code includes auto_adjust parameter fix:
```bash
# Just run again, usually resolves itself
python examples/basic_qsw_example.py
```

---

## 📊 Understanding the Output

### When you see this:
```
Expected Return: 23.73%
Volatility: 15.14%
Sharpe Ratio: 1.568
```

**Means:**
- **Expected Return:** If you hold this portfolio for a year, expect ~24% gain
- **Volatility:** Risk level (15% = moderate risk)
- **Sharpe Ratio:** Risk-adjusted return (1.5 = good, >2.0 = excellent)

---

### When you see this:
```
Top 10 Holdings:
  NVDA: 3.79%
  META: 3.68%
  ...
```

**Means:** 
- Put 3.79% of your money in NVDA stock
- Put 3.68% in META stock
- etc.
- This is your recommended portfolio allocation

---

### When you see validation results:
```
✓ PASSED: 90% turnover reduction
✗ FAILED: 15% avg Sharpe improvement
```

**Means:**
- ✓ = This feature works as claimed in research
- ✗ = This feature doesn't meet research claims (needs work)

---

## 🎯 Recommended Running Order

### First Time:
1. `python -m pytest tests/test_quantum_walk.py -v` (verify install)
2. `python examples/basic_qsw_example.py` (see it work, press Ctrl+C when asked)
3. `python tests/phase1.py` (see diagnostic report)

### Daily Development:
1. Make changes to code
2. `python -m pytest tests/ -v` (ensure no regressions)
3. `python examples/basic_qsw_example.py` (test with real data)

### Before Committing:
1. `python tests/phase1.py` (full verification)
2. `python examples/basic_qsw_example.py` (press Enter for validation)
3. Review generated charts and metrics

---

## 🔍 Current Status

**What's Working:**
- ✅ All unit tests pass (7/7)
- ✅ Basic optimization runs
- ✅ Real market data integration
- ✅ Regime adaptation

**What Needs Work:**
- ⚠️ Performance: QSW underperforms classical by ~34%
- ⚠️ Graph construction has issues
- ⚠️ Parameter tuning needed

**Next Steps:**
- Fix graph edge weight formula
- Tune evolution parameters
- Improve Hamiltonian construction

---

## 📞 Quick Commands Reference

```bash
# Tests only
pytest tests/test_quantum_walk.py -v

# Quick demo (10 sec)
python examples/basic_qsw_example.py
# Press Ctrl+C when prompted

# Full validation (60 sec)
python examples/basic_qsw_example.py
# Press Enter when prompted

# Diagnostic
python tests/phase1.py

# Jupyter
jupyter lab

# Check status
python -c "from core.quantum_inspired.quantum_walk import QuantumStochasticWalkOptimizer; print('✓ Working')"
```

---

**Last Updated:** After restoring deleted files  
**Status:** Fully operational ✅  
**All core files present:** quantum_walk.py, evolution_dynamics.py, stability_enhancer.py
