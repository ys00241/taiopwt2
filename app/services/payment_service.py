"""Payment service — payment recording and receipt generation."""
from io import BytesIO


def generate_receipt_xlsx(member_id: int, year: int) -> BytesIO:
    """Generate a PWT RECEIPT XLSX with 3 receipts per A4 page.

    Args:
        member_id: The member's ID.
        year: The edition year.

    Returns:
        BytesIO buffer containing the .xlsx file.
    """
    buf = BytesIO()
    return buf


def record_payment(member_id: int, year: int, amount: float,
                   payment_method: str, handler: str) -> int:
    """Record a live payment and return the payment ID.

    Args:
        member_id: Member ID.
        year: Current event year.
        amount: Payment amount.
        payment_method: Cash / FPS / etc.
        handler: Staff who collected payment.

    Returns:
        The new payment record ID.
    """
    return 0
