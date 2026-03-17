"""
api_config_patch.py — drop-in replacements for the /api/config/* endpoints.

Replace the existing /api/config/objectives and /api/config/presets route
handlers in api.py with these functions.
"""

OBJECTIVES_CONFIG = {
    "equal_weight": {
        "label": "Equal Weight",
        "description": "1/N — equal allocation across all assets",
        "paper": "Benchmark baseline",
        "fast": True,
    },
    "markowitz": {
        "label": "Markowitz Max-Sharpe",
        "description": "Maximum Sharpe Ratio via SLSQP with multi-start",
        "paper": "Markowitz (1952)",
        "fast": True,
    },
    "min_variance": {
        "label": "Minimum Variance",
        "description": "Global minimum-variance portfolio",
        "paper": "Markowitz (1952)",
        "fast": True,
    },
    "hrp": {
        "label": "HRP",
        "description": "Hierarchical Risk Parity via recursive bisection",
        "paper": "López de Prado (2016)",
        "fast": True,
    },
    "qubo_sa": {
        "label": "QUBO + Simulated Annealing",
        "description": "Binary asset selection via QUBO solved with SA (D-Wave proxy)",
        "paper": "Orús et al. (2019) arXiv:1811.03975",
        "fast": False,
    },
    "vqe": {
        "label": "VQE (PauliTwoDesign)",
        "description": "Variational Quantum Eigensolver with noise-robust ansatz",
        "paper": "Scientific Reports (2023)",
        "fast": False,
    },
    "hybrid": {
        "label": "Hybrid Pipeline",
        "description": "3-stage: IC screening → QUBO-SA selection → Markowitz allocation",
        "paper": "Buonaiuto/Springer 2025, Herman/arXiv 2025",
        "fast": False,
    },
    "target_return": {
        "label": "Target Return",
        "description": "Minimum-variance portfolio achieving a specified return",
        "paper": "Markowitz (1952)",
        "fast": True,
    },
}

PRESETS_CONFIG = {
    "default": {
        "label": "Default",
        "objective": "hybrid",
        "weight_min": 0.005,
        "weight_max": 0.30,
        "K_screen": None,
        "K_select": None,
    },
    "classical": {
        "label": "Classical",
        "objective": "markowitz",
        "weight_min": 0.005,
        "weight_max": 0.30,
    },
    "conservative": {
        "label": "Conservative",
        "objective": "min_variance",
        "weight_min": 0.005,
        "weight_max": 0.20,
    },
    "diversified": {
        "label": "Diversified",
        "objective": "hrp",
        "weight_min": 0.005,
        "weight_max": 0.25,
    },
    "quantum_select": {
        "label": "Quantum Select",
        "objective": "qubo_sa",
        "weight_min": 0.0,
        "weight_max": 1.0,
        "K": None,  # auto
    },
}
