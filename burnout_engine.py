"""
Burnout Scoring Engine & Sentiment Analysis Pipeline
Computes burnout scores using a weighted composite of assessment answers,
sentiment trends, work patterns, and productivity. Includes anti-faking detection.
"""

from textblob import TextBlob
from datetime import datetime

from mock_data import ASSESSMENT_QUESTIONS


# ─────────────────────────────────────────────────────────────────────────────
# Weights for Composite Burnout Score
# ─────────────────────────────────────────────────────────────────────────────

WEIGHTS = {
    "assessment": 0.75,   # Latest test answers carry the most weight
    "sentiment": 0.10,    # Communication tone (supporting signal)
    "work_pattern": 0.10, # Work hours/patterns (supporting signal)
    "productivity": 0.05, # Task completion trends (minor signal)
}

# Thresholds
RISK_THRESHOLDS = {
    "low": 35,
    "moderate": 55,
    "high": 75,
    "critical": 90,
}


# ─────────────────────────────────────────────────────────────────────────────
# Sentiment Analysis
# ─────────────────────────────────────────────────────────────────────────────

def analyze_sentiment(text):
    """Analyze sentiment of a single message. Returns polarity (-1 to 1) and subjectivity (0 to 1)."""
    blob = TextBlob(text)
    return {
        "polarity": round(blob.sentiment.polarity, 3),
        "subjectivity": round(blob.sentiment.subjectivity, 3),
    }


def analyze_messages(messages):
    """Analyze sentiment across all messages for an employee.
    Returns per-message analysis, overall stats, and trend direction.
    """
    if not messages:
        return {"messages": [], "average_polarity": 0, "trend": "stable", "sentiment_label": "neutral"}

    analyzed = []
    for msg in messages:
        sentiment = analyze_sentiment(msg["content"])
        analyzed.append({
            **msg,
            "polarity": sentiment["polarity"],
            "subjectivity": sentiment["subjectivity"],
            "label": _polarity_label(sentiment["polarity"]),
        })

    # Sort by timestamp
    analyzed.sort(key=lambda x: x["timestamp"])

    # Calculate overall stats
    polarities = [m["polarity"] for m in analyzed]
    avg_polarity = round(sum(polarities) / len(polarities), 3)

    # Calculate trend: compare first half vs second half
    mid = len(polarities) // 2
    if mid > 0:
        first_half_avg = sum(polarities[:mid]) / mid
        second_half_avg = sum(polarities[mid:]) / (len(polarities) - mid)
        diff = second_half_avg - first_half_avg

        if diff < -0.15:
            trend = "declining"
        elif diff > 0.15:
            trend = "improving"
        else:
            trend = "stable"
    else:
        trend = "stable"

    # Weekly sentiment breakdown
    weekly_sentiment = _compute_weekly_sentiment(analyzed)

    return {
        "messages": analyzed,
        "average_polarity": avg_polarity,
        "trend": trend,
        "sentiment_label": _polarity_label(avg_polarity),
        "total_messages": len(analyzed),
        "positive_count": sum(1 for m in analyzed if m["label"] == "positive"),
        "neutral_count": sum(1 for m in analyzed if m["label"] == "neutral"),
        "negative_count": sum(1 for m in analyzed if m["label"] == "negative"),
        "weekly_breakdown": weekly_sentiment,
    }


def _polarity_label(polarity):
    """Convert polarity score to a human-readable label."""
    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    return "neutral"


def _compute_weekly_sentiment(messages):
    """Group messages by week and compute weekly average sentiment."""
    weeks = {}
    for msg in messages:
        try:
            date = datetime.strptime(msg["timestamp"], "%Y-%m-%d %H:%M")
        except (ValueError, KeyError):
            continue
        week_key = date.strftime("%Y-W%U")
        if week_key not in weeks:
            weeks[week_key] = []
        weeks[week_key].append(msg["polarity"])

    weekly = []
    for week_key in sorted(weeks.keys()):
        pols = weeks[week_key]
        weekly.append({
            "week": week_key,
            "avg_polarity": round(sum(pols) / len(pols), 3),
            "message_count": len(pols),
        })
    return weekly


# ─────────────────────────────────────────────────────────────────────────────
# Assessment Score
# ─────────────────────────────────────────────────────────────────────────────

def compute_assessment_score(answers):
    """Compute burnout percentage from assessment answers (0-100).
    Higher = more burnout.
    
    Burnout-indicating categories (exhaustion, detachment, physical)
    are weighted 3x more than positive categories (accomplishment, support).
    """
    if not answers:
        return 0  # No assessment taken yet = 0 burnout

    weighted_total = 0
    total_weight = 0

    for q in ASSESSMENT_QUESTIONS:
        qid = q["id"]
        if qid in answers:
            score = answers[qid]
            # Reverse score for positive categories
            if q["category"] in ("personal_accomplishment", "support"):
                score = 6 - score  # invert: 5→1, 1→5
                weight = 1.0  # Lower weight for positive categories
            else:
                weight = 3.0  # Higher weight for burnout indicators
            
            weighted_total += score * weight
            total_weight += weight

    if total_weight == 0:
        return 0

    # Normalize to 0-100
    raw = weighted_total / total_weight  # 1 to 5
    normalized = ((raw - 1) / 4) * 100  # 0 to 100
    return round(normalized, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Work Pattern Score
# ─────────────────────────────────────────────────────────────────────────────

def compute_work_pattern_score(work_logs):
    """Compute burnout risk from work patterns (0-100). Higher = more burnout risk."""
    if not work_logs:
        return 50

    # Use the most recent 4 weeks
    recent_logs = work_logs[-4:] if len(work_logs) >= 4 else work_logs

    avg_daily_hours = sum(l["avg_daily_hours"] for l in recent_logs) / len(recent_logs)
    avg_weekend_hours = sum(l["weekend_hours"] for l in recent_logs) / len(recent_logs)
    avg_late_nights = sum(l["late_night_sessions"] for l in recent_logs) / len(recent_logs)
    avg_breaks = sum(l["breaks_taken_per_day"] for l in recent_logs) / len(recent_logs)
    avg_pto_balance = sum(l["pto_balance_days"] for l in recent_logs) / len(recent_logs)

    score = 0

    # Daily hours factor (8h normal, 14h extreme)
    hours_factor = min(100, max(0, ((avg_daily_hours - 8) / 6) * 100))
    score += hours_factor * 0.30

    # Weekend work factor
    weekend_factor = min(100, max(0, (avg_weekend_hours / 6) * 100))
    score += weekend_factor * 0.20

    # Late night sessions factor (0-1 normal, 5+ extreme)
    late_factor = min(100, max(0, (avg_late_nights / 5) * 100))
    score += late_factor * 0.20

    # Breaks factor (fewer breaks = higher risk)
    breaks_factor = min(100, max(0, ((5 - avg_breaks) / 5) * 100))
    score += breaks_factor * 0.15

    # PTO factor (low PTO balance = higher risk)
    pto_factor = min(100, max(0, ((15 - avg_pto_balance) / 15) * 100))
    score += pto_factor * 0.15

    return round(score, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Productivity Score
# ─────────────────────────────────────────────────────────────────────────────

def compute_productivity_score(work_logs):
    """Compute burnout risk from productivity changes (0-100). Higher = more risk."""
    if not work_logs or len(work_logs) < 2:
        return 50

    recent = work_logs[-4:] if len(work_logs) >= 4 else work_logs
    older = work_logs[:4] if len(work_logs) >= 4 else work_logs[:1]

    recent_completion = sum(l["tasks_completed"] for l in recent) / len(recent)
    older_completion = sum(l["tasks_completed"] for l in older) / len(older)

    recent_assigned = sum(l["tasks_assigned"] for l in recent) / len(recent)

    # Task completion rate
    completion_rate = recent_completion / max(recent_assigned, 1) * 100

    # Productivity decline
    if older_completion > 0:
        decline = ((older_completion - recent_completion) / older_completion) * 100
    else:
        decline = 0

    score = 0

    # Completion rate factor (100% = 0 risk, 30% = max risk)
    completion_factor = min(100, max(0, ((100 - completion_rate) / 70) * 100))
    score += completion_factor * 0.50

    # Decline factor
    decline_factor = min(100, max(0, decline * 2))  # 50% decline = 100 risk
    score += decline_factor * 0.50

    return round(score, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Sentiment Score (for composite)
# ─────────────────────────────────────────────────────────────────────────────

def compute_sentiment_score(sentiment_analysis):
    """Convert sentiment analysis results to a burnout risk score (0-100)."""
    if not sentiment_analysis or not sentiment_analysis.get("messages"):
        return 50

    avg_polarity = sentiment_analysis["average_polarity"]
    trend = sentiment_analysis["trend"]
    negative_ratio = sentiment_analysis["negative_count"] / max(sentiment_analysis["total_messages"], 1)

    # Polarity factor: -1 → 100, +1 → 0
    polarity_score = ((1 - avg_polarity) / 2) * 100

    # Trend factor
    trend_bonus = 0
    if trend == "declining":
        trend_bonus = 15
    elif trend == "improving":
        trend_bonus = -10

    # Negative ratio factor
    negative_score = negative_ratio * 100

    score = polarity_score * 0.50 + negative_score * 0.30 + (50 + trend_bonus) * 0.20
    return round(min(100, max(0, score)), 1)


# ─────────────────────────────────────────────────────────────────────────────
# Anti-Faking Detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_faking(assessment, work_logs, sentiment_analysis):
    """Detect if an employee is trying to fake their burnout assessment.
    
    Returns a dict with:
      - is_suspicious: bool
      - confidence: float 0-1
      - reasons: list of strings
    """
    reasons = []
    suspicion_score = 0

    if not assessment:
        return {"is_suspicious": False, "confidence": 0, "reasons": []}

    answers = assessment.get("answers", {})
    response_times = assessment.get("response_times", {})

    # 1. Check response time consistency (suspiciously fast = faking)
    if response_times:
        times = list(response_times.values())
        avg_time = sum(times) / len(times)
        if avg_time < 3.0:
            reasons.append("Suspiciously fast response time (avg {:.1f}s per question)".format(avg_time))
            suspicion_score += 0.3

        # Check for uniform response times (robotic)
        if len(times) > 3:
            variance = sum((t - avg_time) ** 2 for t in times) / len(times)
            if variance < 1.0:
                reasons.append("Very uniform response times suggest non-genuine answers")
                suspicion_score += 0.2

    # 2. Self-report vs work data gap
    assessment_score = compute_assessment_score(answers)
    if work_logs:
        work_score = compute_work_pattern_score(work_logs)
        gap = abs(work_score - assessment_score)
        if gap > 40 and assessment_score < work_score:
            reasons.append(
                f"Large gap between self-report ({assessment_score:.0f}%) and work data ({work_score:.0f}%)"
            )
            suspicion_score += 0.3

    # 3. Sentiment vs self-report gap
    if sentiment_analysis and sentiment_analysis.get("messages"):
        sentiment_score = compute_sentiment_score(sentiment_analysis)
        gap = abs(sentiment_score - assessment_score)
        if gap > 35 and assessment_score < sentiment_score:
            reasons.append(
                f"Communication sentiment ({sentiment_score:.0f}%) contradicts self-assessment ({assessment_score:.0f}%)"
            )
            suspicion_score += 0.2

    # 4. All answers the same (pattern detection)
    if answers:
        values = list(answers.values())
        unique_values = set(values)
        if len(unique_values) <= 2:
            reasons.append("Nearly all answers are identical — possible pattern response")
            suspicion_score += 0.15

    is_suspicious = suspicion_score >= 0.3
    return {
        "is_suspicious": is_suspicious,
        "confidence": round(min(1.0, suspicion_score), 2),
        "reasons": reasons,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Composite Burnout Score
# ─────────────────────────────────────────────────────────────────────────────

def compute_burnout_score(employee_id, assessments, work_logs, messages):
    """Compute the final composite burnout score for an employee.
    
    Returns a detailed breakdown dict.
    If no assessment has been taken, returns 0% burnout.
    """
    # If no assessment taken yet, return 0 — employee hasn't been tested
    if not assessments:
        sentiment_analysis = analyze_messages(messages)
        return {
            "employee_id": employee_id,
            "composite_score": 0,
            "adjusted_score": 0,
            "risk_level": "low",
            "breakdown": {
                "assessment": {"score": 0, "weight": WEIGHTS["assessment"]},
                "sentiment": {"score": 0, "weight": WEIGHTS["sentiment"]},
                "work_pattern": {"score": 0, "weight": WEIGHTS["work_pattern"]},
                "productivity": {"score": 0, "weight": WEIGHTS["productivity"]},
            },
            "sentiment_analysis": sentiment_analysis,
            "faking_detection": {"is_suspicious": False, "confidence": 0, "reasons": []},
            "assessment_trend": [],
            "last_assessment_date": None,
        }

    # Get most recent assessment
    latest_assessment = assessments[-1]
    assessment_answers = latest_assessment["answers"]

    # Compute individual scores
    assessment_score = compute_assessment_score(assessment_answers)
    sentiment_analysis = analyze_messages(messages)
    sentiment_score = compute_sentiment_score(sentiment_analysis)
    work_score = compute_work_pattern_score(work_logs)
    productivity_score = compute_productivity_score(work_logs)

    # Weighted composite
    composite = (
        assessment_score * WEIGHTS["assessment"]
        + sentiment_score * WEIGHTS["sentiment"]
        + work_score * WEIGHTS["work_pattern"]
        + productivity_score * WEIGHTS["productivity"]
    )
    composite = round(min(100, max(0, composite)), 1)

    # Anti-faking check
    faking_result = detect_faking(latest_assessment, work_logs, sentiment_analysis)

    # If faking detected, adjust score upward using objective data
    adjusted_score = composite
    if faking_result["is_suspicious"]:
        objective_score = (
            sentiment_score * 0.40
            + work_score * 0.35
            + productivity_score * 0.25
        )
        adjusted_score = round(max(composite, objective_score), 1)

    # Determine risk level
    risk_level = _get_risk_level(adjusted_score)

    # Assessment history trend
    assessment_trend = []
    for a in assessments:
        s = compute_assessment_score(a["answers"])
        assessment_trend.append({
            "date": a["timestamp"],
            "score": s,
        })

    return {
        "employee_id": employee_id,
        "composite_score": composite,
        "adjusted_score": adjusted_score,
        "risk_level": risk_level,
        "breakdown": {
            "assessment": {"score": assessment_score, "weight": WEIGHTS["assessment"]},
            "sentiment": {"score": sentiment_score, "weight": WEIGHTS["sentiment"]},
            "work_pattern": {"score": work_score, "weight": WEIGHTS["work_pattern"]},
            "productivity": {"score": productivity_score, "weight": WEIGHTS["productivity"]},
        },
        "sentiment_analysis": sentiment_analysis,
        "faking_detection": faking_result,
        "assessment_trend": assessment_trend,
        "last_assessment_date": latest_assessment["timestamp"],
    }


def _get_risk_level(score):
    """Map a burnout score to a risk level."""
    if score >= RISK_THRESHOLDS["critical"]:
        return "critical"
    elif score >= RISK_THRESHOLDS["high"]:
        return "high"
    elif score >= RISK_THRESHOLDS["moderate"]:
        return "moderate"
    return "low"


# ─────────────────────────────────────────────────────────────────────────────
# HR Alert Generation
# ─────────────────────────────────────────────────────────────────────────────

def generate_alerts(employee, burnout_result):
    """Generate HR alerts for an employee based on their burnout analysis."""
    alerts = []
    score = burnout_result["adjusted_score"]
    risk = burnout_result["risk_level"]
    faking = burnout_result["faking_detection"]
    sentiment = burnout_result["sentiment_analysis"]

    if risk in ("high", "critical"):
        alerts.append({
            "type": "burnout_risk",
            "severity": risk,
            "title": f"High Burnout Risk — {employee['name']}",
            "message": (
                f"{employee['name']} ({employee['role']}, {employee['department']}) "
                f"has a burnout score of {score}%. Immediate attention recommended."
            ),
            "recommended_actions": _get_recommendations(burnout_result),
        })

    if faking["is_suspicious"]:
        alerts.append({
            "type": "faking_detected",
            "severity": "warning",
            "title": f"Possible Assessment Faking — {employee['name']}",
            "message": (
                f"The system has detected potential inconsistencies in {employee['name']}'s "
                f"self-assessment. Confidence: {faking['confidence'] * 100:.0f}%"
            ),
            "details": faking["reasons"],
        })

    if sentiment.get("trend") == "declining":
        alerts.append({
            "type": "sentiment_decline",
            "severity": "moderate",
            "title": f"Declining Sentiment — {employee['name']}",
            "message": (
                f"{employee['name']}'s communication sentiment has been declining over recent weeks. "
                f"Current average polarity: {sentiment['average_polarity']:.2f}"
            ),
        })

    return alerts


def _get_recommendations(burnout_result):
    """Generate HR intervention recommendations based on burnout analysis."""
    recommendations = []
    breakdown = burnout_result["breakdown"]
    score = burnout_result["adjusted_score"]

    if breakdown["work_pattern"]["score"] > 60:
        recommendations.append({
            "action": "reduce_workload",
            "priority": "high",
            "description": "Reduce weekly work hours. Employee shows excessive overtime and limited breaks.",
        })
        recommendations.append({
            "action": "enforce_time_off",
            "priority": "high",
            "description": "Mandate minimum 2 days off in the next 2 weeks. PTO balance appears low.",
        })

    if breakdown["sentiment"]["score"] > 60:
        recommendations.append({
            "action": "schedule_1on1",
            "priority": "high",
            "description": "Schedule a private check-in with the employee to discuss workload and well-being.",
        })

    if breakdown["assessment"]["score"] > 70:
        recommendations.append({
            "action": "counseling_referral",
            "priority": "medium",
            "description": "Refer employee to the Employee Assistance Program (EAP) for professional support.",
        })

    if breakdown["productivity"]["score"] > 60:
        recommendations.append({
            "action": "task_redistribution",
            "priority": "medium",
            "description": "Redistribute some tasks to other team members to reduce cognitive overload.",
        })

    if score >= RISK_THRESHOLDS["critical"]:
        recommendations.append({
            "action": "immediate_intervention",
            "priority": "critical",
            "description": "This employee is at critical risk. Consider immediate workload reduction and mandatory time off.",
        })

    return recommendations