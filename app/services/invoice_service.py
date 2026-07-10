"""Invoice service — 粉紅紙 (Pink Slip) DOCX generation."""
from io import BytesIO


def generate_invoice_docx(member_id: int, year: int) -> BytesIO:
    """Generate a 粉紅紙 DOCX for a member's bids in the given year.

    Args:
        member_id: The member's ID.
        year: The edition year.

    Returns:
        BytesIO buffer containing the .docx file.
    """
    # TODO: implement DOCX generation using python-docx
    buf = BytesIO()
    return buf
