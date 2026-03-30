"""
Braket runtime and cost estimator.

Estimates the number of Braket tasks, total shots, QUBO size, wall-clock time,
and cost for single optimize, backtest, and batch operations—aligned with
braket_backend.py and backtest.py.

Uses Braket gate-based QPU pricing.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from dateutil.relativedelta import relativedelta

# Official Amazon Braket QPU pricing (per-task, per-shot) in USD
BRAKET_QPU_PRICING = {
    "rigetti_ankaa": (0.30, 0.00090),
    "iqm_garnet": (0.30, 0.00145),
    "iqm_emerald": (0.30, 0.00160),
    "quera_aquila": (0.30, 0.01000),
    "aqt_ibex": (0.30, 0.02350),
    "ionq_aria": (0.30, 0.03000),
    "ionq_forte": (0.30, 0.08000),
}

# Max QUBO assets (from QUBOPortfolioConfig.max_assets_qubo)
MAX_ASSETS_QUBO = 64

# Default shots per task (from braket_gate_backend QAOA runs)
DEFAULT_SHOTS_PER_TASK = 1000


def count_rebalance_dates(
    start_date: Union[datetime, str],
    end_date: Union[datetime, str],
    frequency: str,
) -> int:
    """
    Count rebalance dates for a given range and frequency.
    Matches logic in services/backtest._get_rebalance_dates.

    Args:
        start_date: Start date (datetime or ISO string)
        end_date: End date (datetime or ISO string)
        frequency: "weekly", "monthly", "quarterly", or "yearly"

    Returns:
        Number of rebalance dates.
    """
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

    dates = []
    current = start_date

    while current < end_date:
        dates.append(current)
        if frequency == "weekly":
            current += timedelta(weeks=1)
        elif frequency == "monthly":
            current += relativedelta(months=1)
        elif frequency == "quarterly":
            current += relativedelta(months=3)
        elif frequency == "yearly":
            current += relativedelta(years=1)
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")

    if dates and dates[-1] < end_date:
        dates.append(end_date)

    return len(dates)


def estimate_braket_usage(
    scenario: str,
    n_assets: int = 10,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    rebalance_frequency: str = "monthly",
    batch_size: int = 1,
    objectives: Optional[list] = None,
    shots_per_task: int = DEFAULT_SHOTS_PER_TASK,
    minutes_per_task: float = 3.0,
    device: str = "rigetti_ankaa",
) -> Dict[str, Any]:
    """
    Estimate Braket usage and cost for a given scenario.

    Args:
        scenario: "single_optimize", "backtest", "batch_optimize", "batch_backtest"
        n_assets: Number of assets (used for n_qubits)
        start_date: For backtest
        end_date: For backtest
        rebalance_frequency: For backtest ("weekly", "monthly", "quarterly", "yearly")
        batch_size: For batch scenarios (number of requests or backtest scenarios)
        objectives: For batch, which use braket_annealing (assume all if None)
        shots_per_task: Default 1000
        minutes_per_task: Default 3.0
        device: Braket QPU pricing preset

    Returns:
        Dict with num_tasks, total_shots, n_qubits, n_quadratic, est_time_minutes,
        est_cost_usd, device, per_task_usd, per_shot_usd, breakdown, disclaimer.
    """
    if device not in BRAKET_QPU_PRICING:
        device = "rigetti_ankaa"
    per_task_usd, per_shot_usd = BRAKET_QPU_PRICING[device]

    n_qubits = min(n_assets, MAX_ASSETS_QUBO)
    n_quadratic = n_qubits * (n_qubits - 1) // 2

    num_tasks = 0
    breakdown = None

    if scenario == "single_optimize":
        num_tasks = 1

    elif scenario == "backtest":
        if not start_date or not end_date:
            raise ValueError("backtest requires start_date and end_date")
        num_tasks = count_rebalance_dates(start_date, end_date, rebalance_frequency)

    elif scenario == "batch_optimize":
        # Assume all batch requests use braket_annealing if not specified
        n_braket = batch_size
        if objectives is not None:
            n_braket = sum(1 for o in objectives if o == "braket_annealing")
        num_tasks = min(n_braket, 100)  # Max batch 100

    elif scenario == "batch_backtest":
        if not start_date or not end_date:
            raise ValueError("batch_backtest requires start_date and end_date")
        tasks_per_scenario = count_rebalance_dates(
            start_date, end_date, rebalance_frequency
        )
        n_braket = batch_size
        if objectives is not None:
            n_braket = sum(1 for o in objectives if o == "braket_annealing")
        num_tasks = min(n_braket * tasks_per_scenario, 50 * tasks_per_scenario)

    else:
        raise ValueError(
            f"Unsupported scenario: {scenario}. "
            "Use single_optimize, backtest, batch_optimize, or batch_backtest."
        )

    total_shots = num_tasks * shots_per_task
    est_time_minutes = num_tasks * minutes_per_task
    est_cost_usd = round(
        num_tasks * (per_task_usd + shots_per_task * per_shot_usd), 2
    )

    result = {
        "num_tasks": num_tasks,
        "total_shots": total_shots,
        "n_qubits": n_qubits,
        "n_quadratic": n_quadratic,
        "est_time_minutes": round(est_time_minutes, 1),
        "est_cost_usd": est_cost_usd,
        "device": device,
        "per_task_usd": per_task_usd,
        "per_shot_usd": per_shot_usd,
        "disclaimer": "Uses Braket gate-based QPU pricing.",
    }

    if breakdown is not None:
        result["breakdown"] = breakdown

    return result
