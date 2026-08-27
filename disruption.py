from app import app
from extensions import db

from models.room import Room
from models.panel import Panel
from models.interview import Interview


# ============================================================
# HELPER
# ============================================================

def show_interview(interview):
    print(
        f"Interview {interview.id}: "
        f"Student {interview.student_id} | "
        f"Company {interview.company_id} | "
        f"Day {interview.day} | "
        f"{interview.start_time}-{interview.end_time} | "
        f"Room {interview.room_id} | "
        f"Panel {interview.panel_id}"
    )


# ============================================================
# 1. ROOM BECOMES UNAVAILABLE
# ============================================================

def disable_room(room_id):

    room = Room.query.get(room_id)

    if room is None:
        print(f"Room {room_id} not found.")
        return

    room.available = False

    affected = Interview.query.filter_by(
        room_id=room_id,
        status="SCHEDULED"
    ).all()

    print()
    print("=" * 60)
    print("DISRUPTION: ROOM UNAVAILABLE")
    print("=" * 60)

    print(f"Room {room_id} marked unavailable.")
    print(f"Affected interviews: {len(affected)}")

    for interview in affected:
        show_interview(interview)

    db.session.commit()


# ============================================================
# 2. PANEL MEMBER DROPS OUT
# ============================================================

def disable_panel(panel_id):

    panel = Panel.query.get(panel_id)

    if panel is None:
        print(f"Panel {panel_id} not found.")
        return

    panel.available = False

    affected = Interview.query.filter_by(
        panel_id=panel_id,
        status="SCHEDULED"
    ).all()

    print()
    print("=" * 60)
    print("DISRUPTION: PANEL UNAVAILABLE")
    print("=" * 60)

    print(f"Panel {panel_id} marked unavailable.")
    print(f"Affected interviews: {len(affected)}")

    for interview in affected:
        show_interview(interview)

    db.session.commit()


# ============================================================
# 3. COMPANY ARRIVES LATE
# ============================================================

def company_arrives_late(company_id, new_arrival_time):

    affected = Interview.query.filter_by(
        company_id=company_id,
        status="SCHEDULED"
    ).all()

    new_hour, new_minute = map(
        int,
        new_arrival_time.split(":")
    )

    new_minutes = new_hour * 60 + new_minute

    affected_interviews = []

    for interview in affected:

        start_hour, start_minute = map(
            int,
            interview.start_time.split(":")
        )

        start_minutes = (
            start_hour * 60 +
            start_minute
        )

        if start_minutes < new_minutes:
            affected_interviews.append(interview)

    print()
    print("=" * 60)
    print("DISRUPTION: COMPANY ARRIVES LATE")
    print("=" * 60)

    print(
        f"Company {company_id} arrival changed "
        f"to {new_arrival_time}"
    )

    print(
        f"Affected interviews: "
        f"{len(affected_interviews)}"
    )

    for interview in affected_interviews:
        show_interview(interview)


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    with app.app_context():

        print()
        print("Current rooms:")

        rooms = Room.query.limit(5).all()

        for room in rooms:
            print(
                f"Room ID: {room.id}, "
                f"Name: {room.name}, "
                f"Available: {room.available}"
            )

        print()
        print("Current panels:")

        panels = Panel.query.limit(5).all()

        for panel in panels:
            print(
                f"Panel ID: {panel.id}, "
                f"Name: {panel.name}, "
                f"Available: {panel.available}"
            )

        disable_room(2)    