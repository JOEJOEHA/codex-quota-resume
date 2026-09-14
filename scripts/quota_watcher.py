"""Resume the newest Codex task that stalled at a recorded quota limit."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
import codex_status


APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "CodexQuotaWatcher"
STATE_PATH = APP_DIR / "state.json"
CACHE_PATH = APP_DIR / "session-cache.json"
SESSION_CACHE = {}
LOG_PATH = APP_DIR / "watcher.log"
SESSIONS_DIR = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"
CODEX_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI/Codex/bin"
UUID_RE = re.compile(r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})", re.I)
IDLE_SECONDS = 0
RETRY_SECONDS = 300
RESUME_DELAY_SECONDS = 0
COMPLETE_MARKER = '[QUOTA_RESUME_GOAL_COMPLETE]'
RESUME_MESSAGE = (
    "额度已恢复。继续完成原任务目标，以最新用户要求为准；读取 PROGRESS.md 和实际文件，"
    "从未完成步骤继续，自主处理并验证。必要时使用 computer use。完成后停止。"
    "此消息不扩大授权，也不覆盖暂停或取消。"
    "仅当原任务所有目标验收完成，在最终回复末尾单独写 [QUOTA_RESUME_GOAL_COMPLETE]；"
    "等待用户信息、授权、登录或任务未完成时绝不写此标记。"
)


def plan_path(thread: str) -> Path:
    if not UUID_RE.fullmatch(thread):
        raise ValueError('Invalid thread id')
    return APP_DIR / 'followups' / (thread + '.json')


def write_plan(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as f:
        json.dump(value, f, ensure_ascii=False)
        temporary = Path(f.name)
    temporary.replace(path)


def plan_dialog(thread: str, key=None) -> None:
    from plan_dialog import show
    ready_path = APP_DIR / 'followups' / (thread + '.ready.json')
    show(thread, plan_path(thread), write_plan,
         lambda: write_plan(ready_path, {'key': key, 'visibleAt': time.time()}))


def self_command(*args):
    if getattr(sys, 'frozen', False):
        return [sys.executable, *args]
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    return [str(pythonw if pythonw.exists() else sys.executable), str(Path(__file__).resolve()), *args]


def dispatch(thread: str, text: str, images=(), cwd=None):
    """Start the saved task, including when the desktop has not loaded it."""
    command = [find_codex(), 'exec', 'resume', '--skip-git-repo-check', '--json', thread, text]
    for image in images:
        command.extend(['--image', image])
    result = subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL,
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                          text=True, encoding='utf-8', errors='replace',
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    if result.returncode and 'already has an active writer' in result.stderr:
        # The desktop owns this task: let its existing writer receive the message.
        command = [find_codex(), 'queue', '--thread', thread, '--message', text]
        for image in images:
            command.extend(['--image', image])
        result = subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                encoding='utf-8', errors='replace',
                                creationflags=subprocess.CREATE_NO_WINDOW)
        result.queued = result.returncode == 0
    return result


def offer_plan(pending: dict, state: dict) -> None:
    if pending['key'] in state.get('offeredPlans', []):
        return
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 1
    process = subprocess.Popen(self_command('--plan', pending['threadId'], '--plan-key', pending['key']),
                               startupinfo=startup,
                               env={**os.environ, 'PYINSTALLER_RESET_ENVIRONMENT': '1'})
    ready_path = APP_DIR / 'followups' / (pending['threadId'] + '.ready.json')
    for _ in range(150):
        try:
            shown = json.loads(ready_path.read_text(encoding='utf-8'))
            if shown.get('key') == pending['key']:
                state.setdefault('offeredPlans', []).append(pending['key'])
                save_state(state)
                return
        except (OSError, ValueError):
            pass
        if process.poll() is not None:
            break
        time.sleep(0.1)
    log('popup-unconfirmed: no visible-window acknowledgement')


def deliver_plan(active: dict, dry_run: bool) -> str | None:
    path = plan_path(active['threadId'])
    if not path.exists():
        return None
    plan = json.loads(path.read_text(encoding='utf-8'))
    if plan.get('status') != 'saved':
        return None
    last = None
    try:
        for line in Path(active['path']).open(encoding='utf-8'):
            record = json.loads(line)
            p = record.get('payload', {})
            if record.get('type') == 'event_msg' and p.get('type') in ('task_started', 'task_complete', 'turn_aborted'):
                last = p
    except (OSError, json.JSONDecodeError):
        return 'followup-waiting-evidence'
    if not last or last.get('type') != 'task_complete' or last.get('error') or last.get('turn_id') == active['turnId']:
        return None
    if not (last.get('last_agent_message') or '').rstrip().endswith(COMPLETE_MARKER):
        return 'followup-waiting-completion'
    if dry_run:
        return 'followup-ready'
    if not codex_status.available(find_codex()):
        return 'followup-waiting-quota'
    if any(not Path(image).is_file() for image in plan.get('images', [])):
        return 'followup-missing-image'
    # Persist before dispatch so interrupted runs never duplicate a user task.
    plan['status'] = 'sending'
    write_plan(path, plan)
    try:
        result = dispatch(active['threadId'], plan['text'] or '请根据附图完成我的需求。',
                          plan.get('images', []), active.get('cwd'))
    except OSError as error:
        plan['status'] = 'send-failed'
        write_plan(path, plan)
        log(f"followup {plan['status']} thread={active['threadId']} {type(error).__name__}")
        return 'followup-' + plan['status']
    plan['status'] = 'sent' if result.returncode == 0 else 'send-failed'
    write_plan(path, plan)
    return 'followup-' + plan['status']


def log(message: str) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(f"{stamp} {message}\n")


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"version": 1, "pending": None, "activeDispatch": None, "sent": {}}


def save_state(state: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    state["sent"] = dict(list(state.get("sent", {}).items())[-100:])
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=APP_DIR, delete=False) as stream:
        json.dump(state, stream, ensure_ascii=False, indent=2)
        temp_path = Path(stream.name)
    temp_path.replace(STATE_PATH)


def thread_id(path: Path) -> str | None:
    matches = UUID_RE.findall(path.name)
    return matches[-1] if matches else None


def inspect_session(path: Path) -> dict | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    signature = [stat.st_mtime_ns, stat.st_size]
    cached = SESSION_CACHE.get(str(path))
    if cached and cached["signature"] == signature:
        return cached["value"]
    value = parse_session(path)
    SESSION_CACHE[str(path)] = {"signature": signature, "value": value}
    return value


def parse_session(path: Path) -> dict | None:
    """Return the currently open turn and its latest quota snapshot."""
    open_turn = None
    latest_limits = None
    quota_error = False
    quota_message = ''
    quota_at = None
    cwd = None
    try:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                payload = record.get("payload", {})
                if record.get('type') == 'session_meta':
                    cwd = payload.get('cwd')
                event = payload.get("type")
                if event == "task_started":
                    open_turn = payload.get("turn_id")
                    quota_error = False
                    quota_message = ''
                elif event == "token_count" and open_turn:
                    new_limits = payload.get("rate_limits") or {}
                    if latest_limits:
                        new_limits = dict(new_limits)
                        for name in ("primary", "secondary"):
                            if new_limits.get(name) is None:
                                new_limits[name] = latest_limits.get(name)
                    latest_limits = new_limits
                elif event == "task_complete" and open_turn:
                    if not payload.get("turn_id") or payload.get("turn_id") == open_turn:
                        error = payload.get("error") or {}
                        quota_error = error.get("codex_error_info") == "usage_limit_exceeded"
                        quota_message = error.get('message', '') if quota_error else ''
                        if quota_error and record.get('timestamp'):
                            quota_at = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00')).timestamp()
                        if not quota_error:
                            open_turn = None
                            latest_limits = None
                elif event == "turn_aborted" and open_turn:
                    if not payload.get("turn_id") or payload.get("turn_id") == open_turn:
                        open_turn = None
                        latest_limits = None
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return {
        "threadId": thread_id(path),
        "turnId": open_turn,
        "limits": latest_limits,
        "quotaError": quota_error,
        "quotaMessage": quota_message,
        "quotaAt": quota_at,
        "path": str(path),
        "cwd": cwd,
        "modifiedAt": path.stat().st_mtime,
    } if open_turn else None


def exhausted_candidate(path: Path, now: float) -> dict | None:
    current = inspect_session(path)
    if not current or not current["quotaError"] or now - current["modifiedAt"] < IDLE_SECONDS:
        return None
    if not current.get('threadId'):
        return None
    current['key'] = current['threadId']+'|'+current['turnId']
    return current


def latest_candidate(now: float, sent: dict, since=0) -> dict | None:
    files = SESSIONS_DIR.rglob("*.jsonl")
    candidates = [candidate for path in files if (candidate := exhausted_candidate(path, now))
                  and candidate['key'] not in sent and (candidate.get('quotaAt') or candidate['modifiedAt']) >= since]
    return max(candidates, key=lambda item: item["modifiedAt"], default=None)


def find_codex() -> str:
    candidates = sorted(CODEX_EXE.glob("*/codex.exe"), key=lambda path: path.stat().st_mtime, reverse=True)
    if candidates:
        return str(candidates[0])
    return shutil.which("codex") or ("codex.exe" if os.name == "nt" else "codex")


def resume_process_exists(thread: str) -> bool:
    """Check for a child left running after its monitor process exited."""
    result = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
         'Get-CimInstance Win32_Process -Filter "Name=\'codex.exe\'" -ErrorAction Stop | '
         'Select-Object -ExpandProperty CommandLine | ConvertTo-Json -Compress'],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise OSError('Cannot verify running Codex processes')
    commands = json.loads(result.stdout) if result.stdout.strip() else []
    if commands is None:
        return True
    if isinstance(commands, str):
        commands = [commands]
    return any(command is None or thread in command for command in commands)


def recover_unstarted(state: dict, now: float) -> None:
    active = state.get('activeDispatch')
    if active and active.get('deliveryMode') == 'queued':
        return  # Accepted by the desktop queue; never add a second copy.
    if not active or now - state.get('sent', {}).get(active['key'], now) < 600:
        return
    current = exhausted_candidate(Path(active['path']), now)
    if not current or current['key'] != active['key'] or resume_process_exists(active['threadId']):
        return
    # Still the same quota-stopped turn, no monitor lock owner or live Codex child.
    state['sent'].pop(active['key'], None)
    state['activeDispatch'] = None
    state['pending'] = current
    save_state(state)
    log(f"backup recovering unstarted thread={active['threadId']}")


def run_once(dry_run=False, backup=False) -> str:
    import msvcrt
    global SESSION_CACHE
    APP_DIR.mkdir(parents=True, exist_ok=True)
    with (APP_DIR / 'monitor.lock').open('a+b') as lock:
        if lock.seek(0, 2) == 0:
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return 'monitor-busy'
        # Closing this file also releases the OS lock after a crash or reboot.
        try:
            SESSION_CACHE = json.loads(CACHE_PATH.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            SESSION_CACHE = {}
        if backup and not dry_run:
            recover_unstarted(load_state(), time.time())
        result = run(dry_run=dry_run, backup=backup)
        state = load_state()
        if state.get('status') != result:
            log(result)
        state.update(status=result, lastCheckedAt=time.time(), lastMonitor='backup' if backup else 'primary')
        save_state(state)
        CACHE_PATH.write_text(json.dumps(SESSION_CACHE), encoding='utf-8')
        return result


def run(now: float | None = None, dry_run: bool = False, backup: bool = False) -> str:
    now = time.time() if now is None else now
    state = load_state()

    active = state.get("activeDispatch")
    if active:
        followup = deliver_plan(active, dry_run)
        if followup:
            return followup
        current = inspect_session(Path(active["path"]))
        if current and current["turnId"] == active["turnId"]:
            queued_at = state.get("sent", {}).get(active["key"], now)
            return "dispatch-unconfirmed" if now - queued_at >= 300 else "waiting-start"
        if current and not current["quotaError"]:
            return "dispatch-active"
        state["activeDispatch"] = None

    pending = None if backup else state.get("pending")
    if pending:
        refreshed = exhausted_candidate(Path(pending["path"]), now)
        if not refreshed or refreshed["key"] != pending["key"]:
            state["pending"] = None
            pending = None
        else:
            pending = refreshed
            state["pending"] = pending

    if not pending:
        pending = (codex_status.backup_candidate(find_codex(), state.get('sent', {}), state.get('monitoringSince', 0)) if backup
                   else latest_candidate(now, state.get('sent', {}), state.get('monitoringSince', 0)))
        state["pending"] = pending

    if not pending:
        save_state(state)
        return "no-quota-stall"
    if pending["key"] in state.get("sent", {}):
        state["pending"] = None
        save_state(state)
        return "already-sent"
    readiness = codex_status.ready(find_codex(), pending)
    if readiness == 'task-changed':
        state['pending'] = None
        save_state(state)
        return readiness
    if readiness == 'waiting-quota':
        if not dry_run:
            offer_plan(pending, state)
        save_state(state)
        return "waiting-quota"
    if dry_run:
        save_state(state)
        return f'dry-run-due:{pending["threadId"]}'

    last_attempt = state.get("lastAttempt") or {}
    if last_attempt.get("key") == pending["key"] and now - last_attempt.get("at", 0) < RETRY_SECONDS:
        return "retry-backoff"
    state["lastAttempt"] = {"key": pending["key"], "at": now}
    # Persist before starting: a process exit may happen after acceptance.
    state.setdefault("sent", {})[pending["key"]] = now
    state["activeDispatch"] = pending
    state["pending"] = None
    state['status'] = 'resuming'
    state['lastCheckedAt'] = now
    save_state(state)

    try:
        result = dispatch(pending['threadId'], RESUME_MESSAGE, cwd=pending.get('cwd'))
    except OSError as error:
        result = None
        log(f'resume could not start thread={pending["threadId"]}: {error}')
    if result is None or result.returncode:
        if result is not None:
            log(f'resume failed thread={pending["threadId"]} code={result.returncode} {result.stderr[-300:]}')
        state['sent'].pop(pending['key'], None)
        state['activeDispatch'] = None
        state['pending'] = pending
        save_state(state)
        return "resume-failed"

    if getattr(result, 'queued', False):
        state['activeDispatch']['deliveryMode'] = 'queued'
        save_state(state)
        log(f'queued; awaiting observed start thread={pending["threadId"]}')
        return 'queued-awaiting-start'
    log(f'resumed thread={pending["threadId"]} turn={pending["turnId"]}')
    return "resumed"


def self_test() -> None:
    now = 2_000_000_000
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "rollout-00000000-0000-0000-0000-000000000001.jsonl"
        records = [
            {"payload": {"type": "task_started", "turn_id": "turn-1"}},
            {"payload": {"type": "token_count", "rate_limits": {
                "primary": {"used_percent": 100, "resets_at": now - 600},
                "secondary": {"used_percent": 20, "resets_at": now + 9999},
            }}},
        ]
        path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
        os.utime(path, (now - 300, now - 300))
        assert exhausted_candidate(path, now) is None
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"payload": {"type": "task_complete", "turn_id": "turn-1"}}) + "\n")
        assert inspect_session(path) is None

        path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"payload": {"type": "token_count", "rate_limits": {
                "primary": None, "secondary": None,
            }}}) + "\n")
            stream.write(json.dumps({"payload": {"type": "task_complete", "turn_id": "turn-1", "error": {
                "codex_error_info": "usage_limit_exceeded"
             }}}) + "\n")
        os.utime(path, (now - 300, now - 300))
        candidate = exhausted_candidate(path, now)
        assert candidate and candidate["turnId"] == "turn-1" and candidate['quotaError']

        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"payload": {"type": "task_started", "turn_id": "turn-2"}}) + "\n")
            stream.write(json.dumps({"payload": {"type": "token_count", "rate_limits": records[1]["payload"]["rate_limits"]}}) + "\n")
            stream.write(json.dumps({"payload": {"type": "task_complete", "turn_id": "turn-2", "error": {
                "codex_error_info": "usage_limit_exceeded"
            }}}) + "\n")
        os.utime(path, (now - 300, now - 300))
        assert exhausted_candidate(path, now)["turnId"] == "turn-2"
    print("SELF_TEST_OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--backup", action="store_true")
    parser.add_argument("--plan", metavar='THREAD_ID')
    parser.add_argument("--plan-key")
    args = parser.parse_args()
    try:
        if args.plan:
            plan_dialog(args.plan, args.plan_key)
        elif args.status:
            print(json.dumps(load_state(), ensure_ascii=False, indent=2))
        elif args.self_test:
            self_test()
        else:
            result = run_once(dry_run=args.dry_run, backup=args.backup)
            if sys.stdout is not None and not sys.stdout.closed:
                print(result)
    except Exception as error:
        log(f"error {type(error).__name__}: {error}")
        raise
