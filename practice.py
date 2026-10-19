import logging
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, abort, current_app
from flask_login import login_required, current_user
from models import db, PracticeSession, get_current_ist_date, get_current_ist_time
from exam import get_exam_window_status
from executor import executor

practice_bp = Blueprint('practice', __name__)
logger = logging.getLogger('daily_code_exam.security')


@practice_bp.route('/practice')
@login_required
def practice_page():
    """
    Practice Mode Workspace:
    Open strictly between 9:00 PM and 10:00 PM IST (server-enforced).
    Loads or initializes today's persistent PracticeSession.
    """
    is_open, window_info = get_exam_window_status()
    today_ist = get_current_ist_date()

    if not is_open:
        return render_template(
            'closed.html',
            window_info=window_info,
            now_ist=get_current_ist_time().strftime('%I:%M:%S %p IST')
        )

    # Fetch or initialize today's persistent practice session
    session_rec = PracticeSession.query.filter_by(
        user_id=current_user.id,
        session_date=today_ist
    ).first()

    if not session_rec:
        initial_snippets = [
            {
                'id': 'snippet_1',
                'title': 'Snippet 1',
                'language': 'python',
                'code': "# Practice Snippet 1 - Daily Code Exam\nimport sys\n\nprint('Today I practiced Python algorithms!')\n"
            }
        ]
        session_rec = PracticeSession(
            user_id=current_user.id,
            session_date=today_ist,
            topic="What I learned today",
            language="python",
            code=initial_snippets[0]['code'],
            minutes=0,
            heartbeat_seconds=0,
            run_count=0
        )
        session_rec.snippets = initial_snippets
        db.session.add(session_rec)
        db.session.commit()

    return render_template(
        'practice.html',
        practice_session=session_rec,
        window_info=window_info,
        today_ist=today_ist
    )


@practice_bp.route('/practice/autosave', methods=['POST'])
@login_required
def autosave():
    """
    Autosaves active code, snippets array, language, and topic every 10 seconds.
    Enforces time-window and 10 KB code limit.
    """
    is_open, _ = get_exam_window_status()
    if not is_open:
        return jsonify({'error': 'Practice window is closed.'}), 403

    today_ist = get_current_ist_date()
    session_rec = PracticeSession.query.filter_by(
        user_id=current_user.id,
        session_date=today_ist
    ).first()

    if not session_rec:
        return jsonify({'error': 'No active practice session for today.'}), 404

    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    topic = data.get('topic', '').strip() or session_rec.topic
    language = data.get('language', session_rec.language)
    snippets = data.get('snippets', [])

    # Validation: 10 KB code size limit
    max_size = current_app.config.get('MAX_CODE_SIZE_BYTES', 10240)
    if len(code.encode('utf-8')) > max_size:
        return jsonify({'error': f'Code size exceeds {max_size // 1024} KB limit.'}), 400

    session_rec.code = code
    session_rec.topic = topic[:255]
    session_rec.language = language
    if snippets and isinstance(snippets, list):
        session_rec.snippets = snippets

    db.session.commit()

    return jsonify({
        'status': 'saved',
        'updated_at': session_rec.updated_at.strftime('%I:%M:%S %p'),
        'topic': session_rec.topic
    })


@practice_bp.route('/practice/heartbeat', methods=['POST'])
@login_required
def heartbeat():
    """
    30-second study timer heartbeat.
    Only counts minutes inside the 9:00 PM - 10:00 PM IST window.
    At least 20 minutes awards a daily streak (+1).
    """
    is_open, _ = get_exam_window_status()
    if not is_open:
        return jsonify({'error': 'Outside practice window; heartbeat rejected.'}), 403

    today_ist = get_current_ist_date()
    session_rec = PracticeSession.query.filter_by(
        user_id=current_user.id,
        session_date=today_ist
    ).first()

    if not session_rec:
        return jsonify({'error': 'Practice session not found.'}), 404

    # Prevent flooding: verify at least 20 seconds elapsed since last heartbeat if recorded
    now_utc = datetime.now(timezone.utc)
    if session_rec.last_heartbeat:
        elapsed = (now_utc - session_rec.last_heartbeat.replace(tzinfo=timezone.utc)).total_seconds()
        if elapsed < 20:
            return jsonify({
                'status': 'skipped',
                'minutes': session_rec.minutes,
                'total_seconds': session_rec.heartbeat_seconds
            })

    # Record 30 seconds of study time
    result = session_rec.record_heartbeat()
    db.session.commit()

    if result['awarded_streak']:
        logger.info(f"User {current_user.username} earned daily streak from 20+ mins practice study time!")

    return jsonify({
        'status': 'ok',
        'minutes': session_rec.minutes,
        'total_seconds': session_rec.heartbeat_seconds,
        'awarded_streak': result['awarded_streak'],
        'streak': current_user.current_streak
    })


@practice_bp.route('/practice/run', methods=['POST'])
@login_required
def run_practice_code():
    """
    Executes practice code via sandbox (Piston/Judge0) or records run.
    Rate limited to 20 requests per minute per user.
    """
    is_open, _ = get_exam_window_status()
    if not is_open:
        return jsonify({'error': 'Practice window is closed.'}), 403

    today_ist = get_current_ist_date()
    session_rec = PracticeSession.query.filter_by(
        user_id=current_user.id,
        session_date=today_ist
    ).first()

    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    raw_language = data.get('language', 'python').lower()
    stdin = data.get('stdin', '')

    # Validation: code size limit (10 KB)
    max_size = current_app.config.get('MAX_CODE_SIZE_BYTES', 10240)
    if len(code.encode('utf-8')) > max_size:
        return jsonify({'error': f'Code size exceeds {max_size // 1024} KB limit.'}), 400

    # Whitelist
    allowed_langs = current_app.config.get('ALLOWED_LANGUAGES', {'python'})
    if raw_language not in allowed_langs:
        return jsonify({'error': f'Language "{raw_language}" not permitted.'}), 400

    if session_rec:
        session_rec.run_count += 1
        db.session.commit()

    backend_language = 'python' if raw_language in ('python', 'python_pyodide') else raw_language
    result = executor.execute(code=code, language=backend_language, stdin=stdin)

    return jsonify({
        'stdout': result.get('stdout', ''),
        'stderr': result.get('stderr', ''),
        'exit_code': result.get('exit_code', 0),
        'time_ms': result.get('time_ms', 0),
        'status': result.get('status', 'SUCCESS'),
        'run_count': session_rec.run_count if session_rec else 1
    })
