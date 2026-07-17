"""Bid model — 投標記錄."""
import uuid
from app.extensions import db


class Bid(db.Model):
    """會員投標記錄 — Member bid record."""

    __tablename__ = "bids"

    __table_args__ = (
        db.Index("idx_bids_year", "year"),
        db.Index("idx_bids_member", "member_id"),
        db.Index("idx_bids_item", "item_id"),
    )

    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    record_id = db.Column(db.Integer, unique=True, comment="CSV record ID")
    year = db.Column(db.Integer, nullable=False, comment="年份")
    member_id = db.Column(
        db.Integer,
        db.ForeignKey("members.member_id"),
        nullable=False,
        comment="會員編號",
    )
    referrer_id = db.Column(
        db.Integer,
        db.ForeignKey("members.member_id"),
        nullable=True,
        comment="經手人會員編號 (介紹人)",
    )
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("items.item_id"),
        comment="聖物編號",
    )
    bid_amount = db.Column(db.Float, default=0, comment="投標金額")
    membership_fee = db.Column(db.Float, default=0, comment="會員費")
    paid_amount = db.Column(db.Float, default=0, comment="已付金額")
    payment_method = db.Column(db.String(50), comment="付款方式")
    handler = db.Column(db.String(100), comment="經手人")
    operator = db.Column(db.String(100), default="", comment="操作員")
    photo_no = db.Column(db.String(100), comment="相片編號")
    receipt_no = db.Column(db.String(100), comment="收據編號")
    bid_no = db.Column(db.Integer, comment="投標編號")
    source = db.Column(db.String(50), comment="來源")
    remarks = db.Column(db.Text, comment="備註")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    member = db.relationship("Member", back_populates="bids", foreign_keys=[member_id])
    item = db.relationship("Item", back_populates="bids")

    def __repr__(self) -> str:
        return f"<Bid {self.year} Member#{self.member_id} ${self.bid_amount}>"
