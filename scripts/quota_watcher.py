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


APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "CodexQuotaWatcher"
STATE_PATH = APP_DIR / "state.json"
CACHE_PATH = APP_DIR / "session-cache.json"
SESSION_CACHE = {}
LOG_PATH = APP_DIR / "watcher.log"
SESSIONS_DIR = Path.home() / ".codex" / "sessions"
CODEX_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI/Codex/bin"
UUID_RE = re.compile(r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})", re.I)
IDLE_SECONDS = 120
RETRY_SECONDS = 300
RESUME_DELAY_SECONDS = 300
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


def plan_dialog(thread: str) -> None:
    import tkinter as tk
    from tkinter import messagebox
    path = plan_path(thread)
    old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    root = tk.Tk()
    root.title('续跑后还想跑什么任务')
    root.geometry('640x430')
    tk.Label(root, text='续跑后还想跑什么任务', font=('Microsoft YaHei UI', 18)).pack(pady=12)
    tk.Label(root, text='对应任务：' + thread + '\n原任务验收完成后才发送；保存不消耗 Codex 额度。').pack()
    editor = tk.Text(root, wrap='word', font=('Microsoft YaHei UI', 11))
    editor.pack(fill='both', expand=True, padx=16, pady=12)
    if old.get('status') == 'saved':
        editor.insert('1.0', old.get('text', ''))
    def save():
        text = editor.get('1.0', 'end').strip()
        if not text:
            messagebox.showinfo('请输入需求', '填写希望原任务完成后执行的需求。')
            return
        write_plan(path, {'threadId': thread, 'text': text, 'status': 'saved', 'savedAt': time.time()})
        root.destroy()
    tk.Button(root, text='保存后续任务', command=save).pack(side='left', padx=16, pady=12)
    tk.Button(root, text='暂不安排', command=root.destroy).pack(side='right', padx=16, pady=12)
    root.mainloop()


def offer_plan(pending: dict, state: dict) -> None:
    if pending['key'] in state.get('offeredPlans', []):
        return
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    subprocess.Popen([str(pythonw if pythonw.exists() else sys.executable), str(Path(__file__).resolve()),
                      '--plan', pending['threadId']])
    state.setdefault('offeredPlans', []).append(pending['key'])
    save_state(state)


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
    # An uncertain queue result must not silently duplicate a new user task.
    plan['status'] = 'sending'
    write_plan(path, plan)
    result = subprocess.run([find_codex(), 'queue', '--thread', active['threadId'], '--message', plan['text']],
                            capture_output=True, text=True, timeout=60)
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
    try:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                payload = record.get("payload", {})
                event = payload.get("type")
                if event == "task_started":
                    open_turn = payload.get("turn_id")
                    latest_limits = None
                    quota_error = False
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
        "path": str(path),
        "modifiedAt": path.stat().st_mtime,
    } if open_turn else None


def exhausted_candidate(path: Path, now: float) -> dict | None:
    current = inspect_session(path)
    if not current or not current["quotaError"] or now - current["modifiedAt"] < IDLE_SECONDS:
        return None
    limits = current.get("limits") or {}
    exhausted = []
    for name in ("primary", "secondary"):
        window = limits.get(name) or {}
        if (window.get("used_percent") or 0) >= 100 and window.get("resets_at"):
            exhausted.append(int(window["resets_at"]))
    if not exhausted or not current.get("threadId"):
        return None
    current["resetAt"] = max(exhausted)
    current["dueAt"] = current["resetAt"] + RESUME_DELAY_SECONDS
    current["key"] = f'{current["threadId"]}|{current["turnId"]}|{current["resetAt"]}'
    return current


def latest_candidate(now: float, sent: dict) -> dict | None:
    files = SESSIONS_DIR.rglob("*.jsonl")
    candidates = [candidate for path in files if (candidate := exhausted_candidate(path, now)) and candidate["key"] not in sent]
    return max(candidates, key=lambda item: item["modifiedAt"], default=None)


def find_codex() -> str:
    candidates = sorted(CODEX_EXE.glob("*/codex.exe"), key=lambda path: path.stat().st_mtime, reverse=True)
    if candidates:
        return str(candidates[0])
    return shutil.which("codex") or ("codex.exe" if os.name == "nt" else "codex")


def run(now: float | None = None, dry_run: bool = False) -> str:
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

    pending = state.get("pending")
    if pending:
        refreshed = exhausted_candidate(Path(pending["path"]), now)
        if not refreshed or refreshed["key"] != pending["key"]:
            state["pending"] = None
            pending = None
        else:
            pending = refreshed
            state["pending"] = pending

    if not pending:
        pending = latest_candidate(now, state.get("sent", {}))
        state["pending"] = pending

    if not pending:
        save_state(state)
        return "no-quota-stall"
    if pending["key"] in state.get("sent", {}):
        state["pending"] = None
        save_state(state)
        return "already-sent"
    if now < pending["dueAt"]:
        if not dry_run:
            offer_plan(pending, state)
        save_state(state)
        return "waiting-reset"
    if dry_run:
        save_state(state)
        return f'dry-run-due:{pending["threadId"]}'

    last_attempt = state.get("lastAttempt") or {}
    if last_attempt.get("key") == pending["key"] and now - last_attempt.get("at", 0) < RETRY_SECONDS:
        return "retry-backoff"
    state["lastAttempt"] = {"key": pending["key"], "at": now}
    save_state(state)

    result = subprocess.run(
        [find_codex(), "queue", "--thread", pending["threadId"], "--message", RESUME_MESSAGE],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode:
        log(f'queue failed thread={pending["threadId"]} code={result.returncode} {result.stderr[-300:]}')
        return "queue-failed"

    state = load_state()
    state.setdefault("sent", {})[pending["key"]] = now
    state["activeDispatch"] = pending
    state["pending"] = None
    save_state(state)
    log(f'queued thread={pending["threadId"]} turn={pending["turnId"]}')
    return "queued"


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
        assert candidate and candidate["turnId"] == "turn-1" and candidate["dueAt"] == now - 300

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
    parser.add_argument("--plan", metavar='THREAD_ID')
    args = parser.parse_args()
    try:
        if args.plan:
            plan_dialog(args.plan)
        elif args.status:
            print(json.dumps(load_state(), ensure_ascii=False, indent=2))
        elif args.self_test:
            self_test()
        else:
            try:
                SESSION_CACHE = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            result = run(dry_run=args.dry_run)
            state = load_state()
            if state.get("status") != result:
                log(result)
            state.update(status=result, lastCheckedAt=time.time())
            save_state(state)
            CACHE_PATH.write_text(json.dumps(SESSION_CACHE), encoding="utf-8")
            if sys.stdout is not None and not sys.stdout.closed:
                print(result)
    except Exception as error:
        log(f"error {type(error).__name__}: {error}")
        raise
