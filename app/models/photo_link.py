"""PhotoLink model — 相片關聯 (polymorphic)."""
from app.extensions import db


class PhotoLink(db.Model):
    """相片與其他實體的關聯 — Polymorphic photo association.

    Links a photo to any entity via ``target_table`` (table name) and
    ``target_id`` (row primary key).
    """

    __tablename__ = "photo_links"

    __table_args__ = (
        db.Index("idx_photo_links_target", "target_table", "target_id"),
        db.Index("idx_photo_links_photo", "photo_id"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    photo_id = db.Column(
        db.Integer,
        db.ForeignKey("photos.id", ondelete="CASCADE"),
        nullable=False,
        comment="相片 ID",
    )
    target_table = db.Column(db.String(50), nullable=False, comment="目標表名")
    target_id = db.Column(db.Integer, nullable=False, comment="目標記錄 ID")
    sort_order = db.Column(db.Integer, default=0, comment="排序")
    caption = db.Column(db.String(500), default="", comment="標題 / 說明")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    photo = db.relationship("Photo", back_populates="links")

    def __repr__(self) -> str:
        return f"<PhotoLink Photo#{self.photo_id} -> {self.target_table}#{self.target_id}>"
