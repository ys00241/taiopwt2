"""Edition model — 屆別 / 年度."""
from app.extensions import db


class Edition(db.Model):
    """花炮會屆別 — Festival edition / year."""

    __tablename__ = "editions"

    id = db.Column(db.String, primary_key=True)
    edition_id = db.Column(db.Integer, comment="屆別編號")
    edition_no = db.Column(db.Integer, comment="屆數")
    year = db.Column(db.Integer, nullable=False, index=True, comment="年份")
    event_date = db.Column(db.String(50), comment="活動日期")
    venue = db.Column(db.String(300), comment="場地")
    tables = db.Column(db.Integer, default=0, comment="席數")
    singer = db.Column(db.String(200), comment="歌星")
    member_count = db.Column(db.Integer, default=0, comment="會員人數")
    remarks = db.Column(db.Text, comment="備註")
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self) -> str:
        return f"<Edition {self.year}>"
