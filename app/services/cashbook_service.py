"""Cashbook service — daily cashbook business logic."""


def get_daily_entries(year: int, month: int | None = None) -> list:
    """Retrieve daily cashbook entries for a given period.

    Args:
        year: Year to filter.
        month: Optional month (1-12) to filter.

    Returns:
        List of DailyEntry dicts.
    """
    return []


def get_cashbook_summary(year: int) -> dict:
    """Compute income/expense totals for the year.

    Returns:
        Dict with 'total_income', 'total_expense', 'balance'.
    """
    return {"total_income": 0.0, "total_expense": 0.0, "balance": 0.0}
