"""Export service — Excel/CSV export logic."""
from io import BytesIO


def export_items_excel(year: int) -> BytesIO:
    """Export this-year items as an XLSX workbook.

    Args:
        year: The edition year.

    Returns:
        BytesIO buffer containing the .xlsx file.
    """
    buf = BytesIO()
    return buf
