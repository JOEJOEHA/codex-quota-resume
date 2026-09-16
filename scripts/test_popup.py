import json,tempfile,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import quota_watcher as w
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory)
 pending={'threadId':'00000000-0000-0000-0000-000000000001','key':'visible-test'}
 with patch.object(w,'APP_DIR',root), patch.object(w,'LOG_PATH',root/'log'), patch.object(w,'save_state') as save:
  with patch.object(w.subprocess,'Popen',return_value=SimpleNamespace(poll=lambda:1)):
   state={};w.offer_plan(pending,state)
   assert not state.get('offeredPlans')
   save.assert_not_called()
  def launch(*args,**kwargs):
   assert kwargs['startupinfo'].wShowWindow==1 if os.name=='nt' else kwargs['startupinfo'] is None
   assert kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT']=='1'
   w.write_plan(root/'followups'/(pending['threadId']+'.ready.json'),{'key':'visible-test'})
   return SimpleNamespace(poll=lambda:None)
  with patch.object(w.subprocess,'Popen',side_effect=launch) as start:
   state={};w.offer_plan(pending,state)
   assert state['offeredPlans']==['visible-test']
   w.offer_plan(pending,state)
   assert start.call_count==1
print('POPUP_ACK_OK: show normally, fresh frozen process, no false success, dedupe after visible ack')
