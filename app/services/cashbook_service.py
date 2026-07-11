"""Cashbook service — daily cashbook business logic."""
from datetime import date

from sqlalchemy import func

from app.extensions import db
from app.models.daily_entry import DailyEntry


INCOME_CATEGORIES = ["利息", "香油", "捐獻", "會費", "其他收入"]
EXPENSE_CATEGORIES = ["伙食", "車馬", "衣紙", "雜項", "其他支出"]


def get_year() -> int:
    """Return the current/default year."""
    max_year = db.session.query(func.max(DailyEntry.year)).scalar()
    return max_year or date.today().year


def get_daily_entries(year: int, month: int | None = None) -> list[dict]:
    """Retrieve daily cashbook entries for a given period.

    Args:
        year: Year to filter.
        month: Optional month (1-12) to filter.

    Returns:
        List of DailyEntry dicts.
    """
    q = DailyEntry.query.filter(DailyEntry.year == year)
    if month is not None:
        q = q.filter(db.extract("month", DailyEntry.entry_date) == month)
    entries = q.order_by(DailyEntry.entry_date.desc(), DailyEntry.id.desc()).all()

    return [
        {
            "id": e.id,
            "year": e.year,
            "entry_date": e.entry_date.isoformat() if e.entry_date else "",
            "entry_type": e.entry_type,
            "category": e.category or "",
            "subject": e.subject or "",
            "amount": e.amount or 0,
            "payment_method": e.payment_method or "",
            "handler": e.handler or "",
            "notes": e.notes or "",
            "receipt_photo_id": e.receipt_photo_id,
            "created_at": e.created_at.isoformat() if e.created_at else "",
            "updated_at": e.updated_at.isoformat() if e.updated_at else "",
        }
        for e in entries
    ]


def get_cashbook_summary(year: int) -> dict:
    """Compute income/expense totals for the year.

    Returns:
        Dict with 'total_income', 'total_expense', 'balance'.
    """
    totals = (
        db.session.query(
            DailyEntry.entry_type,
            func.coalesce(func.sum(DailyEntry.amount), 0),
        )
        .filter(DailyEntry.year == year)
        .group_by(DailyEntry.entry_type)
        .all()
    )
    totals_map = dict(totals)
    total_income = float(totals_map.get("income", 0))
    total_expense = float(totals_map.get("expense", 0))
    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "balance": total_income - total_expense,
    }


def create_entry(data: dict) -> dict:
    """Create a new daily entry.

    Args:
        data: Dict with entry fields.

    Returns:
        The created entry dict.
    """
    today = date.today()
    entry_date = data.get("entry_date")
    if isinstance(entry_date, str) and entry_date:
        from datetime import date as dt_date
        entry_date = dt_date.fromisoformat(entry_date)

    entry = DailyEntry(
        year=data.get("year", entry_date.year if entry_date else today.year),
        entry_date=entry_date or today,
        entry_type=data.get("entry_type", "expense"),
        category=data.get("category", ""),
        subject=data.get("subject", ""),
        amount=float(data.get("amount", 0)),
        payment_method=data.get("payment_method", ""),
        handler=data.get("handler", ""),
        notes=data.get("notes", ""),
    )
    db.session.add(entry)
    db.session.commit()
    return _entry_to_dict(entry)


def update_entry(entry_id: int, data: dict) -> dict | None:
    """Update an existing daily entry.

    Args:
        entry_id: Entry ID.
        data: Dict with fields to update.

    Returns:
        Updated entry dict, or None if not found.
    """
    entry = DailyEntry.query.get(entry_id)
    if not entry:
        return None

    if "entry_date" in data and data["entry_date"]:
        from datetime import date as dt_date
        if isinstance(data["entry_date"], str):
            entry.entry_date = dt_date.fromisoformat(data["entry_date"])
        else:
            entry.entry_date = data["entry_date"]
    if "entry_type" in data:
        entry.entry_type = data["entry_type"]
    if "category" in data:
        entry.category = data["category"]
    if "subject" in data:
        entry.subject = data["subject"]
    if "amount" in data:
        entry.amount = float(data["amount"])
    if "payment_method" in data:
        entry.payment_method = data["payment_method"]
    if "handler" in data:
        entry.handler = data["handler"]
    if "notes" in data:
        entry.notes = data["notes"]
    if "year" in data:
        entry.year = int(data["year"])

    db.session.commit()
    return _entry_to_dict(entry)


def delete_entry(entry_id: int) -> bool:
    """Delete a daily entry.

    Args:
        entry_id: Entry ID.

    Returns:
        True if deleted, False if not found.
    """
    entry = DailyEntry.query.get(entry_id)
    if not entry:
        return False
    db.session.delete(entry)
    db.session.commit()
    return True


def export_csv(year: int, month: int | None = None) -> str:
    """Generate CSV content for cashbook entries.

    Args:
        year: Year to filter.
        month: Optional month to filter.

    Returns:
        CSV string content.
    """
    import csv
    import io

    entries = get_daily_entries(year, month)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["日期", "類型", "類別", "項目", "金額(HKD)", "付款方式", "經手人", "備註"])
    for e in entries:
        entry_type_label = "收入" if e["entry_type"] == "income" else "支出"
        writer.writerow([
            e["entry_date"],
            entry_type_label,
            e["category"],
            e["subject"],
            e["amount"],
            e["payment_method"],
            e["handler"],
            e["notes"],
        ])

    # Add summary at bottom
    summary = get_cashbook_summary(year)
    writer.writerow([])
    writer.writerow(["總結"])
    writer.writerow(["總收入", summary["total_income"]])
    writer.writerow(["總支出", summary["total_expense"]])
    writer.writerow(["結餘", summary["balance"]])

    return output.getvalue()


def _entry_to_dict(entry: DailyEntry) -> dict:
    return {
        "id": entry.id,
        "year": entry.year,
        "entry_date": entry.entry_date.isoformat() if entry.entry_date else "",
        "entry_type": entry.entry_type,
        "category": entry.category or "",
        "subject": entry.subject or "",
        "amount": entry.amount or 0,
        "payment_method": entry.payment_method or "",
        "handler": entry.handler or "",
        "notes": entry.notes or "",
        "receipt_photo_id": entry.receipt_photo_id,
        "created_at": entry.created_at.isoformat() if entry.created_at else "",
        "updated_at": entry.updated_at.isoformat() if entry.updated_at else "",
    }
