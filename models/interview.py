from extensions import db


class Interview(db.Model):
    __tablename__ = "interviews"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("students.id"),
        nullable=False
    )

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("companies.id"),
        nullable=False
    )

    room_id = db.Column(
        db.Integer,
        db.ForeignKey("rooms.id"),
        nullable=True
    )

    panel_id = db.Column(
        db.Integer,
        db.ForeignKey("panels.id"),
        nullable=True
    )

    day = db.Column(
        db.Integer,
        nullable=False
    )

    start_time = db.Column(
        db.String(5),
        nullable=False
    )

    end_time = db.Column(
        db.String(5),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="SCHEDULED"
    )

    student = db.relationship(
        "Student",
        backref=db.backref("interviews", lazy=True)
    )

    company = db.relationship(
        "Company",
        backref=db.backref("interviews", lazy=True)
    )

    room = db.relationship(
        "Room",
        backref=db.backref("interviews", lazy=True)
    )

    panel = db.relationship(
        "Panel",
        backref=db.backref("interviews", lazy=True)
    )

    def __repr__(self):
        return (
            f"<Interview {self.id}: "
            f"Student {self.student_id} - "
            f"Company {self.company_id}>"
        )