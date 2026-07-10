"""Expense model — 支出."""
from app.extensions import db


class Expense(db.Model):
    """支出記錄 — Expense record (pre-event and live-event)."""

    __tablename__ = "expenses"

    __table_args__ = (
        db.Index("idx_expenses_year", "year"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False, comment="年份")
    source = db.Column(
        db.String(20), default="pre",
        comment="來源: pre (前期) / live (現場)",
    )
    date = db.Column(db.String(20), default="", comment="日期")
    category = db.Column(db.String(100), default="", comment="類別")
    subject = db.Column(db.String(300), nullable=False, default="", comment="項目")
    amount = db.Column(db.Float, default=0, comment="金額 (HKD)")
    payment_method = db.Column(db.String(50), default="", comment="付款方式")
    handler = db.Column(db.String(100), default="", comment="經手人")
    details = db.Column(db.Text, default="", comment="詳情")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self) -> str:
        return f"<Expense {self.year} [{self.source}] ${self.amount}: {self.subject}>"
