"""Stats service — dashboard statistics and aggregations."""


def get_dashboard_stats(year: int) -> dict:
    """Compute dashboard statistics for the given year.

    Args:
        year: The edition year.

    Returns:
        Dictionary with keys: members, bids, editions,
        this_year_items, expenses, sponsors, prev_unpaid.
    """
    return {
        "members": 0,
        "bids": 0,
        "editions": 0,
        "this_year_items": 0,
        "expenses": 0.0,
        "sponsors": 0.0,
        "prev_unpaid": 0,
    }
