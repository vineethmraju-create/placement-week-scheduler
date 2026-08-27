from models.interview import Interview
from models.room import Room


def to_minutes(time_string):
    hour, minute = map(int, time_string.split(":"))
    return hour * 60 + minute


def calculate_metrics():

    scheduled = Interview.query.filter_by(
        status="SCHEDULED"
    ).all()

    unscheduled = Interview.query.filter_by(
        status="UNSCHEDULED"
    ).all()

    cancelled = Interview.query.filter_by(
        status="CANCELLED"
    ).all()

    total_required = (
        len(scheduled)
        + len(unscheduled)
    )

    if total_required > 0:
        scheduling_rate = (
            len(scheduled) / total_required
        ) * 100
    else:
        scheduling_rate = 0

    rooms = Room.query.all()

    total_room_minutes = (
        len(rooms)
        * 4
        * 8
        * 60
    )

    used_room_minutes = 0

    for interview in scheduled:

        start = to_minutes(
            interview.start_time
        )

        end = to_minutes(
            interview.end_time
        )

        used_room_minutes += (
            end - start
        )

    if total_room_minutes > 0:
        room_utilization = (
            used_room_minutes /
            total_room_minutes
        ) * 100
    else:
        room_utilization = 0

    student_conflicts = 0

    for i in range(len(scheduled)):

        first = scheduled[i]

        first_start = to_minutes(
            first.start_time
        )

        first_end = to_minutes(
            first.end_time
        )

        for j in range(
            i + 1,
            len(scheduled)
        ):

            second = scheduled[j]

            if (
                first.student_id
                != second.student_id
            ):
                continue

            if first.day != second.day:
                continue

            second_start = to_minutes(
                second.start_time
            )

            second_end = to_minutes(
                second.end_time
            )

            if (
                first_start < second_end
                and
                second_start < first_end
            ):
                student_conflicts += 1

    student_day_interviews = {}

    for interview in scheduled:

        key = (
            interview.student_id,
            interview.day
        )

        student_day_interviews.setdefault(
            key,
            []
        ).append(
            interview
        )

    waiting_times = []

    for interviews in (
        student_day_interviews.values()
    ):

        if len(interviews) < 2:
            continue

        interviews.sort(
            key=lambda item:
                to_minutes(
                    item.start_time
                )
        )

        for i in range(
            len(interviews) - 1
        ):

            current_end = to_minutes(
                interviews[i].end_time
            )

            next_start = to_minutes(
                interviews[i + 1].start_time
            )

            waiting = (
                next_start
                - current_end
            )

            if waiting >= 0:
                waiting_times.append(
                    waiting
                )

    if waiting_times:
        average_waiting_time = (
            sum(waiting_times)
            / len(waiting_times)
        )
    else:
        average_waiting_time = 0

    return {
        "total_scheduled":
            len(scheduled),

        "total_unscheduled":
            len(unscheduled),

        "total_cancelled":
            len(cancelled),

        "scheduling_rate":
            round(
                scheduling_rate,
                2
            ),

        "room_utilization":
            round(
                room_utilization,
                2
            ),

        "student_conflicts":
            student_conflicts,

        "average_waiting_time":
            round(
                average_waiting_time,
                2
            )
    }