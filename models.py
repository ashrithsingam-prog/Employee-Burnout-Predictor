from flask_sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    department = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    join_date = db.Column(db.String(20), nullable=False)
    is_hr = db.Column(db.Boolean, default=False)
    is_manager = db.Column(db.Boolean, default=False)
    manager = db.Column(db.String(10), nullable=True) # ID of manager
    last_login = db.Column(db.String(50), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "department": self.department,
            "role": self.role,
            "join_date": self.join_date,
            "is_hr": self.is_hr,
            "is_manager": self.is_manager,
            "manager": self.manager
        }

class WorkLog(db.Model):
    __tablename__ = 'work_logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_id = db.Column(db.String(10), db.ForeignKey('employees.id'), nullable=False)
    week_start = db.Column(db.String(20), nullable=False)
    avg_daily_hours = db.Column(db.Float, nullable=False)
    weekend_hours = db.Column(db.Float, nullable=False)
    weekend_screen_time = db.Column(db.Float, nullable=False)
    tasks_assigned = db.Column(db.Integer, nullable=False)
    tasks_completed = db.Column(db.Integer, nullable=False)
    late_night_sessions = db.Column(db.Integer, nullable=False)
    breaks_taken_per_day = db.Column(db.Integer, nullable=False)
    
    def to_dict(self):
        return {
            "week_start": self.week_start,
            "avg_daily_hours": self.avg_daily_hours,
            "weekend_hours": self.weekend_hours,
            "weekend_screen_time": self.weekend_screen_time,
            "tasks_assigned": self.tasks_assigned,
            "tasks_completed": self.tasks_completed,
            "late_night_sessions": self.late_night_sessions,
            "breaks_taken_per_day": self.breaks_taken_per_day
        }

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_id = db.Column(db.String(10), db.ForeignKey('employees.id'), nullable=False)
    timestamp = db.Column(db.String(30), nullable=False)
    content = db.Column(db.Text, nullable=False)
    channel = db.Column(db.String(50), nullable=False)
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "content": self.content,
            "channel": self.channel
        }

class Assessment(db.Model):
    __tablename__ = 'assessments'
    id = db.Column(db.String(50), primary_key=True)
    employee_id = db.Column(db.String(10), db.ForeignKey('employees.id'), nullable=False)
    timestamp = db.Column(db.String(30), nullable=False)
    _answers = db.Column('answers', db.Text, nullable=False)
    _response_times = db.Column('response_times', db.Text, nullable=False)
    is_fake_attempt = db.Column(db.Boolean, default=False)

    @property
    def answers(self):
        return json.loads(self._answers)
    
    @answers.setter
    def answers(self, value):
        self._answers = json.dumps(value)
        
    @property
    def response_times(self):
        return json.loads(self._response_times) if self._response_times else {}
        
    @response_times.setter
    def response_times(self, value):
        self._response_times = json.dumps(value)
        
    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "timestamp": self.timestamp,
            "answers": self.answers,
            "response_times": self.response_times,
            "is_fake_attempt": self.is_fake_attempt
        }

class HRAction(db.Model):
    __tablename__ = 'hr_actions'
    id = db.Column(db.String(50), primary_key=True)
    employee_id = db.Column(db.String(10), db.ForeignKey('employees.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "action_type": self.action_type,
            "details": self.details,
            "timestamp": self.timestamp,
            "status": self.status
        }

class PeerReport(db.Model):
    __tablename__ = 'peer_reports'
    id = db.Column(db.String(50), primary_key=True)
    reporter_id = db.Column(db.String(10), nullable=True) # Null if anonymous
    reporter_name = db.Column(db.String(100), nullable=True)
    reported_employee_id = db.Column(db.String(10), db.ForeignKey('employees.id'), nullable=False)
    reported_employee_name = db.Column(db.String(100), nullable=False)
    concern_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    resolved_at = db.Column(db.String(30), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "reporter_id": self.reporter_id,
            "reporter_name": self.reporter_name,
            "reported_employee_id": self.reported_employee_id,
            "reported_employee_name": self.reported_employee_name,
            "concern_type": self.concern_type,
            "description": self.description,
            "timestamp": self.timestamp,
            "status": self.status,
            "resolved_at": self.resolved_at
        }
