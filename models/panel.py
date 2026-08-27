from extensions import db


class Panel(db.Model):
    __tablename__ = "panels"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(50),
        nullable=False
    )

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id"),
        nullable=False
    )

    available = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    company = db.relationship(
        "Company",
        backref=db.backref("panels", lazy=True)
    )

    def __repr__(self):
        return f"<Panel {self.name}>"