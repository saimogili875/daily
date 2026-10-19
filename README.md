# ⚡ Daily Code Exam

A production-ready, highly secure Flask web platform for daily timed algorithmic coding exams (strictly 9:00 PM to 10:00 PM IST) with integrated Python online compiler, Groq LLaMA-3.3 AI question setter, sandboxed code execution, and candidate streak tracking.

---

## 🌟 Key Features

- **Strict Server-Enforced Time Window**:
  - Exam access and run/submit operations open **strictly from 9:00 PM to 10:00 PM IST (Asia/Kolkata)**.
  - Server time is calculated using `pytz` (never trusts client system clocks).
  - Outside the window, a live countdown ticks down to the next 9:00 PM IST, and `/exam/run` + `/exam/submit` endpoints reject requests with HTTP 403.
- **🧪 Daily Practice Mode (9:00 PM - 10:00 PM IST)**:
  - **Strict Server Time Window**: Open only during the 9:00 - 10:00 PM IST window (enforced on workspace, autosave, heartbeat, and code run).
  - **Persistent Daily Editor**: One persistent session per day with Monaco editor, "What I learned today" topic header, and custom STDIN box.
  - **Multi-Language Support**: Python 3 (Sandbox), Python (Browser, numpy via Pyodide WebWorker), JavaScript (Node.js), C++ (GCC), and Java (OpenJDK).
  - **Multi-Snippet Tabs**: "New Snippet" button adds and switches between multiple snippet tabs within the same day's session.
  - **10-Second Autosave**: Automatically persists code, tabs array, language, and topic every 10 seconds.
  - **Study Time Heartbeat & Streak Qualification**:
    - Timer starts upon entering the workspace.
    - Dispatches a heartbeat every 30 seconds (flooding protected, only counts minutes inside the 9-10 PM window).
    - **Earning Streak**: Practicing for at least 20 minutes (`minutes >= 20`) automatically awards a daily streak (+1)!
  - **Rate Limits & Size Controls**: 20 code runs per minute per user, 10 KB code limit, and full CSRF verification.
  - **Dashboard Analytics & Re-Run**:
    - Displays today's study minutes, total study hours, and a 7-day weekly bar chart with 20-minute goal threshold.
    - Snippet history table with detailed code viewer, multi-snippet inspection, copy button, and a live re-run terminal.
- **Embedded Python Online Compiler & Pyodide WebWorker**:
  - Monaco Editor (VS Code core) loaded via CDN with dark mode syntax highlighting, auto-indentation, and line numbers.
  - Interactive online compiler console supporting **Custom STDIN**, real-time STDOUT/STDERR stream output, exit code, and execution runtime in milliseconds.
  - Instant **Sample Test Case Runner** testing against visible problem cases.
  - **"Python (Browser, numpy)" Option**:
    - Powered by Pyodide (v0.26.4 WASM) running in an isolated background **Web Worker** so the browser UI never freezes.
    - Pre-bundles and lazy-loads **NumPy** (with auto-import for Pandas and Matplotlib).
    - **In-Browser Virtual File System (FS)**: Code can write, read, and manipulate files with standard `open('data.txt', 'w')`. Exam workspace includes an interactive File System panel to list, view, create, and delete files.
    - **Worker Guardrails**: Strict 10-second timeout automatically terminates and restarts hanging or infinite loops, and stdout/stderr output is safely capped at 50 KB.
    - **Untrusted Browser Grading**: Browser execution is strictly for candidate testing and running. On **Submit**, the code is evaluated entirely on the secure server-side sandbox against hidden test cases. If a question is flagged with `numpy_allowed`, execution routes to the dedicated numpy executor.
- **Groq AI Question Setter & Evaluator**:
  - Generates original algorithmic coding problems based on study files uploaded by the administrator (.py, .txt, .pdf, .docx).
  - Automatically flags questions with `numpy_allowed = True` when study material covers arrays, matrices, or numerical computing.
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
├── models.py                  # SQLAlchemy ORM (User, Question, Submission, PracticeSession, LoginAttempt, Upload)
├── auth.py                    # Secure authentication, lockout, single-session logic
├── exam.py                    # Exam page, online compiler run, submit, time-window logic
├── practice.py                # Practice mode (9-10 PM window, autosave, 30s heartbeat, multi-language runner)
├── dashboard.py               # Heatmap generation, weekly practice bar chart, streak tracker, leaderboard
├── executor.py                # External sandbox execution client (Piston / Judge0)
├── groq_client.py             # Groq AI question generator, text extractor, and evaluator
├── seed.py                    # Database seeding (30 algorithmic Python questions + admin)
├── templates/
│   ├── base.html              # Core layout, theme switcher, CSRF meta
│   ├── login.html             # Secure login form
│   ├── register.html          # Registration with password complexity validator
│   ├── change_password.html   # Password change form
│   ├── exam.html              # Monaco editor + Python online compiler workspace
│   ├── practice.html          # Practice mode workspace (multi-tab snippets, STDIN, Pyodide FS)
│   ├── dashboard.html         # Activity heatmap, weekly practice chart, snippet history, leaderboard
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
│       ├── exam.js            # Monaco setup, online compiler console, countdown
│       ├── practice.js        # Practice mode tabs, 10s autosave, 30s heartbeat timer, code runner
│       └── pyodide_runner.js  # Background WebWorker running Pyodide with virtual file system
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

## 🐍 Python (Browser, NumPy) via Pyodide & File System Support

Candidates can select **"Python (Browser, numpy)"** from the language dropdown:
1. **Isolated Web Worker**: Pyodide runs in a background thread using WebAssembly (`wasm-unsafe-eval` CSP enabled). The browser UI and Monaco editor remain completely fluid.
2. **NumPy & Data Libraries**: NumPy is bundled and lazy-loaded via `loadPackage('numpy')`. If user code imports `pandas` or `matplotlib`, the worker dynamically loads them.
3. **In-Browser File System (FS)**: Emscripten's virtual FS operates at `/home/pyodide`. Candidates can create, read, and write files directly in Python (`open("data.txt", "w")`). The exam UI includes an interactive **File System panel** to inspect, create, view, and delete virtual files.
4. **Safety Guardrails**: A strict 10-second timer terminates and restarts hanging workers, and output is capped at 50 KB.
5. **Zero Trust in Client Grading**: The browser is never trusted for official grading. On Submit, code is posted to `/exam/submit` where hidden test cases run on the backend sandbox (configured via `EXECUTOR_URL` / `EXECUTOR_NUMPY_URL`).

---

## 🧪 Testing Verification

You can run automated or interactive validation:
```bash
./venv/bin/python3 test_suite.py
```
Validates:
- **Lockout Mechanism**: 5 failed login attempts trigger 15-minute lock with generic "Invalid credentials."
- **Time Window**: Server-side 9:00 PM – 10:00 PM IST enforcement (closed countdown clock & 403 on run/submit).
- **Sandbox Execution**: Piston / Judge0 execution with custom STDIN.
- **Pyodide & CSP Compliance**: Verifies Content-Security-Policy headers allow `cdn.jsdelivr.net`, `'wasm-unsafe-eval'`, and `worker-src blob:`.
- **Untrusted Browser Grading**: Verifies submissions under `python_pyodide` are securely graded on the backend sandbox.
- **NumPy Question Routing**: Verifies `numpy_allowed` flag and study file keyword detection.
- **Streak Calculation**: Increments on consecutive IST dates and resets on gaps.

