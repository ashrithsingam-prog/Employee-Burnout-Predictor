<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-2.x-000000?style=for-the-badge&logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/NLP-TextBlob-FF6F00?style=for-the-badge&logo=data:image/svg+xml;base64,..." />
  <img src="https://img.shields.io/badge/License-MIT-34d399?style=for-the-badge" />
</p>

<h1 align="center">🛡 BurnShield</h1>
<h3 align="center">Employee Burnout Prediction & Wellness Intelligence Platform</h3>

<p align="center">
  <em>A data-driven, multi-signal burnout detection system that goes beyond simple surveys —<br>
  combining NLP sentiment analysis, work pattern tracking, anti-faking intelligence, and emotional masking detection<br>
  to give HR teams the full picture before it's too late.</em>
</p>

---

## 🎯 The Problem

Employee burnout costs companies an estimated **$322 billion globally** in turnover and lost productivity (Gallup, 2024). Traditional solutions rely on **self-reported surveys** — but burned-out employees often:

- ❌ **Fake** their responses to avoid attention
- ❌ **Mask** their emotions with forced positivity in official channels
- ❌ Go unnoticed by managers who lack **data-driven visibility**

**BurnShield** solves this by triangulating **4 independent data signals** to produce an accurate, tamper-resistant burnout score.

---

## 🧠 How It Works — The Intelligence Pipeline

BurnShield doesn't just ask "How are you feeling?" — it **cross-validates** self-reports against objective behavioral data.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    BURNOUT SCORING ENGINE                            │
│                                                                      │
│   ┌─────────────┐   ┌─────────────┐   ┌──────────────┐   ┌────────┐│
│   │ Assessment  │   │  Sentiment  │   │ Work Pattern │   │Produc- ││
│   │   (40%)     │   │   (20%)     │   │   (30%)      │   │tivity  ││
│   │             │   │             │   │              │   │(10%)   ││
│   │ Maslach-    │   │ NLP on      │   │ Hours, Late  │   │Task    ││
│   │ style       │   │ Slack/Email │   │ Nights, PTO, │   │Compl.  ││
│   │ Survey +    │   │ Messages    │   │ Weekend Work │   │Trends  ││
│   │ Trick Qs    │   │ (TextBlob)  │   │              │   │        ││
│   └──────┬──────┘   └──────┬──────┘   └──────┬───────┘   └───┬────┘│
│          │                 │                  │               │      │
│          ▼                 ▼                  ▼               ▼      │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │              WEIGHTED COMPOSITE SCORE (0-100%)              │    │
│   └──────────────────────┬──────────────────────────────────────┘    │
│                          │                                           │
│          ┌───────────────┼───────────────┐                          │
│          ▼               ▼               ▼                          │
│   ┌────────────┐  ┌────────────┐  ┌─────────────┐                  │
│   │Anti-Faking │  │ Emotional  │  │   Score      │                  │
│   │ Detection  │  │  Masking   │  │ Adjustment   │                  │
│   │            │  │ Detection  │  │ & Risk Level │                  │
│   └────────────┘  └────────────┘  └─────────────┘                  │
└──────────────────────────────────────────────────────────────────────┘
```

### Signal Weights
| Signal | Weight | Source |
|---|---|---|
| **Self-Assessment** | 40% | Maslach-style burnout questionnaire (17 questions) |
| **Work Patterns** | 30% | Daily hours, weekend screen time, late nights, breaks, PTO |
| **Sentiment Analysis** | 20% | NLP polarity tracking on Slack/email messages |
| **Productivity** | 10% | Task completion rates and decline trends |

---

## 🔥 Key Features

### 1. 🎭 Anti-Faking Intelligence
Most burnout tools are trivially gameable. BurnShield uses **5 independent faking signals**:

| Detection Method | How It Works |
|---|---|
| **Attention Check Questions** | Two hidden "trick questions" embedded in the assessment (e.g., "Select 'Often' for this question"). Failing = instant flag. |
| **Response Time Analysis** | Average response time < 3 seconds/question → speed-clicking detected |
| **Response Time Variance** | Extremely uniform timing (variance < 1.0s) → robotic/non-genuine |
| **Self-Report vs Work Data Gap** | If self-report says 20% burnout but work logs show 14hr days → flagged |
| **Sentiment vs Self-Report Gap** | If self-report says "fine" but Slack messages say "I can't do this anymore" → flagged |

> When faking is detected, the system **overrides** the self-reported score with objective data (sentiment + work pattern + productivity).

### 2. 🧠 Emotional Masking Detection
**The hardest burnout cases to catch.** Some employees maintain a cheerful facade in official channels while objectively drowning.

BurnShield detects this by comparing:
- **Sentiment polarity** (positive tone in messages) vs **work stress score** (high hours, no breaks)
- **Positive message ratio** vs **objective workload**
- **Improving sentiment trend** vs **worsening work hours** (classic overcompensation)

When masking is detected, the UI displays a dedicated purple alert card with detailed reasoning.

### 3. 📊 Composite Burnout Scoring
- **Weighted 4-signal composite** (not just a survey score)
- **Risk levels**: Low (< 35%) → Moderate (< 55%) → High (< 75%) → Critical (< 90%)
- **Flight Risk calculation**: Probability of quitting (0-100%) with estimated replacement cost
- **Assessment trend tracking**: Historical score visualization over time

### 4. 👔 Manager Blindspot Analysis
HR can identify **systemic leadership issues** — not just individual burnout:
- Teams grouped by manager with average burnout scores
- High-risk team member counts
- Actionable warnings when a manager's entire team shows elevated burnout

### 5. 📩 Peer Concern Reporting
- Employees can report concerns about colleagues (anonymous or identified)
- HR receives categorized reports: **Workload, Burnout, Behavior Change, Health, Other**
- One-click "Take Action" from the HR dashboard auto-generates appropriate interventions

### 6. 💬 Ghostwritten Empathy (Safe Icebreakers)
HR managers often don't know **how** to start a conversation about burnout. BurnShield generates **context-aware outreach messages** based on each employee's data:
- Masking detected → "Hi [Name], you always bring great energy, but I want to make sure you're taking care of yourself too..."
- High workload → "I know the team has been pushing hard. Do we need to shift some priorities?"
- Routine check-in → "How are you feeling about your current bandwidth and projects?"

Copy-paste ready for Slack or Email.

### 7. 🏢 Role-Based Access Control
| Role | Access |
|---|---|
| **Employee** | Personal dashboard, self-assessment, peer reporting |
| **Manager** | Employee dashboard + team HR action notifications |
| **HR** | Full HR dashboard, employee deep-dives, action tools, blindspot analysis |

### 8. 📄 PDF Export
Assessment results can be downloaded as branded PDF reports with `html2pdf.js`.

---

## 🖥 Screenshots & UI

BurnShield features a **premium dark-mode dashboard** built with a custom CSS design system featuring:
- Glassmorphism cards with subtle hover effects
- SVG wellness ring visualizations
- Color-coded risk meters and progress bars
- Responsive layout with mobile bottom navigation
- Custom scrollbar styling and micro-animations

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+, Flask |
| **NLP Engine** | TextBlob (sentiment polarity & subjectivity analysis) |
| **Frontend** | Jinja2 templates, custom CSS design system (no frameworks), SVG graphics |
| **PDF Export** | html2pdf.js |
| **Data** | In-memory mock data generator with realistic burnout profiles |
| **Auth** | Flask sessions with role-based decorators |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/ashrithsingam-prog/Employee-Burnout-Predictor.git
cd Employee-Burnout-Predictor

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download TextBlob corpora (first time only)
python -m textblob.download_corpora

# 4. Run the server
python app.py
```

The server starts at **http://localhost:5050**

### Demo Login Credentials

| Role | Employee ID | What You'll See |
|---|---|---|
| 🧑‍💼 **Employee** | `EMP001` – `EMP015` | Personal wellness dashboard, assessments, peer reports |
| 👔 **Manager** | `MGR001` – `MGR005` | Employee dashboard + team HR action notifications |
| 🏢 **HR** | `HR001` – `HR005` | Full HR dashboard with all analytics and action tools |

> **Tip:** Log in as `HR001` first to see the full platform. Then try `EMP001` as an employee.

---

## 📁 Project Structure

```
Employee-Burnout-Predictor/
├── app.py                  # Flask server — routes, auth, page rendering
├── burnout_engine.py       # Scoring engine, NLP, faking/masking detection
├── mock_data.py            # Realistic data generator (25 employees)
├── requirements.txt        # Python dependencies
├── static/
│   └── style.css           # Custom CSS design system
└── templates/
    ├── base.html            # Master layout (sidebar, mobile nav, 1600+ lines of CSS)
    ├── index.html           # Landing page
    ├── login.html           # Employee login
    ├── dashboard.html       # Employee wellness dashboard
    ├── assesment.html       # Burnout assessment questionnaire
    ├── assesment_result.html# Assessment results + PDF export
    ├── peer_report.html     # Peer concern submission form
    ├── profile.html         # Employee profile page
    ├── hr_dashboard.html    # HR overview — risk distribution, blindspots, reports
    └── hr_employee.html     # HR deep-dive — per-employee analytics & actions
```

---

## 📊 API Endpoints

BurnShield also exposes a full REST API for integration:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/employees` | List all employees with burnout scores |
| `GET` | `/api/employee/<id>` | Detailed burnout analysis for one employee |
| `GET` | `/api/assessment/questions` | Get assessment questionnaire |
| `POST` | `/api/assessment/submit` | Submit assessment answers (JSON) |
| `GET` | `/api/sentiment/<id>` | Get sentiment analysis for an employee |
| `GET` | `/api/alerts` | Get all HR alerts for at-risk employees |
| `GET` | `/api/departments` | List all departments |

---

## 🧪 Burnout Scoring — Technical Details

### Assessment Score (`compute_assessment_score`)
- 17 Maslach-style questions across 5 categories:
  - Emotional Exhaustion (5 questions, 3x weight)
  - Depersonalization (4 questions, 3x weight)
  - Personal Accomplishment (3 questions, 1x weight, reverse-scored)
  - Physical Symptoms (2 questions, 3x weight)
  - Support (1 question, 1x weight, reverse-scored)
  - Attention Check (2 trick questions, not scored but flag faking)

### Work Pattern Score (`compute_work_pattern_score`)
- **Daily hours** (8h normal → 14h extreme): 30% weight
- **Weekend work**: 20% weight
- **Late night sessions** (0-1 normal → 5+ extreme): 20% weight
- **Breaks taken** (fewer = higher risk): 15% weight
- **PTO balance** (low = higher risk): 15% weight

### Faking Score Adjustment
When faking is detected (suspicion ≥ 0.3):
```
adjusted_score = max(composite_score, objective_only_score)
where objective_only_score = sentiment(40%) + work_pattern(35%) + productivity(25%)
```

### Masking Score Adjustment
When masking is detected and work score exceeds adjusted score:
```
final_score = adjusted_score(40%) + work_score(60%)
```

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

## 📜 License

This project is licensed under the MIT License.

---

<p align="center">
  <strong>Built with ❤️ for employee wellbeing</strong><br>
  <em>Because your team's health is your company's greatest asset.</em>
</p>