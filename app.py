"""
Employee Burnout Prediction & Monitoring — Flask API Server
============================================================
Endpoints for employee login, burnout assessments, HR dashboard,
peer reporting, HR actions, and anti-faking intelligence.
"""

from flask import Flask, jsonify, request, render_template
from datetime import datetime
import uuid

from mock_data import MOCK_DATA, ASSESSMENT_QUESTIONS, generate_assessment_answers
from burnout_engine import (
    compute_burnout_score,
    analyze_messages,
    detect_faking,
    generate_alerts,
    compute_assessment_score,
)

app = Flask(__name__)

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
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

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
        "burnout_score": burnout["adjusted_score"],
        "risk_level": burnout["risk_level"],
        "last_assessment_date": burnout["last_assessment_date"],
        "faking_suspected": burnout["faking_detection"]["is_suspicious"],
    }


# ═════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve the single-page application."""
    return render_template("index.html")


# ═════════════════════════════════════════════════════════════════════════════
# AUTH ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/login", methods=["POST"])
def login():
    """Employee login with emp ID. Also supports HR login."""
    data = request.get_json()
    emp_id = data.get("employee_id", "").strip().upper()
    role_type = data.get("role", "employee")  # "employee" or "hr"

    if not emp_id:
        return jsonify({"error": "Employee ID is required"}), 400

    employee = DATA["employees"].get(emp_id)
    if not employee:
        return jsonify({"error": f"Employee {emp_id} not found"}), 404

    # Store session
    DATA["sessions"][emp_id] = datetime.now().isoformat()

    response = {
        "success": True,
        "employee": {
            "id": employee["id"],
            "name": employee["name"],
            "email": employee["email"],
            "department": employee["department"],
            "role": employee["role"],
        },
        "login_as": role_type,
    }

    return jsonify(response)


# ═════════════════════════════════════════════════════════════════════════════
# EMPLOYEE ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/employees", methods=["GET"])
def list_employees():
    """List all employees with burnout scores (HR view)."""
    department = request.args.get("department")
    risk_level = request.args.get("risk_level")

    employees = []
    for emp in DATA["employees"].values():
        summary = employee_summary(emp)

        # Apply filters
        if department and emp["department"] != department:
            continue
        if risk_level and summary["risk_level"] != risk_level:
            continue

        employees.append(summary)

    # Sort by burnout score descending
    employees.sort(key=lambda x: x["burnout_score"], reverse=True)

    return jsonify({
        "employees": employees,
        "total": len(employees),
    })


@app.route("/api/employee/<emp_id>", methods=["GET"])
def get_employee(emp_id):
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


# ═════════════════════════════════════════════════════════════════════════════
# ASSESSMENT ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/assessment/questions", methods=["GET"])
def get_questions():
    """Get the list of burnout assessment questions."""
    return jsonify({
        "questions": ASSESSMENT_QUESTIONS,
        "scale": {
            "1": "Never",
            "2": "Rarely",
            "3": "Sometimes",
            "4": "Often",
            "5": "Always",
        },
        "total_questions": len(ASSESSMENT_QUESTIONS),
    })


@app.route("/api/assessment/submit", methods=["POST"])
def submit_assessment():
    """Submit a burnout assessment for an employee.
    
    Expected JSON body:
    {
        "employee_id": "EMP001",
        "answers": {"q1": 3, "q2": 4, ...},
        "response_times": {"q1": 8.2, "q2": 5.1, ...}  // optional
    }
    """
    data = request.get_json()
    emp_id = data.get("employee_id", "").strip().upper()
    answers = data.get("answers", {})
    response_times = data.get("response_times", {})

    # Validation
    if not emp_id:
        return jsonify({"error": "Employee ID is required"}), 400

    employee = DATA["employees"].get(emp_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    if not answers:
        return jsonify({"error": "Answers are required"}), 400

    # Validate answer values
    for qid, value in answers.items():
        if not isinstance(value, int) or value < 1 or value > 5:
            return jsonify({"error": f"Answer for {qid} must be an integer between 1 and 5"}), 400

    # Check for missing questions
    answered_ids = set(answers.keys())
    expected_ids = {q["id"] for q in ASSESSMENT_QUESTIONS}
    missing = expected_ids - answered_ids
    if missing:
        return jsonify({"error": f"Missing answers for: {', '.join(sorted(missing))}"}), 400

    # Create assessment record
    assessment = {
        "id": str(uuid.uuid4())[:8],
        "employee_id": emp_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "answers": answers,
        "response_times": response_times,
        "is_fake_attempt": False,
    }

    # Store assessment
    if emp_id not in DATA["assessments"]:
        DATA["assessments"][emp_id] = []
    DATA["assessments"][emp_id].append(assessment)

    # Compute updated burnout score
    burnout = get_employee_burnout(emp_id)

    # Generate alerts if needed
    alerts = generate_alerts(employee, burnout)

    return jsonify({
        "success": True,
        "assessment_id": assessment["id"],
        "burnout_score": burnout["adjusted_score"],
        "risk_level": burnout["risk_level"],
        "breakdown": burnout["breakdown"],
        "faking_detection": burnout["faking_detection"],
        "alerts_generated": len(alerts),
        "message": f"Assessment submitted. Your burnout score is {burnout['adjusted_score']}%.",
    })


@app.route("/api/assessment/history/<emp_id>", methods=["GET"])
def assessment_history(emp_id):
    """Get assessment history for an employee."""
    emp_id = emp_id.upper()
    employee = DATA["employees"].get(emp_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    assessments = DATA["assessments"].get(emp_id, [])
    history = []
    for a in assessments:
        score = compute_assessment_score(a["answers"])
        history.append({
            "id": a["id"],
            "timestamp": a["timestamp"],
            "score": score,
        })

    return jsonify({
        "employee_id": emp_id,
        "assessments": history,
        "total": len(history),
    })


# ═════════════════════════════════════════════════════════════════════════════
# WORK LOG ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/work-log/<emp_id>", methods=["GET"])
def get_work_log(emp_id):
    """Get work hours & productivity data for an employee."""
    emp_id = emp_id.upper()
    employee = DATA["employees"].get(emp_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    logs = DATA["work_logs"].get(emp_id, [])

    # Compute aggregates
    if logs:
        recent = logs[-4:] if len(logs) >= 4 else logs
        avg_hours = round(sum(l["avg_daily_hours"] for l in recent) / len(recent), 1)
        avg_weekend = round(sum(l["weekend_hours"] for l in recent) / len(recent), 1)
        avg_tasks = round(sum(l["tasks_completed"] for l in recent) / len(recent), 1)
        avg_late_nights = round(sum(l["late_night_sessions"] for l in recent) / len(recent), 1)
    else:
        avg_hours = avg_weekend = avg_tasks = avg_late_nights = 0

    return jsonify({
        "employee_id": emp_id,
        "work_logs": logs,
        "summary": {
            "avg_daily_hours_recent": avg_hours,
            "avg_weekend_hours_recent": avg_weekend,
            "avg_tasks_completed_recent": avg_tasks,
            "avg_late_nights_recent": avg_late_nights,
            "total_weeks_tracked": len(logs),
        },
    })


# ═════════════════════════════════════════════════════════════════════════════
# SENTIMENT ANALYSIS ROUTES
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/sentiment/<emp_id>", methods=["GET"])
def get_sentiment(emp_id):
    """Get sentiment analysis of an employee's communications."""
    emp_id = emp_id.upper()
    employee = DATA["employees"].get(emp_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    messages = DATA["messages"].get(emp_id, [])
    analysis = analyze_messages(messages)

    return jsonify({
        "employee_id": emp_id,
        "employee_name": employee["name"],
        "analysis": analysis,
    })


# ═════════════════════════════════════════════════════════════════════════════
# HR ALERTS & DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
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

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "warning": 2, "moderate": 3}
    all_alerts.sort(key=lambda x: severity_order.get(x.get("severity", "moderate"), 4))

    return jsonify({
        "alerts": all_alerts,
        "total": len(all_alerts),
    })


@app.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    """Get aggregate statistics for the HR dashboard."""
    total = len(DATA["employees"])
    risk_counts = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    department_stats = {}
    total_score = 0

    for emp in DATA["employees"].values():
        burnout = get_employee_burnout(emp["id"])
        risk = burnout["risk_level"]
        score = burnout["adjusted_score"]
        dept = emp["department"]

        risk_counts[risk] = risk_counts.get(risk, 0) + 1
        total_score += score

        if dept not in department_stats:
            department_stats[dept] = {"total": 0, "total_score": 0, "high_risk": 0}
        department_stats[dept]["total"] += 1
        department_stats[dept]["total_score"] += score
        if risk in ("high", "critical"):
            department_stats[dept]["high_risk"] += 1

    # Compute department averages
    for dept in department_stats:
        s = department_stats[dept]
        s["avg_score"] = round(s["total_score"] / s["total"], 1) if s["total"] > 0 else 0

    # Get peer reports count
    total_peer_reports = len(DATA["peer_reports"])
    unresolved_peer_reports = sum(1 for r in DATA["peer_reports"] if r.get("status") == "pending")

    # Get total HR actions
    total_hr_actions = sum(len(v) for v in DATA["hr_actions"].values())

    return jsonify({
        "total_employees": total,
        "avg_burnout_score": round(total_score / total, 1) if total > 0 else 0,
        "risk_distribution": risk_counts,
        "at_risk_count": risk_counts.get("high", 0) + risk_counts.get("critical", 0),
        "department_stats": department_stats,
        "total_peer_reports": total_peer_reports,
        "unresolved_peer_reports": unresolved_peer_reports,
        "total_hr_actions": total_hr_actions,
        "departments": list(department_stats.keys()),
    })


# ═════════════════════════════════════════════════════════════════════════════
# HR ACTIONS (Reduce Workload, Time Off, etc.)
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/hr-action", methods=["POST"])
def create_hr_action():
    """Create an HR action for an employee.
    
    Expected JSON body:
    {
        "employee_id": "EMP001",
        "action_type": "reduce_workload" | "time_off" | "counseling" | "task_redistribution" | "schedule_1on1",
        "details": "Description of the action taken",
        "hr_manager_id": "EMP010"  // the HR person taking action
    }
    """
    data = request.get_json()
    emp_id = data.get("employee_id", "").strip().upper()
    action_type = data.get("action_type", "")
    details = data.get("details", "")
    hr_manager_id = data.get("hr_manager_id", "")

    # Validation
    if not emp_id:
        return jsonify({"error": "Employee ID is required"}), 400

    employee = DATA["employees"].get(emp_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    valid_actions = [
        "reduce_workload", "time_off", "counseling",
        "task_redistribution", "schedule_1on1", "immediate_intervention", "other"
    ]
    if action_type not in valid_actions:
        return jsonify({"error": f"Invalid action type. Must be one of: {', '.join(valid_actions)}"}), 400

    action = {
        "id": str(uuid.uuid4())[:8],
        "employee_id": emp_id,
        "employee_name": employee["name"],
        "action_type": action_type,
        "details": details,
        "hr_manager_id": hr_manager_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "active",
    }

    if emp_id not in DATA["hr_actions"]:
        DATA["hr_actions"][emp_id] = []
    DATA["hr_actions"][emp_id].append(action)

    return jsonify({
        "success": True,
        "action": action,
        "message": f"HR action '{action_type}' created for {employee['name']}.",
    })


@app.route("/api/hr-actions/<emp_id>", methods=["GET"])
def get_hr_actions(emp_id):
    """Get all HR actions for a specific employee."""
    emp_id = emp_id.upper()
    employee = DATA["employees"].get(emp_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    actions = DATA["hr_actions"].get(emp_id, [])

    return jsonify({
        "employee_id": emp_id,
        "employee_name": employee["name"],
        "actions": actions,
        "total": len(actions),
    })


@app.route("/api/hr-action/<action_id>/complete", methods=["POST"])
def complete_hr_action(action_id):
    """Mark an HR action as completed."""
    for emp_id, actions in DATA["hr_actions"].items():
        for action in actions:
            if action["id"] == action_id:
                action["status"] = "completed"
                action["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                return jsonify({"success": True, "action": action})

    return jsonify({"error": "Action not found"}), 404


# ═════════════════════════════════════════════════════════════════════════════
# PEER REPORTING
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/peer-report", methods=["POST"])
def submit_peer_report():
    """Submit a peer concern report for a co-worker.
    
    Expected JSON body:
    {
        "reporter_id": "EMP005",
        "reported_employee_id": "EMP003",
        "concern_type": "workload" | "burnout" | "behavior_change" | "health" | "other",
        "description": "I've noticed my colleague working very late...",
        "anonymous": true/false
    }
    """
    data = request.get_json()
    reporter_id = data.get("reporter_id", "").strip().upper()
    reported_id = data.get("reported_employee_id", "").strip().upper()
    concern_type = data.get("concern_type", "other")
    description = data.get("description", "").strip()
    anonymous = data.get("anonymous", True)

    # Validation
    if not reporter_id or not reported_id:
        return jsonify({"error": "Both reporter and reported employee IDs are required"}), 400

    if reporter_id == reported_id:
        return jsonify({"error": "You cannot report yourself. Please use the assessment instead."}), 400

    reporter = DATA["employees"].get(reporter_id)
    reported = DATA["employees"].get(reported_id)

    if not reporter:
        return jsonify({"error": f"Reporter {reporter_id} not found"}), 404
    if not reported:
        return jsonify({"error": f"Employee {reported_id} not found"}), 404

    if not description:
        return jsonify({"error": "Please provide a description of your concern"}), 400

    valid_types = ["workload", "burnout", "behavior_change", "health", "other"]
    if concern_type not in valid_types:
        concern_type = "other"

    report = {
        "id": str(uuid.uuid4())[:8],
        "reporter_id": reporter_id if not anonymous else "anonymous",
        "reporter_name": reporter["name"] if not anonymous else "Anonymous",
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

    return jsonify({
        "success": True,
        "report_id": report["id"],
        "message": "Your concern has been submitted to HR. Thank you for looking out for your colleague.",
    })


@app.route("/api/peer-reports", methods=["GET"])
def get_peer_reports():
    """Get all peer concern reports (HR view)."""
    status_filter = request.args.get("status")

    reports = DATA["peer_reports"]

    if status_filter:
        reports = [r for r in reports if r["status"] == status_filter]

    # Sort by timestamp (newest first)
    reports.sort(key=lambda x: x["timestamp"], reverse=True)

    return jsonify({
        "reports": reports,
        "total": len(reports),
    })


@app.route("/api/peer-report/<report_id>/resolve", methods=["POST"])
def resolve_peer_report(report_id):
    """Mark a peer report as resolved."""
    data = request.get_json() or {}
    resolution = data.get("resolution", "Addressed by HR")

    for report in DATA["peer_reports"]:
        if report["id"] == report_id:
            report["status"] = "resolved"
            report["resolution"] = resolution
            report["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            return jsonify({"success": True, "report": report})

    return jsonify({"error": "Report not found"}), 404


# ═════════════════════════════════════════════════════════════════════════════
# DEPARTMENTS
# ═════════════════════════════════════════════════════════════════════════════

@app.route("/api/departments", methods=["GET"])
def get_departments():
    """Get list of all departments."""
    departments = set(emp["department"] for emp in DATA["employees"].values())
    return jsonify({"departments": sorted(departments)})


# ═════════════════════════════════════════════════════════════════════════════
# RUN SERVER
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  Employee Burnout Prediction & Monitoring System")
    print("=" * 60)
    print(f"  Loaded {len(DATA['employees'])} employees")
    print(f"  Server starting at http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5000)