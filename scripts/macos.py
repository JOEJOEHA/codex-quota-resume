"""macOS integration; watcher business rules remain in quota_watcher."""
import os
import plistlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

LABELS = ('com.codexquota.watcher', 'com.codexquota.backup')
AGENTS = Path.home() / 'Library/LaunchAgents'


def find_codex():
    override = os.environ.get('CODEX_EXECUTABLE')
    candidates = ([override] if override else []) + [
        shutil.which('codex'), '/Applications/Codex.app/Contents/Resources/codex',
        str(Path.home() / 'Applications/Codex.app/Contents/Resources/codex'),
        '/Applications/ChatGPT.app/Contents/Resources/codex',
        str(Path.home() / 'Applications/ChatGPT.app/Contents/Resources/codex'),
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


def compatible_agent(existing, desired):
    """Compare effective configuration without rewriting a loaded job.

    PATH is inherited from the launching app and can contain temporary entries.
    The CLI and watcher are absolute paths; retain the loaded job's PATH when
    those identities and all other settings still match.
    """
    def normalized(value):
        result=dict(value)
        environment=dict(result.get('EnvironmentVariables',{}))
        # Only ignore PATH when both jobs explicitly select an absolute CLI.
        cli=environment.get('CODEX_EXECUTABLE','')
        if Path(cli).is_absolute():
            environment.pop('PATH',None)
            environment['CODEX_EXECUTABLE']=str(Path(cli).resolve())
        home=environment.get('CODEX_HOME') or str(Path.home()/'.codex')
        environment['CODEX_HOME']=str(Path(home).expanduser().resolve())
        result['EnvironmentVariables']=environment
        args=list(result.get('ProgramArguments',[]))
        if args and Path(args[0]).is_absolute():args[0]=str(Path(args[0]).resolve())
        result['ProgramArguments']=args
        for key in ('WorkingDirectory','StandardOutPath','StandardErrorPath'):
            if result.get(key):result[key]=str(Path(result[key]).resolve())
        return result
    return normalized(existing)==normalized(desired)


def install(w):
    executable = find_codex()
    w.codex_status.available(executable)  # Read-only login/API check, even at zero quota.
    if getattr(sys, 'frozen', False):
        bundle = Path(sys.executable).resolve().parents[2]
        if bundle.parent not in (Path('/Applications'), Path.home() / 'Applications'):
            raise RuntimeError('请先把应用移到“应用程序”文件夹，再启用监控。')
        command = [str(Path(sys.executable).resolve()), '--monitor']
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
        if loaded and (not path.exists() or not compatible_agent(plistlib.loads(path.read_bytes()), value)):
            raise RuntimeError('已加载的监控路径或环境不同。请使用原安装路径；更换路径需在确认任务结束后手动重新注册 LaunchAgent。当前监控未停止。')
        jobs.append((label, path, value, loaded))
    # Installing/updating must not overwrite an active watcher's send records.
    with (w.APP_DIR / 'monitor.lock').open('a+b') as lock:
        if lock.seek(0, 2) == 0:lock.write(b'0');lock.flush()
        lock.seek(0)
        try:w.lock_monitor(lock)
        except OSError:raise RuntimeError('监控正在处理任务，请等本次执行结束后再更新。')
        state = w.load_state()
        state.setdefault('monitoringSince', time.time())
        w.save_state(state)
    for label, path, value, loaded in jobs:
        launchctl('enable', domain + '/' + label)
        if not loaded:
            temporary = path.with_suffix('.tmp')
            temporary.write_bytes(plistlib.dumps(value))
            temporary.chmod(0o600)
            temporary.replace(path)
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


def repaint_on_layout(root):
    """Invalidate Cocoa's whole backing view after transparent Tk windows relayout."""
    from AppKit import NSApplication
    timer=[None]
    def repaint():
        timer[0]=None
        for window in NSApplication.sharedApplication().windows():
            view=window.contentView()
            if view is not None:view.setNeedsDisplay_(True)
    def schedule(event=None):
        if timer[0] is None:timer[0]=root.after_idle(repaint)
    def close(event):
        if event.widget==root and timer[0] is not None:
            root.after_cancel(timer[0]);timer[0]=None
    root.bind('<Configure>',schedule,add='+')
    root.bind('<Map>',schedule,add='+')
    root.bind('<Destroy>',close,add='+')
    schedule()


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
    """Keep partial read-only diagnostics; never expose failed commands' output."""
    results = {name: None for name in ('executable', 'version', 'resume', 'queue',
                                       'quotaAvailable', 'turnsAPI')}
    results.update(ok=False, errors={})

    def failed(name, message, error=None, **details):
        results['errors'][name] = {'message': message, **details}
        if error is not None:results['errors'][name]['type'] = type(error).__name__

    try:
        executable = find_codex()
        results['executable'] = executable
    except Exception as error:
        failed('executable', 'Codex CLI could not be located. Install Codex or set CODEX_EXECUTABLE.', error)
        return results
    for name, args in [('version', ['--version']), ('resume', ['exec', 'resume', '--help']),
                       ('queue', ['queue', '--help'])]:
        try:
            result = subprocess.run([executable, *args], capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=20)
            if result.returncode:
                failed(name, 'Codex command exited unsuccessfully; capability could not be verified.',
                       returncode=result.returncode)
            elif name == 'version' and not result.stdout.strip():
                failed(name, 'Codex did not return a version string.')
            else:
                results[name] = result.stdout.strip() if name == 'version' else True
        except subprocess.TimeoutExpired as error:
            failed(name, 'Codex command timed out after 20 seconds.', error)
        except Exception as error:
            failed(name, 'Codex command could not be executed.', error)
    try:
        with w.codex_status.connection(executable) as request:
            try:
                results['quotaAvailable'] = w.codex_status.quota_open(request('account/rateLimits/read', {}))
            except Exception as error:
                failed('quotaAvailable', 'Live account quota could not be read.', error,
                       method='account/rateLimits/read')
            method = 'thread/list'
            try:
                threads = request(method, {'limit': 1})['data']
                if not threads:
                    results['turnsAPI'] = 'no thread to verify'
                    failed('turnsAPI', 'No existing thread is available to verify the turns API.')
                else:
                    method = 'thread/turns/list'
                    request(method, {'threadId': threads[0]['id'], 'limit': 1,
                                     'sortDirection': 'desc', 'itemsView': 'summary'})
                    results['turnsAPI'] = True
            except Exception as error:
                failed('turnsAPI', 'The turns API could not be verified.', error, method=method)
    except Exception as error:
        failed('appServer', 'Codex App Server connection failed; check local execution permissions and Codex login.', error)
    results['ok'] = not results['errors']
    return results
