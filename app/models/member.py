"""Member model — 會員資料."""
import uuid
from app.extensions import db


class Member(db.Model):
    """花炮會會員 — Association member."""

    __tablename__ = "members"

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    member_id = db.Column(db.Integer, unique=True, nullable=False, index=True, comment="會員編號")
    name = db.Column(db.String(200), nullable=False, comment="會員姓名")
    phone = db.Column(db.String(50), comment="電話")
    phone_2 = db.Column(db.String(50), comment="後備電話")
    home_address = db.Column(db.Text, comment="地址")
    first_year = db.Column(db.Integer, comment="加入年份")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # Relationships
    bids = db.relationship("Bid", back_populates="member", lazy="dynamic",
                           foreign_keys="Bid.member_id")

    def __repr__(self) -> str:
        return f"<Member {self.member_id}: {self.name}>"

    @property
    def total_due(self) -> float:
        return sum(b.bid_amount for b in self.bids if b.bid_amount and b.bid_amount > 0)

    @property
    def total_paid(self) -> float:
        return sum(b.paid_amount for b in self.bids if b.paid_amount)
