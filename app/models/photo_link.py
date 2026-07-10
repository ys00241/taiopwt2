"""PhotoLink model — 相片關聯 (polymorphic)."""
from app.extensions import db


class PhotoLink(db.Model):
    """相片與其他實體的關聯 — Polymorphic photo association."""

    __tablename__ = "photo_links"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    photo_id = db.Column(db.Integer, db.ForeignKey("photos.id"), nullable=False, index=True)
    entity_type = db.Column(db.String(50), nullable=False, comment="關聯類型: item / member / edition / this_year_item")
    entity_id = db.Column(db.Integer, nullable=False, index=True, comment="關聯實體 ID")
    sort_order = db.Column(db.Integer, default=0, comment="排序")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    photo = db.relationship("Photo", back_populates="links")

    def __repr__(self) -> str:
        return f"<PhotoLink Photo#{self.photo_id} -> {self.entity_type}#{self.entity_id}>"
