import random

from app import app
from extensions import db


from models.company import Company
from models.student import Student
from models.room import Room
from models.panel import Panel

app.app_context().push()


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

random.seed(42)

NUMBER_OF_COMPANIES = 35
NUMBER_OF_STUDENTS = 800
NUMBER_OF_ROOMS = 20


# --------------------------------------------------
# SAMPLE DATA
# --------------------------------------------------

company_names = [
    "TCS",
    "Infosys",
    "Wipro",
    "Accenture",
    "Cognizant",
    "Capgemini",
    "Deloitte",
    "IBM",
    "HCLTech",
    "Tech Mahindra",
    "LTIMindtree",
    "Oracle",
    "Microsoft",
    "Amazon",
    "Cisco",
    "Dell",
    "SAP",
    "EY",
    "KPMG",
    "PwC",
    "Genpact",
    "Mphasis",
    "Mindtree",
    "Hexaware",
    "Persistent Systems",
    "Coforge",
    "UST",
    "Virtusa",
    "Zoho",
    "Freshworks",
    "Razorpay",
    "PhonePe",
    "Juspay",
    "Mu Sigma",
    "Bosch"
]

branches = [
    "MCA",
    "CSE",
    "ISE",
    "ECE"
]

priority_tiers = [
    "TIER-1",
    "TIER-2",
    "TIER-3"
]

days = [
    "Day 1",
    "Day 2",
    "Day 3",
    "Day 4",
    "Day 5"
]


# --------------------------------------------------
# RESET DATABASE
# --------------------------------------------------

print("Resetting database...")

db.session.remove()

db.drop_all()
db.create_all()

print("Database reset complete.")


# --------------------------------------------------
# CREATE COMPANIES
# --------------------------------------------------

print("Creating companies...")

companies = []

for i, name in enumerate(company_names):

    if i < 10:
        tier = "TIER-1"
        cutoff = round(random.uniform(7.5, 8.5), 2)
    elif i < 25:
        tier = "TIER-2"
        cutoff = round(random.uniform(6.5, 7.5), 2)
    else:
        tier = "TIER-3"
        cutoff = round(random.uniform(5.5, 7.0), 2)

    duration = random.choice([
        20,
        30,
        45,
        60
    ])

    panel_count = random.randint(1, 4)

    available_days = random.sample(
        days,
        random.randint(2, 5)
    )

    company = Company(
        name=name,
        cgpa_cutoff=cutoff,
        interview_duration=duration,
        panel_count=panel_count,
        priority_tier=tier,
        available_days=",".join(available_days),
        arrival_time=random.choice([
            "08:30",
            "09:00",
            "09:30",
            "10:00"
        ])
    )

    db.session.add(company)
    companies.append(company)


db.session.commit()

print(f"Created {len(companies)} companies.")


# --------------------------------------------------
# CREATE PANELS
# --------------------------------------------------

print("Creating panels...")

panel_count = 0

for company in companies:

    for number in range(1, company.panel_count + 1):

        panel = Panel(
            name=f"{company.name}-P{number:02d}",
            company_id=company.id,
            available=True
        )

        db.session.add(panel)

        panel_count += 1


db.session.commit()

print(f"Created {panel_count} panels.")


# --------------------------------------------------
# CREATE STUDENTS
# --------------------------------------------------

print("Creating students...")

students = []

for i in range(1, NUMBER_OF_STUDENTS + 1):

    student = Student(
        name=f"Student {i:03d}",
        cgpa=round(random.uniform(5.5, 9.8), 2),
        branch=random.choice(branches),
        status="ACTIVE"
    )

    db.session.add(student)
    students.append(student)


db.session.commit()

print(f"Created {len(students)} students.")


# --------------------------------------------------
# CREATE COMPANY SHORTLISTS
# --------------------------------------------------

print("Creating company shortlists...")

shortlist_count = 0

for company in companies:

    eligible_students = [
        student
        for student in students
        if student.cgpa >= company.cgpa_cutoff
    ]

    # Select a realistic number of students
    maximum = min(180, len(eligible_students))

    if maximum >= 50:
        selected_count = random.randint(50, maximum)
    else:
        selected_count = maximum

    selected_students = random.sample(
        eligible_students,
        selected_count
    )

    company.shortlisted_students.extend(
        selected_students
    )

    shortlist_count += selected_count


db.session.commit()

print(f"Created {shortlist_count} shortlist entries.")


# --------------------------------------------------
# CREATE ROOMS
# --------------------------------------------------

print("Creating rooms...")

for i in range(1, NUMBER_OF_ROOMS + 1):

    room = Room(
        name=f"R{i:02d}",
        available=True
    )

    db.session.add(room)


db.session.commit()

print(f"Created {NUMBER_OF_ROOMS} rooms.")


# --------------------------------------------------
# FINAL SUMMARY
# --------------------------------------------------

print()
print("=" * 50)
print("DATASET CREATION COMPLETE")
print("=" * 50)

print(f"Companies : {Company.query.count()}")
print(f"Students  : {Student.query.count()}")
print(f"Panels    : {Panel.query.count()}")
print(f"Rooms     : {Room.query.count()}")
print(f"Shortlists: {shortlist_count}")

print("=" * 50)