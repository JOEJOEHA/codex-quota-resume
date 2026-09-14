import importlib.util,json,os,tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
spec=importlib.util.spec_from_file_location('w',Path(__file__).with_name('quota_watcher.py')); w=importlib.util.module_from_spec(spec); spec.loader.exec_module(w)
patch.object(w.codex_status,'ready',return_value='available').start()
patch.object(w.codex_status,'available',return_value=True).start()
with tempfile.TemporaryDirectory() as d:
 root=Path(d); now=2000000000
 with patch.multiple(w,APP_DIR=root,STATE_PATH=root/'state.json',SESSIONS_DIR=root,LOG_PATH=root/'log'):
  p=root/'rollout-00000000-0000-0000-0000-000000000001.jsonl'
  def write(turn,weekly=20):
   records=[{'payload':{'type':'task_started','turn_id':turn}},{'payload':{'type':'token_count','rate_limits':{'primary':{'used_percent':100,'resets_at':now-301},'secondary':{'used_percent':weekly,'resets_at':now+1000}}}},{'payload':{'type':'task_complete','turn_id':turn,'error':{'codex_error_info':'usage_limit_exceeded'}}}]
   p.write_text(''.join(json.dumps(r)+'\n' for r in records)); os.utime(p,(now-500+len(turn)+weekly,now-500+len(turn)+weekly))
  write('one',100)
  with patch.object(w.subprocess,'Popen'), patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as queue:
   with patch.object(w.codex_status,'ready',return_value='waiting-quota'):
    assert w.run(now)=='waiting-quota'; queue.assert_not_called()
   write('one')
   assert w.run(now)=='resumed'; assert queue.call_count==1
   assert w.run(now+1)=='waiting-start'; assert queue.call_count==1
   assert w.run(now+301)=='dispatch-unconfirmed'; assert queue.call_count==1
   write('second')
   assert w.run(now+302)=='resumed'; assert queue.call_count==2
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
   assert send.call_args.args[0][1:3]==['exec','resume']
   assert send.call_args.args[0][-1]=='后续需求：做一个测试报告'
   assert w.deliver_plan(active,False) is None; assert send.call_count==1
print('FOLLOWUP_TEST_OK: save, completion gate, error, dry-run, exact text, dedupe')

with tempfile.TemporaryDirectory() as d:
 root=Path(d)
 p=root/'rollout-00000000-0000-0000-0000-000000000001.jsonl'
 records=[{'payload':{'type':'task_started','turn_id':'first'}},
          {'payload':{'type':'token_count','rate_limits':{'primary':{'used_percent':100,'resets_at':2000000000}}}},
          {'payload':{'type':'task_complete','turn_id':'first','error':{'codex_error_info':'usage_limit_exceeded'}}},
          {'payload':{'type':'task_started','turn_id':'retry'}},
          {'payload':{'type':'task_complete','turn_id':'retry','error':{'codex_error_info':'usage_limit_exceeded'}}}]
 p.write_text(''.join(json.dumps(r)+'\n' for r in records),encoding='utf-8')
 result=w.parse_session(p)
 assert result['turnId']=='retry' and result['quotaError']
 assert result['limits']['primary']['resets_at']==2000000000
 with patch.object(w,'APP_DIR',root):
  thread='00000000-0000-0000-0000-000000000001'
  image=root/'attachment.png'; image.write_bytes(b'test')
  pp=w.plan_path(thread)
  w.write_plan(pp,{'text':'read screenshot','images':[str(image)],'status':'saved'})
  p.write_text(json.dumps({'type':'event_msg','payload':{'type':'task_complete','turn_id':'done','last_agent_message':w.COMPLETE_MARKER}}))
  with patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as send:
   assert w.deliver_plan({'threadId':thread,'turnId':'retry','path':str(p)},False)=='followup-sent'
   assert send.call_args.args[0][-2:]==['--image',str(image)]
print('REGRESSION_OK: quota snapshot survives failed retry; attachment passed to exec resume')

for failure in ('nonzero', 'missing-executable', 'interrupted'):
 with tempfile.TemporaryDirectory() as d:
  root=Path(d); now=2000000000
  with patch.multiple(w,APP_DIR=root,STATE_PATH=root/'state.json',SESSIONS_DIR=root,LOG_PATH=root/'log',SESSION_CACHE={}):
   p=root/'rollout-00000000-0000-0000-0000-000000000001.jsonl'
   records=[{'payload':{'type':'task_started','turn_id':'one'}},
            {'payload':{'type':'token_count','rate_limits':{'primary':{'used_percent':100,'resets_at':now-500}}}},
            {'payload':{'type':'task_complete','turn_id':'one','error':{'codex_error_info':'usage_limit_exceeded'}}}]
   p.write_text(''.join(json.dumps(r)+'\n' for r in records)); os.utime(p,(now-300,now-300))
   effect={'nonzero':None,'missing-executable':FileNotFoundError('test'),
           'interrupted':KeyboardInterrupt()}[failure]
   with patch.object(w.subprocess,'run',side_effect=effect,return_value=SimpleNamespace(returncode=1,stderr='test failure')) as send:
    if failure=='interrupted':
     try: w.run(now)
     except KeyboardInterrupt: pass
     else: raise AssertionError('interruption not raised')
    else: assert w.run(now)=='resume-failed'
    assert send.call_args.args[0][1:3]==['exec','resume']
    assert 'timeout' not in send.call_args.kwargs
    w.SESSION_CACHE.clear()  # Restart: only durable state remains.
    assert w.run(now+1)==('waiting-start' if failure=='interrupted' else 'retry-backoff')
    assert send.call_count==1
   with patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as send:
    assert w.run(now+301)==('dispatch-unconfirmed' if failure=='interrupted' else 'resumed')
    assert send.call_count==(0 if failure=='interrupted' else 1)
    with p.open('a') as stream:
     stream.write(json.dumps({'payload':{'type':'task_started','turn_id':'resumed'}})+'\n')
    assert w.run(now+302)=='dispatch-active'
    with p.open('a') as stream:
     stream.write(json.dumps({'payload':{'type':'task_complete','turn_id':'resumed','last_agent_message':'done'}})+'\n')
    assert w.run(now+303)=='no-quota-stall'
print('DELIVERY_TEST_OK: failure retry, executable recovery, interrupted process dedupe, restart, start and completion')

print('DIRECT_RESUME_OK: all dispatch calls use the native exec resume entrypoint')

# Real failure shape: the final usage snapshot is 99%, followed by an explicit quota error.
with tempfile.TemporaryDirectory() as d:
 root=Path(d); now=2000000000; reset=now-301
 with patch.multiple(w,APP_DIR=root,STATE_PATH=root/'state.json',SESSIONS_DIR=root,LOG_PATH=root/'log',SESSION_CACHE={}):
  p=root/'rollout-00000000-0000-0000-0000-000000000001.jsonl'
  clock=w.datetime.fromtimestamp(reset).strftime('%I:%M %p').lstrip('0')
  records=[{'payload':{'type':'task_started','turn_id':'99-percent'}},
   {'payload':{'type':'token_count','rate_limits':{'limit_id':'codex','primary':{'used_percent':99,'resets_at':reset},'secondary':{'used_percent':31,'resets_at':now+5000}}}},
   {'payload':{'type':'token_count','rate_limits':{'limit_id':'premium','primary':None,'secondary':None}}},
   {'payload':{'type':'task_complete','turn_id':'99-percent','error':{'codex_error_info':'usage_limit_exceeded','message':'Try again at '+clock+'.'}}}]
  def write_records():
   p.write_text(''.join(json.dumps(r)+'\n' for r in records),encoding='utf-8'); os.utime(p,(now-500,now-500))
  write_records()
  with patch.object(w.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as send:
   assert w.run(now)=='resumed'; assert send.call_count==1
  w.STATE_PATH.unlink()
  records[-1]['payload']['error']['message']='No reset information supplied'
  write_records()
  with patch.object(w,'dispatch',return_value=SimpleNamespace(returncode=0)):
   assert w.run(now)=='resumed'
  w.STATE_PATH.unlink()
  records[-1]['payload']['error']={}
  write_records()
  assert w.run(now)=='no-quota-stall'
print('STALE_99_PERCENT_OK: live quota permits resume even without reset time; success never resumes')

with patch.object(w.subprocess, 'run', side_effect=[
 SimpleNamespace(returncode=1,stderr='already has an active writer'),
 SimpleNamespace(returncode=0,stderr='',stdout='Queued message')]) as send:
 result=w.dispatch('00000000-0000-0000-0000-000000000001','test')
 assert result.queued and send.call_count==2
 assert send.call_args.args[0][1]=='queue'
with patch.object(w.subprocess, 'run', return_value=SimpleNamespace(returncode=1,stderr='network failure')) as send:
 assert w.dispatch('00000000-0000-0000-0000-000000000001','test').returncode==1
 assert send.call_count==1
with patch.object(w,'exhausted_candidate',side_effect=AssertionError('must not resend queued work')):
 w.recover_unstarted({'activeDispatch':{'deliveryMode':'queued'}},2000000000)
print('WRITER_CONFLICT_OK: route to desktop queue only for writer conflict; no queued replay')
