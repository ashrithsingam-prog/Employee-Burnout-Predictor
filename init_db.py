from app import app
from models import db, Employee, WorkLog, Message, Assessment, HRAction, PeerReport
from mock_data import MOCK_DATA

def seed_database():
    with app.app_context():
        db.create_all()

        # Check if we already have data
        if Employee.query.first():
            print("Database already seeded. Skipping.")
            return

        print("Seeding Employees...")
        for emp_data in MOCK_DATA["employees"]:
            emp = Employee(
                id=emp_data["id"],
                name=emp_data["name"],
                email=emp_data["email"],
                department=emp_data["department"],
                role=emp_data["role"],
                join_date=emp_data["join_date"],
                is_hr=emp_data.get("is_hr", False),
                is_manager=emp_data.get("is_manager", False),
                manager=emp_data.get("manager")
            )
            db.session.add(emp)
        db.session.commit()

        print("Seeding WorkLogs...")
        for emp_id, logs in MOCK_DATA["work_logs"].items():
            for log in logs:
                wl = WorkLog(
                    employee_id=emp_id,
                    week_start=log["week_start"],
                    avg_daily_hours=log["avg_daily_hours"],
                    weekend_hours=log["weekend_hours"],
                    weekend_screen_time=log["weekend_screen_time"],
                    tasks_assigned=log["tasks_assigned"],
                    tasks_completed=log["tasks_completed"],
                    late_night_sessions=log["late_night_sessions"],
                    breaks_taken_per_day=log["breaks_taken_per_day"]
                )
                db.session.add(wl)
        db.session.commit()

        print("Seeding Messages...")
        for emp_id, msgs in MOCK_DATA["messages"].items():
            for msg in msgs:
                m = Message(
                    employee_id=emp_id,
                    timestamp=msg["timestamp"],
                    content=msg["content"],
                    channel=msg["channel"]
                )
                db.session.add(m)
        db.session.commit()

        print("Seeding Assessments...")
        for emp_id, assessments in MOCK_DATA["assessments"].items():
            for ast in assessments:
                a = Assessment(
                    id=ast["id"],
                    employee_id=emp_id,
                    timestamp=ast["timestamp"],
                    answers=ast["answers"],
                    response_times=ast.get("response_times", {}),
                    is_fake_attempt=ast.get("is_fake_attempt", False)
                )
                db.session.add(a)
        db.session.commit()

        print("Database seeding completed successfully.")

if __name__ == "__main__":
    seed_database()
