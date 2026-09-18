"""Loaded agents tolerate launch-environment drift without restarting jobs."""
import copy,os,plistlib,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import macos as m
import quota_watcher as w

class CompatibilityTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  self.cli=self.root/'codex';self.cli.touch()
  self.job=m.agent_plist(m.LABELS[0],60,[str(self.root/'app'),'--monitor'],self.root,str(self.cli))
 def test_path_and_default_home(self):
  old=copy.deepcopy(self.job);new=copy.deepcopy(self.job)
  old['EnvironmentVariables'].update(PATH='/temporary/codex-runtime:/usr/bin',CODEX_HOME=str(Path.home()/'.codex'))
  new['EnvironmentVariables'].update(PATH='/usr/bin:/bin')
  new['EnvironmentVariables'].pop('CODEX_HOME',None)
  self.assertTrue(m.compatible_agent(old,new))
 def test_symlink_identity(self):
  link=self.root/'alias';link.symlink_to(self.cli)
  old=copy.deepcopy(self.job);new=copy.deepcopy(self.job)
  old['ProgramArguments'][0]=str(link);new['ProgramArguments'][0]=str(self.cli)
  old['EnvironmentVariables']['CODEX_EXECUTABLE']=str(link)
  self.assertTrue(m.compatible_agent(old,new))
 def test_real_changes_still_rejected(self):
  changes=[lambda j:j['ProgramArguments'].append('--backup'),
   lambda j:j['ProgramArguments'].__setitem__(0,str(self.root/'different-app')),
   lambda j:j['EnvironmentVariables'].__setitem__('CODEX_HOME',str(self.root/'other-account')),
   lambda j:j['EnvironmentVariables'].__setitem__('CODEX_EXECUTABLE',str(self.root/'other-cli')),
   lambda j:j.__setitem__('StartInterval',300),
   lambda j:j.__setitem__('WorkingDirectory',str(self.root/'other-data')),
   lambda j:j['EnvironmentVariables'].__setitem__('EXTRA_SETTING','value')]
  for change in changes:
   new=copy.deepcopy(self.job);change(new)
   self.assertFalse(m.compatible_agent(self.job,new))
 def test_relative_cli_keeps_path_significant(self):
  old=copy.deepcopy(self.job);old['EnvironmentVariables']['CODEX_EXECUTABLE']='codex'
  new=copy.deepcopy(old);new['EnvironmentVariables']['PATH']='different'
  self.assertFalse(m.compatible_agent(old,new))
 def test_repeat_install_preserves_jobs_and_state(self):
  with patch.multiple(w,APP_DIR=self.root,STATE_PATH=self.root/'state.json'),patch.object(m,'AGENTS',self.root/'agents'),patch.object(m,'find_codex',return_value=str(self.cli)),patch.object(w.codex_status,'available',return_value=True),patch.object(m,'launchctl',return_value=SimpleNamespace(returncode=1)) as ctl:
   m.install(w)
   state=w.load_state();state['sent']={'existing-task':123};w.save_state(state)
   snapshots={p:p.read_bytes() for p in m.AGENTS.glob('*.plist')}
   (self.root/'paused.flag').touch()
   ctl.return_value=SimpleNamespace(returncode=0);ctl.reset_mock()
   with patch.dict(os.environ,{'PATH':'/a/new/launch/environment'}):m.install(w)
   self.assertEqual(w.load_state(),state)
   self.assertFalse((self.root/'paused.flag').exists())
   for p,data in snapshots.items():self.assertEqual(p.read_bytes(),data)
   self.assertFalse(any(c.args[0] in ('bootstrap','bootout','kill') for c in ctl.call_args_list))
   p=next(iter(snapshots));changed=plistlib.loads(p.read_bytes());changed['StartInterval']=999;p.write_bytes(plistlib.dumps(changed))
   ctl.reset_mock()
   with self.assertRaises(RuntimeError):m.install(w)
   self.assertFalse(any(c.args[0] in ('enable','bootstrap','bootout','kill') for c in ctl.call_args_list))

if __name__=='__main__':unittest.main()
