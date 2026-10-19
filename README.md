# ⚡ Daily Code Exam

A production-ready, highly secure Flask web platform for daily timed algorithmic coding exams (strictly 9:00 PM to 10:00 PM IST) with integrated Python online compiler, Groq LLaMA-3.3 AI question setter, sandboxed code execution, and candidate streak tracking.

---

## 🌟 Key Features

- **Strict Server-Enforced Time Window**:
  - Exam access and run/submit operations open **strictly from 9:00 PM to 10:00 PM IST (Asia/Kolkata)**.
  - Server time is calculated using `pytz` (never trusts client system clocks).
  - Outside the window, a live countdown ticks down to the next 9:00 PM IST, and `/exam/run` + `/exam/submit` endpoints reject requests with HTTP 403.
- **Embedded Python Online Compiler**:
  - Monaco Editor (VS Code core) loaded via CDN with dark mode syntax highlighting, auto-indentation, and line numbers.
  - Interactive online compiler console supporting **Custom STDIN**, real-time STDOUT/STDERR stream output, exit code, and execution runtime in milliseconds.
  - Instant **Sample Test Case Runner** testing against visible problem cases.
- **Groq AI Question Setter & Evaluator**:
  - Generates original algorithmic coding problems based on study files uploaded by the administrator (.py, .txt, .pdf, .docx).
  - Uses `llama-3.3-70b-versatile` via Groq's API.
  - Daily automatic generation scheduled at **8:55 PM IST** via `APScheduler`, with manual on-demand generation in the Admin portal.
  - Generates 2 visible sample cases and 5 hidden test cases with strict JSON structure.
  - Evaluates code submissions and returns constructive 2-3 sentence AI feedback and scoring.
  - High-availability fallback to 30 seeded Python questions if no study material exists or if Groq is unavailable.
- **Hardened Security & Authentication**:
  - **Single Active Session**: New logins immediately invalidate previous sessions on other devices or tabs via unique UUID session tokens.
  - **Account Lockout**: 5 failed login attempts locks the username/IP for 15 minutes. Generic error message prevents user enumeration.
  - **Granular Rate Limiting** with `Flask-Limiter`:
    - Login: 5 attempts/min per IP
    - Register: 3 accounts/hour per IP
    - Run Code: 10/min per user
    - Submit Exam: 5/min per user
    - Global: 200 requests/day
  - **Strict Password Rules**: Minimum 10 characters with uppercase, lowercase, digit, and symbol; common passwords automatically blacklisted.
  - **Pass-hash with Bcrypt**: No plain text storage.
  - **CSRF Protection**: Form and AJAX `X-CSRFToken` verification with `Flask-WTF`.
  - **Security Headers via Talisman**: Content Security Policy (CSP), HSTS, X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy.
  - **Sandboxed Execution**: External code runner (Piston / Judge0). **Zero** local `eval`/`exec`/`subprocess` execution.
  - **Security Auditing**: Security events (failed logins, lockouts, illegal window submissions) logged to `security.log`.

---

## 📁 File Structure

```
daily-code-exam/
├── app.py                     # Application factory, extensions, scheduler, rate limits
├── config.py                  # Environment-driven configuration and CSP
├── models.py                  # SQLAlchemy ORM (User, Question, Submission, LoginAttempt, Upload)
├── auth.py                    # Secure authentication, lockout, single-session logic
├── exam.py                    # Exam page, online compiler run, submit, time-window logic
├── dashboard.py               # Heatmap generation, streak tracker, leaderboard
├── executor.py                # External sandbox execution client (Piston / Judge0)
├── groq_client.py             # Groq AI question generator, text extractor, and evaluator
├── seed.py                    # Database seeding (30 algorithmic Python questions + admin)
├── templates/
│   ├── base.html              # Core layout, theme switcher, CSRF meta
│   ├── login.html             # Secure login form
│   ├── register.html          # Registration with password complexity validator
│   ├── change_password.html   # Password change form
│   ├── exam.html              # Monaco editor + Python online compiler workspace
│   ├── dashboard.html         # Activity heatmap, streak metrics, history, leaderboard
│   ├── closed.html            # Off-hours countdown clock to 9:00 PM IST
│   ├── admin_upload.html      # Study material upload and Groq trigger
│   ├── admin_submissions.html # Global submissions inspector
│   ├── 403.html               # Custom 403 Forbidden
│   ├── 404.html               # Custom 404 Not Found
│   ├── 429.html               # Custom 429 Rate Limit Exceeded
│   └── 500.html               # Custom 500 Internal Error (no stack traces)
├── static/
│   ├── css/
│   │   └── style.css          # Responsive dark/light design system
│   └── js/
│       └── exam.js            # Monaco setup, online compiler console, countdown
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── Procfile                   # Gunicorn entry for Render/Heroku
└── README.md                  # Documentation and deployment guide
```

---

## 🚀 Local Installation & Setup

### 1. Clone & Enter Project Directory
```bash
cd /Users/saikumar/.gemini/antigravity-ide/scratch/daily-code-exam
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` to configure your settings:
```ini
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=replace_with_a_long_random_hex_string

# SQLite locally, PostgreSQL in production
DATABASE_URL=sqlite:///daily_code_exam.db

# Sandbox Executor (Piston requires no API key!)
EXECUTOR=piston
EXECUTOR_URL=https://emkc.org/api/v2/piston/execute
EXECUTOR_API_KEY=

# Groq AI Question Generation (Optional for AI generation; defaults to seed questions if empty)
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# Set to true during local development to test the Exam interface outside 9-10 PM IST
BYPASS_TIME_WINDOW=false

# Session Cookie Security (Keep false for local HTTP, true on HTTPS in production)
SESSION_COOKIE_SECURE=false

# Default Admin Credentials
INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@dailycodeexam.com
INITIAL_ADMIN_PASSWORD=AdminSecurePass!2026#
```

### 5. Seed the Database
Seed the 30 algorithmic questions and the initial administrator account:
```bash
flask seed
```

### 6. Run the Application Locally
```bash
flask run --host=0.0.0.0 --port=5000
```
Open your browser at `http://127.0.0.1:5000`.

---

## 🛡️ Admin Setup & Groq Question Generation

1. Log in with the default admin credentials:
   - **Username**: `admin`
   - **Password**: `AdminSecurePass!2026#`
2. Navigate to **AI Question Upload** (`/admin/upload`).
3. Upload any study file (`.py`, `.txt`, `.pdf`, `.docx` up to 2 MB).
4. Click **"⚡ Generate Question Now"** to test Groq AI generation on demand, or let the background `APScheduler` trigger it automatically every evening at **8:55 PM IST**.
5. Check all candidate submissions in the platform under **Submissions** (`/admin/submissions`).

---

## 🌐 Production Deployment on Render

### Step 1: Push Code to GitHub / GitLab
Initialize a Git repository and commit the codebase:
```bash
git init
git add .
git commit -m "Initial commit of Daily Code Exam"
git branch -M main
git remote add origin <your-git-remote-url>
git push -u origin main
```

### Step 2: Create a PostgreSQL Database on Render
1. Log in to [Render.com](https://render.com).
2. Click **New +** -> **PostgreSQL**.
3. Name your database (e.g. `daily-code-exam-db`).
4. Copy the **Internal Database URL** (or External URL).

### Step 3: Create a Web Service on Render
1. Click **New +** -> **Web Service**.
2. Connect your Git repository.
3. Configure the service:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && flask seed`
   - **Start Command**: `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
4. In the **Environment Variables** section, add:
   - `SECRET_KEY`: `<Generate a 64-char random hex key>`
   - `DATABASE_URL`: `<Paste your Render PostgreSQL connection string>`
   - `FLASK_ENV`: `production`
   - `SESSION_COOKIE_SECURE`: `true`
   - `EXECUTOR`: `piston`
   - `EXECUTOR_URL`: `https://emkc.org/api/v2/piston/execute`
   - `GROQ_API_KEY`: `<Your Groq API Key>`
   - `GROQ_MODEL`: `llama-3.3-70b-versatile`
   - `BYPASS_TIME_WINDOW`: `false`
5. Click **Deploy Web Service**.

Render will automatically provision the container, apply migrations, seed the 30 questions, and launch the Gunicorn application server behind HTTPS.

---

## 🧪 Testing Verification

You can run automated or interactive validation of:
- **Lockout Mechanism**: Make 5 incorrect password attempts with a username; observe that the account enters lockout for 15 minutes with a generic "Invalid credentials." message.
- **Time Window**: Set `BYPASS_TIME_WINDOW=false` (default). Outside 9:00 PM to 10:00 PM IST, the exam page redirects to `closed.html` with a live ticking countdown, and direct POST calls to `/exam/run` or `/exam/submit` respond with HTTP 403.
- **Online Compiler & Sandboxing**: In the exam workspace, write Python code, enter custom input into the STDIN tab, and hit "Run Code" to observe external sandbox execution results in the terminal pane.
- **Streak Calculation**: Submit a solution within the window to verify that the IST-based streak increments safely and reflects on the candidate's dashboard and activity heatmap.
