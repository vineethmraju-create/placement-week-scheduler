from extensions import db


# Many-to-many relationship between students and companies
student_company = db.Table(
    "student_company",

    db.Column(
        "student_id",
        db.Integer,
        db.ForeignKey("students.id"),
        primary_key=True
    ),

    db.Column(
        "company_id",
        db.Integer,
        db.ForeignKey("companies.id"),
        primary_key=True
    )
)


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False,
        unique=True
    )

    cgpa_cutoff = db.Column(
        db.Float,
        nullable=False
    )

    interview_duration = db.Column(
        db.Integer,
        nullable=False
    )

    panel_count = db.Column(
        db.Integer,
        nullable=False
    )

    priority_tier = db.Column(
        db.String(20),
        nullable=False
    )

    available_days = db.Column(
        db.String(100),
        nullable=False
    )

    arrival_time = db.Column(
        db.String(10),
        nullable=True
    )

    shortlisted_students = db.relationship(
        "Student",
        secondary=student_company,
        backref="shortlisted_companies"
    )

    def __repr__(self):
        return f"<Company {self.name}>"