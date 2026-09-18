"""Offline doctor failures and JSON CLI exits; no real Codex processes or jobs."""
import io
import json
import runpy
import subprocess
import sys
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import codex_status
import macos
import quota_watcher


PRIVATE = 'private task content, paths, and server output'


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.responses = {
            'account/rateLimits/read': {'ordinaryUsageAllowed': True},
            'thread/list': {'data': [{'id': 'test-thread'}]},
            'thread/turns/list': {'data': []},
        }
        self.failures = {}
        self.requests = []

        @contextmanager
        def connection(executable):
            def request(method, params):
                self.requests.append(method)
                if method in self.failures:raise self.failures[method]
                return self.responses[method]
            yield request

        self.status = SimpleNamespace(connection=connection, quota_open=codex_status.quota_open)
        self.watcher = SimpleNamespace(codex_status=self.status)
        self.find = self.enterContext(patch.object(macos, 'find_codex', return_value='/fake/codex'))
        self.run = self.enterContext(patch.object(macos.subprocess, 'run',
            return_value=subprocess.CompletedProcess([], 0, 'codex-cli test\n', '')))

    def diagnose(self):
        result = macos.doctor(self.watcher)
        self.assertNotIn(PRIVATE, json.dumps(result))
        return result

    def test_success_and_zero_quota(self):
        for allowed in (True, False):
            with self.subTest(allowed=allowed):
                self.responses['account/rateLimits/read']['ordinaryUsageAllowed'] = allowed
                result = self.diagnose()
                self.assertTrue(result['ok'])
                self.assertEqual(result['version'], 'codex-cli test')
                self.assertTrue(result['resume'] and result['queue'] and result['turnsAPI'])
                self.assertIs(result['quotaAvailable'], allowed)
                self.assertEqual(result['errors'], {})

    def test_missing_cli_does_not_run_commands(self):
        self.find.side_effect = FileNotFoundError(PRIVATE)
        result = self.diagnose()
        self.assertFalse(result['ok'])
        self.assertIsNone(result['executable'])
        self.assertIsNone(result['version'])
        self.assertEqual(result['errors']['executable']['type'], 'FileNotFoundError')
        self.run.assert_not_called()
        self.assertEqual(self.requests, [])

    def test_command_timeout_and_nonzero_keep_other_results(self):
        self.run.side_effect = [
            subprocess.TimeoutExpired(PRIVATE, 20, output=PRIVATE, stderr=PRIVATE),
            subprocess.CompletedProcess([], 7, PRIVATE, PRIVATE),
            subprocess.CompletedProcess([], 0, '', ''),
        ]
        result = self.diagnose()
        self.assertFalse(result['ok'])
        self.assertIsNone(result['version'])
        self.assertIsNone(result['resume'])
        self.assertTrue(result['queue'] and result['quotaAvailable'] and result['turnsAPI'])
        self.assertEqual(result['errors']['version']['type'], 'TimeoutExpired')
        self.assertEqual(result['errors']['resume']['returncode'], 7)

    def test_command_permission_error_and_empty_version(self):
        self.run.side_effect = [
            subprocess.CompletedProcess([], 0, '', ''),
            PermissionError(PRIVATE),
            subprocess.CompletedProcess([], 0, '', ''),
        ]
        result = self.diagnose()
        self.assertIsNone(result['version'])
        self.assertIsNone(result['resume'])
        self.assertEqual(result['errors']['resume']['type'], 'PermissionError')
        self.assertTrue(result['queue'])

    def test_app_server_initialization_failure_keeps_cli_results(self):
        @contextmanager
        def closed(executable):
            raise OSError(PRIVATE)
            yield
        self.status.connection = closed
        result = self.diagnose()
        self.assertFalse(result['ok'])
        self.assertEqual(result['version'], 'codex-cli test')
        self.assertTrue(result['resume'] and result['queue'])
        self.assertIsNone(result['quotaAvailable'])
        self.assertIsNone(result['turnsAPI'])
        self.assertEqual(result['errors']['appServer']['type'], 'OSError')

    def test_quota_failure_does_not_skip_turns_check(self):
        self.failures['account/rateLimits/read'] = RuntimeError(PRIVATE)
        result = self.diagnose()
        self.assertFalse(result['ok'])
        self.assertIsNone(result['quotaAvailable'])
        self.assertTrue(result['turnsAPI'])
        self.assertEqual(result['errors']['quotaAvailable']['method'], 'account/rateLimits/read')

    def test_turns_failures_and_empty_history_are_unverified(self):
        for method in ('thread/list', 'thread/turns/list'):
            with self.subTest(method=method):
                self.failures = {method: RuntimeError(PRIVATE)}
                result = self.diagnose()
                self.assertFalse(result['ok'])
                self.assertTrue(result['quotaAvailable'])
                self.assertIsNone(result['turnsAPI'])
                self.assertEqual(result['errors']['turnsAPI']['method'], method)
        self.failures = {}
        self.responses['thread/list'] = {'data': []}
        result = self.diagnose()
        self.assertFalse(result['ok'])
        self.assertEqual(result['turnsAPI'], 'no thread to verify')

    def test_cli_emits_json_and_never_writes_watcher_log(self):
        # Execute the real entry point, including its outer exception/log handler.
        for diagnostic in ({'ok': True, 'errors': {}}, {'ok': False, 'errors': {}}, RuntimeError(PRIVATE)):
            with self.subTest(diagnostic=type(diagnostic).__name__):
                output = io.StringIO()
                kwargs = {'side_effect': diagnostic} if isinstance(diagnostic, Exception) else {'return_value': diagnostic}
                with patch.object(macos, 'doctor', **kwargs), \
                     patch.object(sys, 'argv', ['app.py', '--doctor']), \
                     patch.object(sys, 'platform', 'darwin'), \
                     patch.object(quota_watcher, 'log', side_effect=PermissionError(PRIVATE)) as log, \
                     redirect_stdout(output):
                    if isinstance(diagnostic, dict) and diagnostic['ok']:
                        runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')
                    else:
                        with self.assertRaises(SystemExit) as stopped:
                            runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')
                        self.assertEqual(stopped.exception.code, 1)
                    log.assert_not_called()
                result = json.loads(output.getvalue())
                self.assertNotIn(PRIVATE, output.getvalue())
                self.assertIs(result['ok'], isinstance(diagnostic, dict) and diagnostic['ok'])


if __name__ == '__main__':unittest.main()
