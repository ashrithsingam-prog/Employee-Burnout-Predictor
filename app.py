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

from mock_data import MOCK_DATA, ASSESSMENT_QUESTIONS, generate_assessment_answers
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
app.secret_key = "burnshield-secret-key-2026"

# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Data Store (loaded from mock_data on startup)
# ─────────────────────────────────────────────────────────────────────────────

DATA = {
    "employees": {e["id"]: e for e in MOCK_DATA["employees"]},
    "work_logs": MOCK_DATA["work_logs"],
    "messages": MOCK_DATA["messages"],
    "assessments": MOCK_DATA["assessments"],
    "hr_actions": {},     # employee_id -> list of HR actions
    "peer_reports": [],   # list of peer concern reports
    "sessions": {},       # simple session store: emp_id -> login timestamp
}


# ─────────────────────────────────────────────────────────────────────────────
# Template Context Processor — inject session info into every template
# ─────────────────────────────────────────────────────────────────────────────

@app.context_processor
def inject_session_globals():
    """Make session data available in all templates."""
    emp_id = session.get("emp_id")
    current_employee = DATA["employees"].get(emp_id) if emp_id else None
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
    assessments = DATA["assessments"].get(emp_id, [])
    work_logs = DATA["work_logs"].get(emp_id, [])
    messages = DATA["messages"].get(emp_id, [])
    return compute_burnout_score(emp_id, assessments, work_logs, messages)


def employee_summary(emp):
    """Return a safely serializable summary of an employee (no hidden fields)."""
    burnout = get_employee_burnout(emp["id"])
    return {
        "id": emp["id"],
        "name": emp["name"],
        "email": emp["email"],
        "department": emp["department"],
        "role": emp["role"],
        "join_date": emp["join_date"],
        "is_hr": emp.get("is_hr", False),
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

        employee = DATA["employees"].get(emp_id)
        if not employee:
            return render_template("login.html", error=f"Employee {emp_id} not found.")

        # Store in session
        session["emp_id"] = emp_id
        session["is_hr"] = employee.get("is_hr", False)
        session["is_manager"] = employee.get("is_manager", False)
        DATA["sessions"][emp_id] = datetime.now().isoformat()

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
    employee = DATA["employees"][emp_id]
    burnout = get_employee_burnout(emp_id)
    assessments = DATA["assessments"].get(emp_id, [])
    work_logs = DATA["work_logs"].get(emp_id, [])[-4:]  # Last 4 weeks
    hr_actions = DATA["hr_actions"].get(emp_id, [])  # HR actions for this employee

    # If logged-in user is a manager, gather HR actions for their team
    team_actions = []
    if employee.get("is_manager"):
        for eid, emp_data in DATA["employees"].items():
            if emp_data.get("manager") == emp_id and eid != emp_id:
                actions = DATA["hr_actions"].get(eid, [])
                for action in actions:
                    team_actions.append({
                        "employee_name": emp_data["name"],
                        "employee_id": eid,
                        "action": action,
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
    employee = DATA["employees"][emp_id]

    if request.method == "POST":
        answers = {}
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
        if emp_id not in DATA["assessments"]:
            DATA["assessments"][emp_id] = []
        DATA["assessments"][emp_id].append(assessment_record)

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
    employee = DATA["employees"][emp_id]

    # Get list of all employees except self for the dropdown
    colleagues = [
        {"id": e["id"], "name": e["name"], "department": e["department"]}
        for e in DATA["employees"].values()
        if e["id"] != emp_id
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

        reported = DATA["employees"].get(reported_id)
        if not reported:
            return render_template(
                "peer_report.html", colleagues=colleagues,
                error="Selected colleague not found.", success=False,
                active_page="peer_report",
            )

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
        DATA["peer_reports"].append(report)

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

    for emp in DATA["employees"].values():
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

    total = len(DATA["employees"])
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
    peer_reports = sorted(DATA["peer_reports"], key=lambda x: x["timestamp"], reverse=True)

    # ── Manager Blindspot Analysis ──────────────────────────────────────
    manager_teams = {}  # manager_id -> list of {name, score, risk_level}
    for emp in DATA["employees"].values():
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
    employee = DATA["employees"].get(emp_id)
    if not employee:
        flash("Employee not found.", "error")
        return redirect(url_for("hr_dashboard"))

    burnout = get_employee_burnout(emp_id)

    # Add sentiment percentage breakdowns
    sa = burnout.get("sentiment_analysis", {})
    total_msgs = sa.get("total_messages", 0)
    if total_msgs > 0:
        sa["positive_pct"] = round(sa.get("positive_count", 0) / total_msgs * 100, 1)
        sa["neutral_pct"] = round(sa.get("neutral_count", 0) / total_msgs * 100, 1)
        sa["negative_pct"] = round(sa.get("negative_count", 0) / total_msgs * 100, 1)

    actions = DATA["hr_actions"].get(emp_id, [])
    peer_reports = [r for r in DATA["peer_reports"] if r["reported_employee_id"] == emp_id]
    work_logs = DATA["work_logs"].get(emp_id, [])[-4:]  # Last 4 weeks

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

    employee = DATA["employees"].get(emp_id)
    if not employee:
        flash("Employee not found.", "error")
        return redirect(url_for("hr_dashboard"))

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

    if emp_id not in DATA["hr_actions"]:
        DATA["hr_actions"][emp_id] = []
    DATA["hr_actions"][emp_id].append(action)

    flash(f"Action '{action_type.replace('_', ' ').title()}' recorded for {employee['name']}.", "success")
    return redirect(url_for("hr_employee_detail", emp_id=emp_id))


# ─────────────────────────────────────────────────────────────────────────────
# EMPLOYEE PROFILE
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/profile")
@login_required
def profile():
    """Employee profile and settings page."""
    emp_id = session["emp_id"]
    # Get the latest data from DATA structure (already injected by context processor, but good to be explicit for route logic)
    employee = DATA["employees"].get(emp_id)
    
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
    for emp in DATA["employees"].values():
        summary = employee_summary(emp)
        if department and emp["department"] != department:
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
    employee = DATA["employees"].get(emp_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    burnout = get_employee_burnout(emp_id)
    hr_actions = DATA["hr_actions"].get(emp_id, [])
    peer_reports = [r for r in DATA["peer_reports"] if r["reported_employee_id"] == emp_id]

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
    employee = DATA["employees"].get(emp_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404
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

    if emp_id not in DATA["assessments"]:
        DATA["assessments"][emp_id] = []
    DATA["assessments"][emp_id].append(assessment_record)

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
    employee = DATA["employees"].get(emp_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404
    messages = DATA["messages"].get(emp_id, [])
    analysis = analyze_messages(messages)
    return jsonify({"employee_id": emp_id, "employee_name": employee["name"], "analysis": analysis})


@app.route("/api/alerts", methods=["GET"])
def api_get_alerts():
    """Get all HR alerts for employees at risk."""
    all_alerts = []
    for emp in DATA["employees"].values():
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
    departments = set(emp["department"] for emp in DATA["employees"].values())
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
    print("\n" + "=" * 60)
    print("  BurnShield -- Employee Burnout Prediction & Monitoring")
    print("=" * 60)
    print(f"  Loaded {len(DATA['employees'])} employees")
    print(f"  Static folder: {app.static_folder}")
    print(f"  Server starting at http://localhost:5050")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5050)