/**
 * Pyodide In-Browser Python & NumPy Web Worker Runner
 * Loads Pyodide 0.26.4 in a dedicated Web Worker to ensure UI remains responsive,
 * provides custom STDIN support, in-browser Emscripten FS file management,
 * 10-second execution timeout with auto-restart, and 50 KB output limits.
 */

(function () {
    const PYODIDE_CDN_BASE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
    const MAX_OUTPUT_BYTES = 50 * 1024; // 50 KB output limit

    // Inline worker script source
    const workerScript = `
        importScripts("${PYODIDE_CDN_BASE}pyodide.js");

        let pyodide = null;
        let isReady = false;
        let loadedPackages = new Set();

        async function initPyodide() {
            try {
                self.postMessage({ type: 'status', message: 'Loading Pyodide runtime (WASM)...' });
                pyodide = await loadPyodide({
                    indexURL: "${PYODIDE_CDN_BASE}"
                });

                self.postMessage({ type: 'status', message: 'Loading NumPy package...' });
                await pyodide.loadPackage('numpy');
                loadedPackages.add('numpy');

                // Ensure /home/pyodide exists and is active working directory
                try {
                    pyodide.FS.mkdir('/home/pyodide');
                } catch(e) {}
                try {
                    pyodide.FS.chdir('/home/pyodide');
                } catch(e) {}

                isReady = true;
                self.postMessage({ type: 'ready', message: 'Pyodide + NumPy ready' });
            } catch (err) {
                self.postMessage({ type: 'init_error', error: err.toString() });
            }
        }

        function cleanFS() {
            if (!pyodide) return;
            try {
                const entries = pyodide.FS.readdir('/home/pyodide');
                for (const name of entries) {
                    if (name !== '.' && name !== '..') {
                        try {
                            const stat = pyodide.FS.stat('/home/pyodide/' + name);
                            if (!pyodide.FS.isDir(stat.mode)) {
                                pyodide.FS.unlink('/home/pyodide/' + name);
                            }
                        } catch(e) {}
                    }
                }
            } catch (e) {}
        }

        function getFSFiles() {
            if (!pyodide) return [];
            try {
                const entries = pyodide.FS.readdir('/home/pyodide');
                const files = [];
                for (const name of entries) {
                    if (name !== '.' && name !== '..') {
                        try {
                            const stat = pyodide.FS.stat('/home/pyodide/' + name);
                            if (!pyodide.FS.isDir(stat.mode)) {
                                files.push({
                                    name: name,
                                    size: stat.size
                                });
                            }
                        } catch(e) {}
                    }
                }
                return files;
            } catch(e) {
                return [];
            }
        }

        self.onmessage = async function (e) {
            const data = e.data;

            if (data.action === 'init') {
                if (!pyodide) await initPyodide();
                return;
            }

            if (!isReady) {
                self.postMessage({ type: 'error', error: 'Pyodide is not yet initialized.' });
                return;
            }

            if (data.action === 'list_files') {
                self.postMessage({ type: 'files_list', files: getFSFiles() });
                return;
            }

            if (data.action === 'read_file') {
                try {
                    const content = pyodide.FS.readFile('/home/pyodide/' + data.filename, { encoding: 'utf8' });
                    self.postMessage({ type: 'file_content', filename: data.filename, content: content });
                } catch(err) {
                    self.postMessage({ type: 'file_error', error: err.toString() });
                }
                return;
            }

            if (data.action === 'write_file') {
                try {
                    pyodide.FS.writeFile('/home/pyodide/' + data.filename, data.content || '', { encoding: 'utf8' });
                    self.postMessage({ type: 'file_written', filename: data.filename, files: getFSFiles() });
                } catch(err) {
                    self.postMessage({ type: 'file_error', error: err.toString() });
                }
                return;
            }

            if (data.action === 'delete_file') {
                try {
                    pyodide.FS.unlink('/home/pyodide/' + data.filename);
                    self.postMessage({ type: 'file_deleted', filename: data.filename, files: getFSFiles() });
                } catch(err) {
                    self.postMessage({ type: 'file_error', error: err.toString() });
                }
                return;
            }

            if (data.action === 'run') {
                const code = data.code || '';
                const stdin = data.stdin || '';
                const clearFS = data.clearFS !== false;

                if (clearFS) {
                    cleanFS();
                }

                // If code requests pandas or matplotlib, auto lazy-load them
                if (code.includes('pandas') && !loadedPackages.has('pandas')) {
                    self.postMessage({ type: 'status', message: 'Loading Pandas package...' });
                    await pyodide.loadPackage('pandas');
                    loadedPackages.add('pandas');
                }
                if (code.includes('matplotlib') && !loadedPackages.has('matplotlib')) {
                    self.postMessage({ type: 'status', message: 'Loading Matplotlib package...' });
                    await pyodide.loadPackage('matplotlib');
                    loadedPackages.add('matplotlib');
                }

                // Prepopulate files if provided
                if (data.files && Array.isArray(data.files)) {
                    data.files.forEach(f => {
                        try {
                            pyodide.FS.writeFile('/home/pyodide/' + f.name, f.content || '', { encoding: 'utf8' });
                        } catch(e) {}
                    });
                }

                const startTime = performance.now();

                // Setup Python execution environment with stdin, stdout, stderr capture
                const pythonHarness = \`
import sys
import io

class CappedStringIO(io.StringIO):
    def __init__(self, max_bytes=51200):
        super().__init__()
        self.max_bytes = max_bytes
        self.bytes_written = 0
        self.truncated = False

    def write(self, s):
        if self.truncated:
            return
        b_len = len(s.encode('utf-8'))
        if self.bytes_written + b_len > self.max_bytes:
            allowed = self.max_bytes - self.bytes_written
            super().write(s[:allowed])
            super().write("\\n[Output truncated at 50 KB limit]\\n")
            self.truncated = True
        else:
            self.bytes_written += b_len
            super().write(s)

__stdin_buf = io.StringIO("""\${stdin.replace(/\\\\/g, '\\\\\\\\').replace(/"""/g, '\\\\"""')}""")
__stdout_buf = CappedStringIO()
__stderr_buf = CappedStringIO()

sys.stdin = __stdin_buf
sys.stdout = __stdout_buf
sys.stderr = __stderr_buf
__exit_code = 0
__error_msg = ""

try:
    __user_globals = {
        '__name__': '__main__',
        '__file__': 'solution.py'
    }
    exec("""\${code.replace(/\\\\/g, '\\\\\\\\').replace(/"""/g, '\\\\"""')\}""", __user_globals)
except SystemExit as e:
    __exit_code = e.code if isinstance(e.code, int) else 0
except Exception as e:
    import traceback
    __exit_code = 1
    __stderr_buf.write(traceback.format_exc())

sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__
sys.stdin = sys.__stdin__

(__stdout_buf.getvalue(), __stderr_buf.getvalue(), __exit_code)
\`;

                try {
                    const result = await pyodide.runPythonAsync(pythonHarness);
                    const stdout = result.get(0);
                    const stderr = result.get(1);
                    const exitCode = result.get(2);
                    result.destroy();

                    const elapsedMs = Math.round(performance.now() - startTime);
                    const currentFiles = getFSFiles();

                    self.postMessage({
                        type: 'result',
                        stdout: stdout || '',
                        stderr: stderr || '',
                        exit_code: exitCode || 0,
                        time_ms: elapsedMs,
                        files: currentFiles,
                        status: exitCode === 0 && !stderr ? 'SUCCESS' : (exitCode !== 0 ? 'ERROR' : 'SUCCESS')
                    });
                } catch (pyErr) {
                    const elapsedMs = Math.round(performance.now() - startTime);
                    self.postMessage({
                        type: 'result',
                        stdout: '',
                        stderr: pyErr.toString(),
                        exit_code: 1,
                        time_ms: elapsedMs,
                        files: getFSFiles(),
                        status: 'ERROR'
                    });
                }
            }
        };

        // Start initialization
        initPyodide();
    `;

    class PyodideRunner {
        constructor() {
            this.worker = null;
            this.isReady = false;
            this.statusMessage = 'Uninitialized';
            this.currentRunReject = null;
            this.executionTimer = null;
            this.onStatusChange = null;
            this.onFilesChange = null;
        }

        init() {
            if (this.worker) return;

            const blob = new Blob([workerScript], { type: 'application/javascript' });
            const workerUrl = URL.createObjectURL(blob);
            this.worker = new Worker(workerUrl);

            this.worker.onmessage = (e) => {
                const data = e.data;

                if (data.type === 'status') {
                    this.statusMessage = data.message;
                    if (this.onStatusChange) this.onStatusChange(data.message, false);
                } else if (data.type === 'ready') {
                    this.isReady = true;
                    this.statusMessage = 'Pyodide + NumPy Ready';
                    if (this.onStatusChange) this.onStatusChange('Pyodide + NumPy Ready', true);
                } else if (data.type === 'init_error') {
                    this.isReady = false;
                    this.statusMessage = `Init Error: ${data.error}`;
                    if (this.onStatusChange) this.onStatusChange(this.statusMessage, false);
                } else if (data.type === 'result') {
                    if (this.executionTimer) {
                        clearTimeout(this.executionTimer);
                        this.executionTimer = null;
                    }
                    if (this.currentRunResolve) {
                        this.currentRunResolve(data);
                        this.currentRunResolve = null;
                    }
                    if (this.onFilesChange && data.files) {
                        this.onFilesChange(data.files);
                    }
                } else if (data.type === 'files_list' || data.type === 'file_written' || data.type === 'file_deleted') {
                    if (this.onFilesChange && data.files) {
                        this.onFilesChange(data.files);
                    }
                    if (this.fileOpResolve) {
                        this.fileOpResolve(data);
                        this.fileOpResolve = null;
                    }
                } else if (data.type === 'file_content') {
                    if (this.fileOpResolve) {
                        this.fileOpResolve(data.content);
                        this.fileOpResolve = null;
                    }
                } else if (data.type === 'file_error') {
                    if (this.fileOpReject) {
                        this.fileOpReject(new Error(data.error));
                        this.fileOpReject = null;
                    }
                }
            };

            this.worker.onerror = (err) => {
                console.error('Pyodide Worker Error:', err);
                if (this.currentRunResolve) {
                    this.currentRunResolve({
                        stdout: '',
                        stderr: `Pyodide Worker Error: ${err.message || 'Worker crash'}`,
                        exit_code: 1,
                        time_ms: 0,
                        status: 'ERROR'
                    });
                    this.currentRunResolve = null;
                }
            };
        }

        restartWorker() {
            if (this.worker) {
                try {
                    this.worker.terminate();
                } catch (e) {}
                this.worker = null;
            }
            this.isReady = false;
            this.init();
        }

        run(code, stdin = '', files = [], clearFS = true) {
            return new Promise((resolve, reject) => {
                if (!this.worker) this.init();

                this.currentRunResolve = resolve;

                // 10-Second Execution Timeout
                this.executionTimer = setTimeout(() => {
                    console.warn('Pyodide worker execution timed out (10s). Terminating and restarting...');
                    this.restartWorker();
                    resolve({
                        stdout: '',
                        stderr: 'Execution timed out after 10.0 seconds. Pyodide worker was terminated and restarted.',
                        exit_code: 124,
                        time_ms: 10000,
                        status: 'TIMEOUT'
                    });
                }, 10000);

                this.worker.postMessage({
                    action: 'run',
                    code: code,
                    stdin: stdin,
                    files: files,
                    clearFS: clearFS
                });
            });
        }

        listFiles() {
            return new Promise((resolve) => {
                this.fileOpResolve = (data) => resolve(data.files || []);
                this.worker.postMessage({ action: 'list_files' });
            });
        }

        readFile(filename) {
            return new Promise((resolve, reject) => {
                this.fileOpResolve = resolve;
                this.fileOpReject = reject;
                this.worker.postMessage({ action: 'read_file', filename: filename });
            });
        }

        writeFile(filename, content) {
            return new Promise((resolve, reject) => {
                this.fileOpResolve = resolve;
                this.fileOpReject = reject;
                this.worker.postMessage({ action: 'write_file', filename: filename, content: content });
            });
        }

        deleteFile(filename) {
            return new Promise((resolve, reject) => {
                this.fileOpResolve = resolve;
                this.fileOpReject = reject;
                this.worker.postMessage({ action: 'delete_file', filename: filename });
            });
        }
    }

    window.PyodideRunner = new PyodideRunner();
})();
