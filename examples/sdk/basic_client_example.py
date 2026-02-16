from quantum_portfolio_sdk import QuantumPortfolioClient


def main():
    client = QuantumPortfolioClient(base_url="http://localhost:5000", api_key=None)

    print("Health:", client.health())

    optimize_payload = {
        "returns": [0.12, 0.10, 0.14, 0.09],
        "covariance": [
            [0.04, 0.01, 0.01, 0.00],
            [0.01, 0.05, 0.01, 0.00],
            [0.01, 0.01, 0.06, 0.01],
            [0.00, 0.00, 0.01, 0.03],
        ],
        "asset_names": ["AAPL", "MSFT", "NVDA", "JNJ"],
        "sectors": ["Tech", "Tech", "Tech", "Health"],
        "objective": "max_sharpe",
        "strategyPreset": "balanced",
    }

    optimize_res = client.optimize(optimize_payload)
    print("Sharpe:", optimize_res["qsw_result"]["sharpe_ratio"])
    print("Weights:", optimize_res["qsw_result"]["weights"])

    batch_res = client.optimize_batch([optimize_payload, optimize_payload], stop_on_error=False)
    print("Batch count:", batch_res["count"])


if __name__ == "__main__":
    main()

