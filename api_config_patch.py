"""
api_config_patch.py — drop-in replacements for the /api/config/* endpoints.

Replace the existing /api/config/objectives and /api/config/presets route
handlers in api.py with these functions.
"""

# Heuristic scalars only; not historical realized returns.
OBJECTIVES_CONFIG = {
    "equal_weight": {
        "label": "Equal Weight",
        "description": "1/N — equal allocation across all assets",
        "paper": "Benchmark baseline",
        "family": "classical",
        "fast": True,
        "papers": [
            {"citation": "Benchmark baseline (no single canonical paper)"},
        ],
        "notebooks": [],
        "code_refs": [
            {"path": "methods/equal_weight.py", "label": "equal_weight"},
            {"path": "core/optimizers/equal_weight.py", "label": "optimizer wrapper"},
        ],
    },
    "markowitz": {
        "label": "Markowitz Max-Sharpe",
        "description": "Maximum Sharpe Ratio via SLSQP with multi-start",
        "paper": "Markowitz (1952)",
        "family": "classical",
        "fast": True,
        "papers": [
            {
                "title": "Portfolio Selection",
                "citation": "Markowitz (1952)",
                "url": "https://www.jstor.org/stable/2975974",
            },
        ],
        "notebooks": [],
        "code_refs": [
            {"path": "methods/markowitz.py", "label": "markowitz_max_sharpe"},
            {"path": "core/optimizers/markowitz.py", "label": "optimizer wrapper"},
        ],
    },
    "min_variance": {
        "label": "Minimum Variance",
        "description": "Global minimum-variance portfolio",
        "paper": "Markowitz (1952)",
        "family": "classical",
        "fast": True,
        "papers": [
            {
                "title": "Portfolio Selection",
                "citation": "Markowitz (1952)",
                "url": "https://www.jstor.org/stable/2975974",
            },
        ],
        "notebooks": [],
        "code_refs": [
            {"path": "methods/markowitz.py", "label": "min_variance"},
            {"path": "core/optimizers/markowitz.py", "label": "optimizer wrapper"},
        ],
    },
    "hrp": {
        "label": "HRP",
        "description": "Hierarchical Risk Parity via recursive bisection",
        "paper": "López de Prado (2016)",
        "family": "classical",
        "fast": True,
        "papers": [
            {
                "title": "Building diversified portfolios that outperform out of sample",
                "citation": "López de Prado (2016)",
                "url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2708678",
            },
        ],
        "notebooks": [],
        "code_refs": [
            {"path": "methods/hrp.py", "label": "hrp_weights"},
            {"path": "core/optimizers/hrp.py", "label": "optimizer wrapper"},
        ],
    },
    "target_return": {
        "label": "Target Return",
        "description": "Minimum-variance portfolio achieving a specified return",
        "paper": "Markowitz (1952)",
        "family": "classical",
        "fast": True,
        "papers": [
            {
                "title": "Portfolio Selection",
                "citation": "Markowitz (1952)",
                "url": "https://www.jstor.org/stable/2975974",
            },
        ],
        "notebooks": [],
        "code_refs": [
            {"path": "methods/markowitz.py", "label": "target_return_frontier"},
            {"path": "core/optimizers/markowitz.py", "label": "optimizer wrapper"},
        ],
    },
    "hybrid": {
        "label": "Hybrid Pipeline",
        "description": "3-stage: IC screening → QUBO-SA selection → Markowitz allocation",
        "paper": "Buonaiuto/Springer 2025, Herman/arXiv 2025",
        "family": "hybrid",
        "fast": False,
        "papers": [
            {
                "citation": "Buonaiuto et al., Springer (2025); Herman et al. arXiv (2025)",
            },
        ],
        "notebooks": [
            {
                "path": "notebooks/05_hybrid_pipeline_grand_comparison.ipynb",
                "title": "Hybrid pipeline — grand comparison",
            },
        ],
        "code_refs": [
            {"path": "methods/hybrid_pipeline.py", "label": "hybrid_pipeline_weights"},
            {"path": "core/optimizers/hybrid_pipeline.py", "label": "optimizer wrapper"},
        ],
    },
    "qubo_sa": {
        "label": "QUBO + Simulated Annealing",
        "description": "Binary asset selection via QUBO solved with SA (D-Wave proxy)",
        "paper": "Orús et al. (2019) arXiv:1811.03975",
        "family": "quantum",
        "fast": False,
        "papers": [
            {
                "title": "Quantum computing for finance: Overview and prospects",
                "citation": "Orús et al. (2019)",
                "url": "https://arxiv.org/abs/1811.03975",
            },
        ],
        "notebooks": [
            {
                "path": "notebooks/04_qubo_vqe_portfolio.ipynb",
                "title": "QUBO & VQE portfolio",
            },
        ],
        "code_refs": [
            {"path": "methods/qubo_sa.py", "label": "qubo_sa_weights"},
            {"path": "core/optimizers/qubo_sa.py", "label": "optimizer wrapper"},
        ],
    },
    "vqe": {
        "label": "VQE (PauliTwoDesign)",
        "description": "Variational Quantum Eigensolver with noise-robust ansatz",
        "paper": "Scientific Reports (2023)",
        "family": "quantum",
        "fast": False,
        "papers": [
            {"citation": "See implementation notes in methods/vqe.py"},
        ],
        "notebooks": [
            {
                "path": "notebooks/04_qubo_vqe_portfolio.ipynb",
                "title": "QUBO & VQE portfolio",
            },
            {
                "path": "notebooks/03_quantum_risk_option_pricing.ipynb",
                "title": "Quantum risk / option pricing (related)",
            },
        ],
        "code_refs": [
            {"path": "methods/vqe.py", "label": "vqe_weights"},
            {"path": "core/optimizers/vqe.py", "label": "optimizer wrapper"},
        ],
    },
}

PRESETS_CONFIG = {
    "default": {
        "label": "Balanced · Hybrid",
        "description": "3-stage hybrid (screen → QUBO select → allocate). Good default for exploration.",
        "objective": "hybrid",
        "weight_min": 0.005,
        "weight_max": 0.30,
        "K_screen": None,
        "K_select": None,
    },
    "classical": {
        "label": "Classical · Max Sharpe",
        "description": "Markowitz max-Sharpe (SLSQP). Stable when covariance is well behaved.",
        "objective": "markowitz",
        "weight_min": 0.005,
        "weight_max": 0.30,
    },
    "conservative": {
        "label": "Defensive · Min variance",
        "description": "Global minimum-variance; prioritize capital preservation over return.",
        "objective": "min_variance",
        "weight_min": 0.005,
        "weight_max": 0.20,
    },
    "diversified": {
        "label": "Diversified · HRP",
        "description": "Hierarchical risk parity — balances clusters without full-matrix inversion.",
        "objective": "hrp",
        "weight_min": 0.005,
        "weight_max": 0.25,
    },
    "quantum_select": {
        "label": "Quantum · QUBO select",
        "description": "Binary asset selection via QUBO + simulated annealing; wide cap on chosen names.",
        "objective": "qubo_sa",
        "weight_min": 0.0,
        "weight_max": 1.0,
        "K": None,  # auto
    },
    # Align with Simulations → Stress Scenarios (same narrative, not a live shock engine).
    "sim_crash_day": {
        "label": "Stress · Crash day",
        "description": "For single-day crash narrative (cf. Simulations: Black Monday 1987): min-var, tight 10% cap.",
        "objective": "min_variance",
        "weight_min": 0.02,
        "weight_max": 0.10,
    },
    "sim_gfc_drawdown": {
        "label": "Stress · Credit drawdown",
        "description": "For prolonged credit crisis narrative (cf. Simulations: 2008 GFC, COVID): HRP, 18% cap.",
        "objective": "hrp",
        "weight_min": 0.005,
        "weight_max": 0.18,
    },
    "sim_relief_rally": {
        "label": "Stress · Relief rally",
        "description": "For relief / momentum day narrative (cf. Simulations: Vaccine Monday, stimulus): max-Sharpe, 35% cap.",
        "objective": "markowitz",
        "weight_min": 0.005,
        "weight_max": 0.35,
    },
}
