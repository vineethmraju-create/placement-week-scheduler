from extensions import db


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(50),
        nullable=False,
        unique=True
    )

    available = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    def __repr__(self):
        return f"<Room {self.name}>"
    