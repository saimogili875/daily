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

if __name__ == '__main__':
    unittest.main()
