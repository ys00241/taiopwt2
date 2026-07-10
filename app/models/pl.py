"""PL model — 損益表 (Profit & Loss)."""
import uuid
from app.extensions import db


class PL(db.Model):
    """損益表記錄 — Profit & Loss entry."""

    __tablename__ = "pl"

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    record_id = db.Column(db.Integer, unique=True, comment="CSV record ID")
    year = db.Column(db.Integer, nullable=False, index=True, comment="年份")
    pl_type = db.Column(db.String(20), comment="類型: 收入 / 支出")
    subject = db.Column(db.String(300), comment="科目")
    payment_method = db.Column(db.String(50), comment="付款方式")
    period = db.Column(db.String(50), comment="期間")
    amount_hkd = db.Column(db.Float, default=0, comment="金額 (HKD)")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self) -> str:
        return f"<PL {self.year} {self.pl_type} ${self.amount_hkd}>"
