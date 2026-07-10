"""Sponsor model — 贊助."""
from app.extensions import db


class Sponsor(db.Model):
    """贊助記錄 — Sponsorship record."""

    __tablename__ = "sponsors"

    __table_args__ = (
        db.Index("idx_sponsors_year", "year"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False, comment="年份")
    sponsor_name = db.Column(db.String(300), nullable=False, default="", comment="贊助者")
    amount = db.Column(db.Float, default=0, comment="贊助金額 (HKD)")
    item_name = db.Column(db.String(300), default="", comment="贊助聖物")
    details = db.Column(db.Text, default="", comment="詳情")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self) -> str:
        return f"<Sponsor {self.year} {self.sponsor_name} ${self.amount}>"
