from app import app
from extensions import db

from models.company import Company
from models.room import Room
from models.panel import Panel
from models.interview import Interview


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def to_minutes(time_string):
    """Convert HH:MM into total minutes."""
    hour, minute = map(int, time_string.split(":"))
    return hour * 60 + minute


def minutes_to_time(minutes):
    """Convert total minutes into HH:MM."""
    hour = minutes // 60
    minute = minutes % 60
    return f"{hour:02d}:{minute:02d}"


def overlaps(start1, end1, start2, end2):
    """Return True if two time intervals overlap."""
    return start1 < end2 and start2 < end1


# ============================================================
# ROOM AVAILABILITY
# ============================================================

def room_free(
    room_id,
    day,
    start,
    end,
    ignore_interview_id=None
):

    interviews = Interview.query.filter_by(
        room_id=room_id,
        day=day,
        status="SCHEDULED"
    ).all()

    for interview in interviews:

        if interview.id == ignore_interview_id:
            continue

        existing_start = to_minutes(
            interview.start_time
        )

        existing_end = to_minutes(
            interview.end_time
        )

        if overlaps(
            start,
            end,
            existing_start,
            existing_end
        ):
            return False

    return True


# ============================================================
# STUDENT AVAILABILITY
# ============================================================

def student_free(
    student_id,
    day,
    start,
    end,
    ignore_interview_id=None
):

    interviews = Interview.query.filter_by(
        student_id=student_id,
        day=day,
        status="SCHEDULED"
    ).all()

    for interview in interviews:

        if interview.id == ignore_interview_id:
            continue

        existing_start = to_minutes(
            interview.start_time
        )

        existing_end = to_minutes(
            interview.end_time
        )

        if overlaps(
            start,
            end,
            existing_start,
            existing_end
        ):
            return False

    return True


# ============================================================
# PANEL AVAILABILITY
# ============================================================

def panel_free(
    panel_id,
    day,
    start,
    end,
    ignore_interview_id=None
):

    interviews = Interview.query.filter_by(
        panel_id=panel_id,
        day=day,
        status="SCHEDULED"
    ).all()

    for interview in interviews:

        if interview.id == ignore_interview_id:
            continue

        existing_start = to_minutes(
            interview.start_time
        )

        existing_end = to_minutes(
            interview.end_time
        )

        if overlaps(
            start,
            end,
            existing_start,
            existing_end
        ):
            return False

    return True


# ============================================================
# ROOM DISRUPTION REPLANNER
# ============================================================

def replan_unavailable_room(room_id):

    room = db.session.get(
        Room,
        room_id
    )

    if room is None:
        print(
            f"Room {room_id} does not exist."
        )
        return

    if room.available:
        print(
            f"Room {room.name} is currently available."
        )
        return

    affected = (
        Interview.query
        .filter_by(
            room_id=room_id,
            status="SCHEDULED"
        )
        .order_by(
            Interview.day,
            Interview.start_time
        )
        .all()
    )

    available_rooms = (
        Room.query
        .filter(
            Room.available.is_(True),
            Room.id != room_id
        )
        .order_by(Room.id)
        .all()
    )

    print()
    print("=" * 70)
    print("ROOM DISRUPTION REPLAN")
    print("=" * 70)

    print(
        f"Unavailable room   : {room.name}"
    )

    print(
        f"Affected interviews: {len(affected)}"
    )

    moved = []
    unscheduled = []

    for interview in affected:

        start = to_minutes(
            interview.start_time
        )

        end = to_minutes(
            interview.end_time
        )

        replacement_room = None

        # Try to preserve the same day and time.
        for candidate_room in available_rooms:

            if room_free(
                candidate_room.id,
                interview.day,
                start,
                end,
                interview.id
            ):

                replacement_room = candidate_room
                break

        if replacement_room:

            old_room = room.name

            interview.room_id = (
                replacement_room.id
            )

            moved.append({
                "interview_id": interview.id,
                "student_id": interview.student_id,
                "company_id": interview.company_id,
                "old_room": old_room,
                "new_room": replacement_room.name,
                "day": interview.day,
                "start": interview.start_time,
                "end": interview.end_time
            })

        else:

            interview.status = "UNSCHEDULED"

            unscheduled.append({
                "interview_id": interview.id,
                "student_id": interview.student_id,
                "company_id": interview.company_id,
                "reason":
                    "No alternative room available "
                    "at the same time"
            })

    db.session.commit()

    total = Interview.query.count()

    changed = (
        len(moved) +
        len(unscheduled)
    )

    churn = (
        changed / total * 100
        if total > 0
        else 0
    )

    print()
    print("=" * 70)
    print("REPLAN SUMMARY")
    print("=" * 70)

    print(
        f"Affected interviews : {len(affected)}"
    )

    print(
        f"Room changed        : {len(moved)}"
    )

    print(
        f"Unscheduled         : {len(unscheduled)}"
    )

    print(
        f"Replan churn        : {churn:.2f}%"
    )

    if moved:

        print()
        print("CHANGED INTERVIEWS")
        print("-" * 70)

        for item in moved[:20]:

            print(
                f"Interview {item['interview_id']} | "
                f"Student {item['student_id']} | "
                f"{item['old_room']} "
                f"-> {item['new_room']} | "
                f"Day {item['day']} "
                f"{item['start']}-{item['end']}"
            )

    if unscheduled:

        print()
        print("COULD NOT REPLAN")
        print("-" * 70)

        for item in unscheduled[:20]:

            print(
                f"Interview {item['interview_id']} | "
                f"Student {item['student_id']} | "
                f"{item['reason']}"
            )

    return {
        "affected": len(affected),
        "moved": len(moved),
        "unscheduled": len(unscheduled),
        "churn": churn
    }


# ============================================================
# COMPANY LATE ARRIVAL REPLANNER
# ============================================================

def replan_late_company(
    company_id,
    delay_hours,
    disruption_day=1
):

    company = db.session.get(
        Company,
        company_id
    )

    if company is None:

        print(
            f"Company {company_id} not found."
        )

        return

    # --------------------------------------------------------
    # CALCULATE NEW ARRIVAL TIME
    # --------------------------------------------------------

    original_arrival = to_minutes(
        company.arrival_time or "09:00"
    )

    # Interviews start at 09:00.
    original_arrival = max(
        original_arrival,
        9 * 60
    )

    delay_minutes = (
        delay_hours * 60
    )

    new_arrival = (
        original_arrival +
        delay_minutes
    )

    # --------------------------------------------------------
    # GET COMPANY INTERVIEWS ON DISRUPTION DAY
    # --------------------------------------------------------

    company_interviews = (
        Interview.query
        .filter_by(
            company_id=company_id,
            day=disruption_day,
            status="SCHEDULED"
        )
        .order_by(
            Interview.start_time
        )
        .all()
    )

    # --------------------------------------------------------
    # ONLY INTERVIEWS BEFORE NEW ARRIVAL ARE AFFECTED
    # --------------------------------------------------------

    affected = []

    for interview in company_interviews:

        start = to_minutes(
            interview.start_time
        )

        if start < new_arrival:

            affected.append(
                interview
            )

    print()
    print("=" * 70)
    print("COMPANY DELAY REPLAN")
    print("=" * 70)

    print(
        f"Company             : {company.name}"
    )

    print(
        f"Company ID          : {company_id}"
    )

    print(
        f"Original arrival    : "
        f"{minutes_to_time(original_arrival)}"
    )

    print(
        f"Delay               : "
        f"{delay_hours} hour(s)"
    )

    print(
        f"New arrival         : "
        f"{minutes_to_time(new_arrival)}"
    )

    print(
        f"Disruption day      : "
        f"Day {disruption_day}"
    )

    print(
        f"Company interviews  : "
        f"{len(company_interviews)}"
    )

    print(
        f"Affected interviews : "
        f"{len(affected)}"
    )

    if not affected:

        print()
        print(
            "No interviews require replanning."
        )

        return {
            "affected": 0,
            "moved": 0,
            "unscheduled": 0,
            "churn": 0
        }

    # --------------------------------------------------------
    # SAVE ORIGINAL INFORMATION
    # --------------------------------------------------------

    original_data = {}

    for interview in affected:

        original_data[
            interview.id
        ] = {

            "day":
                interview.day,

            "start":
                interview.start_time,

            "end":
                interview.end_time,

            "room_id":
                interview.room_id,

            "panel_id":
                interview.panel_id
        }

    # --------------------------------------------------------
    # TEMPORARILY REMOVE AFFECTED INTERVIEWS
    #
    # This allows them to be replanned without blocking
    # themselves.
    # --------------------------------------------------------

    for interview in affected:

        interview.status = (
            "PENDING_REPLAN"
        )

    db.session.flush()

    # --------------------------------------------------------
    # AVAILABLE ROOMS
    # --------------------------------------------------------

    available_rooms = (
        Room.query
        .filter(
            Room.available.is_(True)
        )
        .order_by(
            Room.id
        )
        .all()
    )

    # --------------------------------------------------------
    # AVAILABLE COMPANY PANELS
    # --------------------------------------------------------

    available_panels = (
        Panel.query
        .filter_by(
            company_id=company_id,
            available=True
        )
        .order_by(
            Panel.id
        )
        .all()
    )

    # --------------------------------------------------------
    # COMPANY AVAILABLE DAYS
    # --------------------------------------------------------

    company_days = []

    for value in company.available_days.split(","):

        value = value.strip()

        try:

            number = int(
                value.split()[1]
            )

            if 1 <= number <= 4:

                company_days.append(
                    number
                )

        except (
            IndexError,
            ValueError
        ):
            continue

    company_days = sorted(
        set(company_days)
    )

    # --------------------------------------------------------
    # SETTINGS
    # --------------------------------------------------------

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    SLOT_STEP = 5

    moved = []
    unscheduled = []

    # ========================================================
    # FIND AVAILABLE PANEL
    # ========================================================

    def find_panel(
        interview,
        day,
        start,
        end
    ):

        # Prefer the original panel.
        panel_order = sorted(
            available_panels,
            key=lambda panel:
                0
                if panel.id ==
                interview.panel_id
                else 1
        )

        for panel in panel_order:

            if panel_free(
                panel.id,
                day,
                start,
                end,
                interview.id
            ):

                return panel

        return None

    # ========================================================
    # FIND AVAILABLE ROOM
    # ========================================================

    def find_room(
        interview,
        day,
        start,
        end
    ):

        # Prefer original room.
        room_order = sorted(
            available_rooms,
            key=lambda room:
                0
                if room.id ==
                interview.room_id
                else 1
        )

        for candidate_room in room_order:

            if room_free(
                candidate_room.id,
                day,
                start,
                end,
                interview.id
            ):

                return candidate_room

        return None

    # ========================================================
    # REPLAN EACH AFFECTED INTERVIEW
    # ========================================================

    for interview in affected:

        old = original_data[
            interview.id
        ]

        old_start = to_minutes(
            old["start"]
        )

        old_end = to_minutes(
            old["end"]
        )

        duration = (
            old_end -
            old_start
        )

        placed = False

        # ----------------------------------------------------
        # OPTION 1:
        # TRY A LATER SLOT ON THE SAME DAY
        # ----------------------------------------------------

        preferred_start = max(
            old_start + delay_minutes,
            new_arrival
        )

        candidate_start = (
            preferred_start
        )

        while (
            candidate_start +
            duration
            <= WORK_END
        ):

            candidate_end = (
                candidate_start +
                duration
            )

            # Student check
            if not student_free(
                interview.student_id,
                disruption_day,
                candidate_start,
                candidate_end,
                interview.id
            ):

                candidate_start += (
                    SLOT_STEP
                )

                continue

            # Panel check
            selected_panel = find_panel(
                interview,
                disruption_day,
                candidate_start,
                candidate_end
            )

            if selected_panel is None:

                candidate_start += (
                    SLOT_STEP
                )

                continue

            # Room check
            selected_room = find_room(
                interview,
                disruption_day,
                candidate_start,
                candidate_end
            )

            if selected_room is None:

                candidate_start += (
                    SLOT_STEP
                )

                continue

            # ------------------------------------------------
            # SUCCESSFUL SAME-DAY REPLAN
            # ------------------------------------------------

            interview.day = (
                disruption_day
            )

            interview.start_time = (
                minutes_to_time(
                    candidate_start
                )
            )

            interview.end_time = (
                minutes_to_time(
                    candidate_end
                )
            )

            interview.room_id = (
                selected_room.id
            )

            interview.panel_id = (
                selected_panel.id
            )

            interview.status = (
                "SCHEDULED"
            )

            db.session.flush()

            moved.append({

                "interview_id":
                    interview.id,

                "student_id":
                    interview.student_id,

                "old_day":
                    old["day"],

                "old_start":
                    old["start"],

                "old_end":
                    old["end"],

                "old_room":
                    old["room_id"],

                "new_day":
                    interview.day,

                "new_start":
                    interview.start_time,

                "new_end":
                    interview.end_time,

                "new_room":
                    selected_room.id
            })

            placed = True

            break

        # ----------------------------------------------------
        # OPTION 2:
        # TRY A LATER COMPANY DAY
        # ----------------------------------------------------

        if not placed:

            later_days = [

                day

                for day in company_days

                if day >
                disruption_day
            ]

            for day in later_days:

                candidate_start = (
                    WORK_START
                )

                while (
                    candidate_start +
                    duration
                    <= WORK_END
                ):

                    candidate_end = (
                        candidate_start +
                        duration
                    )

                    if not student_free(
                        interview.student_id,
                        day,
                        candidate_start,
                        candidate_end,
                        interview.id
                    ):

                        candidate_start += (
                            SLOT_STEP
                        )

                        continue

                    selected_panel = (
                        find_panel(
                            interview,
                            day,
                            candidate_start,
                            candidate_end
                        )
                    )

                    if selected_panel is None:

                        candidate_start += (
                            SLOT_STEP
                        )

                        continue

                    selected_room = (
                        find_room(
                            interview,
                            day,
                            candidate_start,
                            candidate_end
                        )
                    )

                    if selected_room is None:

                        candidate_start += (
                            SLOT_STEP
                        )

                        continue

                    # ----------------------------------------
                    # SUCCESSFUL LATER-DAY REPLAN
                    # ----------------------------------------

                    interview.day = day

                    interview.start_time = (
                        minutes_to_time(
                            candidate_start
                        )
                    )

                    interview.end_time = (
                        minutes_to_time(
                            candidate_end
                        )
                    )

                    interview.room_id = (
                        selected_room.id
                    )

                    interview.panel_id = (
                        selected_panel.id
                    )

                    interview.status = (
                        "SCHEDULED"
                    )

                    db.session.flush()

                    moved.append({

                        "interview_id":
                            interview.id,

                        "student_id":
                            interview.student_id,

                        "old_day":
                            old["day"],

                        "old_start":
                            old["start"],

                        "old_end":
                            old["end"],

                        "old_room":
                            old["room_id"],

                        "new_day":
                            interview.day,

                        "new_start":
                            interview.start_time,

                        "new_end":
                            interview.end_time,

                        "new_room":
                            selected_room.id
                    })

                    placed = True

                    break

                if placed:
                    break

        # ----------------------------------------------------
        # STILL IMPOSSIBLE
        # ----------------------------------------------------

        if not placed:

            interview.status = (
                "UNSCHEDULED"
            )

            # Keep original values for reference.
            interview.day = (
                old["day"]
            )

            interview.start_time = (
                old["start"]
            )

            interview.end_time = (
                old["end"]
            )

            interview.room_id = (
                old["room_id"]
            )

            interview.panel_id = (
                old["panel_id"]
            )

            unscheduled.append({

                "interview_id":
                    interview.id,

                "student_id":
                    interview.student_id,

                "reason":
                    "No feasible later slot "
                    "without student, room "
                    "or panel conflict"
            })

    # --------------------------------------------------------
    # UPDATE COMPANY ARRIVAL TIME
    # --------------------------------------------------------

    company.arrival_time = (
        minutes_to_time(
            new_arrival
        )
    )

    db.session.commit()

    # ========================================================
    # METRICS
    # ========================================================

    total_interviews = (
        Interview.query.count()
    )

    changed_count = (
        len(moved) +
        len(unscheduled)
    )

    churn = (
        changed_count /
        total_interviews *
        100

        if total_interviews > 0

        else 0
    )

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print("=" * 70)
    print("REPLAN SUMMARY")
    print("=" * 70)

    print(
        f"Affected interviews : "
        f"{len(affected)}"
    )

    print(
        f"Successfully moved  : "
        f"{len(moved)}"
    )

    print(
        f"Unscheduled         : "
        f"{len(unscheduled)}"
    )

    print(
        f"Replan churn        : "
        f"{churn:.2f}%"
    )

    # --------------------------------------------------------
    # SHOW CHANGES
    # --------------------------------------------------------

    if moved:

        print()
        print("SCHEDULE CHANGES")
        print("-" * 70)

        for item in moved[:25]:

            print(
                f"Interview "
                f"{item['interview_id']} | "
                f"Student "
                f"{item['student_id']} | "
                f"Day "
                f"{item['old_day']} "
                f"{item['old_start']}-"
                f"{item['old_end']} "
                f"Room "
                f"{item['old_room']} "
                f"-> "
                f"Day "
                f"{item['new_day']} "
                f"{item['new_start']}-"
                f"{item['new_end']} "
                f"Room "
                f"{item['new_room']}"
            )

        if len(moved) > 25:

            print(
                f"... and "
                f"{len(moved) - 25} "
                f"more changes."
            )

    # --------------------------------------------------------
    # SHOW UNSCHEDULED
    # --------------------------------------------------------

    if unscheduled:

        print()
        print("COULD NOT REPLAN")
        print("-" * 70)

        for item in unscheduled[:20]:

            print(
                f"Interview "
                f"{item['interview_id']} | "
                f"Student "
                f"{item['student_id']} | "
                f"{item['reason']}"
            )

        if len(unscheduled) > 20:

            print(
                f"... and "
                f"{len(unscheduled) - 20} "
                f"more."
            )

    # --------------------------------------------------------
    # NOTIFICATIONS
    # --------------------------------------------------------

    students_to_notify = {

        item["student_id"]

        for item in moved
    }

    students_to_notify.update({

        item["student_id"]

        for item in unscheduled
    })

    print()
    print("NOTIFICATION SUMMARY")
    print("-" * 70)

    print(
        f"Students to notify : "
        f"{len(students_to_notify)}"
    )

    print(
        f"Company to notify  : "
        f"{company.name}"
    )

    return {

        "affected":
            len(affected),

        "moved":
            len(moved),

        "unscheduled":
            len(unscheduled),

        "churn":
            churn,

        "changes":
            moved,

        "failures":
            unscheduled
    }


# ============================================================
# MAIN
# ============================================================
def replan_dropped_panel(panel_id):

    panel = db.session.get(Panel, panel_id)

    if panel is None:
        print(f"Panel {panel_id} not found.")
        return

    company_id = panel.company_id

    affected = (
        Interview.query
        .filter_by(
            panel_id=panel_id,
            status="SCHEDULED"
        )
        .order_by(
            Interview.day,
            Interview.start_time
        )
        .all()
    )

    print()
    print("=" * 70)
    print("PANEL DROP REPLAN")
    print("=" * 70)

    print(f"Panel              : {panel.name}")
    print(f"Company ID         : {company_id}")
    print(f"Affected interviews: {len(affected)}")

    # Mark panel unavailable
    panel.available = False

    available_panels = (
        Panel.query
        .filter_by(
            company_id=company_id,
            available=True
        )
        .order_by(Panel.id)
        .all()
    )

    available_rooms = (
        Room.query
        .filter(
            Room.available.is_(True)
        )
        .order_by(Room.id)
        .all()
    )

    moved = []
    unscheduled = []

    WORK_START = 9 * 60
    WORK_END = 17 * 60
    SLOT_STEP = 5

    # Temporarily remove affected interviews
    for interview in affected:
        interview.status = "PENDING_REPLAN"

    db.session.flush()

    for interview in affected:

        old_day = interview.day
        old_start_text = interview.start_time
        old_end_text = interview.end_time
        old_room_id = interview.room_id

        old_start = to_minutes(
            interview.start_time
        )

        old_end = to_minutes(
            interview.end_time
        )

        duration = old_end - old_start

        placed = False

        # ----------------------------------------------------
        # OPTION 1:
        # Same day + same time + another panel
        # ----------------------------------------------------

        for candidate_panel in available_panels:

            if not panel_free(
                candidate_panel.id,
                old_day,
                old_start,
                old_end,
                interview.id
            ):
                continue

            # Prefer same room
            if room_free(
                old_room_id,
                old_day,
                old_start,
                old_end,
                interview.id
            ):

                interview.panel_id = (
                    candidate_panel.id
                )

                interview.status = "SCHEDULED"

                db.session.flush()

                moved.append({
                    "interview_id": interview.id,
                    "student_id": interview.student_id,
                    "old_panel": panel_id,
                    "new_panel": candidate_panel.id,
                    "old_day": old_day,
                    "new_day": old_day,
                    "old_start": old_start_text,
                    "old_end": old_end_text,
                    "new_start": old_start_text,
                    "new_end": old_end_text,
                    "old_room": old_room_id,
                    "new_room": old_room_id
                })

                placed = True
                break

        # ----------------------------------------------------
        # OPTION 2:
        # Same day + nearby later time
        # ----------------------------------------------------

        if not placed:

            candidate_start = old_start + SLOT_STEP

            while (
                candidate_start + duration
                <= WORK_END
            ):

                candidate_end = (
                    candidate_start + duration
                )

                if not student_free(
                    interview.student_id,
                    old_day,
                    candidate_start,
                    candidate_end,
                    interview.id
                ):

                    candidate_start += SLOT_STEP
                    continue

                selected_panel = None

                for candidate_panel in available_panels:

                    if panel_free(
                        candidate_panel.id,
                        old_day,
                        candidate_start,
                        candidate_end,
                        interview.id
                    ):

                        selected_panel = (
                            candidate_panel
                        )
                        break

                if selected_panel is None:

                    candidate_start += SLOT_STEP
                    continue

                selected_room = None

                # Prefer original room first
                room_order = sorted(
                    available_rooms,
                    key=lambda room:
                        0
                        if room.id == old_room_id
                        else 1
                )

                for candidate_room in room_order:

                    if room_free(
                        candidate_room.id,
                        old_day,
                        candidate_start,
                        candidate_end,
                        interview.id
                    ):

                        selected_room = (
                            candidate_room
                        )
                        break

                if selected_room is None:

                    candidate_start += SLOT_STEP
                    continue

                interview.panel_id = (
                    selected_panel.id
                )

                interview.room_id = (
                    selected_room.id
                )

                interview.start_time = (
                    minutes_to_time(
                        candidate_start
                    )
                )

                interview.end_time = (
                    minutes_to_time(
                        candidate_end
                    )
                )

                interview.status = "SCHEDULED"

                db.session.flush()

                moved.append({
                    "interview_id": interview.id,
                    "student_id": interview.student_id,
                    "old_panel": panel_id,
                    "new_panel": selected_panel.id,
                    "old_day": old_day,
                    "new_day": old_day,
                    "old_start": old_start_text,
                    "old_end": old_end_text,
                    "new_start": interview.start_time,
                    "new_end": interview.end_time,
                    "old_room": old_room_id,
                    "new_room": selected_room.id
                })

                placed = True
                break

        # ----------------------------------------------------
        # OPTION 3:
        # If impossible, mark unscheduled
        # ----------------------------------------------------

        if not placed:

            interview.status = "UNSCHEDULED"

            unscheduled.append({
                "interview_id": interview.id,
                "student_id": interview.student_id,
                "reason":
                    "No feasible alternative panel/time"
            })

    db.session.commit()

    total_interviews = (
        Interview.query.count()
    )

    changed = (
        len(moved) +
        len(unscheduled)
    )

    churn = (
        changed /
        total_interviews *
        100

        if total_interviews > 0

        else 0
    )

    print()
    print("=" * 70)
    print("REPLAN SUMMARY")
    print("=" * 70)

    print(
        f"Affected interviews : "
        f"{len(affected)}"
    )

    print(
        f"Successfully moved  : "
        f"{len(moved)}"
    )

    print(
        f"Unscheduled         : "
        f"{len(unscheduled)}"
    )

    print(
        f"Replan churn        : "
        f"{churn:.2f}%"
    )

    if moved:

        print()
        print("SCHEDULE CHANGES")
        print("-" * 70)

        for item in moved[:25]:

            print(
                f"Interview "
                f"{item['interview_id']} | "
                f"Student "
                f"{item['student_id']} | "
                f"Panel "
                f"{item['old_panel']} "
                f"-> "
                f"{item['new_panel']} | "
                f"Day "
                f"{item['old_day']} "
                f"{item['old_start']}-"
                f"{item['old_end']} "
                f"-> "
                f"Day "
                f"{item['new_day']} "
                f"{item['new_start']}-"
                f"{item['new_end']}"
            )

    if unscheduled:

        print()
        print("COULD NOT REPLAN")
        print("-" * 70)

        for item in unscheduled[:20]:

            print(
                f"Interview "
                f"{item['interview_id']} | "
                f"Student "
                f"{item['student_id']} | "
                f"{item['reason']}"
            )

    students_to_notify = {
        item["student_id"]
        for item in moved
    }

    students_to_notify.update(
        item["student_id"]
        for item in unscheduled
    )

    print()
    print("NOTIFICATION SUMMARY")
    print("-" * 70)

    print(
        f"Students to notify : "
        f"{len(students_to_notify)}"
    )

    print(
        f"Panel dropped      : "
        f"{panel.name}"
    )

    return {
        "affected": len(affected),
        "moved": len(moved),
        "unscheduled": len(unscheduled),
        "churn": churn
    }

# ============================================================
# STUDENT WITHDRAWAL
# ============================================================

def withdraw_student(student_id):

    from models.student import Student

    student = db.session.get(
        Student,
        student_id
    )

    if student is None:
        print(
            f"Student {student_id} not found."
        )
        return

    # Find all active interviews for this student
    interviews = (
        Interview.query
        .filter_by(
            student_id=student_id,
            status="SCHEDULED"
        )
        .order_by(
            Interview.day,
            Interview.start_time
        )
        .all()
    )

    print()
    print("=" * 70)
    print("STUDENT WITHDRAWAL")
    print("=" * 70)

    print(
        f"Student ID          : {student.id}"
    )

    print(
        f"Student name        : {student.name}"
    )

    print(
        f"Scheduled interviews: {len(interviews)}"
    )

    # Mark student withdrawn
    student.status = "WITHDRAWN"

    cancelled = []

    for interview in interviews:

        cancelled.append({
            "interview_id":
                interview.id,

            "company_id":
                interview.company_id,

            "day":
                interview.day,

            "start":
                interview.start_time,

            "end":
                interview.end_time,

            "room_id":
                interview.room_id,

            "panel_id":
                interview.panel_id
        })

        # We do not delete the interview.
        # Keeping it preserves history/audit information.
        interview.status = "CANCELLED"

    db.session.commit()

    total_interviews = (
        Interview.query.count()
    )

    churn = (
        len(cancelled) /
        total_interviews *
        100
        if total_interviews > 0
        else 0
    )

    print()
    print("=" * 70)
    print("WITHDRAWAL SUMMARY")
    print("=" * 70)

    print(
        f"Cancelled interviews: "
        f"{len(cancelled)}"
    )

    print(
        f"Replan churn        : "
        f"{churn:.2f}%"
    )

    if cancelled:

        print()
        print("CANCELLED INTERVIEWS")
        print("-" * 70)

        for item in cancelled:

            print(
                f"Interview "
                f"{item['interview_id']} | "
                f"Company "
                f"{item['company_id']} | "
                f"Day "
                f"{item['day']} | "
                f"{item['start']}-"
                f"{item['end']} | "
                f"Room "
                f"{item['room_id']} | "
                f"Panel "
                f"{item['panel_id']}"
            )

    company_ids = {
        item["company_id"]
        for item in cancelled
    }

    print()
    print("NOTIFICATION SUMMARY")
    print("-" * 70)

    print(
        f"Student status      : WITHDRAWN"
    )

    print(
        f"Companies to notify : "
        f"{len(company_ids)}"
    )

    if company_ids:

        print(
            "Company IDs         : "
            + ", ".join(
                map(
                    str,
                    sorted(company_ids)
                )
            )
        )

    return {
        "student_id":
            student_id,

        "cancelled":
            len(cancelled),

        "companies_to_notify":
            list(company_ids),

        "churn":
            churn
    }

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    with app.app_context():

        withdraw_student(
            student_id=425
        )