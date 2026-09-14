from contextlib import contextmanager
from unittest.mock import patch
import codex_status as s

assert s.quota_open({'ordinaryUsageAllowed': True})
assert not s.quota_open({'ordinaryUsageAllowed': False})
assert s.quota_open({'rateLimits': {'primary': {'usedPercent': 99}, 'secondary': {'usedPercent': 31}}})
assert not s.quota_open({'rateLimits': {'primary': {'usedPercent': 0}, 'secondary': {'usedPercent': 100}}})
turn = {'id': 'stopped', 'status': 'failed', 'error': {'codexErrorInfo': 'usageLimitExceeded'}}
allowed = True
@contextmanager
def fake_connection(executable):
    def request(method, params):
        if method == 'account/rateLimits/read':
            return {'ordinaryUsageAllowed': allowed}
        if method == 'thread/list':
            return {'data': [{'id': 'thread', 'path': 'unavailable-log.jsonl', 'cwd': '.', 'updatedAt': 1}]}
        if method == 'thread/turns/list':
            return {'data': [turn]}
        raise AssertionError(method)
    yield request
with patch.object(s, 'connection', fake_connection):
    candidate = s.backup_candidate('codex', {})
    assert candidate['key'] == 'thread|stopped'  # No local log or percentage needed.
    assert s.ready('codex', candidate) == 'available'
    allowed = False
    assert s.ready('codex', candidate) == 'waiting-quota'
    allowed = True
    assert s.backup_candidate('codex', {'thread|stopped': 1}) is None
    turn['status'] = 'completed'
    assert s.backup_candidate('codex', {}) is None
    assert s.ready('codex', candidate) == 'task-changed'
    turn['status'] = 'interrupted'
    assert s.backup_candidate('codex', {}) is None
print('LIVE_STATUS_OK: live availability, weekly block, independent API discovery without log, dedupe, cancel')
