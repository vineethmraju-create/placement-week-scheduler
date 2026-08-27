from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from config import Config
from extensions import db

from models.company import Company
from models.student import Student
from models.room import Room
from models.panel import Panel
from models.interview import Interview

from metrics import calculate_metrics
from validate_schedule import validate_schedule


# ============================================================
# CREATE APP
# ============================================================

app = Flask(__name__)

app.config.from_object(Config)

app.secret_key = "placement_scheduler_secret"

db.init_app(app)


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
def dashboard():

    # --------------------------------------------------------
    # BASIC COUNTS
    # --------------------------------------------------------

    total_interviews = Interview.query.count()

    scheduled_interviews = Interview.query.filter_by(
        status="SCHEDULED"
    ).count()

    cancelled_interviews = Interview.query.filter_by(
        status="CANCELLED"
    ).count()

    unscheduled_interviews = Interview.query.filter_by(
        status="UNSCHEDULED"
    ).count()

    companies = Company.query.count()

    students = Student.query.count()


    # --------------------------------------------------------
    # ROOMS
    # --------------------------------------------------------

    available_rooms = Room.query.filter_by(
        available=True
    ).count()

    unavailable_rooms = Room.query.filter_by(
        available=False
    ).count()


    # --------------------------------------------------------
    # PANELS
    # --------------------------------------------------------

    available_panels = Panel.query.filter_by(
        available=True
    ).count()

    unavailable_panels = Panel.query.filter_by(
        available=False
    ).count()


    # --------------------------------------------------------
    # UPCOMING INTERVIEWS
    # --------------------------------------------------------

    upcoming_interviews = (
        Interview.query
        .filter_by(
            status="SCHEDULED"
        )
        .order_by(
            Interview.day,
            Interview.start_time
        )
        .limit(20)
        .all()
    )


    # --------------------------------------------------------
    # DROPDOWN DATA
    # --------------------------------------------------------

    all_companies = (
        Company.query
        .order_by(
            Company.name
        )
        .all()
    )

    all_panels = (
        Panel.query
        .order_by(
            Panel.name
        )
        .all()
    )

    all_rooms = (
        Room.query
        .order_by(
            Room.name
        )
        .all()
    )


    # --------------------------------------------------------
    # PERFORMANCE METRICS
    # --------------------------------------------------------

    schedule_metrics = (
        calculate_metrics()
    )


    # --------------------------------------------------------
    # SCHEDULE VALIDATION
    # --------------------------------------------------------

    validation = (
        validate_schedule()
    )


    # --------------------------------------------------------
    # RECENT REPLAN
    # --------------------------------------------------------

    latest_replan = session.get(
        "latest_replan"
    )


    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render_template(
        "dashboard.html",

        total_interviews=total_interviews,

        scheduled_interviews=scheduled_interviews,

        cancelled_interviews=cancelled_interviews,

        unscheduled_interviews=unscheduled_interviews,

        companies=companies,

        students=students,

        available_rooms=available_rooms,

        unavailable_rooms=unavailable_rooms,

        available_panels=available_panels,

        unavailable_panels=unavailable_panels,

        upcoming_interviews=upcoming_interviews,

        all_companies=all_companies,

        all_panels=all_panels,

        all_rooms=all_rooms,

        schedule_metrics=schedule_metrics,

        validation=validation,

        latest_replan=latest_replan
    )


# ============================================================
# STUDENT WITHDRAWAL
# ============================================================

@app.route(
    "/withdraw-student",
    methods=["POST"]
)
def withdraw_student_route():

    student_id = request.form.get(
        "student_id"
    )

    if not student_id:

        flash(
            "Please enter a student ID."
        )

        return redirect(
            url_for("dashboard")
        )


    try:

        student_id = int(
            student_id
        )

    except ValueError:

        flash(
            "Invalid student ID."
        )

        return redirect(
            url_for("dashboard")
        )


    student = db.session.get(
        Student,
        student_id
    )


    if student is None:

        flash(
            f"Student ID {student_id} not found."
        )

        return redirect(
            url_for("dashboard")
        )


    if student.status == "WITHDRAWN":

        flash(
            f"Student {student_id} has already withdrawn."
        )

        return redirect(
            url_for("dashboard")
        )


    from replanner import withdraw_student


    result = withdraw_student(
        student_id
    )


    if result:

        session["latest_replan"] = {

            "type":
                "Student Withdrawal",

            "affected":
                result["cancelled"],

            "moved":
                0,

            "unscheduled":
                0,

            "churn":
                round(
                    result["churn"],
                    2
                )
        }


        flash(
            f"Student {student_id} withdrawn successfully. "
            f"{result['cancelled']} interview(s) cancelled."
        )

    else:

        flash(
            "Unable to process student withdrawal."
        )


    return redirect(
        url_for("dashboard")
    )


# ============================================================
# PANEL DROP
# ============================================================

@app.route(
    "/drop-panel",
    methods=["POST"]
)
def drop_panel_route():

    panel_id = request.form.get(
        "panel_id"
    )


    if not panel_id:

        flash(
            "Please select a panel."
        )

        return redirect(
            url_for("dashboard")
        )


    try:

        panel_id = int(
            panel_id
        )

    except ValueError:

        flash(
            "Invalid panel ID."
        )

        return redirect(
            url_for("dashboard")
        )


    panel = db.session.get(
        Panel,
        panel_id
    )


    if panel is None:

        flash(
            f"Panel ID {panel_id} not found."
        )

        return redirect(
            url_for("dashboard")
        )


    if not panel.available:

        flash(
            f"Panel {panel.name} is already unavailable."
        )

        return redirect(
            url_for("dashboard")
        )


    panel_name = panel.name


    from replanner import replan_dropped_panel


    result = replan_dropped_panel(
        panel_id
    )


    if result:

        session["latest_replan"] = {

            "type":
                "Panel Drop",

            "affected":
                result["affected"],

            "moved":
                result["moved"],

            "unscheduled":
                result["unscheduled"],

            "churn":
                round(
                    result["churn"],
                    2
                )
        }


        flash(
            f"Panel {panel_name} dropped. "
            f"{result['affected']} interview(s) affected, "
            f"{result['moved']} moved, "
            f"{result['unscheduled']} unscheduled."
        )

    else:

        flash(
            "Unable to process panel drop."
        )


    return redirect(
        url_for("dashboard")
    )


# ============================================================
# ROOM UNAVAILABLE
# ============================================================

@app.route(
    "/disable-room",
    methods=["POST"]
)
def disable_room_route():

    room_id = request.form.get(
        "room_id"
    )


    if not room_id:

        flash(
            "Please select a room."
        )

        return redirect(
            url_for("dashboard")
        )


    try:

        room_id = int(
            room_id
        )

    except ValueError:

        flash(
            "Invalid room ID."
        )

        return redirect(
            url_for("dashboard")
        )


    room = db.session.get(
        Room,
        room_id
    )


    if room is None:

        flash(
            f"Room ID {room_id} not found."
        )

        return redirect(
            url_for("dashboard")
        )


    if not room.available:

        flash(
            f"Room {room.name} is already unavailable."
        )

        return redirect(
            url_for("dashboard")
        )


    room_name = room.name


    room.available = False

    db.session.commit()


    from replanner import replan_unavailable_room


    result = replan_unavailable_room(
        room_id
    )


    if result:

        session["latest_replan"] = {

            "type":
                "Room Unavailable",

            "affected":
                result["affected"],

            "moved":
                result["moved"],

            "unscheduled":
                result["unscheduled"],

            "churn":
                round(
                    result["churn"],
                    2
                )
        }


        flash(
            f"Room {room_name} marked unavailable. "
            f"{result['affected']} interview(s) affected, "
            f"{result['moved']} moved, "
            f"{result['unscheduled']} unscheduled."
        )

    else:

        flash(
            f"Room {room_name} marked unavailable."
        )


    return redirect(
        url_for("dashboard")
    )


# ============================================================
# COMPANY DELAY
# ============================================================

@app.route(
    "/company-delay",
    methods=["POST"]
)
def company_delay_route():

    company_id = request.form.get(
        "company_id"
    )

    delay_hours = request.form.get(
        "delay_hours"
    )

    disruption_day = request.form.get(
        "disruption_day"
    )


    if (
        not company_id
        or not delay_hours
        or not disruption_day
    ):

        flash(
            "Please select a company and enter "
            "Delay Hours and Day."
        )

        return redirect(
            url_for("dashboard")
        )


    try:

        company_id = int(
            company_id
        )

        delay_hours = int(
            delay_hours
        )

        disruption_day = int(
            disruption_day
        )

    except ValueError:

        flash(
            "Company, Delay Hours and Day "
            "must contain valid numbers."
        )

        return redirect(
            url_for("dashboard")
        )


    company = db.session.get(
        Company,
        company_id
    )


    if company is None:

        flash(
            f"Company ID {company_id} not found."
        )

        return redirect(
            url_for("dashboard")
        )


    if delay_hours <= 0:

        flash(
            "Delay hours must be greater than 0."
        )

        return redirect(
            url_for("dashboard")
        )


    if (
        disruption_day < 1
        or disruption_day > 4
    ):

        flash(
            "Day must be between 1 and 4."
        )

        return redirect(
            url_for("dashboard")
        )


    company_name = company.name


    from replanner import replan_late_company


    result = replan_late_company(
        company_id=company_id,
        delay_hours=delay_hours,
        disruption_day=disruption_day
    )


    if result:

        session["latest_replan"] = {

            "type":
                "Company Delay",

            "affected":
                result["affected"],

            "moved":
                result["moved"],

            "unscheduled":
                result["unscheduled"],

            "churn":
                round(
                    result["churn"],
                    2
                )
        }


        flash(
            f"{company_name} delayed by "
            f"{delay_hours} hour(s) on Day {disruption_day}. "
            f"{result['affected']} interview(s) affected, "
            f"{result['moved']} moved, "
            f"{result['unscheduled']} unscheduled."
        )

    else:

        flash(
            f"No interviews required replanning "
            f"for {company_name}."
        )


    return redirect(
        url_for("dashboard")
    )


# ============================================================
# CLEAR RECENT REPLAN
# ============================================================

@app.route(
    "/clear-replan",
    methods=["POST"]
)
def clear_replan():

    session.pop(
        "latest_replan",
        None
    )


    return redirect(
        url_for("dashboard")
    )


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

    app.run(
        debug=True
    )