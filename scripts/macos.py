"""macOS integration; watcher business rules remain in quota_watcher."""
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

LABELS = ('com.codexquota.watcher', 'com.codexquota.backup')
AGENTS = Path.home() / 'Library/LaunchAgents'


def find_codex():
    override = os.environ.get('CODEX_EXECUTABLE')
    candidates = ([override] if override else []) + [
        shutil.which('codex'), '/Applications/Codex.app/Contents/Resources/codex',
        str(Path.home() / 'Applications/Codex.app/Contents/Resources/codex'),
        '/opt/homebrew/bin/codex', '/usr/local/bin/codex', str(Path.home() / '.local/bin/codex')]
    for item in candidates:
        if item and Path(item).is_file() and os.access(item, os.X_OK):return str(Path(item).absolute())
    raise FileNotFoundError('找不到 Codex CLI。请安装并登录 Codex；自定义路径可设置 CODEX_EXECUTABLE。')


def launchctl(*args, check=True):
    result = subprocess.run(['/bin/launchctl', *args], capture_output=True, text=True, timeout=20)
    if check and result.returncode:raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def agent_plist(label, interval, command, app_dir, executable):
    environment = {'PATH': os.pathsep.join(dict.fromkeys([
        str(Path(executable).parent), '/opt/homebrew/bin', '/usr/local/bin', '/usr/bin', '/bin',
        os.environ.get('PATH', '')])), 'CODEX_EXECUTABLE': executable}
    if os.environ.get('CODEX_HOME'):environment['CODEX_HOME'] = os.environ['CODEX_HOME']
    return {'Label': label, 'ProgramArguments': command, 'StartInterval': interval,
            'RunAtLoad': True, 'LimitLoadToSessionType': 'Aqua',
            'WorkingDirectory': str(app_dir), 'EnvironmentVariables': environment,
            'StandardOutPath': str(app_dir / (label + '.log')),
            'StandardErrorPath': str(app_dir / (label + '.log'))}


def install(w):
    executable = find_codex()
    w.codex_status.available(executable)  # Read-only login/API check, even at zero quota.
    if getattr(sys, 'frozen', False):
        bundle = Path(sys.executable).resolve().parents[2]
        if bundle.parent not in (Path('/Applications'), Path.home() / 'Applications'):
            raise RuntimeError('请先把应用移到“应用程序”文件夹，再启用监控。')
        command = [sys.executable, '--monitor']
    else:
        command = [sys.executable, str(Path(__file__).with_name('app.py').resolve()), '--monitor']
    w.APP_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS.mkdir(parents=True, exist_ok=True)
    domain = f'gui/{os.getuid()}'
    jobs = []
    for label, interval in zip(LABELS, (60, 300)):
        path = AGENTS / (label + '.plist')
        value = agent_plist(label, interval, command + (['--backup'] if interval == 300 else []),
                            w.APP_DIR, executable)
        loaded = launchctl('print', domain + '/' + label, check=False).returncode == 0
        if loaded and (not path.exists() or plistlib.loads(path.read_bytes()) != value):
            raise RuntimeError('已加载的监控配置不同。为保留正在执行的任务，请先暂停监控，注销并重新登录后再更新。')
        jobs.append((label, path, value, loaded))
    state = w.load_state()
    state.setdefault('monitoringSince', __import__('time').time())
    w.save_state(state)
    for label, path, value, loaded in jobs:
        if not loaded:
            temporary = path.with_suffix('.tmp')
            temporary.write_bytes(plistlib.dumps(value))
            temporary.chmod(0o600)
            temporary.replace(path)
            launchctl('enable', domain + '/' + label)
            launchctl('bootstrap', domain, str(path))
    (w.APP_DIR / 'paused.flag').unlink(missing_ok=True)
    return '已启用主备监控（每分钟 / 每五分钟），退出界面后继续运行。'


def pause(w):
    w.APP_DIR.mkdir(parents=True, exist_ok=True)
    (w.APP_DIR / 'paused.flag').touch()
    return '已暂停后续检查；正在执行的任务不受影响。'


def monitor_indicator(w):
    if (w.APP_DIR / 'paused.flag').exists():return ('● 监控已暂停', '#999999', False)
    try:
        enabled = all(launchctl('print', f'gui/{os.getuid()}/{label}', check=False).returncode == 0
                      for label in LABELS)
        return ('● 监控已启用（主备）', '#43c77a', True) if enabled else ('● 监控未全部启用', '#e5b454', False)
    except (OSError, subprocess.SubprocessError):
        return ('● 无法确认监控状态', '#e5b454', False)


def clipboard_files():
    from AppKit import NSPasteboard, NSURL
    urls = NSPasteboard.generalPasteboard().readObjectsForClasses_options_([NSURL], {}) or []
    return [str(url.path()) for url in urls if url.isFileURL()]


def work_area(x, y):
    from AppKit import NSScreen
    screens = list(NSScreen.screens())
    top = screens[0].frame().size.height
    areas = []
    for screen in screens:
        rect = screen.visibleFrame()
        areas.append((int(rect.origin.x), int(top - rect.origin.y - rect.size.height),
                      int(rect.origin.x + rect.size.width), int(top - rect.origin.y)))
    return min(areas, key=lambda r: max(r[0]-x, 0, x-r[2])**2 + max(r[1]-y, 0, y-r[3])**2)


def doctor(w):
    executable = find_codex()
    results = {'executable': executable}
    for name, args in [('version', ['--version']), ('resume', ['exec', 'resume', '--help']),
                       ('queue', ['queue', '--help'])]:
        result = subprocess.run([executable, *args], capture_output=True, text=True, timeout=20)
        results[name] = result.stdout.strip() if name == 'version' else result.returncode == 0
    with w.codex_status.connection(executable) as request:
        results['quotaAvailable'] = w.codex_status.quota_open(request('account/rateLimits/read', {}))
        threads = request('thread/list', {'limit': 1})['data']
        results['turnsAPI'] = 'no thread to verify'
        if threads:
            request('thread/turns/list', {'threadId': threads[0]['id'], 'limit': 1,
                                        'sortDirection': 'desc', 'itemsView': 'summary'})
            results['turnsAPI'] = True
    return results
