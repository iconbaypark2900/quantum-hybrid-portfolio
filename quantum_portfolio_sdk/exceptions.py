class QuantumPortfolioError(Exception):
    """Base SDK exception."""


class APIError(QuantumPortfolioError):
    """Raised when API returns a non-2xx response."""

    def __init__(self, status_code: int, message: str):
        super().__init__(f"API error {status_code}: {message}")
        self.status_code = status_code
        self.message = message

