"""DailyEntry model — 現金收支日記帳."""
from app.extensions import db


class DailyEntry(db.Model):
    """現金收支日記帳 — Daily cashbook entry."""

    __tablename__ = "daily_entries"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False, index=True, comment="日期")
    entry_type = db.Column(db.String(10), nullable=False, comment="類型: income / expense")
    subject = db.Column(db.String(300), nullable=False, default="", comment="項目")
    amount = db.Column(db.Float, default=0, comment="金額")
    category = db.Column(db.String(100), default="", comment="類別")
    payment_method = db.Column(db.String(50), default="", comment="付款方式")
    reference = db.Column(db.String(200), default="", comment="參考編號")
    notes = db.Column(db.Text, default="", comment="備註")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self) -> str:
        return f"<DailyEntry {self.date} {self.entry_type} ${self.amount}>"
