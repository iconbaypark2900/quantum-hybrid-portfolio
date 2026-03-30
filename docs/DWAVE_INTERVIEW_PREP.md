# D-Wave Interview Prep: Models, Use Cases & Portfolio Optimization

**Interview with Axel Daian, D-Wave — Monday**  
**Focus:** Optimization models, good use cases per model, and applying to your quantum-hybrid-portfolio project.

---

## 1. Model Overview & Your Project Connection

| Model | Variables | Sampler | Your project relevance |
|-------|-----------|---------|-------------------------|
| **Nonlinear (NL)** | Binary, integer | LeapHybridNLSampler | Permutations, TSP, logic structure |
| **Constrained Quadratic (CQM)** | Binary, integer, real | LeapHybridCQMSampler | **Best fit for portfolio optimization** (budget, cardinality, turnover) |
| **Binary Quadratic (BQM)** | Binary, spin | LeapHybridSampler, DWaveSampler | QUBO/Ising — **what you use today** |
| **Discrete Quadratic (DQM)** | Discrete | LeapHybridDQMSampler | Assignment problems (e.g., asset-to-bucket) |

---

## 2. Constrained vs Unconstrained

**Unconstrained** (QUBO, Ising, BQM):  
- Directly supported by D-Wave QPUs  
- Binary variables only  
- Constraints must be turned into **penalties** (e.g., \( P \cdot (\sum x_i - 1)^2 \) for budget)

**Constrained** (CQM, NL):  
- Native constraints (e.g., `x1 + x2 <= 10`)  
- Supported by hybrid samplers  
- Often easier and more natural to express real-world problems

**Your project:** In `braket_backend.py` you use QUBO + penalty formulation for budget and cardinality. In D-Wave terms, this is a BQM approach. CQM would let you express those constraints directly.

---

## 3. QUBO & Ising (BQM) — What You Use

### Formulation

**QUBO (binary 0/1):**
$$\min_{x \in \{0,1\}^n} \quad x^T Q x = \sum_i Q_{ii} x_i + \sum_{i<j} Q_{ij} x_i x_j$$

**Ising (spin ±1):**
$$E(s) = \sum_i h_i s_i + \sum_{i<j} J_{ij} s_i s_j, \quad s_i \in \{-1,+1\}$$

They are equivalent via \( x_i = \frac{1+s_i}{2} \).

### Your Portfolio QUBO (from `build_qubo_portfolio`)

```
minimize: -λ·return + (1-λ)·risk + penalty_budget·(Σx_i - 1)² + penalty_cardinality·(Σx_i - K)²
```

- Linear: return + variance + penalty terms  
- Quadratic: covariance + penalty interaction terms  
- Penalties encode budget and cardinality

### D-Wave use cases (QUBO/BQM)

- **Graph partitioning** — minimize edges between groups (risk clustering, asset grouping)
- **Job scheduling** — assign jobs to slots
- **Knapsack** — binary asset inclusion (portfolio subset selection)
- **Max-cut / graph problems** — risk diversification as a graph cut
- **Portfolio selection** — binary include/exclude (your use case)

---

## 4. Constrained Quadratic Model (CQM)

### Form

$$\min \quad \sum_i a_i x_i + \sum_{i\le j} b_{ij} x_i x_j + c$$  
subject to \(\sum_i a_i^{(m)} x_i + \sum_{i\le j} b_{ij}^{(m)} x_i x_j + c^{(m)} \circ 0\) for \(m = 1,\ldots,M\), where \(\circ \in \{\ge, \le, =\}\).

Variables can be **binary, integer, or real**.

### Why CQM is ideal for portfolio optimization

1. **Budget:** \(\sum_i w_i = 1\) — equality constraint (no penalty tuning)  
2. **Cardinality:** \(\sum_i x_i = K\) — exact number of assets  
3. **Bounds:** \(w_i \ge 0\), \(w_i \le u_i\) — bounds on weights  
4. **Sector limits:** \(\sum_{i \in \text{sector}} w_i \le L\) — sector exposure  

D-Wave’s `dwave-training/portfolio-optimization` example uses CQM for exactly this.

### D-Wave CQM use cases

- **Portfolio optimization** (BBVA, Bankia, D-Wave examples)
- **Employee scheduling** — shifts, availability, fairness
- **Job-shop scheduling** — jobs, machines, deadlines
- **Airline hub location** — choose hub airports with capacity limits
- **Tour planning** — routing with cost, duration, capacity
- **Meeting scheduling** — time slots, attendees, preferences

---

## 5. Discrete Quadratic Model (DQM)

### Form

Variables take values from discrete sets, e.g. `{red, green, blue}` or `{0, 1, 2, 3}`.

$$H(d) = \sum_i a_i(d_i) + \sum_{i,j} b_{i,j}(d_i, d_j) + c$$

Often implemented with one-hot encoding over binaries, but DQM keeps the model compact.

### Portfolio-relevant DQM use cases

- **Asset-to-bucket assignment** — assign assets to buckets (e.g., risk buckets)
- **Map coloring** — region coloring (risk zones, sector mapping)
- **Image segmentation** — grouping by similarity
- **Graph coloring** — radio frequency assignment, scheduling

For your project: DQM could model “which risk bucket each asset belongs to” instead of purely binary selection.

---

## 6. Nonlinear Model

### Scope

General optimization over binary and integer variables with:
- Nonlinear objective
- Nonlinear constraints

Designed for logic structures: **subsets** (knapsack) and **permutations** (TSP).

### D-Wave NL use cases

- **Traveling salesperson (TSP)** — ordering cities
- **Vehicle routing (CVRP)** — routing with capacity
- **Knapsack** — subset selection
- **Other permutation problems**

### Portfolio angle

Order-dependent problems (e.g., trading sequence, rebalancing order) could map to permutation-style NL models.

---

## 7. How Your Project Fits D-Wave’s Models

| Component | Model | Current implementation | Potential D-Wave evolution |
|-----------|-------|------------------------|----------------------------|
| `build_qubo_portfolio` | BQM/QUBO | Penalty-based constraints | Keep or migrate to CQM for native constraints |
| Asset selection | BQM | Binary \(x_i \in \{0,1\}\) | Same; or CQM for richer constraints |
| Braket backend | BQM | QUBO → classical/QAOA | Use `DWaveSampler` or `LeapHybridSampler` for annealing |
| Weight allocation | Real variables | Post-processing from binary | CQM with continuous weights |
| Cardinality | Penalty | \(P(\sum x_i - K)^2\) | CQM: \(\sum x_i = K\) |
| Budget | Penalty | \(P(\sum x_i - 1)^2\) | CQM: \(\sum w_i = 1\) |

---

## 8. Interview Talking Points

### Your project

- “I built a quantum-inspired portfolio optimizer that uses **QUBO** for binary asset selection and a penalty formulation for budget and cardinality. It runs on AWS Braket and falls back to classical simulated annealing.”
- “The QUBO objective balances risk and return, with quadratic terms from the covariance matrix and linear terms from expected returns.”
- “I’m aware D-Wave has a **CQM portfolio example** — migrating to CQM would let me express budget and cardinality as hard constraints instead of penalties.”

### D-Wave models

- “I understand the difference between **unconstrained** (QUBO/Ising for QPU) and **constrained** (CQM for hybrid).”
- “**CQM** seems best for portfolio optimization because of budget, cardinality, and exposure constraints.”
- “**DQM** could be useful for **assignment** problems, like assigning assets to risk buckets or sectors.”
- “**Nonlinear** models seem best for **permutation** problems, e.g. TSP and vehicle routing.”

### Use cases

- “QUBO/BQM: graph partitioning, knapsack, binary selection — exactly our asset selection problem.”
- “CQM: BBVA and Bankia portfolio optimization, scheduling, routing — constraints-heavy.”
- “DQM: map coloring, image segmentation, discrete assignment.”
- “NL: TSP, CVRP, and other permutation/ordering problems.”

### Technical depth

- “I implemented **QUBO→Ising** conversion for compatibility with annealing.” (see `_qubo_to_ising` in braket_backend)
- “Penalty strength tuning is a challenge; CQM would remove some of that.”
- “Portfolio size is limited by qubit count; hybrid solvers help scale.”

---

## 9. Quick Reference: Samplers & Capabilities

| Sampler | Models | Notes |
|---------|--------|-------|
| DWaveSampler | BQM (QUBO/Ising) | Native QPU, ~5000 qubits |
| LeapHybridSampler | BQM | Hybrid, larger problems |
| LeapHybridCQMSampler | CQM | Hybrid, constraints, real/integer vars |
| LeapHybridDQMSampler | DQM | Hybrid, discrete vars |
| LeapHybridNLSampler | Nonlinear | Hybrid, TSP, CVRP, permutations |

---

## 10. References

- D-Wave Portfolio Optimization: https://github.com/dwave-training/portfolio-optimization  
- D-Wave Finance Overview: https://dwavesys.com/media/h3ebako0/dwave_finance_overview_v5.pdf  
- Portfolio 60 Stocks Study: https://dwavequantum.com/resources/application/portfolio-optimization-of-60-stocks-using-classical-and-quantum-algorithms  
- Ocean Models Docs: https://docs.ocean.dwavesys.com/en/latest/concepts/
