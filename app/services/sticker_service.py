"""Sticker service — sticker label PDF generation."""
from io import BytesIO


def generate_sticker_pdf(year: int) -> BytesIO:
    """Generate sticker labels PDF for the given year's items.

    Produces a printable A4 PDF with 3x8 = 24 labels per page.

    Args:
        year: The edition year.

    Returns:
        BytesIO buffer containing the PDF.
    """
    buf = BytesIO()
    return buf
