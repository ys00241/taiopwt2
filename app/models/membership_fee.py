"""MembershipFee model — 會費記錄."""

import uuid
from app.extensions import db


class MembershipFee(db.Model):
    """花炮會會費 — Association membership fee record."""

    __tablename__ = "membership_fees"

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = db.Column(db.Integer, db.ForeignKey("members.member_id"), nullable=False, comment="會員編號")
    year = db.Column(db.Integer, nullable=False, comment="年份")
    amount = db.Column(db.Float, default=0, comment="會費金額")
    payment_method = db.Column(db.String(50), default="", comment="付款方式")
    handler = db.Column(db.String(100), default="", comment="經手人")
    notes = db.Column(db.Text, default="", comment="備註")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    member = db.relationship("Member", back_populates="membership_fees")

    def __repr__(self) -> str:
        return f"<MembershipFee {self.member_id} year={self.year} amount={self.amount}>"
