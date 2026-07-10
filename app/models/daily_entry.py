"""DailyEntry model — 現金收支日記帳."""
from app.extensions import db


class DailyEntry(db.Model):
    """現金收支日記帳 — Daily cashbook entry."""

    __tablename__ = "daily_entries"

    __table_args__ = (
        db.Index("idx_daily_entries_date", "entry_date"),
        db.Index("idx_daily_entries_year", "year"),
        db.CheckConstraint("entry_type IN ('income', 'expense')", name="ck_daily_entry_type"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False, comment="年份")
    entry_date = db.Column(db.Date, nullable=False, comment="日期")
    entry_type = db.Column(db.String(10), nullable=False, comment="類型: income / expense")
    category = db.Column(db.String(100), default="", comment="類別")
    subject = db.Column(db.String(300), nullable=False, default="", comment="項目")
    amount = db.Column(db.Float, default=0, comment="金額 (HKD)")
    payment_method = db.Column(db.String(50), default="", comment="付款方式")
    handler = db.Column(db.String(100), default="", comment="經手人")
    notes = db.Column(db.Text, default="", comment="備註")
    receipt_photo_id = db.Column(
        db.Integer,
        db.ForeignKey("photos.id"),
        nullable=True,
        comment="收據相片 ID",
    )
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # Relationships
    receipt_photo = db.relationship("Photo", foreign_keys=[receipt_photo_id])

    def __repr__(self) -> str:
        return f"<DailyEntry {self.entry_date} {self.entry_type} ${self.amount}>"
