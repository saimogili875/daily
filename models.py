import json
import uuid
from datetime import datetime, timedelta, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import pytz

db = SQLAlchemy()
IST = pytz.timezone('Asia/Kolkata')


def get_current_ist_time():
    """Returns the current timezone-aware datetime in IST."""
    return datetime.now(IST)


def get_current_ist_date():
    """Returns today's date in IST."""
    return datetime.now(IST).date()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    session_token = db.Column(db.String(64), nullable=True, index=True)
    
    # Streak tracking
    current_streak = db.Column(db.Integer, default=0, nullable=False)
    longest_streak = db.Column(db.Integer, default=0, nullable=False)
    last_submission_date = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    submissions = db.relationship('Submission', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    practice_sessions = db.relationship('PracticeSession', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def generate_session_token(self):
        """Generates a unique session token to enforce a single active session."""
        self.session_token = uuid.uuid4().hex
        return self.session_token

    def update_streak(self, submission_ist_date):
        """
        Safely update user streaks based on IST dates:
        - If submitted yesterday: increment current_streak.
        - If submitted today: streak already counted.
        - Otherwise (missed 1+ days or first time): reset current_streak to 1.
        """
        if self.last_submission_date == submission_ist_date:
            return  # Already counted today

        yesterday = submission_ist_date - timedelta(days=1)
        if self.last_submission_date == yesterday:
            self.current_streak += 1
        else:
            self.current_streak = 1

        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

        self.last_submission_date = submission_ist_date


class LoginAttempt(db.Model):
    __tablename__ = 'login_attempts'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    successful = db.Column(db.Boolean, default=False, nullable=False)

    @classmethod
    def is_locked_out(cls, username, ip_address, max_attempts=5, window_minutes=15):
        """
        Check if account or IP is locked out:
        5 failed logins within the last 15 minutes locks the account.
        Checked by matching either the username OR the IP address.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        
        # Check by username
        user_failures = cls.query.filter(
            cls.username == username.lower().strip(),
            cls.successful.is_(False),
            cls.timestamp >= cutoff
        ).count()

        if user_failures >= max_attempts:
            return True, "username"

        # Check by IP
        ip_failures = cls.query.filter(
            cls.ip_address == ip_address.strip(),
            cls.successful.is_(False),
            cls.timestamp >= cutoff
        ).count()

        if ip_failures >= max_attempts:
            return True, "ip"

        return False, None

    @classmethod
    def record(cls, username, ip_address, successful):
        """Records a login attempt."""
        attempt = cls(
            username=username.lower().strip() if username else "unknown",
            ip_address=ip_address.strip() if ip_address else "0.0.0.0",
            successful=successful,
            timestamp=datetime.now(timezone.utc)
        )
        db.session.add(attempt)
        db.session.commit()


class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    difficulty = db.Column(db.String(20), default='medium', nullable=False)
    topic = db.Column(db.String(100), default='Algorithms', nullable=False)
    description = db.Column(db.Text, nullable=False)
    input_format = db.Column(db.Text, nullable=True)
    output_format = db.Column(db.Text, nullable=True)
    constraints = db.Column(db.Text, nullable=True)
    
    # JSON strings for test cases
    _samples = db.Column('samples', db.Text, nullable=False, default='[]')
    _hidden_tests = db.Column('hidden_tests', db.Text, nullable=False, default='[]')
    
    hint = db.Column(db.Text, nullable=True)
    time_limit_sec = db.Column(db.Integer, default=5, nullable=False)
    
    # Specific date this question is assigned to (in IST)
    exam_date = db.Column(db.Date, unique=True, nullable=True, index=True)
    is_ai_generated = db.Column(db.Boolean, default=False, nullable=False)
    numpy_allowed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    submissions = db.relationship('Submission', backref='question', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def samples(self):
        try:
            return json.loads(self._samples) if self._samples else []
        except (ValueError, TypeError):
            return []

    @samples.setter
    def samples(self, value):
        self._samples = json.dumps(value) if isinstance(value, (list, dict)) else str(value)

    @property
    def hidden_tests(self):
        try:
            return json.loads(self._hidden_tests) if self._hidden_tests else []
        except (ValueError, TypeError):
            return []

    @hidden_tests.setter
    def hidden_tests(self, value):
        self._hidden_tests = json.dumps(value) if isinstance(value, (list, dict)) else str(value)


class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Date of exam in IST (ensures 1 submission per user per day)
    submission_date = db.Column(db.Date, nullable=False, index=True)
    
    language = db.Column(db.String(30), default='python', nullable=False)
    code = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), default='Pending', nullable=False)  # Accepted, Wrong Answer, etc.
    passed_test_cases = db.Column(db.Integer, default=0, nullable=False)
    total_test_cases = db.Column(db.Integer, default=0, nullable=False)
    score = db.Column(db.Float, default=0.0, nullable=False)  # 0.0 to 100.0
    execution_time_ms = db.Column(db.Float, default=0.0, nullable=False)
    
    ai_feedback = db.Column(db.Text, nullable=True)
    _test_results = db.Column('test_results', db.Text, nullable=True, default='[]')
    
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Unique constraint: User can submit only ONCE per day
    __table_args__ = (
        db.UniqueConstraint('user_id', 'submission_date', name='uq_user_daily_submission'),
    )

    @property
    def test_results(self):
        try:
            return json.loads(self._test_results) if self._test_results else []
        except (ValueError, TypeError):
            return []

    @test_results.setter
    def test_results(self, value):
        self._test_results = json.dumps(value) if isinstance(value, (list, dict)) else str(value)


class Upload(db.Model):
    __tablename__ = 'uploads'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(30), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    extracted_text = db.Column(db.Text, nullable=False)
    upload_date = db.Column(db.Date, nullable=False, default=get_current_ist_date, index=True)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    used_for_generation = db.Column(db.Boolean, default=False, nullable=False)


class PracticeSession(db.Model):
    __tablename__ = 'practice_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_date = db.Column(db.Date, nullable=False, index=True)  # IST date
    
    topic = db.Column(db.String(255), default='Daily Coding Practice', nullable=False)
    language = db.Column(db.String(30), default='python', nullable=False)
    code = db.Column(db.Text, default='', nullable=False)
    _snippets = db.Column('snippets', db.Text, default='[]', nullable=False)
    
    # Study time tracking
    minutes = db.Column(db.Integer, default=0, nullable=False)
    heartbeat_seconds = db.Column(db.Integer, default=0, nullable=False)
    run_count = db.Column(db.Integer, default=0, nullable=False)
    last_heartbeat = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Unique constraint: exactly ONE practice session per user per day
    __table_args__ = (
        db.UniqueConstraint('user_id', 'session_date', name='uq_user_daily_practice'),
    )

    @property
    def snippets(self):
        try:
            return json.loads(self._snippets) if self._snippets else []
        except (ValueError, TypeError):
            return []

    @snippets.setter
    def snippets(self, value):
        self._snippets = json.dumps(value) if isinstance(value, (list, dict)) else str(value)

    def record_heartbeat(self):
        """
        Records a 30-second heartbeat of active study time.
        Calculates accumulated minutes and checks for streak eligibility (at least 20 minutes = streak +1).
        """
        now_utc = datetime.now(timezone.utc)
        self.heartbeat_seconds += 30
        self.minutes = self.heartbeat_seconds // 60
        self.last_heartbeat = now_utc

        awarded_streak = False
        if self.minutes >= 20:
            # Check if streak already updated today
            if self.user and self.user.last_submission_date != self.session_date:
                self.user.update_streak(self.session_date)
                awarded_streak = True

        return {
            'minutes': self.minutes,
            'total_seconds': self.heartbeat_seconds,
            'awarded_streak': awarded_streak,
            'streak': self.user.current_streak if self.user else 0
        }
