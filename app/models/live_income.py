"""LiveIncome model — 現場收款."""
from app.extensions import db


class LiveIncome(db.Model):
    """活動現場收款記錄 — Live event income entry."""

    __tablename__ = "live_income"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False, index=True, comment="收款年份")
    member_id = db.Column(db.Integer, comment="會員編號")
    member_name = db.Column(db.String(200), default="", comment="會員名稱")
    source_year = db.Column(db.Integer, comment="來源年份 (欠款年份)")
    amount = db.Column(db.Float, default=0, comment="金額")
    payment_method = db.Column(db.String(50), default="", comment="付款方式")
    handler = db.Column(db.String(100), default="", comment="經手人")
    remarks = db.Column(db.Text, default="", comment="備註")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self) -> str:
        return f"<LiveIncome {self.year} Member#{self.member_id} ${self.amount}>"
