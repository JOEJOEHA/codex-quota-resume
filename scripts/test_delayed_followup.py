"""Delayed delivery works for queued and long-running resumes, without replay."""
import json,tempfile,threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import quota_watcher as w
for long_running in (False,True):
 with tempfile.TemporaryDirectory() as directory:
  folder=Path(directory);session=folder/'session.jsonl';clock=[100.0];delivered=threading.Event()
  pending={'threadId':'00000000-0000-0000-0000-000000000001','turnId':'old','path':str(session)}
  def record(turn):session.write_text(json.dumps({'type':'event_msg','payload':{'type':'task_started','turn_id':turn}})+'\n')
  record('old')
  def resume(*args,**kwargs):
   if long_running:
    record('resumed')
    assert delivered.wait(3),'Follow-up must queue before exec resume returns'
   return SimpleNamespace(returncode=0,queued=not long_running)
  def queue(*args,**kwargs):
   assert clock[0]>=110
   delivered.set();return SimpleNamespace(returncode=0,queued=True)
  def sleep(seconds):clock[0]+=seconds
  with patch.object(w,'APP_DIR',folder),patch.object(w,'LOG_PATH',folder/'log'),patch.object(w.time,'time',side_effect=lambda:clock[0]),patch.object(w.time,'sleep',side_effect=sleep),patch.object(w.codex_status,'available',return_value=True),patch.object(w,'find_codex',return_value='codex'),patch.object(w,'dispatch',side_effect=resume),patch.object(w,'queue_dispatch',side_effect=queue) as send:
   w.write_plan(w.plan_path(pending['threadId']),{'status':'saved','text':'followup','images':[],'files':[]})
   assert w.dispatch_resume(pending).returncode==0
   assert send.call_count==1
   assert w.deliver_plan(pending,False)=='followup-queued'
   assert send.call_count==1
   saved=json.loads(w.plan_path(pending['threadId']).read_text())
   assert saved['resumeSendAfter']==110 and saved['sendRequested']
   saved['status']='saved';w.write_plan(w.plan_path(pending['threadId']),saved)
   clock[0]=109;assert w.deliver_plan(pending,False)=='followup-waiting-delay'
   clock[0]=111
   with patch.object(w.codex_status,'available',return_value=False):
    assert w.deliver_plan(pending,False)=='followup-waiting-quota'
   assert send.call_count==1
print('DELAYED_FOLLOWUP_OK: ten seconds, busy thread, quota gate, restart state, no replay')
