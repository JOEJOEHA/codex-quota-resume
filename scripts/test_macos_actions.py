"""Main-window dispatch, pause/resume, GitHub and quit wiring; no real Codex."""
import json
import tempfile
import time
import tkinter as tk
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
import app

thread='00000000-0000-0000-0000-000000000001'
errors=[]
original=tk.Tk.mainloop
@contextmanager
def connection(*args):yield lambda *args:{'data':[{'id':thread,'name':'Action test'}]}
def walk(widget):
    yield widget
    for child in widget.winfo_children():yield from walk(child)
def button(root,text):return next(w for w in walk(root) if isinstance(w,tk.Button) and w.cget('text')==text)
def wait(root,predicate):
    deadline=time.monotonic()+5
    while not predicate() and time.monotonic()<deadline:
        root.update();time.sleep(.02)
    assert predicate()
def resume():
    (app.w.APP_DIR/'paused.flag').unlink(missing_ok=True)
    return 'RESUME_COMPLETE'
def loop(root):
    root.report_callback_exception=lambda kind,error,tb:errors.append(error)
    def check():
        try:
            assert button(root,'编辑后续任务').winfo_viewable()
            button(root,'请求发送').invoke()
            wait(root,lambda:any(isinstance(w,tk.Label) and w.cget('text')=='SEND_COMPLETE' for w in walk(root)))
            sender.assert_called_once_with(thread)
            button(root,'GitHub').invoke()
            opened.assert_called_once_with('https://github.com/joejoeha/codex-quota-resume')
            button(root,'暂停监控').invoke()
            wait(root,lambda:any(isinstance(w,tk.Label) and w.cget('text')=='已暂停后续检查；正在执行的任务不受影响。' for w in walk(root)))
            assert (app.w.APP_DIR/'paused.flag').exists()
            wait(root,lambda:any(isinstance(w,tk.Button) and w.cget('text')=='恢复监控' for w in walk(root)))
            button(root,'恢复监控').invoke()
            wait(root,lambda:any(isinstance(w,tk.Label) and w.cget('text')=='RESUME_COMPLETE' for w in walk(root)))
            installer.assert_called_once()
            assert not (app.w.APP_DIR/'paused.flag').exists()
            root.withdraw();root.tray.restore();root.update()
            assert root.winfo_viewable()
            root.tray.target.quit_(None)
            root.tray.poll()
            assert (app.w.APP_DIR/'paused.flag').exists()
        except BaseException as error:
            errors.append(error)
            root.tray.close();root.destroy()
    root.after(2400,check)
    original(root)
with tempfile.TemporaryDirectory() as folder:
    with patch.multiple(app.w,APP_DIR=Path(folder),STATE_PATH=Path(folder)/'state.json'), \
         patch.object(app.w.codex_status,'connection',connection),patch.object(app.w,'find_codex',return_value='mock'), \
         patch.object(app.w,'latest_candidate',return_value=None), \
         patch.object(app,'monitor_indicator',side_effect=lambda:('test','#43c77a',not (app.w.APP_DIR/'paused.flag').exists())), \
         patch.object(app.w,'request_plan_send',return_value='SEND_COMPLETE') as sender, \
         patch.object(app,'install',side_effect=resume) as installer, \
         patch.object(app.webbrowser,'open') as opened,patch.object(tk.Tk,'mainloop',loop):
        path=app.w.plan_path(thread);path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'status':'saved','text':'Follow-up','threadId':thread}))
        app.show()
assert not errors,errors
print('MACOS_ACTIONS_OK: saved dispatch, GitHub, pause/resume, restore, quit pauses future checks')
