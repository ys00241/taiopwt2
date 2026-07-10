"""Item model — 聖物."""
from app.extensions import db


class Item(db.Model):
    """花炮會聖物 — Festival item / sacred object."""

    __tablename__ = "items"

    id = db.Column(db.String, primary_key=True)
    item_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    name_1_auspicious = db.Column(db.String(300), comment="吉利名稱 (e.g. 一帆風順)")
    name_2_description = db.Column(db.String(300), comment="描述名稱 (e.g. 花炮頭)")
    year_data = db.Column(db.Text, comment="JSON array of {year, cost_hkd, supplier}")
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    # Relationships
    bids = db.relationship("Bid", back_populates="item", lazy="dynamic")

    def __repr__(self) -> str:
        name = self.name_1_auspicious or self.name_2_description or "?"
        return f"<Item {self.item_id}: {name}>"
