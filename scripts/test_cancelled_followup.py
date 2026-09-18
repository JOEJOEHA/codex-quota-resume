"""Cancellation is persistent, including aborts between two monitor polls."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import quota_watcher as w


class CancellationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.session=self.folder/'session.jsonl'
        self.thread='00000000-0000-0000-0000-000000000001'
        self.active={'threadId':self.thread,'turnId':'old','path':str(self.session)}
        for p in (patch.object(w,'APP_DIR',self.folder),patch.object(w,'LOG_PATH',self.folder/'log'),
                  patch.object(w,'find_codex',return_value='mock'),patch.object(w.time,'time',return_value=100)):
            p.start();self.addCleanup(p.stop)
        self.plan=w.plan_path(self.thread)
        self.original={'status':'saved','text':'keep me','files':[],'images':[],
                       'sendRequested':True,'resumeSendAfter':90,'resumeAbortCount':0}
        w.write_plan(self.plan,self.original)
        self.events('task_started')

    def events(self,*kinds):
        self.session.write_text(''.join(json.dumps({'type':'event_msg','payload':
            {'type':kind,'turn_id':str(index)}})+'\n' for index,kind in enumerate(kinds)))

    def test_abort_then_new_turn_never_replays(self):
        self.events('task_started','turn_aborted','task_started')
        with patch.object(w,'queue_dispatch') as send:
            self.assertEqual(w.deliver_plan(self.active,False),'followup-cancelled')
            self.events('task_complete')
            self.assertEqual(w.deliver_plan(self.active,False),'followup-cancelled')
            self.assertEqual(w.scan_plans({},False),'followup-cancelled')
            send.assert_not_called()
        saved=json.loads(self.plan.read_text())
        self.assertEqual(saved['text'],'keep me')
        self.assertFalse(saved['sendRequested'])
        self.assertNotIn('resumeSendAfter',saved)
        w.request_plan_send(self.thread)
        self.assertEqual(json.loads(self.plan.read_text())['status'],'saved')
        with patch.object(w.codex_status,'available',return_value=True),patch.object(w,'dispatch',return_value=SimpleNamespace(returncode=0)) as send:
            self.assertEqual(w.deliver_plan(self.active,False),'followup-sent')
            send.assert_called_once()

    def test_cancel_before_deadline_and_dry_run(self):
        self.original['resumeSendAfter']=110
        w.write_plan(self.plan,self.original)
        self.events('turn_aborted')
        self.assertEqual(w.deliver_plan(self.active,True),'followup-cancelled')
        self.assertEqual(json.loads(self.plan.read_text()),self.original)
        self.assertEqual(w.deliver_plan(self.active,False),'followup-cancelled')

    def test_legacy_delayed_plan(self):
        self.original.pop('resumeAbortCount')
        w.write_plan(self.plan,self.original)
        self.events('turn_aborted')
        self.assertEqual(w.deliver_plan(self.active,False),'followup-cancelled')

    def test_cancellation_during_quota_lookup(self):
        def quota(*args):self.events('turn_aborted','task_started');return True
        with patch.object(w.codex_status,'available',side_effect=quota),patch.object(w,'queue_dispatch') as send:
            self.assertEqual(w.deliver_plan(self.active,False),'followup-cancelled')
            send.assert_not_called()

    def test_pause_during_quota_lookup(self):
        def quota(*args):(self.folder/'paused.flag').touch();return True
        with patch.object(w.codex_status,'available',side_effect=quota),patch.object(w,'queue_dispatch') as send:
            self.assertEqual(w.deliver_plan(self.active,False),'paused')
            send.assert_not_called()
        self.assertEqual(json.loads(self.plan.read_text()),self.original)

    def test_old_abort_does_not_cancel_new_resume(self):
        self.original['resumeAbortCount']=1
        w.write_plan(self.plan,self.original)
        self.events('turn_aborted','task_started')
        with patch.object(w.codex_status,'available',return_value=True),patch.object(w,'queue_dispatch',return_value=SimpleNamespace(returncode=0,queued=True)) as send:
            self.assertEqual(w.deliver_plan(self.active,False),'followup-queued')
            send.assert_called_once()

    def test_missing_or_truncated_evidence(self):
        self.original['resumeAbortCount']=1
        w.write_plan(self.plan,self.original)
        self.assertEqual(w.deliver_plan(self.active,False),'followup-waiting-evidence')
        self.session.write_text('{')
        self.assertEqual(w.deliver_plan(self.active,False),'followup-waiting-evidence')


if __name__=='__main__':unittest.main()
