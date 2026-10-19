import json
from datetime import timedelta
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
from models import User, Submission, Question, get_current_ist_date
from auth import admin_required

dashboard_bp = Blueprint('dashboard', __name__)


def generate_calendar_heatmap(user_id):
    """
    Generates a 120-day heatmap grid ending on today's IST date.
    Each cell contains {date_str, submitted: bool, score: float, status: str, count: int}.
    """
    today_ist = get_current_ist_date()
    start_date = today_ist - timedelta(days=119)  # Approx 17 weeks

    # Fetch all submissions by user in range
    submissions = Submission.query.filter(
        Submission.user_id == user_id,
        Submission.submission_date >= start_date,
        Submission.submission_date <= today_ist
    ).all()

    sub_map = {s.submission_date: s for s in submissions}

    days_data = []
    curr = start_date
    while curr <= today_ist:
        sub = sub_map.get(curr)
        days_data.append({
            'date': curr.strftime('%Y-%m-%d'),
            'display_date': curr.strftime('%b %d, %Y'),
            'weekday': curr.weekday(),  # 0=Monday, 6=Sunday
            'submitted': sub is not None,
            'status': sub.status if sub else 'None',
            'score': sub.score if sub else 0,
            'passed': f"{sub.passed_test_cases}/{sub.total_test_cases}" if sub else "0/0"
        })
        curr += timedelta(days=1)

    return days_data


@dashboard_bp.route('/dashboard')
@login_required
def view_dashboard():
    # User's submissions ordered by latest
    user_submissions = Submission.query.filter_by(user_id=current_user.id)\
        .order_by(Submission.submission_date.desc(), Submission.id.desc()).all()

    # User performance metrics
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
        # Fallback to display top users by longest streak if current streaks are 0
        leaderboard = User.query.order_by(User.longest_streak.desc(), User.current_streak.desc()).limit(10).all()

    return render_template(
        'dashboard.html',
        submissions=user_submissions,
        total_submissions=total_submissions,
        accepted_count=accepted_count,
        avg_score=avg_score,
        heatmap_days=heatmap_days,
        leaderboard=leaderboard,
        today_ist=get_current_ist_date()
    )


@dashboard_bp.route('/admin/submissions')
@login_required
@admin_required
def admin_submissions():
    """Admin route to inspect all submissions across the platform."""
    all_submissions = Submission.query.order_by(Submission.id.desc()).limit(100).all()
    return render_template('admin_submissions.html', submissions=all_submissions)
