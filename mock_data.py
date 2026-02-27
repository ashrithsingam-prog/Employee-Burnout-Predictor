"""
Mock Data Generator for Employee Burnout Prediction App
Generates realistic employee data, communication history, work logs, and assessment history.
"""

import random
import uuid
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# Employee Profiles
# ─────────────────────────────────────────────────────────────────────────────

DEPARTMENTS = ["Engineering", "Marketing", "Sales", "HR", "Finance", "Design", "Product", "Support"]
ROLES = {
    "Engineering": ["Software Engineer", "Senior Engineer", "Tech Lead", "DevOps Engineer"],
    "Marketing": ["Marketing Analyst", "Content Strategist", "Campaign Manager", "Brand Specialist"],
    "Sales": ["Sales Executive", "Account Manager", "Business Development Rep", "Sales Lead"],
    "HR": ["HR Coordinator", "HR Business Partner", "Talent Acquisition Specialist"],
    "Finance": ["Financial Analyst", "Accountant", "Finance Manager"],
    "Design": ["UI Designer", "UX Researcher", "Product Designer", "Design Lead"],
    "Product": ["Product Manager", "Product Analyst", "Scrum Master"],
    "Support": ["Support Engineer", "Customer Success Manager", "Support Lead"],
}

FIRST_NAMES = [
    "Ashrith", "Amogh", "Diddy", "Sneha", "Vikram", "Ananya", "Rohan", "Kavya",
    "Arjun", "Meera", "Aditya", "Ishita", "Karan", "Pooja", "Nikhil", "Divya",
    "Siddharth", "Nisha", "Amit", "Riya"
]

LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Kumar", "Singh", "Gupta", "Reddy", "Nair",
    "Joshi", "Mehta", "Chopra", "Sarvak", "Bhat", "Iyer", "Rao", "Das",
    "Chauhan", "Pillai", "Banerjee", "Kulkarni"
]

# ─────────────────────────────────────────────────────────────────────────────
# Mock Slack / Email Messages by Sentiment Profile
# ─────────────────────────────────────────────────────────────────────────────

POSITIVE_MESSAGES = [
    "Had a great brainstorming session today! Feeling energized about the project.",
    "Really enjoyed collaborating with the team this week. Good vibes all around!",
    "Managed to finish the sprint goals early. Feeling accomplished!",
    "The new project kickoff was exciting. Looking forward to the challenges ahead.",
    "Got some wonderful feedback from the client today. Team effort really paid off!",
    "Love the direction we're heading. This quarter's goals feel super achievable.",
    "Amazing team lunch today. These moments really boost morale!",
    "Completed the certification course! Feeling more confident in my skills now.",
    "The mentorship program has been incredibly helpful. Grateful for the support.",
    "Friday wrap-up went smoothly. Ready for a well-deserved weekend!",
]

NEUTRAL_MESSAGES = [
    "Attending the standup meeting at 10 AM. Will share my updates then.",
    "Reviewed the PR and left some comments. Let me know if you have questions.",
    "Working on the documentation for the new API endpoints today.",
    "Scheduled a meeting with the client for next Tuesday. Please confirm availability.",
    "Updated the task tracker with this week's progress. On track so far.",
    "Going through the backlog items. Will prioritize by end of day.",
    "Shared the meeting notes in the channel. Please review when you get a chance.",
    "Setting up the staging environment for the next release.",
    "Coordinating with the QA team for the testing phase.",
    "Will be working from home tomorrow. Available on all channels.",
]

NEGATIVE_MESSAGES = [
    "Feeling really overwhelmed with the current workload. Need some help here.",
    "This deadline is impossible. We're being set up to fail.",
    "Can't focus on anything. Too many meetings eating into productive time.",
    "Exhausted from the weekend work. This pace is unsustainable.",
    "Starting to dread Monday mornings. Something needs to change.",
    "The constant context-switching is killing my productivity and my sanity.",
    "I've been working 12-hour days for three weeks straight. This isn't healthy.",
    "Feeling completely disconnected from the team. Nobody seems to care.",
    "Another all-nighter to meet the deadline. My health is taking a hit.",
    "I don't see the point anymore. Nothing I do seems to make a difference.",
    "Stressed out beyond belief. The pressure from management is relentless.",
    "Haven't taken a day off in months. I'm running on empty.",
]

# ─────────────────────────────────────────────────────────────────────────────
# Burnout Assessment Questions (Maslach-style)
# ─────────────────────────────────────────────────────────────────────────────

ASSESSMENT_QUESTIONS = [
    {
        "id": "q1",
        "question": "I feel emotionally drained from my work.",
        "category": "emotional_exhaustion"
    },
    {
        "id": "q2",
        "question": "I feel used up at the end of the workday.",
        "category": "emotional_exhaustion"
    },
    {
        "id": "q3",
        "question": "I feel fatigued when I get up in the morning and have to face another day at work.",
        "category": "emotional_exhaustion"
    },
    {
        "id": "q4",
        "question": "Working all day is really a strain for me.",
        "category": "emotional_exhaustion"
    },
    {
        "id": "q5",
        "question": "I feel burned out from my work.",
        "category": "emotional_exhaustion"
    },
    {
        "id": "q6",
        "question": "I have become less interested in my work since I started this job.",
        "category": "depersonalization"
    },
    {
        "id": "q7",
        "question": "I have become less enthusiastic about my work.",
        "category": "depersonalization"
    },
    {
        "id": "q8",
        "question": "I feel detached from my job and coworkers.",
        "category": "depersonalization"
    },
    {
        "id": "q9",
        "question": "I doubt the significance of my work.",
        "category": "depersonalization"
    },
    {
        "id": "q10",
        "question": "I can effectively solve the problems that arise at work.",
        "category": "personal_accomplishment"
    },
    {
        "id": "q11",
        "question": "I feel I am making an effective contribution to my organization.",
        "category": "personal_accomplishment"
    },
    {
        "id": "q12",
        "question": "I feel confident about my ability to get things done.",
        "category": "personal_accomplishment"
    },
    {
        "id": "q13",
        "question": "My sleep quality has been poor due to work stress.",
        "category": "physical_symptoms"
    },
    {
        "id": "q14",
        "question": "I experience headaches, muscle tension, or fatigue frequently.",
        "category": "physical_symptoms"
    },
    {
        "id": "q15",
        "question": "I feel supported by my manager and team.",
        "category": "support"
    },
]

# Answer scale: 1 = Never, 2 = Rarely, 3 = Sometimes, 4 = Often, 5 = Always


# ─────────────────────────────────────────────────────────────────────────────
# Data Generation Functions
# ─────────────────────────────────────────────────────────────────────────────

def generate_employee_id(index):
    """Generate a realistic employee ID like EMP001."""
    return f"EMP{str(index).zfill(3)}"


def generate_employees(count=20):
    """Generate a list of mock employees with varied burnout profiles."""
    employees = []
    used_names = set()

    # Assign burnout profiles: ~30% healthy, ~40% at-risk, ~30% burnout
    profiles = (
        ["healthy"] * max(1, int(count * 0.3))
        + ["at_risk"] * max(1, int(count * 0.4))
        + ["burnout"] * max(1, int(count * 0.3))
    )
    random.shuffle(profiles)

    for i in range(1, count + 1):
        # Pick unique name
        while True:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            full_name = f"{first} {last}"
            if full_name not in used_names:
                used_names.add(full_name)
                break

        dept = random.choice(DEPARTMENTS)
        role = random.choice(ROLES[dept])
        profile = profiles[i - 1] if i - 1 < len(profiles) else random.choice(profiles)

        emp = {
            "id": generate_employee_id(i),
            "name": full_name,
            "email": f"{first.lower()}.{last.lower()}@company.com",
            "department": dept,
            "role": role,
            "profile": profile,  # hidden from frontend — used for data generation
            "join_date": (datetime.now() - timedelta(days=random.randint(180, 1800))).strftime("%Y-%m-%d"),
            "manager": f"MGR{str(random.randint(1, 5)).zfill(3)}",
        }
        employees.append(emp)

    return employees


def generate_work_logs(employee, weeks=8):
    """Generate weekly work log data for an employee."""
    logs = []
    profile = employee["profile"]
    today = datetime.now()

    for week in range(weeks, 0, -1):
        week_start = today - timedelta(weeks=week)

        if profile == "healthy":
            daily_hours = round(random.uniform(7.5, 9.0), 1)
            weekend_hours = round(random.uniform(0, 0.5), 1)
            tasks_completed = random.randint(8, 15)
            late_night_sessions = random.randint(0, 1)
            breaks_taken = random.randint(3, 5)
        elif profile == "at_risk":
            # Gradually worsening pattern
            severity = week / weeks  # lower = more recent = worse
            daily_hours = round(random.uniform(8.5 + (1 - severity) * 2, 10.0 + (1 - severity) * 2), 1)
            weekend_hours = round(random.uniform(1.0 + (1 - severity) * 2, 3.0 + (1 - severity) * 2), 1)
            tasks_min = min(max(4, int(12 * severity)), 12)
            tasks_completed = random.randint(tasks_min, 12)
            late_night_sessions = random.randint(1, max(1, 3 + int((1 - severity) * 2)))
            breaks_min = min(max(1, int(4 * severity)), 3)
            breaks_taken = random.randint(breaks_min, 3)
        else:  # burnout
            daily_hours = round(random.uniform(10.5, 14.0), 1)
            weekend_hours = round(random.uniform(3.0, 7.0), 1)
            tasks_completed = random.randint(2, 6)
            late_night_sessions = random.randint(3, 6)
            breaks_taken = random.randint(0, 1)

        log = {
            "employee_id": employee["id"],
            "week_start": week_start.strftime("%Y-%m-%d"),
            "avg_daily_hours": daily_hours,
            "weekend_hours": weekend_hours,
            "total_weekly_hours": round(daily_hours * 5 + weekend_hours, 1),
            "tasks_completed": tasks_completed,
            "tasks_assigned": tasks_completed + random.randint(0, 5),
            "late_night_sessions": late_night_sessions,
            "breaks_taken_per_day": breaks_taken,
            "days_absent": random.randint(0, 1) if profile != "burnout" else random.randint(0, 2),
            "pto_balance_days": random.randint(12, 20) if profile == "healthy" else random.randint(0, 8),
        }
        logs.append(log)

    return logs


def generate_messages(employee, weeks=8):
    """Generate mock Slack/email messages based on employee's burnout profile."""
    messages = []
    profile = employee["profile"]
    today = datetime.now()

    for week in range(weeks, 0, -1):
        # Number of messages per week
        msg_count = random.randint(3, 7)
        week_start = today - timedelta(weeks=week)

        for j in range(msg_count):
            msg_date = week_start + timedelta(days=random.randint(0, 4), hours=random.randint(8, 20))

            if profile == "healthy":
                pool = POSITIVE_MESSAGES * 3 + NEUTRAL_MESSAGES * 2
            elif profile == "at_risk":
                severity = 1 - (week / weeks)
                if severity < 0.4:
                    pool = POSITIVE_MESSAGES + NEUTRAL_MESSAGES * 2 + NEGATIVE_MESSAGES
                else:
                    pool = NEUTRAL_MESSAGES + NEGATIVE_MESSAGES * 2
            else:  # burnout
                pool = NEGATIVE_MESSAGES * 3 + NEUTRAL_MESSAGES

            msg = {
                "id": str(uuid.uuid4())[:8],
                "employee_id": employee["id"],
                "timestamp": msg_date.strftime("%Y-%m-%d %H:%M"),
                "channel": random.choice(["slack", "email"]),
                "content": random.choice(pool),
            }
            messages.append(msg)

    return messages


def generate_assessment_answers(profile, is_fake_attempt=False):
    """Generate mock assessment answers based on burnout profile.
    
    If is_fake_attempt=True, simulates an employee trying to fake good results
    (but work data will contradict the self-report).
    """
    answers = {}

    for q in ASSESSMENT_QUESTIONS:
        qid = q["id"]
        cat = q["category"]
        reverse_scored = cat == "personal_accomplishment" or cat == "support"

        if is_fake_attempt:
            # Trying to appear healthy — all low burnout scores
            if reverse_scored:
                answers[qid] = random.choice([4, 5])  # high = good
            else:
                answers[qid] = random.choice([1, 2])  # low = good
        elif profile == "healthy":
            if reverse_scored:
                answers[qid] = random.randint(3, 5)
            else:
                answers[qid] = random.randint(1, 3)
        elif profile == "at_risk":
            if reverse_scored:
                answers[qid] = random.randint(2, 4)
            else:
                answers[qid] = random.randint(2, 4)
        else:  # burnout
            if reverse_scored:
                answers[qid] = random.randint(1, 3)
            else:
                answers[qid] = random.randint(3, 5)

    return answers


def generate_assessment_history(employee, weeks=6):
    """Generate past assessment records for an employee."""
    assessments = []
    today = datetime.now()
    profile = employee["profile"]

    for week in range(weeks, 0, -1):
        # ~70% chance they took the weekly assessment
        if random.random() < 0.7:
            assess_date = today - timedelta(weeks=week)

            # 10% chance of fake attempt for burnout profiles
            is_fake = profile == "burnout" and random.random() < 0.1

            answers = generate_assessment_answers(profile, is_fake_attempt=is_fake)

            # Simulate response time (seconds per question)
            if is_fake:
                # Suspiciously fast and consistent
                response_times = {q["id"]: round(random.uniform(1.5, 3.0), 1) for q in ASSESSMENT_QUESTIONS}
            elif profile == "healthy":
                response_times = {q["id"]: round(random.uniform(5.0, 15.0), 1) for q in ASSESSMENT_QUESTIONS}
            else:
                response_times = {q["id"]: round(random.uniform(4.0, 20.0), 1) for q in ASSESSMENT_QUESTIONS}

            assessment = {
                "id": str(uuid.uuid4())[:8],
                "employee_id": employee["id"],
                "timestamp": assess_date.strftime("%Y-%m-%d %H:%M"),
                "answers": answers,
                "response_times": response_times,
                "is_fake_attempt": is_fake,  # hidden flag — used by anti-fake engine
            }
            assessments.append(assessment)

    return assessments


def generate_all_data(employee_count=20):
    """Generate complete mock dataset."""
    employees = generate_employees(employee_count)

    all_work_logs = {}
    all_messages = {}
    all_assessments = {}

    for emp in employees:
        all_work_logs[emp["id"]] = generate_work_logs(emp)
        all_messages[emp["id"]] = generate_messages(emp)
        all_assessments[emp["id"]] = generate_assessment_history(emp)

    return {
        "employees": employees,
        "work_logs": all_work_logs,
        "messages": all_messages,
        "assessments": all_assessments,
    }


# Generate data on import
MOCK_DATA = generate_all_data()