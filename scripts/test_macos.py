"""Offline integration contracts; never install jobs or contact real Codex."""
import os
import plistlib
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import macos as m
import quota_watcher as w

with tempfile.TemporaryDirectory() as folder:
    root = Path(folder)
    exe = root/'CLI with spaces'
    exe.write_text('test')
    exe.chmod(0o700)
    with patch.dict(os.environ, {'CODEX_EXECUTABLE': str(exe)}):
        assert m.find_codex() == str(exe)
    job = m.agent_plist(m.LABELS[0], 60, ['/App Folder/app', '--monitor'], root, str(exe))
    assert plistlib.loads(plistlib.dumps(job)) == job
    assert job['ProgramArguments'] == ['/App Folder/app', '--monitor']
    assert job['StartInterval'] == 60 and 'KeepAlive' not in job
    with patch.multiple(w,APP_DIR=root,STATE_PATH=root/'state.json',LOG_PATH=root/'log',CACHE_PATH=root/'cache'):
        with patch.object(m,'launchctl',return_value=SimpleNamespace(returncode=0)) as ctl:
            with patch.object(m.os,'getuid',return_value=501,create=True):
                assert m.monitor_indicator(w)[2]
                m.pause(w)
                assert not m.monitor_indicator(w)[2]
                with patch.object(w,'run',side_effect=AssertionError('paused job must not query or send')):
                    assert w.run_once() == 'paused'
                assert not any(c.args[0] in ('bootout','kill') for c in ctl.call_args_list)
        (root/'paused.flag').unlink()
        with patch.object(m,'AGENTS',root/'agents'),patch.object(m,'find_codex',return_value=str(exe)), \
             patch.object(m.os,'getuid',return_value=501,create=True),patch.object(w.codex_status,'available',return_value=False), \
             patch.object(m,'launchctl',return_value=SimpleNamespace(returncode=1)) as ctl:
            m.install(w)
            assert w.load_state()['monitoringSince'] > 0
            for label,interval in zip(m.LABELS,(60,300)):
                assert plistlib.loads((m.AGENTS/(label+'.plist')).read_bytes())['StartInterval']==interval
            assert sum(c.args[0]=='bootstrap' for c in ctl.call_args_list)==2
            since=w.load_state()['monitoringSince']
            ctl.reset_mock()
            ctl.return_value=SimpleNamespace(returncode=0)
            m.install(w)
            assert w.load_state()['monitoringSince']==since
            assert not any(c.args[0] in ('bootstrap','bootout','kill') for c in ctl.call_args_list)
print('MACOS_CONTRACTS_OK: paths, plist, main/backup intervals, pause gate, non-destructive install')
