"""
Employee Burnout Prediction & Monitoring — Flask Server
============================================================
Server-side rendered pages + JSON API endpoints for employee login,
burnout assessments, HR dashboard, peer reporting, HR actions, and
anti-faking intelligence.
"""

from flask import (
    Flask, jsonify, request, render_template,
    session, redirect, url_for, flash,
)
from datetime import datetime
import uuid
import os

from mock_data import ASSESSMENT_QUESTIONS
from models import db, Employee, WorkLog, Message, Assessment, HRAction, PeerReport
from burnout_engine import (
    compute_burnout_score,
    analyze_messages,
    detect_faking,
    generate_alerts,
    compute_assessment_score,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates"),
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "burnshield-dev-key-change-in-production")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///burnshield.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)



# ─────────────────────────────────────────────────────────────────────────────
# Template Context Processor — inject session info into every template
# ─────────────────────────────────────────────────────────────────────────────

@app.context_processor
def inject_session_globals():
    """Make session data available in all templates."""
    emp_id = session.get("emp_id")
    current_employee = None
    if emp_id:
        emp = db.session.get(Employee, emp_id)
        if emp:
            current_employee = emp.to_dict()
    return {
        "session": session,
        "current_employee": current_employee,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def login_required(f):
    """Decorator to require login for a page route."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "emp_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def hr_required(f):
    """Decorator to require HR role for a page route."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "emp_id" not in session:
            return redirect(url_for("login"))
        if not session.get("is_hr"):
            flash("Access denied. HR credentials required.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


def get_employee_burnout(emp_id):
    """Compute full burnout analysis for one employee."""
    assessments = [a.to_dict() for a in Assessment.query.filter_by(employee_id=emp_id).all()]
    work_logs = [w.to_dict() for w in WorkLog.query.filter_by(employee_id=emp_id).all()]
    messages = [m.to_dict() for m in Message.query.filter_by(employee_id=emp_id).all()]
    return compute_burnout_score(emp_id, assessments, work_logs, messages)


def employee_summary(emp_dict):
    """Return a safely serializable summary of an employee (no hidden fields)."""
    burnout = get_employee_burnout(emp_dict["id"])
    return {
        "id": emp_dict["id"],
        "name": emp_dict["name"],
        "email": emp_dict["email"],
        "department": emp_dict["department"],
        "role": emp_dict["role"],
        "join_date": emp_dict["join_date"],
        "is_hr": emp_dict.get("is_hr", False),
        "burnout_score": burnout["adjusted_score"],
        "risk_level": burnout["risk_level"],
        "last_assessment": burnout["last_assessment_date"],
        "faking_suspected": burnout["faking_detection"]["is_suspicious"],
    }


# ═════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES (Server-Side Rendered)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Root — landing page or redirect to dashboard."""
    if "emp_id" in session:
        if session.get("is_hr"):
            return redirect(url_for("hr_dashboard"))
        return redirect(url_for("dashboard"))
    return render_template("index.html")


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    """Employee login page."""
    if request.method == "POST":
        emp_id = request.form.get("emp_id", "").strip().upper()

        if not emp_id:
            return render_template("login.html", error="Please enter your Employee ID.")

        emp = db.session.get(Employee, emp_id)
        if not emp:
            return render_template("login.html", error=f"Employee {emp_id} not found.")
        
        employee = emp.to_dict()

        # Store in session
        session["emp_id"] = emp_id
        session["is_hr"] = employee.get("is_hr", False)
        session["is_manager"] = employee.get("is_manager", False)
        
        emp.last_login = datetime.now().isoformat()
        db.session.commit()

        if employee.get("is_hr"):
            return redirect(url_for("hr_dashboard"))
        return redirect(url_for("dashboard"))

    return render_template("login.html", error=None)


@app.route("/logout")
def logout():
    """Clear session and redirect to login."""
    session.clear()
    return redirect(url_for("login"))


# ─────────────────────────────────────────────────────────────────────────────
# EMPLOYEE DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    """Employee's personal wellbeing dashboard."""
    emp_id = session["emp_id"]
    emp = db.session.get(Employee, emp_id)
    employee = emp.to_dict()
    burnout = get_employee_burnout(emp_id)
    assessments = [a.to_dict() for a in Assessment.query.filter_by(employee_id=emp_id).all()]
    work_logs = [w.to_dict() for w in WorkLog.query.filter_by(employee_id=emp_id).order_by(WorkLog.id.desc()).limit(4).all()][::-1]  # Last 4 weeks
    hr_actions = [h.to_dict() for h in HRAction.query.filter_by(employee_id=emp_id).all()]

    team_actions = []
    if employee.get("is_manager"):
        team = Employee.query.filter_by(manager=emp_id).all()
        for t_emp in team:
            if t_emp.id != emp_id:
                actions = HRAction.query.filter_by(employee_id=t_emp.id).all()
                for action in actions:
                    team_actions.append({
                        "employee_name": t_emp.name,
                        "employee_id": t_emp.id,
                        "action": action.to_dict(),
                    })
        team_actions.sort(key=lambda x: x["action"].get("timestamp", ""), reverse=True)

    return render_template(
        "dashboard.html",
        employee=employee,
        burnout=burnout,
        assessments=assessments,
        work_logs=work_logs,
        hr_actions=hr_actions,
        team_actions=team_actions,
        active_page="dashboard",
    )


# ─────────────────────────────────────────────────────────────────────────────
# BURNOUT ASSESSMENT
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/assessment", methods=["GET", "POST"])
@login_required
def assessment():
    """Burnout assessment form and submission."""
    emp_id = session["emp_id"]
    emp = db.session.get(Employee, emp_id)
    employee = emp.to_dict()

    if request.method == "POST":
        import json
        answers = {}
        try:
            response_times = json.loads(request.form.get("response_times", "{}"))
        except json.JSONDecodeError:
            response_times = {}

        for q in ASSESSMENT_QUESTIONS:
            val = request.form.get(q["id"])
            if val is None:
                return render_template(
                    "assesment.html",
                    questions=ASSESSMENT_QUESTIONS,
                    error="Please answer all questions.",
                    active_page="assessment",
                )
            answers[q["id"]] = int(val)

        # Create assessment record
        assessment_record = {
            "id": str(uuid.uuid4())[:8],
            "employee_id": emp_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "answers": answers,
            "response_times": response_times,
            "is_fake_attempt": False,
        }

        # Store
        a = Assessment(
            id=assessment_record["id"],
            employee_id=assessment_record["employee_id"],
            timestamp=assessment_record["timestamp"],
            answers=assessment_record["answers"],
            response_times=assessment_record["response_times"],
            is_fake_attempt=assessment_record["is_fake_attempt"]
        )
        db.session.add(a)
        db.session.commit()

        # Compute updated burnout
        burnout = get_employee_burnout(emp_id)

        return render_template(
            "assesment_result.html",
            burnout=burnout,
            employee=employee,
            active_page="assessment",
        )

    # GET — show the assessment form
    return render_template(
        "assesment.html",
        questions=ASSESSMENT_QUESTIONS,
        error=None,
        active_page="assessment",
    )


# ─────────────────────────────────────────────────────────────────────────────
# PEER REPORT
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/peer-report", methods=["GET", "POST"])
@login_required
def peer_report():
    """Submit a concern about a colleague."""
    emp_id = session["emp_id"]
    emp = db.session.get(Employee, emp_id)
    employee = emp.to_dict()

    all_emps = Employee.query.all()
    colleagues = [
        {"id": e.id, "name": e.name, "department": e.department}
        for e in all_emps
        if e.id != emp_id
    ]
    colleagues.sort(key=lambda x: x["name"])

    if request.method == "POST":
        reported_id = request.form.get("reported_employee_id", "").strip().upper()
        concern_type = request.form.get("concern_type", "other")
        description = request.form.get("description", "").strip()
        anonymous = request.form.get("anonymous") == "on"

        # Validation
        if not reported_id:
            return render_template(
                "peer_report.html", colleagues=colleagues,
                error="Please select a colleague.", success=False,
                active_page="peer_report",
            )

        r_emp = db.session.get(Employee, reported_id)
        if not r_emp:
            return render_template(
                "peer_report.html", colleagues=colleagues,
                error="Selected colleague not found.", success=False,
                active_page="peer_report",
            )
        reported = r_emp.to_dict()

        if not description:
            return render_template(
                "peer_report.html", colleagues=colleagues,
                error="Please describe your concern.", success=False,
                active_page="peer_report",
            )

        valid_types = ["workload", "burnout", "behavior_change", "health", "other"]
        if concern_type not in valid_types:
            concern_type = "other"

        report = {
            "id": str(uuid.uuid4())[:8],
            "reporter_id": emp_id if not anonymous else "anonymous",
            "reporter_name": employee["name"] if not anonymous else "Anonymous",
            "reported_employee_id": reported_id,
            "reported_employee_name": reported["name"],
            "reported_department": reported["department"],
            "concern_type": concern_type,
            "description": description,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": "pending",
            "anonymous": anonymous,
        }
        pr = PeerReport(
            id=report["id"],
            reporter_id=report["reporter_id"] if report["reporter_id"] != "anonymous" else None,
            reporter_name=report["reporter_name"] if report["reporter_name"] != "Anonymous" else None,
            reported_employee_id=report["reported_employee_id"],
            reported_employee_name=report["reported_employee_name"],
            concern_type=report["concern_type"],
            description=report["description"],
            timestamp=report["timestamp"],
            status=report["status"]
        )
        db.session.add(pr)
        db.session.commit()

        return render_template(
            "peer_report.html", colleagues=colleagues,
            error=None, success=True,
            active_page="peer_report",
        )

    return render_template(
        "peer_report.html", colleagues=colleagues,
        error=None, success=False,
        active_page="peer_report",
    )


# ─────────────────────────────────────────────────────────────────────────────
# HR DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/hr")
@hr_required
def hr_dashboard():
    """HR overview — all employees, risk distribution, peer reports."""
    search_query = request.args.get("search", "").strip()
    risk_filter = request.args.get("risk", "").strip()

    # Build employee summaries
    employees = []
    risk_counts = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    total_score = 0

    all_emps = Employee.query.all()
    for emp_model in all_emps:
        emp = emp_model.to_dict()
        summary = employee_summary(emp)
        risk_counts[summary["risk_level"]] = risk_counts.get(summary["risk_level"], 0) + 1
        total_score += summary["burnout_score"]

        # Apply filters
        if search_query:
            q = search_query.lower()
            if (q not in summary["name"].lower()
                    and q not in summary["id"].lower()
                    and q not in summary["department"].lower()):
                continue

        if risk_filter and summary["risk_level"] != risk_filter:
            continue

        employees.append(summary)

    employees.sort(key=lambda x: x["burnout_score"], reverse=True)

    total = Employee.query.count()
    avg_score = round(total_score / total, 1) if total > 0 else 0
    at_risk = risk_counts.get("high", 0) + risk_counts.get("critical", 0)

    # Risk distribution with percentages
    risk_dist = {}
    for level in ["low", "moderate", "high", "critical"]:
        count = risk_counts.get(level, 0)
        risk_dist[level] = {
            "count": count,
            "pct": round(count / total * 100, 1) if total > 0 else 0,
        }

    # Get peer reports
    peer_reports = [p.to_dict() for p in PeerReport.query.order_by(PeerReport.timestamp.desc()).all()]

    # ── Manager Blindspot Analysis ──────────────────────────────────────
    manager_teams = {}  # manager_id -> list of {name, score, risk_level}
    for emp_model in Employee.query.all():
        emp = emp_model.to_dict()
        if emp.get("is_hr"):
            continue  # Skip HR managers themselves
        mgr_id = emp.get("manager", "Unknown")
        if mgr_id not in manager_teams:
            manager_teams[mgr_id] = {"members": [], "total_score": 0}
        burnout = get_employee_burnout(emp["id"])
        score = burnout["adjusted_score"]
        manager_teams[mgr_id]["members"].append({
            "name": emp["name"],
            "id": emp["id"],
            "score": score,
            "risk_level": burnout["risk_level"],
        })
        manager_teams[mgr_id]["total_score"] += score

    # Build sorted list of manager summaries
    manager_blindspots = []
    for mgr_id, data in manager_teams.items():
        count = len(data["members"])
        avg = round(data["total_score"] / count, 1) if count > 0 else 0
        high_risk_count = sum(1 for m in data["members"] if m["risk_level"] in ("high", "critical"))
        if avg >= 70:
            risk = "critical"
        elif avg >= 50:
            risk = "high"
        elif avg >= 30:
            risk = "moderate"
        else:
            risk = "low"
        manager_blindspots.append({
            "manager_id": mgr_id,
            "team_size": count,
            "avg_score": avg,
            "high_risk_count": high_risk_count,
            "risk": risk,
            "members": sorted(data["members"], key=lambda x: x["score"], reverse=True),
        })
    manager_blindspots.sort(key=lambda x: x["avg_score"], reverse=True)

    return render_template(
        "hr_dashboard.html",
        employees=employees,
        total=total,
        avg_score=avg_score,
        at_risk=at_risk,
        risk_dist=risk_dist,
        peer_reports=peer_reports,
        manager_blindspots=manager_blindspots,
        search_query=search_query,
        risk_filter=risk_filter,
        active_page="hr",
    )


# ─────────────────────────────────────────────────────────────────────────────
# HR EMPLOYEE DETAIL
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/hr/employee/<emp_id>")
@hr_required
def hr_employee_detail(emp_id):
    """HR detailed view of a single employee."""
    emp_id = emp_id.upper()
    emp = db.session.get(Employee, emp_id)
    if not emp:
        flash("Employee not found.", "error")
        return redirect(url_for("hr_dashboard"))
    employee = emp.to_dict()

    burnout = get_employee_burnout(emp_id)

    # Add sentiment percentage breakdowns
    sa = burnout.get("sentiment_analysis", {})
    total_msgs = sa.get("total_messages", 0)
    if total_msgs > 0:
        sa["positive_pct"] = round(sa.get("positive_count", 0) / total_msgs * 100, 1)
        sa["neutral_pct"] = round(sa.get("neutral_count", 0) / total_msgs * 100, 1)
        sa["negative_pct"] = round(sa.get("negative_count", 0) / total_msgs * 100, 1)

    actions = [a.to_dict() for a in HRAction.query.filter_by(employee_id=emp_id).all()]
    peer_reports = [p.to_dict() for p in PeerReport.query.filter_by(reported_employee_id=emp_id).all()]
    work_logs = [w.to_dict() for w in WorkLog.query.filter_by(employee_id=emp_id).order_by(WorkLog.id.desc()).limit(4).all()][::-1]

    # Generate Safe Icebreakers (Ghostwritten Empathy)
    icebreakers = []
    first_name = employee.get("name", "").split()[0] if employee.get("name") else "there"

    if burnout.get("masking_detection", {}).get("is_masking"):
        icebreakers.append({
            "title": "Addressing Emotional Masking",
            "text": f"Hi {first_name}, just doing some routine check-ins this week. You always bring such great energy, but I want to make sure you're taking care of yourself too. How are things really going?"
        })
    elif burnout.get("breakdown", {}).get("sentiment", {}).get("score", 0) >= 60:
        icebreakers.append({
            "title": "Addressing Communication Shifts",
            "text": f"Hi {first_name}, I wanted to proactively touch base. I want to ensure you have the support you need right now. Would you be open to a quick 10-minute chat when you're free?"
        })

    if burnout.get("breakdown", {}).get("work_pattern", {}).get("score", 0) >= 60:
        icebreakers.append({
            "title": "Addressing High Workload",
            "text": f"Hey {first_name}, I know the team has been pushing really hard lately. I wanted to check in — do we need to shift some priorities or get you some extra coverage this week?"
        })

    if not icebreakers:
        icebreakers.append({
            "title": "Routine Wellness Check",
            "text": f"Hi {first_name}, performing my monthly check-ins with the team! How are you feeling about your current bandwidth and projects?"
        })
        icebreakers.append({
            "title": "Open Door Reminder",
            "text": f"Hey {first_name}, hope you're having a good week. Just a quick reminder that my virtual door is always open if you ever need to chat about workload, team dynamics, or career growth."
        })

    return render_template(
        "hr_employee.html",
        employee=employee,
        burnout=burnout,
        icebreakers=icebreakers[:2],  # Provide top 2 contextually relevant icebreakers

        actions=actions,
        peer_reports=peer_reports,
        work_logs=work_logs,
        active_page="hr",
    )


# ─────────────────────────────────────────────────────────────────────────────
# HR ACTION (form POST handler)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/hr/action", methods=["POST"])
@hr_required
def hr_action():
    """Process an HR action form submission."""
    emp_id = request.form.get("employee_id", "").strip().upper()
    action_type = request.form.get("action_type", "")
    details = request.form.get("details", "").strip()

    emp = db.session.get(Employee, emp_id)
    if not emp:
        flash("Employee not found.", "error")
        return redirect(url_for("hr_dashboard"))
    employee = emp.to_dict()

    if not details:
        flash("Please provide action details.", "error")
        return redirect(url_for("hr_employee_detail", emp_id=emp_id))

    action = {
        "id": str(uuid.uuid4())[:8],
        "employee_id": emp_id,
        "employee_name": employee["name"],
        "action_type": action_type,
        "details": details,
        "hr_manager_id": session.get("emp_id", ""),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "active",
    }

    hr_a = HRAction(
        id=action["id"],
        employee_id=action["employee_id"],
        action_type=action["action_type"],
        details=action["details"],
        timestamp=action["timestamp"],
        status=action["status"]
    )
    db.session.add(hr_a)
    db.session.commit()

    flash(f"Action '{action_type.replace('_', ' ').title()}' recorded for {employee['name']}.", "success")
    return redirect(url_for("hr_employee_detail", emp_id=emp_id))


# ─────────────────────────────────────────────────────────────────────────────
# HR ACTION ON PEER REPORT (quick action from dashboard)
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/hr/report-action", methods=["POST"])
@hr_required
def hr_report_action():
    """Take action on a peer report directly from the HR dashboard."""
    report_id = request.form.get("report_id", "").strip()
    action_type = request.form.get("action_type", "reduce_workload")

    # Find the report
    report_model = db.session.get(PeerReport, report_id)
    if not report_model:
        flash("Report not found.", "error")
        return redirect(url_for("hr_dashboard"))
    report = report_model.to_dict()

    emp_id = report["reported_employee_id"]
    emp = db.session.get(Employee, emp_id)
    if not emp:
        flash("Reported employee not found.", "error")
        return redirect(url_for("hr_dashboard"))
    employee = emp.to_dict()

    # Auto-generate action details based on concern type
    concern = report.get("concern_type", "other")
    details_map = {
        "workload": f"Workload review initiated based on peer concern report. Will assess task distribution and redistribute if needed.",
        "burnout": f"Wellness check-in scheduled based on peer concern report. Will monitor wellbeing and offer support resources.",
        "behavior_change": f"1-on-1 meeting scheduled to check in based on observed behavioral changes reported by a peer.",
        "health": f"Health and wellness support offered based on peer concern. Employee will be connected with available resources.",
        "other": f"Follow-up initiated based on peer concern report. HR will reach out to assess the situation.",
    }
    action_type_map = {
        "workload": "reduce_workload",
        "burnout": "grant_leave",
        "behavior_change": "schedule_1on1",
        "health": "counseling_referral",
        "other": "schedule_1on1",
    }

    final_action_type = action_type if action_type != "auto" else action_type_map.get(concern, "schedule_1on1")
    details = details_map.get(concern, details_map["other"])

    # Create HR action
    action = {
        "id": str(uuid.uuid4())[:8],
        "employee_id": emp_id,
        "employee_name": employee["name"],
        "action_type": final_action_type,
        "details": details,
        "hr_manager_id": session.get("emp_id", ""),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "active",
        "source": "peer_report",
        "report_id": report_id,
    }

    hr_a = HRAction(
        id=action["id"],
        employee_id=action["employee_id"],
        action_type=action["action_type"],
        details=action["details"],
        timestamp=action["timestamp"],
        status=action["status"]
    )
    db.session.add(hr_a)
    db.session.commit()

    # Mark report as resolved
    report["status"] = "resolved"
    report["resolved_by"] = session.get("emp_id", "")
    report["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    flash(f"Action taken for {employee['name']}: {final_action_type.replace('_', ' ').title()}. Report marked as resolved.", "success")
    return redirect(url_for("hr_dashboard"))


# ─────────────────────────────────────────────────────────────────────────────
# EMPLOYEE PROFILE
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/profile")
@login_required
def profile():
    """Employee profile and settings page."""
    emp_id = session["emp_id"]
    emp = db.session.get(Employee, emp_id)
    employee = emp.to_dict() if emp else None
    
    return render_template(
        "profile.html",
        active_page="profile",
        employee=employee
    )


# ═════════════════════════════════════════════════════════════════════════════
# JSON API ROUTES (kept for completeness / API consumers)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/employees", methods=["GET"])
def api_list_employees():
    """List all employees with burnout scores (HR view)."""
    department = request.args.get("department")
    risk_level = request.args.get("risk_level")

    employees = []
    for emp_model in Employee.query.all():
        emp_dict = emp_model.to_dict()
        summary = employee_summary(emp_dict)
        if department and emp_dict["department"] != department:
            continue
        if risk_level and summary["risk_level"] != risk_level:
            continue
        employees.append(summary)

    employees.sort(key=lambda x: x["burnout_score"], reverse=True)
    return jsonify({"employees": employees, "total": len(employees)})


@app.route("/api/employee/<emp_id>", methods=["GET"])
def api_get_employee(emp_id):
    """Get detailed burnout analysis for a single employee."""
    emp_id = emp_id.upper()
    emp = db.session.get(Employee, emp_id)
    if not emp:
        return jsonify({"error": "Employee not found"}), 404
    employee = emp.to_dict()

    burnout = get_employee_burnout(emp_id)
    hr_actions = [h.to_dict() for h in HRAction.query.filter_by(employee_id=emp_id).all()]
    peer_reports = [p.to_dict() for p in PeerReport.query.filter_by(reported_employee_id=emp_id).all()]

    return jsonify({
        "employee": {
            "id": employee["id"],
            "name": employee["name"],
            "email": employee["email"],
            "department": employee["department"],
            "role": employee["role"],
            "join_date": employee["join_date"],
        },
        "burnout": burnout,
        "hr_actions": hr_actions,
        "peer_reports_count": len(peer_reports),
    })


@app.route("/api/assessment/questions", methods=["GET"])
def api_get_questions():
    """Get the list of burnout assessment questions."""
    return jsonify({
        "questions": ASSESSMENT_QUESTIONS,
        "scale": {"1": "Never", "2": "Rarely", "3": "Sometimes", "4": "Often", "5": "Always"},
        "total_questions": len(ASSESSMENT_QUESTIONS),
    })


@app.route("/api/assessment/submit", methods=["POST"])
def api_submit_assessment():
    """Submit a burnout assessment for an employee (API)."""
    data = request.get_json()
    emp_id = data.get("employee_id", "").strip().upper()
    answers = data.get("answers", {})
    response_times = data.get("response_times", {})

    if not emp_id:
        return jsonify({"error": "Employee ID is required"}), 400
    emp = db.session.get(Employee, emp_id)
    if not emp:
        return jsonify({"error": "Employee not found"}), 404
    employee = emp.to_dict()
    if not answers:
        return jsonify({"error": "Answers are required"}), 400

    for qid, value in answers.items():
        if not isinstance(value, int) or value < 1 or value > 5:
            return jsonify({"error": f"Answer for {qid} must be an integer between 1 and 5"}), 400

    answered_ids = set(answers.keys())
    expected_ids = {q["id"] for q in ASSESSMENT_QUESTIONS}
    missing = expected_ids - answered_ids
    if missing:
        return jsonify({"error": f"Missing answers for: {', '.join(sorted(missing))}"}), 400

    assessment_record = {
        "id": str(uuid.uuid4())[:8],
        "employee_id": emp_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "answers": answers,
        "response_times": response_times,
        "is_fake_attempt": False,
    }

    a = Assessment(
        id=assessment_record["id"],
        employee_id=assessment_record["employee_id"],
        timestamp=assessment_record["timestamp"],
        answers=assessment_record["answers"],
        response_times=assessment_record["response_times"],
        is_fake_attempt=assessment_record["is_fake_attempt"]
    )
    db.session.add(a)
    db.session.commit()

    burnout = get_employee_burnout(emp_id)
    alerts = generate_alerts(employee, burnout)

    return jsonify({
        "success": True,
        "assessment_id": assessment_record["id"],
        "burnout_score": burnout["adjusted_score"],
        "risk_level": burnout["risk_level"],
        "breakdown": burnout["breakdown"],
        "faking_detection": burnout["faking_detection"],
        "alerts_generated": len(alerts),
        "message": f"Assessment submitted. Your burnout score is {burnout['adjusted_score']}%.",
    })


@app.route("/api/sentiment/<emp_id>", methods=["GET"])
def api_get_sentiment(emp_id):
    """Get sentiment analysis of an employee's communications."""
    emp_id = emp_id.upper()
    emp = db.session.get(Employee, emp_id)
    if not emp:
        return jsonify({"error": "Employee not found"}), 404
    employee = emp.to_dict()
    messages = [m.to_dict() for m in Message.query.filter_by(employee_id=emp_id).all()]
    analysis = analyze_messages(messages)
    return jsonify({"employee_id": emp_id, "employee_name": employee["name"], "analysis": analysis})


@app.route("/api/alerts", methods=["GET"])
def api_get_alerts():
    """Get all HR alerts for employees at risk."""
    all_alerts = []
    for emp_model in Employee.query.all():
        emp = emp_model.to_dict()
        burnout = get_employee_burnout(emp["id"])
        emp_alerts = generate_alerts(emp, burnout)
        for alert in emp_alerts:
            alert["employee_id"] = emp["id"]
            alert["employee_name"] = emp["name"]
            alert["department"] = emp["department"]
            alert["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            all_alerts.append(alert)

    severity_order = {"critical": 0, "high": 1, "warning": 2, "moderate": 3}
    all_alerts.sort(key=lambda x: severity_order.get(x.get("severity", "moderate"), 4))
    return jsonify({"alerts": all_alerts, "total": len(all_alerts)})


@app.route("/api/departments", methods=["GET"])
def api_get_departments():
    """Get list of all departments."""
    departments = set(e.department for e in Employee.query.all())
    return jsonify({"departments": sorted(departments)})


# ═════════════════════════════════════════════════════════════════════════════
# RUN SERVER
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/css")
def serve_css():
    """Fallback: serve CSS directly."""
    css_path = os.path.join(BASE_DIR, "static", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()
    from flask import Response
    return Response(css, mimetype="text/css")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    print("\n" + "=" * 60)
    print("  BurnShield -- Employee Burnout Prediction & Monitoring")
    print("=" * 60)
    with app.app_context():
        emp_count = Employee.query.count()
    print(f"  Loaded {emp_count} employees from SQLite Database")
    print(f"  Static folder: {app.static_folder}")
    print(f"  Server starting at http://localhost:{port}")
    print(f"  Debug mode: {debug}")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=port, debug=debug)