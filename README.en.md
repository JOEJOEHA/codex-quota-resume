# Codex Quota Resume · Automatic Task Resumption

[简体中文](README.md) | [English](README.en.md)

A local desktop utility that resumes unfinished Codex tasks interrupted by explicit quota errors once live quota is available. **Windows Beta / macOS Developer Preview.** This is an independent MIT-licensed community project, not an official OpenAI product.

[Downloads](https://github.com/JOEJOEHA/codex-quota-resume/releases/latest) · [Contributing](CONTRIBUTING.md) · [macOS Codex handoff prompt (中文 / English)](docs/macos-handoff.md)

## Downloads and status

| Platform | Release asset | Status |
|---|---|---|
| Windows 10 / 11 | `CodexQuotaResume.exe` | v3.0.0-beta.15; includes Python, Tkinter and Pillow |
| Apple Silicon: M1 / M2 / M3 and other M-series Macs | `CodexQuotaResume-macOS-arm64-preview.zip` | Development preview |
| Intel Mac | `CodexQuotaResume-macOS-x86_64-preview.zip` | Development preview |

Download from [Releases](https://github.com/JOEJOEHA/codex-quota-resume/releases/latest); verify with `SHA256SUMS.txt`. The macOS builds passed CI on macOS 14 arm64 and macOS 15 Intel. They are ad-hoc signed, without Developer ID signing or Apple notarization. Target-device testing and a real quota-exhaustion/recovery cycle are still pending; individual M-series models have not all been tested. Do not disable system security to run a build.

**macOS development source is on [`macos-port`](https://github.com/JOEJOEHA/codex-quota-resume/tree/macos-port), with [draft PR #1](https://github.com/JOEJOEHA/codex-quota-resume/pull/1). `main` does not yet contain the port.** Read the [handoff](docs/macos-handoff.md) before starting.

## Behavior

- The primary watcher checks every 60 seconds; an independent backup checks every 300 seconds. Both share a process lock and send records.
- Only explicit quota interruptions of unfinished work qualify. Zero remaining quota alone, normal completion and ordinary network errors do not trigger resumption. Live quota is checked before sending.
- `codex exec resume` continues the original session. Only a desktop writer conflict triggers a `codex queue` fallback. Queue acceptance is not task completion; subsequent state is still checked. No new session, model change or quota purchase is initiated.
- Save follow-up text, images and ordinary files without sending immediately. Follow-ups require completion of the original task resumed by the watcher, the `[QUOTA_RESUME_GOAL_COMPLETE]` marker and available quota. A normal turn end, cancellation or request for user input is insufficient.
- Attachments are copied to local storage. Images have no fixed six-image limit; previews scroll horizontally. Click an image to remove it; double-click a file or press Delete to remove it.
- Dark rounded main/composer windows are 430 × 535. The expanded editor is 760 × 620 and returns its text on close. A saved follow-up flag flashes red/green five times, remains red until handed to Codex and is restored after restart.
- Composers show task names, reuse open drafts in the same process, and sit beside the main window. Closing/minimizing the main window leaves a tray/menu-bar icon. Exiting the interface does not stop monitoring or silently discard open drafts.

Monitoring makes no model calls. Resumed work and follow-ups consume normal Codex quota.

“保存后续任务” (Save Follow-up) keeps the completion gates above. “现在发送 ↑” (Send Now) explicitly requests a new instruction on the next monitor check once the session has ended normally and live quota is available; this explicit action does not require a prior quota interruption or completion marker. Both watchers scan saved plans independently of the current resume record and expose waiting reasons. If the desktop owns the session and the CLI explicitly rejects queued image attachments, the original session receives the copied images' local paths with the text so it can open them. Queue acceptance is tracked separately from observed startup and is never retried blindly.

## Windows installation and controls

Run the EXE and click **启用 / 更新监控 (Enable / Update Monitoring)**. A compatible signed-in Codex CLI is required, including `exec resume`, `app-server --stdio`, `account/rateLimits/read` and the experimental `thread/turns/list` interface.

The app installs under `%LOCALAPPDATA%\CodexQuotaWatcher`, creates a desktop shortcut and uses scheduled tasks `Codex Quota Resume Watcher` and `Codex Quota Resume Backup`. Keep the computer on, the user signed in and the network available. By default, only quota interruptions occurring after monitoring was enabled are handled.

For source installation, use Python 3.11+ with Tkinter and run in PowerShell:

```powershell
python -m pip install -r requirements.txt
& .\scripts\install_windows.ps1
& .\scripts\manage_windows.ps1 status
# Other commands: pause, resume, uninstall
```

Follow your device's execution policy. Pausing prevents subsequent checks but does not terminate running work. Uninstall preserves local follow-ups, attachments and records. Use both monitoring layers consistently.

`Ctrl+V` pastes screenshots; `Ctrl+Enter` saves. The screenshot button opens the Windows capture tool. “+ 添加 → 添加文件” adds ordinary files. The tray icon restores the main window; its menu opens or exits the interface.

An optional source Skill can be installed by placing the repository in your Codex skills directory as `codex-quota-resume`, with `SKILL.md` at that directory's root. Copying the Skill alone does not enable monitoring.

## macOS development

Start from `macos-port` as described in the [handoff prompt](docs/macos-handoff.md). On a Mac, use Python 3.13 with Tk (for example, the python.org distribution):

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt pyinstaller
python scripts/app.py --doctor
python scripts/build_macos.py
```

The read-only doctor checks CLI/help, quota and task interfaces without sending work. `CODEX_EXECUTABLE` can select the CLI; otherwise the app checks PATH, Codex.app, Homebrew and `~/.local/bin`. A custom `CODEX_HOME` is retained in the LaunchAgent environment. With no task history, the doctor cannot verify turn queries.

The build produces `dist/CodexQuotaResume.app` and an architecture-specific ZIP/checksum. Place the app in `/Applications` or `~/Applications`. Enable monitoring through the app after checking compatibility. Data lives in `~/Library/Application Support/CodexQuotaWatcher`; current-user LaunchAgents are `com.codexquota.watcher` and `com.codexquota.backup`. Sleeping Macs do not guarantee scheduled checks. Keep the same installation path for updates; conflicting loaded configurations are not overwritten.

Menu-bar left-click restores the window; right-click opens the menu. `⌘V` pastes images/Finder files, `⌘Enter` saves, and capture uses the system screenshot tool. Screen-recording permission may be required. Native callbacks enqueue actions for Tk's main loop. See [macOS build and acceptance details (中文)](https://github.com/JOEJOEHA/codex-quota-resume/blob/macos-port/docs/macos.md) and the English handoff for remaining tests.

## Development checks

```sh
python scripts/quota_watcher.py --self-test
python scripts/test_watcher.py
python scripts/test_backup.py
python scripts/test_live_status.py
python scripts/test_popup.py
python scripts/test_app.py
```

These use temporary data and simulated responses. For macOS, also follow the native UI, locking, LaunchAgent and packaging checks in `.github/workflows/macos.yml` on `macos-port`. CI does not have a signed-in personal Codex account and cannot prove real quota recovery. Windows builds use `scripts/build_windows.ps1` after installing PyInstaller.

## Data and limits

The app reads local Codex logs, local App Server state and live quota using the existing Codex login. It does not read/upload login tokens, redeem resets or purchase quota. Saved content remains local until it is sent through Codex's normal service flow. Never commit local credentials, logs, task content or attachments; redact reports.

Network outages, expired login, required approvals, API changes and hung processes can prevent recovery. Backup monitoring still shares the OS, Python, Codex and network. When startup cannot be confirmed, avoiding duplicate execution takes priority. No guaranteed recovery is promised.
