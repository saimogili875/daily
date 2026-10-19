/**
 * Daily Code Exam - Online Compiler & Exam Interface
 * Monaco Editor Integration, Interactive Sandbox Execution, Live Countdown Timer, and CSRF Protection
 */

(function () {
    let editor = null;
    let countdownInterval = null;

    // Helper: Retrieve CSRF Token from meta tag
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // Initialize Monaco Editor
    function initMonaco() {
        const editorContainer = document.getElementById('monaco-editor-container');
        if (!editorContainer) return;

        // Configure AMD loader for Monaco
        require.config({
            paths: {
                vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs'
            }
        });

        window.MonacoEnvironment = {
            getWorkerUrl: function (workerId, label) {
                return `data:text/javascript;charset=utf-8,${encodeURIComponent(`
                    self.MonacoEnvironment = {
                        baseUrl: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/'
                    };
                    importScripts('https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/base/worker/workerMain.js');`
                )}`;
            }
        };

        require(['vs/editor/editor.main'], function () {
            const initialCode = editorContainer.dataset.initialCode || 
`# Python 3 Solution
import sys

def solve():
    # Read input from standard input
    # lines = sys.stdin.read().split()
    pass

if __name__ == '__main__':
    solve()
`;

            const currentTheme = document.documentElement.getAttribute('data-theme') === 'light' ? 'vs' : 'vs-dark';

            editor = monaco.editor.create(editorContainer, {
                value: initialCode,
                language: 'python',
                theme: currentTheme,
                automaticLayout: true,
                fontSize: 14,
                fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, monospace",
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                tabSize: 4,
                insertSpaces: true,
                lineNumbers: 'on',
                renderWhitespace: 'selection',
                folding: true,
                padding: { top: 12, bottom: 12 }
            });

            // Update code size counter on content change
            editor.onDidChangeModelContent(updateCodeStats);
            updateCodeStats();
        });
    }

    // Code size counter
    function updateCodeStats() {
        if (!editor) return;
        const code = editor.getValue();
        const bytes = new Blob([code]).size;
        const sizeBadge = document.getElementById('code-size-counter');
        if (sizeBadge) {
            sizeBadge.textContent = `${(bytes / 1024).toFixed(1)} KB / 10 KB`;
            if (bytes > 10 * 1024) {
                sizeBadge.classList.add('text-danger');
            } else {
                sizeBadge.classList.remove('text-danger');
            }
        }
    }

    // Setup Live Countdown Timer
    function initCountdown() {
        const timerEl = document.getElementById('exam-countdown');
        if (!timerEl) return;

        let secondsLeft = parseInt(timerEl.dataset.secondsLeft || '0', 10);

        function tick() {
            if (secondsLeft <= 0) {
                clearInterval(countdownInterval);
                timerEl.textContent = "00:00:00 (Time Expired)";
                timerEl.classList.add('warning');
                if (editor) editor.updateOptions({ readOnly: true });
                alert("The exam window has closed! Submissions are no longer accepted.");
                window.location.reload();
                return;
            }

            const hours = Math.floor(secondsLeft / 3600);
            const minutes = Math.floor((secondsLeft % 3600) / 60);
            const seconds = secondsLeft % 60;

            const pad = (n) => String(n).padStart(2, '0');
            timerEl.textContent = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;

            if (secondsLeft <= 300) {
                timerEl.parentElement.classList.add('warning');
            }

            secondsLeft--;
        }

        tick();
        countdownInterval = setInterval(tick, 1000);
    }

    // Setup Interactive Console Tabs
    function initConsoleTabs() {
        const tabBtns = document.querySelectorAll('.console-tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                const target = this.dataset.tab;
                tabBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                document.querySelectorAll('.console-tab-pane').forEach(p => p.style.display = 'none');
                const activePane = document.getElementById(`tab-${target}`);
                if (activePane) activePane.style.display = 'block';
            });
        });
    }

    // Switch to a specific console tab programmatically
    function switchConsoleTab(tabName) {
        const btn = document.querySelector(`.console-tab-btn[data-tab="${tabName}"]`);
        if (btn) btn.click();
    }

    // Setup Actions: Run Code, Run Samples, Submit
    function initActionButtons() {
        const runBtn = document.getElementById('btn-run-code');
        const runSamplesBtn = document.getElementById('btn-run-samples');
        const submitBtn = document.getElementById('btn-submit-exam');
        const resetBtn = document.getElementById('btn-reset-code');
        const langSelect = document.getElementById('select-language');

        if (langSelect && editor) {
            langSelect.addEventListener('change', function () {
                const lang = this.value;
                monaco.editor.setModelLanguage(editor.getModel(), lang === 'cpp' ? 'cpp' : lang);
            });
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', function () {
                if (confirm("Reset editor to initial template? Any unsaved code will be lost.")) {
                    const defaultCode = document.getElementById('monaco-editor-container').dataset.initialCode || "";
                    if (editor) editor.setValue(defaultCode);
                }
            });
        }

        if (runBtn) {
            runBtn.addEventListener('click', () => executeCode(false));
        }

        if (runSamplesBtn) {
            runSamplesBtn.addEventListener('click', () => executeCode(true));
        }

        if (submitBtn) {
            submitBtn.addEventListener('click', handleSubmitExam);
        }
    }

    // Interactive Code Execution via Sandbox
    function executeCode(runSamples = false) {
        if (!editor) return;
        const code = editor.getValue();
        const stdin = document.getElementById('stdin-textarea')?.value || '';
        const language = document.getElementById('select-language')?.value || 'python';
        const terminalOut = document.getElementById('terminal-stdout');
        const statusBadge = document.getElementById('terminal-status-badge');
        const timeBadge = document.getElementById('terminal-time-badge');
        const runBtn = document.getElementById('btn-run-code');
        const sampleBtn = document.getElementById('btn-run-samples');

        if (!code.trim()) {
            alert("Please enter code before running.");
            return;
        }

        // UI state: loading
        if (runBtn) runBtn.disabled = true;
        if (sampleBtn) sampleBtn.disabled = true;

        if (runSamples) {
            switchConsoleTab('samples');
            const samplesContainer = document.getElementById('samples-output-container');
            if (samplesContainer) samplesContainer.innerHTML = '<div class="text-muted p-2">Running sample test cases in external sandbox...</div>';
        } else {
            switchConsoleTab('output');
            if (terminalOut) terminalOut.textContent = "Executing in secure sandbox...";
            if (statusBadge) {
                statusBadge.textContent = "RUNNING";
                statusBadge.className = "badge badge-ai";
            }
        }

        fetch('/exam/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                code: code,
                language: language,
                stdin: stdin,
                run_samples: runSamples
            })
        })
        .then(res => res.json().then(data => ({ status: res.status, data: data })))
        .then(({ status, data }) => {
            if (status === 403) {
                alert(data.error || "Exam window closed.");
                window.location.reload();
                return;
            }
            if (status !== 200) {
                throw new Error(data.error || `HTTP ${status}`);
            }

            if (runSamples) {
                renderSampleResults(data);
            } else {
                renderTerminalOutput(data);
            }
        })
        .catch(err => {
            if (terminalOut) terminalOut.textContent = `Execution Error: ${err.message}`;
            if (statusBadge) {
                statusBadge.textContent = "FAILED";
                statusBadge.className = "badge badge-hard";
            }
        })
        .finally(() => {
            if (runBtn) runBtn.disabled = false;
            if (sampleBtn) sampleBtn.disabled = false;
        });
    }

    function renderTerminalOutput(res) {
        const terminalOut = document.getElementById('terminal-stdout');
        const statusBadge = document.getElementById('terminal-status-badge');
        const timeBadge = document.getElementById('terminal-time-badge');

        let display = '';
        if (res.stdout) display += res.stdout;
        if (res.stderr) {
            if (display) display += '\n--- STDERR ---\n';
            display += res.stderr;
        }
        if (!display) display = '[No output returned]';

        if (terminalOut) terminalOut.textContent = display;
        if (timeBadge) timeBadge.textContent = `${res.time_ms || 0} ms`;

        if (statusBadge) {
            if (res.status === 'SUCCESS' && res.exit_code === 0 && !res.stderr) {
                statusBadge.textContent = `EXIT 0 (OK)`;
                statusBadge.className = 'badge badge-easy';
            } else if (res.status === 'TIMEOUT') {
                statusBadge.textContent = 'TIMEOUT';
                statusBadge.className = 'badge badge-hard';
            } else {
                statusBadge.textContent = `EXIT ${res.exit_code}`;
                statusBadge.className = 'badge badge-medium';
            }
        }
    }

    function renderSampleResults(data) {
        const container = document.getElementById('samples-output-container');
        if (!container) return;

        let html = `<div style="margin-bottom: 0.75rem; font-weight: 600;">${data.summary}</div>`;
        data.results.forEach((r, i) => {
            const isPass = r.passed;
            const badgeClass = isPass ? 'badge-easy' : 'badge-hard';
            const statusLabel = isPass ? 'PASSED' : 'FAILED';

            html += `
                <div class="sample-box" style="margin-top: 0.5rem; border-left: 3px solid ${isPass ? 'var(--success)' : 'var(--danger)'};">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 0.4rem;">
                        <strong>Sample Case #${r.test_index}</strong>
                        <span class="badge ${badgeClass}">${statusLabel} (${r.time_ms} ms)</span>
                    </div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.25rem;">Input: <code>${escapeHtml(r.input)}</code></div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.25rem;">Expected: <code>${escapeHtml(r.expected)}</code></div>
                    <div style="font-size: 0.8rem; color: ${isPass ? 'var(--success)' : 'var(--danger)'};">Output: <code>${escapeHtml(r.actual)}</code></div>
                    ${r.stderr ? `<div style="color:var(--danger); font-size:0.75rem; margin-top:0.25rem;">${escapeHtml(r.stderr)}</div>` : ''}
                </div>
            `;
        });
        container.innerHTML = html;
    }

    // Daily Exam Final Submission
    function handleSubmitExam() {
        if (!editor) return;
        const code = editor.getValue().trim();
        const language = document.getElementById('select-language')?.value || 'python';
        const submitBtn = document.getElementById('btn-submit-exam');

        if (!code) {
            alert("Cannot submit an empty solution.");
            return;
        }

        const confirmMsg = "Are you sure you want to SUBMIT? You can only submit ONCE per day! All 5 hidden test cases will be evaluated and your streak will update.";
        if (!confirm(confirmMsg)) return;

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> Evaluating...';
        }

        fetch('/exam/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                code: code,
                language: language
            })
        })
        .then(res => res.json().then(data => ({ status: res.status, data: data })))
        .then(({ status, data }) => {
            if (status !== 200) {
                alert(data.error || "Submission error occurred.");
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Submit Exam";
                }
                return;
            }

            // Display submission result in modal
            showSubmissionResultModal(data);
        })
        .catch(err => {
            alert(`Submission failed: ${err.message}`);
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = "Submit Exam";
            }
        });
    }

    function showSubmissionResultModal(data) {
        const modal = document.getElementById('submission-result-modal');
        if (!modal) {
            window.location.href = data.redirect_url || '/dashboard';
            return;
        }

        const isAccepted = data.exam_status === 'Accepted';
        document.getElementById('modal-status-badge').textContent = data.exam_status;
        document.getElementById('modal-status-badge').className = `badge ${isAccepted ? 'badge-easy' : 'badge-hard'}`;
        document.getElementById('modal-score-val').textContent = `${data.score}%`;
        document.getElementById('modal-tests-val').textContent = `${data.passed}/${data.total} Passed`;
        document.getElementById('modal-streak-val').textContent = `${data.streak} Days 🔥`;
        document.getElementById('modal-ai-feedback').textContent = data.ai_feedback || "No feedback generated.";

        modal.classList.add('active');
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Global Theme synchronization with Monaco
    window.updateMonacoTheme = function (theme) {
        if (editor && window.monaco) {
            monaco.editor.setTheme(theme === 'light' ? 'vs' : 'vs-dark');
        }
    };

    // DOM Ready
    document.addEventListener('DOMContentLoaded', function () {
        initMonaco();
        initCountdown();
        initConsoleTabs();
        initActionButtons();
    });
})();
