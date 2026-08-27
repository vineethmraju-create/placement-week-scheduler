from app import app
from extensions import db

from models.company import Company
from models.room import Room
from models.panel import Panel
from models.interview import Interview


# ============================================================
# SCHEDULER SETTINGS
# ============================================================

START_TIME = 9 * 60       # 09:00
END_TIME = 17 * 60        # 17:00
SLOT_STEP = 5
NUMBER_OF_DAYS = 4


# ============================================================
# TIME FUNCTIONS
# ============================================================

def minutes_to_time(minutes):
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours:02d}:{mins:02d}"


# ============================================================
# OVERLAP CHECK
# ============================================================

def overlaps(start1, end1, start2, end2):
    return start1 < end2 and start2 < end1


# ============================================================
# SCHEDULE ENGINE
# ============================================================

def generate_schedule():

    print()
    print("=" * 60)
    print("STARTING OPTIMIZED PLACEMENT SCHEDULER")
    print("=" * 60)

    # --------------------------------------------------------
    # Remove previous schedule
    # --------------------------------------------------------

    Interview.query.delete()
    db.session.commit()

    # --------------------------------------------------------
    # Load data ONCE
    # --------------------------------------------------------

    rooms = Room.query.order_by(Room.id).all()

    companies = Company.query.order_by(
        Company.priority_tier.asc(),
        Company.id.asc()
    ).all()

    # --------------------------------------------------------
    # In-memory availability
    #
    # student_schedule[student_id][day] = [(start, end), ...]
    #
    # room_schedule[room_id][day] = [(start, end), ...]
    #
    # panel_schedule[panel_id][day] = [(start, end), ...]
    # --------------------------------------------------------

    student_schedule = {}
    room_schedule = {}
    panel_schedule = {}

    scheduled_count = 0
    unscheduled_count = 0

    unscheduled_reasons = []

    # ========================================================
    # PROCESS COMPANIES
    # ========================================================

    for company in companies:

        print(
            f"Scheduling {company.name} "
            f"({company.priority_tier})"
        )

        # ----------------------------------------------------
        # Company panels
        # ----------------------------------------------------

        panels = [
            panel
            for panel in company.panels
            if panel.available
        ]

        # ----------------------------------------------------
        # Available company days
        # ----------------------------------------------------

        company_days = [
            int(day.strip().split()[1])
            for day in company.available_days.split(",")
            if int(day.strip().split()[1]) <= NUMBER_OF_DAYS
        ]

        # ----------------------------------------------------
        # Students
        # ----------------------------------------------------

        students = sorted(
            company.shortlisted_students,
            key=lambda student: student.cgpa,
            reverse=True
        )

        # ----------------------------------------------------
        # Schedule each student
        # ----------------------------------------------------

        for student in students:

            scheduled = False

            duration = company.interview_duration

            for day in company_days:

                if scheduled:
                    break

                # ------------------------------------------------
                # Try each time position
                # ------------------------------------------------

                start = START_TIME

                while start + duration <= END_TIME:

                    end = start + duration

                    # ==========================================
                    # STUDENT CHECK
                    # ==========================================

                    student_busy = False

                    student_intervals = student_schedule.get(
                        student.id,
                        {}
                    ).get(day, [])

                    for existing_start, existing_end in student_intervals:

                        if overlaps(
                            start,
                            end,
                            existing_start,
                            existing_end
                        ):
                            student_busy = True
                            break

                    if student_busy:
                        start += SLOT_STEP
                        continue

                    # ==========================================
                    # FIND FREE ROOM
                    # ==========================================

                    selected_room = None

                    for room in rooms:

                        if not room.available:
                            continue

                        room_intervals = room_schedule.get(
                            room.id,
                            {}
                        ).get(day, [])

                        room_busy = False

                        for existing_start, existing_end in room_intervals:

                            if overlaps(
                                start,
                                end,
                                existing_start,
                                existing_end
                            ):
                                room_busy = True
                                break

                        if not room_busy:

                            selected_room = room
                            break

                    if selected_room is None:

                        start += SLOT_STEP
                        continue

                    # ==========================================
                    # FIND FREE PANEL
                    # ==========================================

                    selected_panel = None

                    for panel in panels:

                        panel_intervals = panel_schedule.get(
                            panel.id,
                            {}
                        ).get(day, [])

                        panel_busy = False

                        for existing_start, existing_end in panel_intervals:

                            if overlaps(
                                start,
                                end,
                                existing_start,
                                existing_end
                            ):
                                panel_busy = True
                                break

                        if not panel_busy:

                            selected_panel = panel
                            break

                    if selected_panel is None:

                        start += SLOT_STEP
                        continue

                    # ==========================================
                    # CREATE INTERVIEW
                    # ==========================================

                    interview = Interview(
                        student_id=student.id,
                        company_id=company.id,
                        room_id=selected_room.id,
                        panel_id=selected_panel.id,
                        day=day,
                        start_time=minutes_to_time(start),
                        end_time=minutes_to_time(end),
                        status="SCHEDULED"
                    )

                    db.session.add(interview)

                    # ==========================================
                    # UPDATE MEMORY
                    # ==========================================

                    student_schedule.setdefault(
                        student.id,
                        {}
                    ).setdefault(
                        day,
                        []
                    ).append(
                        (start, end)
                    )

                    room_schedule.setdefault(
                        selected_room.id,
                        {}
                    ).setdefault(
                        day,
                        []
                    ).append(
                        (start, end)
                    )

                    panel_schedule.setdefault(
                        selected_panel.id,
                        {}
                    ).setdefault(
                        day,
                        []
                    ).append(
                        (start, end)
                    )

                    scheduled_count += 1
                    scheduled = True

                    break

                # End while

            # End days

            if not scheduled:

                unscheduled_count += 1

                unscheduled_reasons.append({
                    "student": student.name,
                    "company": company.name,
                    "reason": (
                        "No feasible combination "
                        "of available day, time, room and panel"
                    )
                })

    # --------------------------------------------------------
    # Save all interviews
    # --------------------------------------------------------

    db.session.commit()

    # ========================================================
    # FINAL REPORT
    # ========================================================

    total_requested = (
        scheduled_count +
        unscheduled_count
    )

    print()
    print("=" * 60)
    print("SCHEDULING COMPLETE")
    print("=" * 60)

    print(
        f"Requested interviews  : {total_requested}"
    )

    print(
        f"Scheduled interviews  : {scheduled_count}"
    )

    print(
        f"Unscheduled interviews: {unscheduled_count}"
    )

    if total_requested > 0:

        success_rate = (
            scheduled_count /
            total_requested
        ) * 100

        print(
            f"Scheduling success    : "
            f"{success_rate:.2f}%"
        )

    print("=" * 60)

    # --------------------------------------------------------
    # Show failures
    # --------------------------------------------------------

    if unscheduled_reasons:

        print()
        print("UNSCHEDULED INTERVIEWS")
        print("-" * 60)

        for item in unscheduled_reasons[:20]:

            print(
                f"{item['student']} | "
                f"{item['company']} | "
                f"{item['reason']}"
            )

        if len(unscheduled_reasons) > 20:

            print(
                f"... and "
                f"{len(unscheduled_reasons) - 20} more."
            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    with app.app_context():

        generate_schedule()