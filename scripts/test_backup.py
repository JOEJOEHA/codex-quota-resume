import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import quota_watcher as w
patch.object(w,'find_codex',return_value='codex').start()
patch.object(w.codex_status,"ready",return_value="available").start()
patch.object(w.codex_status,"backup_candidate",side_effect=lambda exe,sent,since=0: w.latest_candidate(time.time(),sent,since)).start()

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    with patch.multiple(w, APP_DIR=root, STATE_PATH=root/'state.json', CACHE_PATH=root/'cache.json',
                        LOG_PATH=root/'log', SESSIONS_DIR=root/'sessions', SESSION_CACHE={}):
        w.SESSIONS_DIR.mkdir()
        now = time.time()
        thread = '00000000-0000-0000-0000-000000000001'
        path = w.SESSIONS_DIR / ('rollout-' + thread + '.jsonl')
        records = [
            {'payload': {'type': 'task_started', 'turn_id': 'stopped'}},
            {'payload': {'type': 'token_count', 'rate_limits': {'primary': {
                'used_percent': 100, 'resets_at': int(now)-1000}}}},
            {'payload': {'type': 'task_complete', 'turn_id': 'stopped',
                         'error': {'codex_error_info': 'usage_limit_exceeded'}}}]
        path.write_text(''.join(json.dumps(r)+'\n' for r in records), encoding='utf-8')
        os.utime(path, (now-500, now-500))
        with patch.object(w, 'dispatch', return_value=SimpleNamespace(returncode=0)) as send:
            # The primary never ran: an independent backup starts the due task.
            assert w.run_once(backup=True) == 'resumed'
            assert send.call_count == 1
            state = w.load_state()
            active = state['activeDispatch']
            state['sent'][active['key']] = now-700
            state['lastAttempt']['at'] = now-700
            w.save_state(state)
            # A surviving native process must not receive a duplicate.
            with patch.object(w, 'resume_process_exists', return_value=True):
                assert w.run_once(backup=True) == 'dispatch-unconfirmed'
                assert send.call_count == 1
            # Primary died before starting Codex: the backup takes over once.
            with patch.object(w, 'resume_process_exists', return_value=False):
                assert w.run_once(backup=True) == 'resumed'
                assert send.call_count == 2
            assert w.run_once(backup=True) == 'waiting-start'
            assert send.call_count == 2
            with path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps({'payload': {'type': 'task_started', 'turn_id': 'new'}})+'\n')
            assert w.run_once(backup=True) == 'dispatch-active'
            assert send.call_count == 2
            with path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps({'payload': {'type': 'turn_aborted', 'turn_id': 'new'}})+'\n')
            assert w.run_once(backup=True) == 'no-quota-stall'
            assert send.call_count == 2
        # A real second Python process cannot pass the primary's OS lock.
        with (root/'monitor.lock').open('r+b') as lock:
            w.lock_monitor(lock)
            code = (f'import sys;sys.path.insert(0,{str(Path(w.__file__).parent)!r});'
                    f'import quota_watcher as w;from pathlib import Path;w.APP_DIR=Path({str(root)!r});'
                    'print(w.run_once(backup=True))')
            result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=10)
            assert result.returncode == 0 and result.stdout.strip() == 'monitor-busy', result.stderr
        assert w.run_once(backup=True) == 'no-quota-stall'
print('BACKUP_TEST_OK: missed primary, orphan recovery, live process guard, dedupe, cancel, interprocess lock release')
