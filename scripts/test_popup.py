import tempfile,time
from pathlib import Path
from unittest.mock import patch
import quota_watcher as w
with tempfile.TemporaryDirectory() as directory,patch.object(w,'APP_DIR',Path(directory)),patch.object(w.subprocess,'Popen') as start:
    pending={'threadId':'00000000-0000-0000-0000-000000000001','key':'one','quotaError':True}
    w.offer_plan(dict(pending,quotaError=False),{})
    start.assert_not_called()
    heartbeat=Path(directory)/'ui-heartbeat';heartbeat.touch()
    w.offer_plan(pending,{})
    start.assert_not_called()
    assert w.claim_popup(pending)
    assert w.claim_popup(pending) is None
    heartbeat.unlink()
    w.offer_plan(dict(pending,key='two'),{})
    w.offer_plan(dict(pending,key='two'),{})
    assert start.call_count==1
    assert '--plan' in start.call_args.args[0]
print('QUOTA_POPUP_OK: explicit error, GUI reuse, one per interruption, background fallback')
