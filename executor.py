import time
import requests
from flask import current_app

LANGUAGE_MAP_PISTON = {
    'python': {'language': 'python', 'version': '3.10.0'},
    'javascript': {'language': 'javascript', 'version': '18.15.0'},
    'cpp': {'language': 'c++', 'version': '10.2.0'},
    'java': {'language': 'java', 'version': '15.0.2'},
}

LANGUAGE_ID_JUDGE0 = {
    'python': 71,       # Python 3
    'javascript': 63,   # JavaScript (Node.js)
    'cpp': 54,          # C++ (GCC 9.2.0)
    'java': 62,         # Java (OpenJDK 13.0.1)
}


class CodeExecutor:
    """
    Code Execution Client for external sandboxes (Piston / Judge0).
    NEVER runs code on the local server.
    """
    def __init__(self, app=None):
        self.app = app

    def _get_config(self, needs_numpy: bool = False):
        backend = current_app.config.get('EXECUTOR', 'piston').lower()
        if needs_numpy and current_app.config.get('EXECUTOR_NUMPY_URL'):
            url = current_app.config.get('EXECUTOR_NUMPY_URL')
        else:
            url = current_app.config.get('EXECUTOR_URL', 'https://emkc.org/api/v2/piston/execute')
        api_key = current_app.config.get('EXECUTOR_API_KEY', '')
        timeout = current_app.config.get('EXECUTOR_TIMEOUT', 10)
        return backend, url, api_key, timeout

    def execute(self, code: str, language: str = 'python', stdin: str = '', needs_numpy: bool = False) -> dict:
        """
        Executes code on the configured sandbox service with a timeout.
        If needs_numpy is True, routes to the dedicated numpy-enabled executor if configured.
        Returns a dict:
        {
            'stdout': str,
            'stderr': str,
            'exit_code': int,
            'time_ms': float,
            'status': 'SUCCESS' | 'ERROR' | 'TIMEOUT' | 'NETWORK_ERROR'
        }
        """
        backend, url, api_key, timeout = self._get_config(needs_numpy=needs_numpy)

        if backend == 'judge0':
            return self._execute_judge0(url, api_key, code, language, stdin, timeout)
        else:
            result = self._execute_piston(url, api_key, code, language, stdin, timeout)
            # If public Piston is locked/rate-limited (e.g. HTTP 401 whitelist), auto-fallback to free public Judge0 sandbox
            if result.get('status') == 'NETWORK_ERROR' and '401' in result.get('stderr', ''):
                return self._execute_judge0('https://ce.judge0.com', '', code, language, stdin, timeout)
            return result

    def _execute_piston(self, url: str, api_key: str, code: str, language: str, stdin: str, timeout: int) -> dict:
        lang_info = LANGUAGE_MAP_PISTON.get(language, LANGUAGE_MAP_PISTON['python'])
        payload = {
            'language': lang_info['language'],
            'version': lang_info['version'],
            'files': [
                {
                    'name': f'solution.{"py" if language == "python" else "txt"}',
                    'content': code
                }
            ],
            'stdin': stdin or '',
            'run_timeout': timeout * 1000,
            'compile_timeout': timeout * 1000
        }

        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = api_key

        start_time = time.time()
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=timeout + 3)
            elapsed_ms = round((time.time() - start_time) * 1000, 2)

            if resp.status_code == 200:
                data = resp.json()
                run_data = data.get('run', {})
                stdout = run_data.get('stdout', '') or ''
                stderr = run_data.get('stderr', '') or ''
                code_exit = run_data.get('code', 0)

                status = 'SUCCESS' if code_exit == 0 and not stderr else ('ERROR' if code_exit != 0 else 'SUCCESS')
                if 'timed out' in stderr.lower() or 'signal: killed' in stderr.lower():
                    status = 'TIMEOUT'

                return {
                    'stdout': stdout,
                    'stderr': stderr,
                    'exit_code': code_exit,
                    'time_ms': elapsed_ms,
                    'status': status
                }
            else:
                return {
                    'stdout': '',
                    'stderr': f"Execution server returned HTTP {resp.status_code}: {resp.text[:200]}",
                    'exit_code': 1,
                    'time_ms': elapsed_ms,
                    'status': 'NETWORK_ERROR'
                }
        except requests.Timeout:
            return {
                'stdout': '',
                'stderr': f"Execution timed out after {timeout} seconds.",
                'exit_code': 124,
                'time_ms': round((time.time() - start_time) * 1000, 2),
                'status': 'TIMEOUT'
            }
        except requests.RequestException as e:
            return {
                'stdout': '',
                'stderr': f"Network error contacting execution service: {str(e)}",
                'exit_code': 1,
                'time_ms': round((time.time() - start_time) * 1000, 2),
                'status': 'NETWORK_ERROR'
            }

    def _execute_judge0(self, url: str, api_key: str, code: str, language: str, stdin: str, timeout: int) -> dict:
        lang_id = LANGUAGE_ID_JUDGE0.get(language, 71)
        base_endpoint = url.rstrip('/')
        if not base_endpoint.endswith('/submissions'):
            endpoint = f"{base_endpoint}/submissions?wait=true"
        else:
            endpoint = f"{base_endpoint}?wait=true"

        payload = {
            'source_code': code,
            'language_id': lang_id,
            'stdin': stdin or '',
            'cpu_time_limit': timeout
        }
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['X-Auth-Token'] = api_key
            headers['X-RapidAPI-Key'] = api_key

        start_time = time.time()
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=timeout + 4)
            elapsed_ms = round((time.time() - start_time) * 1000, 2)

            if resp.status_code in (200, 201):
                data = resp.json()
                stdout = data.get('stdout') or ''
                stderr = data.get('stderr') or data.get('compile_output') or ''
                status_obj = data.get('status', {})
                status_id = status_obj.get('id', 0)
                status_desc = status_obj.get('description', '')
                time_s = float(data.get('time') or 0.0)

                # Judge0 status 3 is Accepted (exited with 0 and no error)
                status = 'SUCCESS' if status_id == 3 else 'ERROR'
                if 'Time Limit Exceeded' in status_desc:
                    status = 'TIMEOUT'

                return {
                    'stdout': stdout,
                    'stderr': stderr,
                    'exit_code': 0 if status_id == 3 else 1,
                    'time_ms': round(time_s * 1000 if time_s else elapsed_ms, 2),
                    'status': status
                }
            else:
                return {
                    'stdout': '',
                    'stderr': f"Judge0 returned status {resp.status_code}: {resp.text[:200]}",
                    'exit_code': 1,
                    'time_ms': elapsed_ms,
                    'status': 'NETWORK_ERROR'
                }
        except requests.Timeout:
            return {
                'stdout': '',
                'stderr': f"Execution timed out after {timeout} seconds.",
                'exit_code': 124,
                'time_ms': round((time.time() - start_time) * 1000, 2),
                'status': 'TIMEOUT'
            }
        except requests.RequestException as e:
            return {
                'stdout': '',
                'stderr': f"Network error contacting Judge0: {str(e)}",
                'exit_code': 1,
                'time_ms': round((time.time() - start_time) * 1000, 2),
                'status': 'NETWORK_ERROR'
            }

    def run_tests(self, code: str, language: str, test_cases: list, needs_numpy: bool = False) -> dict:
        """
        Runs code against a suite of test cases.
        """
        results = []
        passed_count = 0
        total_time = 0.0

        for idx, tc in enumerate(test_cases, start=1):
            test_in = str(tc.get('input', '')).rstrip('\r\n')
            expected_out = str(tc.get('output', '')).strip()

            res = self.execute(code=code, language=language, stdin=test_in, needs_numpy=needs_numpy)
            actual_out = (res.get('stdout') or '').strip()
            total_time += res.get('time_ms', 0.0)

            passed = (res.get('status') == 'SUCCESS' and actual_out == expected_out)
            if passed:
                passed_count += 1

            results.append({
                'test_index': idx,
                'input': test_in,
                'expected': expected_out,
                'actual': actual_out,
                'passed': passed,
                'stderr': res.get('stderr', ''),
                'time_ms': res.get('time_ms', 0),
                'status': 'PASSED' if passed else ('FAILED' if res.get('status') == 'SUCCESS' else res.get('status'))
            })

        total = len(test_cases)
        score = round((passed_count / total * 100), 1) if total > 0 else 0.0

        return {
            'total': total,
            'passed': passed_count,
            'score': score,
            'total_time_ms': round(total_time, 2),
            'results': results
        }


executor = CodeExecutor()
