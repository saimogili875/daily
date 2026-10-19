import os
import logging
from datetime import datetime, time as dtime, timedelta
from flask import Blueprint, render_template, request, jsonify, abort, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import db, Question, Submission, Upload, IST, get_current_ist_time, get_current_ist_date
from executor import executor
from groq_client import extract_text_from_file, generate_groq_question, get_ai_feedback
from auth import admin_required

exam_bp = Blueprint('exam', __name__)
logger = logging.getLogger('daily_code_exam.security')


def get_exam_window_status():
    """
    Checks if current IST server time is within the exam window (9:00 PM to 10:00 PM IST).
    Returns (is_open: bool, time_info: dict).
    """
    if current_app.config.get('BYPASS_TIME_WINDOW', False):
        return True, {
            'is_open': True,
            'seconds_left': 3600,
            'target_time_iso': '',
            'message': 'Bypass Mode Active (Testing)'
        }

    now_ist = get_current_ist_time()
    today_date = now_ist.date()

    window_start = datetime.combine(today_date, dtime(21, 0, 0))
    window_start = IST.localize(window_start)

    window_end = datetime.combine(today_date, dtime(22, 0, 0))
    window_end = IST.localize(window_end)

    if window_start <= now_ist < window_end:
        # Window is currently open
        seconds_left = max(0, int((window_end - now_ist).total_seconds()))
        return True, {
            'is_open': True,
            'seconds_left': seconds_left,
            'target_time_iso': window_end.isoformat(),
            'message': 'Exam window is OPEN'
        }
    else:
        # Window is closed; calculate countdown to next 9:00 PM IST
        if now_ist >= window_end:
            # Next window is tomorrow 9:00 PM IST
            next_start = window_start + timedelta(days=1)
        else:
            # Next window is today 9:00 PM IST
            next_start = window_start

        seconds_until_start = max(0, int((next_start - now_ist).total_seconds()))
        return False, {
            'is_open': False,
            'seconds_left': seconds_until_start,
            'target_time_iso': next_start.isoformat(),
            'message': 'Exam window is CLOSED'
        }


def get_daily_question():
    """
    Selects today's question:
    1. Looks for a question specifically assigned to today's IST date (e.g. from Groq AI generator).
    2. If none, falls back to seeded questions using date ordinal modulo total questions.
    """
    today_ist = get_current_ist_date()

    # Priority 1: AI Question generated specifically for today
    today_ai_q = Question.query.filter_by(exam_date=today_ist).first()
    if today_ai_q:
        return today_ai_q

    # Priority 2: Seeded fallback pool (questions where exam_date is None)
    seeded_questions = Question.query.filter(Question.exam_date.is_(None)).order_by(Question.id).all()
    if not seeded_questions:
        # Any question available
        seeded_questions = Question.query.order_by(Question.id).all()

    if seeded_questions:
        index = today_ist.toordinal() % len(seeded_questions)
        return seeded_questions[index]

    return None


@exam_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('exam.exam_page'))
    return redirect(url_for('auth.login'))


@exam_bp.route('/exam')
@login_required
def exam_page():
    is_open, window_info = get_exam_window_status()
    today_ist = get_current_ist_date()
    question = get_daily_question()

    if not is_open:
        return render_template(
            'closed.html',
            window_info=window_info,
            now_ist=get_current_ist_time().strftime('%I:%M:%S %p IST')
        )

    # Check if user has already submitted today
    submission = Submission.query.filter_by(
        user_id=current_user.id,
        submission_date=today_ist
    ).first()

    return render_template(
        'exam.html',
        question=question,
        submission=submission,
        window_info=window_info,
        today_ist=today_ist
    )


@exam_bp.route('/exam/run', methods=['POST'])
@login_required
def run_code():
    """
    Online Compiler Execution Endpoint:
    Allows running code with custom STDIN or running against visible sample test cases.
    Protected by time-window and rate limiting.
    """
    is_open, _ = get_exam_window_status()
    if not is_open:
        logger.warning(f"Unauthorized Run outside window by user {current_user.username} from IP {request.remote_addr}")
        return jsonify({'error': 'Exam window is currently closed. Execution blocked.'}), 403

    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    raw_language = data.get('language', 'python').lower()
    stdin = data.get('stdin', '')
    run_samples = data.get('run_samples', False)

    # Validation: code size limit (10 KB)
    max_size = current_app.config.get('MAX_CODE_SIZE_BYTES', 10240)
    if len(code.encode('utf-8')) > max_size:
        return jsonify({'error': f'Code size exceeds maximum limit of {max_size // 1024} KB.'}), 400

    # Validation: language whitelist
    allowed_langs = current_app.config.get('ALLOWED_LANGUAGES', {'python'})
    if raw_language not in allowed_langs:
        return jsonify({'error': f'Language "{raw_language}" is not permitted.'}), 400

    backend_language = 'python' if raw_language in ('python', 'python_pyodide') else raw_language
    question = get_daily_question()
    needs_numpy = getattr(question, 'numpy_allowed', False) if question else False

    if run_samples and question:
        sample_results = executor.run_tests(
            code=code, 
            language=backend_language, 
            test_cases=question.samples, 
            needs_numpy=needs_numpy
        )
        return jsonify({
            'type': 'samples',
            'summary': f"Passed {sample_results['passed']}/{sample_results['total']} sample tests.",
            'passed': sample_results['passed'],
            'total': sample_results['total'],
            'results': sample_results['results']
        })
    else:
        result = executor.execute(
            code=code, 
            language=backend_language, 
            stdin=stdin, 
            needs_numpy=needs_numpy
        )
        return jsonify({
            'type': 'custom',
            'stdout': result.get('stdout', ''),
            'stderr': result.get('stderr', ''),
            'exit_code': result.get('exit_code', 0),
            'time_ms': result.get('time_ms', 0),
            'status': result.get('status', 'SUCCESS')
        })


@exam_bp.route('/exam/submit', methods=['POST'])
@login_required
def submit_exam():
    """
    Daily Exam Submission Endpoint:
    Enforces time window, 10 KB code size limit, 1 submission per user per day constraint,
    runs hidden test cases, fetches AI evaluation, and recalculates streaks.
    Browser execution is NEVER trusted for grading; tests are evaluated on the backend sandbox.
    """
    is_open, _ = get_exam_window_status()
    today_ist = get_current_ist_date()

    if not is_open:
        logger.warning(f"Security Alert: Submit rejected outside window for user {current_user.username} from IP {request.remote_addr}")
        return jsonify({'error': 'Exam window is closed. Submissions are only accepted between 9:00 PM and 10:00 PM IST.'}), 403

    # Check unique submission for today
    existing = Submission.query.filter_by(
        user_id=current_user.id,
        submission_date=today_ist
    ).first()
    if existing:
        return jsonify({'error': 'You have already submitted your solution for today.'}), 400

    data = request.get_json(silent=True) or {}
    code = data.get('code', '').strip()
    raw_language = data.get('language', 'python').lower()

    if not code:
        return jsonify({'error': 'Cannot submit empty code.'}), 400

    # Validation: code size limit (10 KB)
    max_size = current_app.config.get('MAX_CODE_SIZE_BYTES', 10240)
    if len(code.encode('utf-8')) > max_size:
        return jsonify({'error': f'Code size exceeds {max_size // 1024} KB limit.'}), 400

    # Validation: language whitelist
    allowed_langs = current_app.config.get('ALLOWED_LANGUAGES', {'python'})
    if raw_language not in allowed_langs:
        return jsonify({'error': 'Unsupported programming language.'}), 400

    backend_language = 'python' if raw_language in ('python', 'python_pyodide') else raw_language
    question = get_daily_question()
    if not question:
        return jsonify({'error': 'No question active for today.'}), 500

    needs_numpy = getattr(question, 'numpy_allowed', False)

    # Evaluate against hidden test cases using backend sandbox
    test_eval = executor.run_tests(
        code=code, 
        language=backend_language, 
        test_cases=question.hidden_tests, 
        needs_numpy=needs_numpy
    )
    passed_count = test_eval['passed']
    total_count = test_eval['total']
    score = test_eval['score']
    status = 'Accepted' if (passed_count == total_count and total_count > 0) else 'Wrong Answer'

    # Groq AI Code Review and Feedback
    ai_feedback = get_ai_feedback(
        question_title=question.title,
        description=question.description,
        code=code,
        passed_count=passed_count,
        total_count=total_count,
        test_results=test_eval['results']
    )

    submission = Submission(
        user_id=current_user.id,
        question_id=question.id,
        submission_date=today_ist,
        language=raw_language,
        code=code,
        status=status,
        passed_test_cases=passed_count,
        total_test_cases=total_count,
        score=score,
        execution_time_ms=test_eval['total_time_ms'],
        ai_feedback=ai_feedback
    )
    submission.test_results = test_eval['results']
    db.session.add(submission)

    # Recalculate streak safely using IST dates
    current_user.update_streak(today_ist)
    db.session.commit()

    logger.info(f"User {current_user.username} successfully submitted daily exam. Score: {score}%. Streak: {current_user.current_streak}")

    return jsonify({
        'status': 'success',
        'submission_id': submission.id,
        'exam_status': status,
        'passed': passed_count,
        'total': total_count,
        'score': score,
        'streak': current_user.current_streak,
        'longest_streak': current_user.longest_streak,
        'ai_feedback': ai_feedback,
        'redirect_url': url_for('dashboard.view_dashboard')
    })


# ==========================================
# ADMIN ROUTES (File Upload & Groq Trigger)
# ==========================================

@exam_bp.route('/admin/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_upload():
    today_ist = get_current_ist_date()

    if request.method == 'POST':
        if 'study_file' not in request.files:
            flash("No file part in the request.", "danger")
            return redirect(request.url)

        file = request.files['study_file']
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(request.url)

        orig_filename = secure_filename(file.filename)
        _, ext = os.path.splitext(orig_filename)
        ext = ext.lower()

        allowed_exts = current_app.config.get('ALLOWED_EXTENSIONS', {'.py', '.txt', '.pdf', '.docx'})
        if ext not in allowed_exts:
            flash(f"Invalid file type. Allowed: {', '.join(allowed_exts)}", "danger")
            return redirect(request.url)

        # Ensure upload folder exists
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        save_path = os.path.join(upload_folder, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{orig_filename}")
        file.save(save_path)
        file_size = os.path.getsize(save_path)

        # Max 2MB check
        if file_size > current_app.config.get('MAX_CONTENT_LENGTH', 2 * 1024 * 1024):
            os.remove(save_path)
            flash("File size exceeds 2 MB limit.", "danger")
            return redirect(request.url)

        # Extract text from file
        extracted = extract_text_from_file(save_path, orig_filename)
        if not extracted.strip():
            flash("Could not extract any readable text from the file.", "warning")

        upload_entry = Upload(
            filename=save_path,
            original_filename=orig_filename,
            file_type=ext,
            file_size=file_size,
            extracted_text=extracted,
            upload_date=today_ist
        )
        db.session.add(upload_entry)
        db.session.commit()

        flash(f"Successfully uploaded and indexed '{orig_filename}' ({round(file_size / 1024, 1)} KB).", "success")
        return redirect(url_for('exam.admin_upload'))

    recent_uploads = Upload.query.order_by(Upload.id.desc()).limit(15).all()
    today_question = Question.query.filter_by(exam_date=today_ist).first()

    return render_template(
        'admin_upload.html',
        recent_uploads=recent_uploads,
        today_question=today_question,
        today_ist=today_ist
    )


@exam_bp.route('/admin/generate-today-question', methods=['POST'])
@login_required
@admin_required
def admin_generate_today_question():
    """
    On-demand question generation using the most recent upload and Groq.
    """
    success, message = trigger_groq_question_generation()
    if success:
        flash(message, "success")
    else:
        flash(f"Question generation failed: {message}", "danger")
    return redirect(url_for('exam.admin_upload'))


def trigger_groq_question_generation():
    """
    Core function for Groq question generation.
    Used by both the on-demand admin endpoint and the daily 8:55 PM IST APScheduler job.
    """
    today_ist = get_current_ist_date()
    yesterday_ist = today_ist - timedelta(days=1)
    weekday_name = get_current_ist_time().strftime('%A')

    # Look for most recent upload (yesterday's file preferred, or latest uploaded)
    upload = Upload.query.filter_by(upload_date=yesterday_ist).order_by(Upload.id.desc()).first()
    if not upload:
        upload = Upload.query.order_by(Upload.id.desc()).first()

    if not upload or not upload.extracted_text.strip():
        logger.warning("No study file found with readable text; falling back to seed question.")
        return False, "No uploaded study file found to generate question from."

    q_data = generate_groq_question(
        file_text=upload.extracted_text,
        today_ist=str(today_ist),
        weekday=weekday_name
    )

    if not q_data:
        return False, "Groq AI generation call failed. Will fall back to seeded question."

    # Remove or update any existing question for today_ist
    existing_today = Question.query.filter_by(exam_date=today_ist).first()
    if existing_today:
        db.session.delete(existing_today)
        db.session.commit()

    new_q = Question(
        title=q_data['title'],
        difficulty=q_data.get('difficulty', 'medium'),
        topic=q_data.get('topic', 'Algorithms'),
        description=q_data['description'],
        input_format=q_data.get('input_format', ''),
        output_format=q_data.get('output_format', ''),
        constraints=q_data.get('constraints', ''),
        hint=q_data.get('hint', ''),
        time_limit_sec=q_data.get('time_limit_sec', 5),
        exam_date=today_ist,
        is_ai_generated=True,
        numpy_allowed=q_data.get('numpy_allowed', False)
    )
    new_q.samples = q_data.get('samples', [])
    new_q.hidden_tests = q_data.get('hidden_tests', [])

    db.session.add(new_q)
    upload.used_for_generation = True
    db.session.commit()

    logger.info(f"Generated new Groq question for {today_ist}: '{new_q.title}' from upload '{upload.original_filename}'")
    return True, f"Successfully generated question '{new_q.title}' for {today_ist} using Groq AI!"
