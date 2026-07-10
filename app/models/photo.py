"""Photo model — 相片."""
from app.extensions import db


class Photo(db.Model):
    """相片記錄 — Photo / image record."""

    __tablename__ = "photos"

    __table_args__ = (
        db.Index("idx_photos_year", "year"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False, comment="年份")
    filename = db.Column(db.String(500), nullable=False, comment="檔案名稱")
    stored_path = db.Column(db.String(1000), nullable=False, comment="儲存路徑")
    thumbnail_path = db.Column(db.String(1000), comment="縮圖路徑")
    mime_type = db.Column(db.String(100), default="image/jpeg", comment="MIME 類型")
    file_size = db.Column(db.Integer, default=0, comment="檔案大小 (bytes)")
    uploaded_at = db.Column(db.DateTime, server_default=db.func.now(), comment="上傳時間")
    uploaded_by = db.Column(db.String(100), comment="上傳者")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    links = db.relationship("PhotoLink", back_populates="photo", lazy="dynamic",
                            cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Photo {self.id}: {self.filename}>"
