from extensions import db


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    cgpa = db.Column(db.Float, nullable=False)

    branch = db.Column(db.String(50), nullable=False)

    status = db.Column(db.String(20), nullable=False, default="ACTIVE")

    def __repr__(self):
        return f"<Student {self.name}>"