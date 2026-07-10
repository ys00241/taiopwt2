"""Photo model — 相片."""
from app.extensions import db


class Photo(db.Model):
    """相片記錄 — Photo record."""

    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False, index=True, comment="年份")
    filename = db.Column(db.String(500), nullable=False, comment="檔案名稱")
    original_name = db.Column(db.String(500), default="", comment="原始檔案名")
    filepath = db.Column(db.String(1000), nullable=False, comment="儲存路徑")
    file_size = db.Column(db.Integer, default=0, comment="檔案大小 (bytes)")
    mime_type = db.Column(db.String(100), default="image/jpeg", comment="MIME 類型")
    caption = db.Column(db.String(500), default="", comment="標題")
    sort_order = db.Column(db.Integer, default=0, comment="排序")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Relationships
    links = db.relationship("PhotoLink", back_populates="photo", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Photo {self.id}: {self.filename}>"
