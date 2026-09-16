"""Run a disposable local LaunchAgent; never load the user's monitor jobs."""
import os
import plistlib
import sys
import tempfile
import time
import uuid
from pathlib import Path
import macos

assert sys.platform == 'darwin'
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    for interval in (60,300):
        label='com.codexquota.smoketest.'+uuid.uuid4().hex
        target=f'gui/{os.getuid()}/{label}'
        marker=root/(label+'.started')
        path=root/(label+'.plist')
        command=[sys.executable,'-c','from pathlib import Path; import sys; Path(sys.argv[1]).touch()',str(marker)]
        path.write_bytes(plistlib.dumps(macos.agent_plist(label,interval,command,root,sys.executable)))
        macos.launchctl('bootstrap',f'gui/{os.getuid()}',str(path))
        try:
            for _ in range(50):
                if marker.exists():break
                time.sleep(.1)
            assert marker.exists(), 'LaunchAgent did not execute in the logged-in GUI domain'
            macos.launchctl('print',target)
        finally:
            macos.launchctl('bootout',target)
        assert macos.launchctl('print',target,check=False).returncode != 0
print('MACOS_LAUNCHD_OK: native load, background execution, main/backup interval configuration, cleanup')
