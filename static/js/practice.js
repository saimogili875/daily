/**
 * Daily Code Exam - Practice Mode Interactive Workspace
 * Multi-Snippet Tabs, 10s Autosave, 30s Study Time Heartbeat,
 * External Sandbox / Pyodide Execution, and Emscripten Virtual File System.
 */

(function () {
    let editor = null;
    let snippets = [];
    let activeSnippetId = null;
    let autosaveTimer = null;
    let heartbeatTimer = null;
    let countdownInterval = null;
    let isDirty = false;

    // Helper: Retrieve CSRF Token from meta tag
    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    // Initialize Monaco Editor and Snippets
    function initPracticeMonaco() {
        const editorContainer = document.getElementById('monaco-editor-container');
        if (!editorContainer) return;

        // Parse initial snippets
        try {
            const rawSnippets = editorContainer.dataset.snippets;
            snippets = rawSnippets ? JSON.parse(rawSnippets) : [];
        } catch (e) {
            snippets = [];
        }

        if (!snippets || snippets.length === 0) {
            const initialCode = editorContainer.dataset.initialCode || "# Practice Mode\nprint('Hello world!')\n";
            snippets = [
                {
                    id: 'snippet_1',
                    title: 'Snippet 1',
                    language: editorContainer.dataset.currentLang || 'python',
                    code: initialCode
                }
            ];
        }

        activeSnippetId = snippets[0].id;

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
            const currentTheme = document.documentElement.getAttribute('data-theme') === 'light' ? 'vs' : 'vs-dark';
            const activeSnippet = getActiveSnippet();

            editor = monaco.editor.create(editorContainer, {
                value: activeSnippet ? activeSnippet.code : "",
                language: getMonacoLanguage(activeSnippet ? activeSnippet.language : 'python'),
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
                padding: { top: 12, bottom: 12 }
            });

            editor.onDidChangeModelContent(() => {
                isDirty = true;
                updateActiveSnippetCode();
                updateCodeSize();
                const indicator = document.getElementById('autosave-indicator');
                if (indicator) indicator.textContent = "● Unsaved changes";
            });

            renderSnippetTabs();
            updateCodeSize();
        });
    }

    function getMonacoLanguage(lang) {
        if (lang === 'cpp') return 'cpp';
        if (lang === 'javascript') return 'javascript';
        if (lang === 'java') return 'java';
        return 'python';
    }

    function getActiveSnippet() {
        return snippets.find(s => s.id === activeSnippetId) || snippets[0];
    }

    function updateActiveSnippetCode() {
        const active = getActiveSnippet();
        if (active && editor) {
            active.code = editor.getValue();
        }
    }

    function updateCodeSize() {
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

    // Render Multi-Snippet Tabs
    function renderSnippetTabs() {
        const bar = document.getElementById('snippet-tabs-bar');
        if (!bar) return;

        bar.innerHTML = '';
        snippets.forEach((s) => {
            const tabBtn = document.createElement('button');
            tabBtn.type = 'button';
            tabBtn.className = `snippet-tab-pill ${s.id === activeSnippetId ? 'active' : ''}`;
            tabBtn.innerHTML = `
                <span>${escapeHtml(s.title)}</span>
                ${snippets.length > 1 ? `<span class="snippet-tab-close" data-id="${s.id}" title="Close snippet">&times;</span>` : ''}
            `;

            tabBtn.addEventListener('click', (e) => {
                if (e.target.classList.contains('snippet-tab-close')) {
                    e.stopPropagation();
                    closeSnippetTab(s.id);
                    return;
                }
                switchSnippetTab(s.id);
            });

            // Double-click to rename snippet
            tabBtn.addEventListener('dblclick', () => {
                const newTitle = prompt("Rename snippet:", s.title);
                if (newTitle && newTitle.trim()) {
                    s.title = newTitle.trim();
                    renderSnippetTabs();
                    triggerAutosave();
                }
            });

            bar.appendChild(tabBtn);
        });

        // "+ New Snippet" button in tab bar
        const addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'btn-new-snippet';
        addBtn.innerHTML = '<span>➕</span>';
        addBtn.title = 'Add new snippet tab';
        addBtn.addEventListener('click', addNewSnippet);
        bar.appendChild(addBtn);
    }

    function switchSnippetTab(targetId) {
        if (targetId === activeSnippetId) return;

        updateActiveSnippetCode();
        activeSnippetId = targetId;
        const newActive = getActiveSnippet();

        if (editor && newActive) {
            editor.setValue(newActive.code || '');
            const lang = newActive.language || 'python';
            monaco.editor.setModelLanguage(editor.getModel(), getMonacoLanguage(lang));

            const langSelect = document.getElementById('select-language');
            if (langSelect) langSelect.value = lang;
        }

        renderSnippetTabs();
        updateCodeSize();
    }

    function addNewSnippet() {
        updateActiveSnippetCode();
        const nextNum = snippets.length + 1;
        const newSnippet = {
            id: `snippet_${Date.now()}`,
            title: `Snippet ${nextNum}`,
            language: document.getElementById('select-language')?.value || 'python',
            code: `# Practice Snippet ${nextNum}\n`
        };

        snippets.push(newSnippet);
        activeSnippetId = newSnippet.id;

        if (editor) {
            editor.setValue(newSnippet.code);
            monaco.editor.setModelLanguage(editor.getModel(), getMonacoLanguage(newSnippet.language));
        }

        renderSnippetTabs();
        updateCodeSize();
        triggerAutosave();
    }

    function closeSnippetTab(snippetId) {
        if (snippets.length <= 1) return;
        if (!confirm("Delete this snippet?")) return;

        updateActiveSnippetCode();
        const idx = snippets.findIndex(s => s.id === snippetId);
        if (idx !== -1) {
            snippets.splice(idx, 1);
            if (activeSnippetId === snippetId) {
                activeSnippetId = snippets[Math.max(0, idx - 1)].id;
            }
        }

        const active = getActiveSnippet();
        if (editor && active) {
            editor.setValue(active.code || '');
            monaco.editor.setModelLanguage(editor.getModel(), getMonacoLanguage(active.language));
        }

        renderSnippetTabs();
        updateCodeSize();
        triggerAutosave();
    }

    // 10-Second Autosave
    function startAutosave() {
        autosaveTimer = setInterval(() => {
            if (isDirty) {
                triggerAutosave();
            }
        }, 10000); // 10 seconds
    }

    function triggerAutosave() {
        updateActiveSnippetCode();
        const active = getActiveSnippet();
        const code = active ? active.code : (editor ? editor.getValue() : '');
        const topic = document.getElementById('practice-topic-input')?.value || 'Daily Practice';
        const language = document.getElementById('select-language')?.value || 'python';
        const indicator = document.getElementById('autosave-indicator');

        if (indicator) indicator.textContent = "Autosaving...";

        fetch('/practice/autosave', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                code: code,
                topic: topic,
                language: language,
                snippets: snippets
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'saved') {
                isDirty = false;
                if (indicator) indicator.textContent = `✓ Saved (${data.updated_at})`;
            }
        })
        .catch(err => {
            if (indicator) indicator.textContent = `Autosave error`;
        });
    }

    // 30-Second Study Time Heartbeat
    function startHeartbeat() {
        heartbeatTimer = setInterval(sendHeartbeat, 30000); // 30 seconds
    }

    function sendHeartbeat() {
        fetch('/practice/heartbeat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                const minDisplay = document.getElementById('practice-minutes-display');
                if (minDisplay) minDisplay.textContent = `${data.minutes}m`;

                if (data.awarded_streak) {
                    alert(`🔥 Fantastic achievement! You reached 20 minutes of study time today and advanced your Daily Streak to ${data.streak} days!`);
                }
            }
        })
        .catch(err => console.warn('Heartbeat error:', err));
    }

    // Live Window Countdown (9-10 PM IST)
    function initCountdown() {
        const timerEl = document.getElementById('exam-countdown');
        if (!timerEl) return;

        let secondsLeft = parseInt(timerEl.dataset.secondsLeft || '0', 10);

        function tick() {
            if (secondsLeft <= 0) {
                clearInterval(countdownInterval);
                timerEl.textContent = "00:00:00 (Closed)";
                if (editor) editor.updateOptions({ readOnly: true });
                alert("Practice Mode window has closed for today! Your work has been autosaved.");
                window.location.reload();
                return;
            }

            const hours = Math.floor(secondsLeft / 3600);
            const minutes = Math.floor((secondsLeft % 3600) / 60);
            const seconds = secondsLeft % 60;

            const pad = (n) => String(n).padStart(2, '0');
            timerEl.textContent = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;

            secondsLeft--;
        }

        tick();
        countdownInterval = setInterval(tick, 1000);
    }

    // Interactive Console Tabs
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

                if (target === 'files' && window.PyodideRunner) {
                    window.PyodideRunner.listFiles().then(renderFilesList);
                }
            });
        });
    }

    function switchConsoleTab(tabName) {
        const btn = document.querySelector(`.console-tab-btn[data-tab="${tabName}"]`);
        if (btn) btn.click();
    }

    // Pyodide Virtual File System Panel in Practice Mode
    function initPyodideFileSystem() {
        if (!window.PyodideRunner) return;

        window.PyodideRunner.onFilesChange = (files) => {
            renderFilesList(files);
        };

        const btnRefresh = document.getElementById('btn-refresh-fs');
        if (btnRefresh) {
            btnRefresh.addEventListener('click', () => {
                window.PyodideRunner.listFiles().then(renderFilesList);
            });
        }

        const btnCreate = document.getElementById('btn-create-fs-file');
        if (btnCreate) {
            btnCreate.addEventListener('click', () => {
                const filename = prompt("Enter virtual filename (e.g. data.txt):");
                if (!filename || !filename.trim()) return;
                const content = prompt("Enter file content (optional):", "");
                window.PyodideRunner.writeFile(filename.trim(), content || '').then(() => {
                    window.PyodideRunner.listFiles().then(renderFilesList);
                });
            });
        }
    }

    function renderFilesList(files) {
        const container = document.getElementById('fs-file-list');
        if (!container) return;

        if (!files || files.length === 0) {
            container.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem; padding:0.5rem 0;">No files in virtual filesystem. Create files with <code>open("data.txt", "w")</code> or via the "+ New File" button.</div>';
            return;
        }

        let html = `
            <table class="custom-table" style="font-size:0.8rem; margin:0;">
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>Size</th>
                        <th style="text-align:right;">Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;

        files.forEach(f => {
            html += `
                <tr>
                    <td><code>${escapeHtml(f.name)}</code></td>
                    <td>${f.size} B</td>
                    <td style="text-align:right;">
                        <button type="button" class="btn btn-secondary btn-sm btn-fs-view" data-filename="${escapeHtml(f.name)}" style="padding:0.2rem 0.5rem; font-size:0.75rem;">View</button>
                        <button type="button" class="btn btn-secondary btn-sm btn-fs-delete" data-filename="${escapeHtml(f.name)}" style="padding:0.2rem 0.5rem; font-size:0.75rem; color:var(--danger);">Delete</button>
                    </td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
        container.innerHTML = html;

        container.querySelectorAll('.btn-fs-view').forEach(b => {
            b.addEventListener('click', function () {
                const fn = this.dataset.filename;
                window.PyodideRunner.readFile(fn).then(content => {
                    alert(`File: ${fn}\n\n${content}`);
                }).catch(err => alert(`Error reading file: ${err.message}`));
            });
        });

        container.querySelectorAll('.btn-fs-delete').forEach(b => {
            b.addEventListener('click', function () {
                const fn = this.dataset.filename;
                if (confirm(`Delete virtual file "${fn}"?`)) {
                    window.PyodideRunner.deleteFile(fn).then(() => {
                        window.PyodideRunner.listFiles().then(renderFilesList);
                    });
                }
            });
        });
    }

    // Code Execution Handler (Run 20/min)
    async function executePracticeCode() {
        if (!editor) return;
        const code = editor.getValue();
        const stdin = document.getElementById('stdin-textarea')?.value || '';
        const language = document.getElementById('select-language')?.value || 'python';
        const terminalOut = document.getElementById('terminal-stdout');
        const statusBadge = document.getElementById('terminal-status-badge');
        const timeBadge = document.getElementById('terminal-time-badge');
        const engineLabel = document.getElementById('terminal-engine-label');
        const runBtn = document.getElementById('btn-run-code');

        if (!code.trim()) {
            alert("Please enter code before running.");
            return;
        }

        if (runBtn) runBtn.disabled = true;
        switchConsoleTab('output');

        // Branch 1: Pyodide In-Browser Execution
        if (language === 'python_pyodide') {
            if (engineLabel) engineLabel.textContent = "Pyodide (Worker)";
            if (terminalOut) terminalOut.textContent = "Executing in Pyodide Web Worker (10s timeout)...";
            if (statusBadge) {
                statusBadge.textContent = "RUNNING";
                statusBadge.className = "badge badge-ai";
            }

            const clearFS = document.getElementById('fs-clear-on-run')?.checked !== false;
            const res = await window.PyodideRunner.run(code, stdin, [], clearFS);
            renderTerminalOutput(res);

            if (runBtn) runBtn.disabled = false;
            return;
        }

        // Branch 2: Server-Side Sandbox (Piston / Judge0, Rate Limited 20/min)
        if (engineLabel) engineLabel.textContent = "Backend Sandbox";
        if (terminalOut) terminalOut.textContent = "Executing in external sandbox...";
        if (statusBadge) {
            statusBadge.textContent = "RUNNING";
            statusBadge.className = "badge badge-ai";
        }

        fetch('/practice/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                code: code,
                language: language,
                stdin: stdin
            })
        })
        .then(res => res.json().then(data => ({ status: res.status, data: data })))
        .then(({ status, data }) => {
            if (status === 429) {
                alert("Rate limit exceeded (maximum 20 runs per minute in Practice Mode). Please wait a moment.");
                return;
            }
            if (status !== 200) {
                throw new Error(data.error || `HTTP ${status}`);
            }

            renderTerminalOutput(data);

            if (data.run_count) {
                const runBadge = document.getElementById('run-count-badge');
                if (runBadge) runBadge.textContent = `Runs: ${data.run_count}`;
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

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Setup Event Listeners
    function initPracticeEventListeners() {
        const runBtn = document.getElementById('btn-run-code');
        const saveBtn = document.getElementById('btn-save-practice');
        const addSnippetBtn = document.getElementById('btn-add-snippet');
        const langSelect = document.getElementById('select-language');
        const topicInput = document.getElementById('practice-topic-input');

        if (runBtn) runBtn.addEventListener('click', executePracticeCode);
        if (saveBtn) saveBtn.addEventListener('click', triggerAutosave);
        if (addSnippetBtn) addSnippetBtn.addEventListener('click', addNewSnippet);

        if (topicInput) {
            topicInput.addEventListener('input', () => { isDirty = true; });
        }

        if (langSelect) {
            langSelect.addEventListener('change', function () {
                const lang = this.value;
                const active = getActiveSnippet();
                if (active) active.language = lang;
                isDirty = true;

                const pyBadge = document.getElementById('pyodide-engine-badge');
                if (lang === 'python_pyodide') {
                    if (pyBadge) pyBadge.style.display = 'inline-block';
                    if (window.PyodideRunner) window.PyodideRunner.init();
                    monaco.editor.setModelLanguage(editor.getModel(), 'python');
                } else {
                    if (pyBadge) pyBadge.style.display = 'none';
                    monaco.editor.setModelLanguage(editor.getModel(), getMonacoLanguage(lang));
                }
            });
        }
    }

    // Global Theme synchronization
    window.updateMonacoTheme = function (theme) {
        if (editor && window.monaco) {
            monaco.editor.setTheme(theme === 'light' ? 'vs' : 'vs-dark');
        }
    };

    // DOM Ready
    document.addEventListener('DOMContentLoaded', function () {
        initPracticeMonaco();
        initPracticeEventListeners();
        initConsoleTabs();
        initPyodideFileSystem();
        initCountdown();
        startAutosave();
        startHeartbeat();
    });
})();
