from models.interview import Interview


def to_minutes(time_string):
    hours, minutes = map(
        int,
        time_string.split(":")
    )

    return hours * 60 + minutes


def overlaps(
    start1,
    end1,
    start2,
    end2
):
    return (
        start1 < end2
        and start2 < end1
    )


def validate_schedule():

    interviews = (
        Interview.query
        .filter_by(
            status="SCHEDULED"
        )
        .all()
    )

    student_conflicts = 0
    room_conflicts = 0
    panel_conflicts = 0
    duration_errors = 0


    # ========================================================
    # CHECK DURATION ERRORS
    # ========================================================

    for interview in interviews:

        start = to_minutes(
            interview.start_time
        )

        end = to_minutes(
            interview.end_time
        )

        if end <= start:

            duration_errors += 1


    # ========================================================
    # CHECK CONFLICTS
    # ========================================================

    for i in range(
        len(interviews)
    ):

        first = interviews[i]

        first_start = to_minutes(
            first.start_time
        )

        first_end = to_minutes(
            first.end_time
        )


        for j in range(
            i + 1,
            len(interviews)
        ):

            second = interviews[j]

            # Different days cannot clash
            if first.day != second.day:
                continue


            second_start = to_minutes(
                second.start_time
            )

            second_end = to_minutes(
                second.end_time
            )


            if not overlaps(
                first_start,
                first_end,
                second_start,
                second_end
            ):
                continue


            # Student conflict
            if (
                first.student_id
                == second.student_id
            ):

                student_conflicts += 1


            # Room conflict
            if (
                first.room_id
                == second.room_id
            ):

                room_conflicts += 1


            # Panel conflict
            if (
                first.panel_id
                == second.panel_id
            ):

                panel_conflicts += 1


    # ========================================================
    # FINAL VALIDATION STATUS
    # ========================================================

    is_valid = (
        student_conflicts == 0
        and room_conflicts == 0
        and panel_conflicts == 0
        and duration_errors == 0
    )


    return {

        "total_interviews":
            len(interviews),

        "student_conflicts":
            student_conflicts,

        "room_conflicts":
            room_conflicts,

        "panel_conflicts":
            panel_conflicts,

        "duration_errors":
            duration_errors,

        "is_valid":
            is_valid
    }