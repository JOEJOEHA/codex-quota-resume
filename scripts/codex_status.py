"""Read current account/turn state through the official local App Server API."""
import json
import queue
import subprocess
import threading
import time
from contextlib import contextmanager


@contextmanager
def connection(executable):
    process = subprocess.Popen([executable, 'app-server', '--stdio'], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                               encoding='utf-8', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    replies = queue.Queue()
    def read():
        try:
            for line in process.stdout:
                replies.put(json.loads(line))
        finally:
            replies.put(None)
    threading.Thread(target=read, daemon=True).start()
    request_id = 0
    def request(method, params):
        nonlocal request_id
        request_id += 1
        process.stdin.write(json.dumps({'id': request_id, 'method': method, 'params': params})+'\n')
        process.stdin.flush()
        deadline = time.monotonic()+25
        while True:
            reply = replies.get(timeout=max(0, deadline-time.monotonic()))
            if reply is None:
                raise OSError('Codex status connection closed')
            if reply.get('id') == request_id:
                if 'error' in reply:
                    raise RuntimeError(f"{method}: {reply['error'].get('message', 'request failed')}")
                return reply['result']
    try:
        request('initialize', {'clientInfo': {'name': 'quota_watcher', 'version': '2.0'},
                               'capabilities': {'experimentalApi': True}})
        process.stdin.write('{"method":"initialized"}\n'); process.stdin.flush()
        yield request
    finally:
        process.terminate()
        process.wait(timeout=5)
        process.stdin.close()
        process.stdout.close()


def quota_open(response):
    allowed = response.get('ordinaryUsageAllowed')
    if isinstance(allowed, bool):
        return allowed
    limits = (response.get('rateLimitsByLimitId') or {}).get('codex') or response.get('rateLimits') or {}
    windows = [limits.get('primary'), limits.get('secondary')]
    if not all(w and w.get('usedPercent') is not None for w in windows):
        raise ValueError('Current quota information is unavailable')
    return not limits.get('spendControlReached') and all(w['usedPercent'] < 100 for w in windows)


def available(executable):
    with connection(executable) as request:
        return quota_open(request('account/rateLimits/read', {}))


def ready(executable, candidate):
    with connection(executable) as request:
        if not quota_open(request('account/rateLimits/read', {})):
            return 'waiting-quota'
        turns = request('thread/turns/list', {'threadId': candidate['threadId'], 'limit': 1,
                                             'sortDirection': 'desc', 'itemsView': 'summary'})['data']
        if not turns or turns[0]['id'] != candidate['turnId'] or turns[0].get('status') != 'failed':
            return 'task-changed'
        if (turns[0].get('error') or {}).get('codexErrorInfo') != 'usageLimitExceeded':
            return 'task-changed'
        return 'available'


def backup_candidate(executable, sent, since=0):
    """Independent discovery: canonical last-turn errors, no rollout parsing."""
    with connection(executable) as request:
        cursor = None
        while True:
            params = {'limit': 100, 'sortKey': 'updated_at', 'sortDirection': 'desc',
                      'sourceKinds': ['cli', 'vscode', 'exec', 'appServer', 'unknown']}
            if cursor:
                params['cursor'] = cursor
            page = request('thread/list', params)
            for thread in page['data']:
                if thread['updatedAt'] < since:
                    return None
                if thread.get('parentThreadId') or not thread.get('path'):
                    continue
                turns = request('thread/turns/list', {'threadId': thread['id'], 'limit': 1,
                                                     'sortDirection': 'desc', 'itemsView': 'summary'})['data']
                if not turns:
                    continue
                turn = turns[0]
                if since and (turn.get('completedAt') or 0) < since:
                    continue
                if turn.get('status') != 'failed' or (turn.get('error') or {}).get('codexErrorInfo') != 'usageLimitExceeded':
                    continue
                key = thread['id']+'|'+turn['id']
                if key not in sent:
                    return {'threadId': thread['id'], 'turnId': turn['id'], 'key': key,
                            'path': thread['path'], 'cwd': thread['cwd'], 'quotaError': True,
                            'modifiedAt': thread['updatedAt']}
            cursor = page.get('nextCursor')
            if not cursor:
                return None
