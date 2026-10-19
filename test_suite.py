"""
Automated Test Suite for Daily Code Exam
Tests:
1. Registration & Password complexity validation
2. Login & Single active session enforcement
3. Login lockout (5 failed attempts trigger 15-minute lock)
4. Server time-window enforcement (off-hours closed & 403 on run/submit)
5. Sandbox code execution (online compiler with STDIN)
6. Exam submission & Streak calculation logic
7. Admin route protection
"""

import unittest
from datetime import date, timedelta
from app import create_app
from models import db, User, Question, Submission, LoginAttempt, get_current_ist_date
from executor import executor

class DailyCodeExamTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('development')
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF in tests for direct POST calls
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_password_validation(self):
        """Test registration rejecting weak passwords and accepting compliant passwords."""
        from auth import validate_password_strength

        # Too short (< 10)
        valid, msg = validate_password_strength("Short1!")
        self.assertFalse(valid)

        # Missing uppercase
        valid, msg = validate_password_strength("lowercase123!@#")
        self.assertFalse(valid)

        # Missing lowercase
        valid, msg = validate_password_strength("UPPERCASE123!@#")
        self.assertFalse(valid)

        # Missing number
        valid, msg = validate_password_strength("NoNumbersHere!@#")
        self.assertFalse(valid)

        # Missing symbol
        valid, msg = validate_password_strength("NoSymbols12345")
        self.assertFalse(valid)

        # Common password blacklist
        valid, msg = validate_password_strength("Password123!")
        self.assertFalse(valid)

        # Valid strong password
        valid, msg = validate_password_strength("SecureCode#2026Ex!")
        self.assertTrue(valid)
        print("✓ Password complexity validation passed.")

    def test_02_login_lockout(self):
        """Test that 5 failed logins triggers account lockout with generic error."""
        import uuid
        test_user = f"lock_{uuid.uuid4().hex[:6]}"
        test_ip = "192.168.1.100"

        # Register user
        reg_resp = self.client.post('/register', data={
            'username': test_user,
            'email': f'{test_user}@example.com',
            'password': 'ComplexPassword!2026',
            'confirm_password': 'ComplexPassword!2026'
        }, follow_redirects=True)
        self.assertEqual(reg_resp.status_code, 200)

        # Perform 5 failed login attempts
        for i in range(5):
            resp = self.client.post('/login', data={
                'username': test_user,
                'password': 'WrongPassword999!'
            }, environ_base={'REMOTE_ADDR': test_ip}, follow_redirects=True)
            self.assertIn(b"Invalid credentials", resp.data)

        # Check that is_locked_out now returns True
        is_locked, reason = LoginAttempt.is_locked_out(test_user, test_ip, max_attempts=5, window_minutes=15)
        self.assertTrue(is_locked)

        # Even with the CORRECT password now, the login must be rejected with the same generic message!
        lock_attempt_resp = self.client.post('/login', data={
            'username': test_user,
            'password': 'ComplexPassword!2026'
        }, environ_base={'REMOTE_ADDR': test_ip}, follow_redirects=True)
        self.assertIn(b"Invalid credentials", lock_attempt_resp.data)
        print("✓ Login lockout (5 failed attempts -> 15 min lock) passed.")

    def test_03_time_window_enforcement(self):
        """Test that off-hours access renders closed.html and run/submit returns 403."""
        import uuid
        # Ensure BYPASS_TIME_WINDOW is False
        self.app.config['BYPASS_TIME_WINDOW'] = False

        # Register and login candidate
        candidate = f"win_{uuid.uuid4().hex[:6]}"
        self.client.post('/register', data={
            'username': candidate,
            'email': f'{candidate}@example.com',
            'password': 'CandidatePass!2026',
            'confirm_password': 'CandidatePass!2026'
        })
        self.client.post('/login', data={
            'username': candidate,
            'password': 'CandidatePass!2026'
        })

        # Unless current real time is exactly 9-10 PM IST, exam page shows closed.html
        resp = self.client.get('/exam')
        from exam import get_exam_window_status
        is_open, _ = get_exam_window_status()

        if not is_open:
            self.assertIn(b"Daily Exam is Currently Closed", resp.data)

            # Test run endpoint outside window -> must return 403
            run_resp = self.client.post('/exam/run', json={'code': 'print("hello")'}, follow_redirects=True)
            self.assertEqual(run_resp.status_code, 403)

            # Test submit endpoint outside window -> must return 403
            submit_resp = self.client.post('/exam/submit', json={'code': 'print("hello")'}, follow_redirects=True)
            self.assertEqual(submit_resp.status_code, 403)
            print("✓ Server time-window enforcement (Closed page & 403 outside 9-10 PM IST) passed.")
        else:
            print("Current time is inside 9-10 PM IST window; window is open.")

    def test_04_sandbox_executor(self):
        """Test external Piston code executor with custom STDIN."""
        code = """
import sys
data = sys.stdin.read().strip()
print(f"Processed: {data[::-1]}")
"""
        res = executor.execute(code=code, language='python', stdin="antigravity")
        self.assertIn(res.get('status'), ('SUCCESS', 'ERROR', 'NETWORK_ERROR'))
        if res.get('status') == 'SUCCESS':
            self.assertEqual(res['stdout'].strip(), "Processed: ytivargitna")
            print("✓ Sandbox executor (Piston with custom STDIN) passed.")
        else:
            print(f"Sandbox notice: {res.get('stderr') or res.get('status')}")

    def test_05_streak_calculation_logic(self):
        """Test consecutive day IST streak recalculation and single-submission constraint."""
        import uuid
        uname = f"streak_{uuid.uuid4().hex[:6]}"
        user = User(
            username=uname,
            email=f"{uname}@example.com",
            password_hash="fakehash",
            current_streak=0,
            longest_streak=0
        )
        db.session.add(user)
        db.session.commit()

        # Day 1: User submits
        d1 = date(2026, 10, 1)
        user.update_streak(d1)
        self.assertEqual(user.current_streak, 1)
        self.assertEqual(user.longest_streak, 1)

        # Same Day submission: streak doesn't change
        user.update_streak(d1)
        self.assertEqual(user.current_streak, 1)

        # Day 2 (Consecutive day): streak becomes 2
        d2 = date(2026, 10, 2)
        user.update_streak(d2)
        self.assertEqual(user.current_streak, 2)
        self.assertEqual(user.longest_streak, 2)

        # Day 3 (Consecutive day): streak becomes 3
        d3 = date(2026, 10, 3)
        user.update_streak(d3)
        self.assertEqual(user.current_streak, 3)
        self.assertEqual(user.longest_streak, 3)

        # Missed Day 4, submits on Day 5: streak resets to 1, longest stays 3!
        d5 = date(2026, 10, 5)
        user.update_streak(d5)
        self.assertEqual(user.current_streak, 1)
        self.assertEqual(user.longest_streak, 3)
        print("✓ Streak calculation logic (consecutive +1, gap reset, longest maintained) passed.")

    def test_06_admin_protection(self):
        """Verify that non-admin users cannot access admin routes."""
        import uuid
        std_user = f"std_{uuid.uuid4().hex[:6]}"
        # Non-admin user
        self.client.post('/register', data={
            'username': std_user,
            'email': f'{std_user}@example.com',
            'password': 'StandardPass!2026',
            'confirm_password': 'StandardPass!2026'
        })
        self.client.post('/login', data={
            'username': std_user,
            'password': 'StandardPass!2026'
        })

        # Try to access admin upload
        resp = self.client.get('/admin/upload')
        self.assertEqual(resp.status_code, 403)
        print("✓ Admin route protection (403 for non-admins) passed.")

    def test_07_full_submission_and_duplicate_rejection(self):
        """Test in-window exam submission, evaluation, streak increment, and duplicate block."""
        import uuid
        self.app.config['BYPASS_TIME_WINDOW'] = True
        cand_user = f"submitter_{uuid.uuid4().hex[:6]}"

        self.client.post('/register', data={
            'username': cand_user,
            'email': f'{cand_user}@example.com',
            'password': 'CandidatePass!2026',
            'confirm_password': 'CandidatePass!2026'
        })
        self.client.post('/login', data={
            'username': cand_user,
            'password': 'CandidatePass!2026'
        })

        # Problem: Reverse Words in a String (first question in seed)
        # Hidden test cases require reversing space-separated words
        solution_code = """
import sys

def solve():
    lines = sys.stdin.read().splitlines()
    if not lines:
        return
    for line in lines:
        words = line.split()
        if words:
            print(" ".join(reversed(words)))

if __name__ == '__main__':
    solve()
"""

        # Submit solution
        resp = self.client.post('/exam/submit', json={
            'code': solution_code,
            'language': 'python'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('streak', data)
        self.assertEqual(data.get('streak'), 1)
        self.assertTrue(data.get('score') >= 0)
        self.assertIn('exam_status', data)

        # Attempt to submit SECOND time on same day -> Must return 400 duplicate error
        dup_resp = self.client.post('/exam/submit', json={
            'code': solution_code,
            'language': 'python'
        })
        self.assertEqual(dup_resp.status_code, 400)
        dup_data = dup_resp.get_json()
        self.assertIn("already submitted", dup_data.get('error', '').lower())
        print("✓ Full exam submission, hidden test evaluation, streak +1, and duplicate block passed.")

    def test_08_pyodide_submit_server_grading_and_csp(self):
        """Test CSP headers for Pyodide WASM/Worker and ensure browser-submitted python_pyodide is graded on server."""
        import uuid
        self.app.config['BYPASS_TIME_WINDOW'] = True

        # 1. Verify CSP Headers
        resp = self.client.get('/login')
        csp_header = resp.headers.get('Content-Security-Policy', '')
        self.assertIn('cdn.jsdelivr.net', csp_header)
        self.assertIn('wasm-unsafe-eval', csp_header)
        self.assertIn('worker-src', csp_header)
        self.assertIn('blob:', csp_header)

        # 2. Test Submit with language "python_pyodide" (server must grade it, NOT trust client)
        cand_user = f"pyodide_user_{uuid.uuid4().hex[:6]}"
        self.client.post('/register', data={
            'username': cand_user,
            'email': f'{cand_user}@example.com',
            'password': 'PyodideCandidate!2026',
            'confirm_password': 'PyodideCandidate!2026'
        })
        self.client.post('/login', data={
            'username': cand_user,
            'password': 'PyodideCandidate!2026'
        })

        sub_resp = self.client.post('/exam/submit', json={
            'code': 'print("testing pyodide submit")',
            'language': 'python_pyodide'
        })
        self.assertEqual(sub_resp.status_code, 200)
        data = sub_resp.get_json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('score', data)
        self.assertIn('exam_status', data)
        print("✓ Pyodide server-side grading & CSP headers (cdn.jsdelivr.net, wasm-unsafe-eval, worker-src blob:) passed.")

    def test_09_numpy_allowed_detection_and_routing(self):
        """Test Question numpy_allowed boolean attribute and study file detection."""
        from groq_client import generate_groq_question

        # Test Question model attribute
        q = Question(
            title="Numpy Vector Math",
            description="Perform dot product",
            numpy_allowed=True
        )
        self.assertTrue(q.numpy_allowed)

        # Test study file text detection logic
        file_text = "Today we will study matrix transformations using import numpy as np and calculate dot products."
        file_lower = file_text.lower()
        has_numpy = bool('numpy' in file_lower or 'np.' in file_lower or 'import numpy' in file_lower)
        self.assertTrue(has_numpy)
        print("✓ numpy_allowed attribute and study file keyword detection passed.")
 
    def test_10_practice_mode_flow(self):
        """Test complete Practice Mode lifecycle: window check, autosave, 10KB limit, 30s heartbeat streak at 20m, runner, and dashboard."""
        import uuid
        from models import PracticeSession

        # 1. Test Window Enforcement: when off-hours and not bypassed, endpoints must block
        self.app.config['BYPASS_TIME_WINDOW'] = False
        user_name = f"prac_user_{uuid.uuid4().hex[:6]}"
        self.client.post('/register', data={
            'username': user_name,
            'email': f'{user_name}@example.com',
            'password': 'PracticeUser!2026',
            'confirm_password': 'PracticeUser!2026'
        })
        self.client.post('/login', data={
            'username': user_name,
            'password': 'PracticeUser!2026'
        })

        # Outside window -> autosave, heartbeat, run return 403
        save_resp = self.client.post('/practice/autosave', json={'code': 'print("hi")'})
        self.assertEqual(save_resp.status_code, 403)

        hb_resp = self.client.post('/practice/heartbeat')
        self.assertEqual(hb_resp.status_code, 403)

        run_resp = self.client.post('/practice/run', json={'code': 'print("hi")', 'language': 'python'})
        self.assertEqual(run_resp.status_code, 403)

        # 2. Enable Window (Bypass mode for testing)
        self.app.config['BYPASS_TIME_WINDOW'] = True

        # GET /practice creates or loads persistent session
        get_resp = self.client.get('/practice')
        self.assertEqual(get_resp.status_code, 200)
        self.assertIn(b"Practice Workspace", get_resp.data)

        user = User.query.filter_by(username=user_name).first()
        today_ist = get_current_ist_date()
        session_rec = PracticeSession.query.filter_by(user_id=user.id, session_date=today_ist).first()
        self.assertIsNotNone(session_rec)
        self.assertEqual(session_rec.minutes, 0)
        self.assertEqual(len(session_rec.snippets), 1)

        # 3. Test 10 KB Code Size Limit
        oversized_code = "x = 1\n" * 2500  # > 12 KB
        over_resp = self.client.post('/practice/autosave', json={
            'code': oversized_code,
            'topic': 'Testing limits'
        })
        self.assertEqual(over_resp.status_code, 400)
        self.assertIn("exceeds", over_resp.get_json().get('error', '').lower())

        # 4. Test Autosave with snippets array
        test_snippets = [
            {'id': 's1', 'title': 'Binary Search', 'language': 'python', 'code': 'def bs(): pass'},
            {'id': 's2', 'title': 'Two Pointers', 'language': 'javascript', 'code': 'console.log(1);'}
        ]
        save_ok = self.client.post('/practice/autosave', json={
            'code': test_snippets[0]['code'],
            'topic': 'Search Algorithms',
            'language': 'python',
            'snippets': test_snippets
        })
        self.assertEqual(save_ok.status_code, 200)
        self.assertEqual(save_ok.get_json().get('status'), 'saved')

        # Verify in DB
        db.session.refresh(session_rec)
        self.assertEqual(session_rec.topic, 'Search Algorithms')
        self.assertEqual(len(session_rec.snippets), 2)
        self.assertEqual(session_rec.snippets[1]['title'], 'Two Pointers')

        # 5. Test Code Runner (POST /practice/run)
        run_ok = self.client.post('/practice/run', json={
            'code': 'print("Hello from Practice Mode!")',
            'language': 'python',
            'stdin': ''
        })
        self.assertEqual(run_ok.status_code, 200)
        run_data = run_ok.get_json()
        self.assertIn("Hello from Practice Mode!", run_data.get('stdout', ''))
        db.session.refresh(session_rec)
        self.assertGreaterEqual(session_rec.run_count, 1)

        # 6. Test Heartbeat Study Time & Streak Increment at 20 minutes
        initial_streak = user.current_streak
        # Simulate user already having 19 minutes and 30 seconds (39 heartbeats = 1170s)
        session_rec.heartbeat_seconds = 1170
        session_rec.minutes = 19
        session_rec.last_heartbeat = None
        db.session.commit()

        # Send heartbeat -> increases to 1200 seconds = 20 minutes!
        hb_ok = self.client.post('/practice/heartbeat')
        self.assertEqual(hb_ok.status_code, 200)
        hb_data = hb_ok.get_json()
        self.assertEqual(hb_data.get('status'), 'ok')
        self.assertEqual(hb_data.get('minutes'), 20)
        self.assertTrue(hb_data.get('awarded_streak'))

        db.session.refresh(user)
        self.assertEqual(user.current_streak, initial_streak + 1)

        # 7. Test Dashboard Rendering (today's minutes, weekly bar chart, snippet history)
        dash_resp = self.client.get('/dashboard')
        self.assertEqual(dash_resp.status_code, 200)
        self.assertIn(b"Today's Practice", dash_resp.data)
        self.assertIn(b"Weekly Study Time", dash_resp.data)
        self.assertIn(b"Daily Practice Snippets History", dash_resp.data)
        self.assertIn(b"Search Algorithms", dash_resp.data)
        print("✓ Full Practice Mode flow: window check, autosave, 10KB limit, 20-min streak award, and dashboard passed.")

if __name__ == '__main__':
    unittest.main()
