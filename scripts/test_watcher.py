import importlib.util,json,os,tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('w',Path(__file__).with_name('quota_watcher.py')); w=importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
with tempfile.TemporaryDirectory() as d:
 root=Path(d); now=2000000000
 with patch.multiple(w,APP_DIR=root,STATE_PATH=root/'state.json',SESSIONS_DIR=root,LOG_PATH=root/'log'):
  p=root/'rollout-00000000-0000-0000-0000-000000000001.jsonl'
  def write(turn,weekly=20):
   records=[{'payload':{'type':'task_started','turn_id':turn}},{'payload':{'type':'token_count','rate_limits':{'primary':{'used_percent':100,'resets_at':now-301},'secondary':{'used_percent':weekly,'resets_at':now+1000}}}},{'payload':{'type':'task_complete','turn_id':turn,'error':{'codex_error_info':'usage_limit_exceeded'}}}]
   p.write_text(''.join(json.dumps(r)+'\n' for r in records)); os.utime(p,(now-500+len(turn)+weekly,now-500+len(turn)+weekly))
  write('one',100)
  with patch.object(w.subprocess,'Popen'), patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as queue:
   assert w.run(now)=='waiting-reset'; queue.assert_not_called()
   write('one')
   assert w.run(now)=='queued'; assert queue.call_count==1
   assert w.run(now+1)=='waiting-start'; assert queue.call_count==1
   assert w.run(now+301)=='dispatch-unconfirmed'; assert queue.call_count==1
   write('second')
   assert w.run(now+302)=='queued'; assert queue.call_count==2
   with p.open('a') as f: f.write(json.dumps({'payload':{'type':'turn_aborted','turn_id':'second'}})+'\n')
   assert w.run(now+303)=='no-quota-stall'
   with patch.object(w,'parse_session',side_effect=AssertionError('cache miss')):
    assert w.run(now+304)=='no-quota-stall'
print('FLOW_TEST_OK: weekly wait, dispatch, dedupe, unconfirmed, second quota, cancel, cache')



with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 with patch.object(w,'APP_DIR',root):
  thread='00000000-0000-0000-0000-000000000001'
  p=root/'session.jsonl'; active={'threadId':thread,'turnId':'old','path':str(p)}
  pp=w.plan_path(thread)
  w.write_plan(pp,{'text':'后续需求：做一个测试报告','status':'saved'})
  def complete(text, error=None):
   p.write_text(json.dumps({'type':'event_msg','payload':{'type':'task_complete','turn_id':'new','last_agent_message':text,'error':error}}))
  with patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as send:
   complete('需要用户登录')
   assert w.deliver_plan(active,False)=='followup-waiting-completion'; send.assert_not_called()
   complete(w.COMPLETE_MARKER,{'code':'failure'})
   assert w.deliver_plan(active,False) is None; send.assert_not_called()
   complete('所有目标验收完成\n'+w.COMPLETE_MARKER)
   assert w.deliver_plan(active,True)=='followup-ready'; send.assert_not_called()
   assert w.deliver_plan(active,False)=='followup-sent'
   assert send.call_args.args[0][-1]=='后续需求：做一个测试报告'
   assert w.deliver_plan(active,False) is None; assert send.call_count==1
print('FOLLOWUP_TEST_OK: save, completion gate, error, dry-run, exact text, dedupe')
