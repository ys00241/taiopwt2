"""ThisYearItem model — 今年聖物 (sticker-based tracking)."""
from app.extensions import db


class ThisYearItem(db.Model):
    """當年聖物 — Current year items with sticker numbers."""

    __tablename__ = "this_year_items"

    __table_args__ = (
        db.Index("idx_this_year_items_year", "year"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False, comment="年份")
    sticker_no = db.Column(db.Integer, comment="貼紙編號 (1-50)")
    item_name = db.Column(db.String(300), nullable=False, default="", comment="聖物名稱")
    actual_item = db.Column(db.String(300), default="", comment="實物名稱")
    category = db.Column(db.String(100), default="", comment="類別")
    cost = db.Column(db.Float, default=0, comment="成本 (HKD)")
    source = db.Column(db.String(200), default="", comment="來源")
    photo_count = db.Column(db.Integer, default=0, comment="相片數量")
    photo_paths = db.Column(db.Text, default="", comment="相片路徑 (JSON)")
    bidder_name = db.Column(db.String(200), default="", comment="投得者")
    bid_amount = db.Column(db.Float, default=0, comment="投標金額")
    paid_amount = db.Column(db.Float, default=0, comment="已付金額")
    payment_method = db.Column(db.String(50), default="", comment="付款方式")
    handler = db.Column(db.String(100), default="", comment="經手人")
    paid_handler = db.Column(db.String(100), default="", comment="收款經手人")
    photo_codes = db.Column(db.Text, default="", comment="相片編碼")
    notes = db.Column(db.Text, default="", comment="備註")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def __repr__(self) -> str:
        return f"<ThisYearItem {self.year} #{self.sticker_no}: {self.item_name}>"
