import json
from datetime import timedelta
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import User, Submission, Question, PracticeSession, get_current_ist_date
from auth import admin_required

dashboard_bp = Blueprint('dashboard', __name__)


def generate_calendar_heatmap(user_id):
    """
    Generates a 120-day heatmap grid ending on today's IST date.
    Each cell contains {date_str, submitted: bool, score: float, status: str, count: int}.
    Includes both exam submissions and qualifying practice sessions (20+ mins).
    """
    today_ist = get_current_ist_date()
    start_date = today_ist - timedelta(days=119)  # Approx 17 weeks

    # Fetch all submissions and practice sessions by user in range
    submissions = Submission.query.filter(
        Submission.user_id == user_id,
        Submission.submission_date >= start_date,
        Submission.submission_date <= today_ist
    ).all()

    practice_sessions = PracticeSession.query.filter(
        PracticeSession.user_id == user_id,
        PracticeSession.session_date >= start_date,
        PracticeSession.session_date <= today_ist
    ).all()

    sub_map = {s.submission_date: s for s in submissions}
    prac_map = {p.session_date: p for p in practice_sessions}

    days_data = []
    curr = start_date
    while curr <= today_ist:
        sub = sub_map.get(curr)
        prac = prac_map.get(curr)

        is_active = (sub is not None) or (prac is not None and prac.minutes >= 20)
        status_label = sub.status if sub else (f"Practice {prac.minutes}m" if prac else "None")
        score_val = sub.score if sub else (100 if (prac and prac.minutes >= 20) else 0)

        days_data.append({
            'date': curr.strftime('%Y-%m-%d'),
            'display_date': curr.strftime('%b %d, %Y'),
            'weekday': curr.weekday(),  # 0=Monday, 6=Sunday
            'submitted': is_active,
            'status': status_label,
            'score': score_val,
            'passed': f"{sub.passed_test_cases}/{sub.total_test_cases}" if sub else (f"{prac.minutes}m" if prac else "0/0")
        })
        curr += timedelta(days=1)

    return days_data


@dashboard_bp.route('/dashboard')
@login_required
def view_dashboard():
    today_ist = get_current_ist_date()

    # User's submissions ordered by latest
    user_submissions = Submission.query.filter_by(user_id=current_user.id)\
        .order_by(Submission.submission_date.desc(), Submission.id.desc()).all()

    # User's practice sessions
    practice_sessions = PracticeSession.query.filter_by(user_id=current_user.id)\
        .order_by(PracticeSession.session_date.desc(), PracticeSession.id.desc()).all()

    # Today's practice session
    today_session = next((p for p in practice_sessions if p.session_date == today_ist), None)
    today_practice_minutes = today_session.minutes if today_session else 0

    # Total practice hours
    total_practice_minutes = sum(p.minutes for p in practice_sessions)
    total_practice_hours = round(total_practice_minutes / 60.0, 1)

    # Weekly bar chart (last 7 days of practice minutes ending today)
    weekly_practice = []
    for i in range(6, -1, -1):
        day_dt = today_ist - timedelta(days=i)
        day_p = next((p for p in practice_sessions if p.session_date == day_dt), None)
        mins = day_p.minutes if day_p else 0
        weekly_practice.append({
            'day': day_dt.strftime('%a'),
            'date': day_dt.strftime('%b %d'),
            'minutes': mins,
            'pct': min(100, max(6, int((mins / 60.0) * 100))) if mins > 0 else 4,
            'target_met': mins >= 20
        })

    # User exam performance metrics
    total_submissions = len(user_submissions)
    accepted_count = sum(1 for s in user_submissions if s.status == 'Accepted')
    avg_score = round(sum(s.score for s in user_submissions) / total_submissions, 1) if total_submissions > 0 else 0.0

    # Heatmap data
    heatmap_days = generate_calendar_heatmap(current_user.id)

    # Leaderboard by streak
    leaderboard = User.query.filter(User.current_streak > 0)\
        .order_by(User.current_streak.desc(), User.longest_streak.desc(), User.id.asc())\
        .limit(20).all()

    if not leaderboard:
        leaderboard = User.query.order_by(User.longest_streak.desc(), User.current_streak.desc()).limit(10).all()

    return render_template(
        'dashboard.html',
        submissions=user_submissions,
        practice_sessions=practice_sessions,
        today_practice_minutes=today_practice_minutes,
        total_practice_hours=total_practice_hours,
        weekly_practice=weekly_practice,
        total_submissions=total_submissions,
        accepted_count=accepted_count,
        avg_score=avg_score,
        heatmap_days=heatmap_days,
        leaderboard=leaderboard,
        today_ist=today_ist
    )


@dashboard_bp.route('/admin/submissions')
@login_required
@admin_required
def admin_submissions():
    """Admin route to inspect all submissions across the platform."""
    all_submissions = Submission.query.order_by(Submission.id.desc()).limit(100).all()
    return render_template('admin_submissions.html', submissions=all_submissions)
