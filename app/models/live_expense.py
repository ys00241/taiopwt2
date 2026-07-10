"""LiveExpense model — 現場支出."""
from app.extensions import db


class LiveExpense(db.Model):
    """活動現場支出記錄 — Live event expense entry."""

    __tablename__ = "live_expenses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False, index=True, comment="年份")
    subject = db.Column(db.String(300), nullable=False, default="", comment="項目")
    amount = db.Column(db.Float, default=0, comment="金額 (HKD)")
    payment_method = db.Column(db.String(50), default="", comment="付款方式")
    handler = db.Column(db.String(100), default="", comment="經手人")
    details = db.Column(db.Text, default="", comment="詳情")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self) -> str:
        return f"<LiveExpense {self.year} ${self.amount}: {self.subject}>"
