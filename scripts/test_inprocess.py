"""Exercise the real compose button without starting Codex or child processes."""
import ctypes
import json
import os
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from contextlib import contextmanager
from PIL import Image
import app
import plan_dialog
from window_ui import window_handle,minimize,TaskPicker

thread='00000000-0000-0000-0000-000000000001'
@contextmanager
def connection(*args):
    yield lambda *args:{'data':[{'id':thread,'name':'Integration task'},{'id':'00000000-0000-0000-0000-000000000002','name':'Other task'}]}
def walk(widget):
    yield widget
    for child in widget.winfo_children():yield from walk(child)
def button(widget,text):
    return next(w for w in walk(widget) if isinstance(w,tk.Button) and w.cget('text')==text)
original=tk.Tk.mainloop
errors=[]
def loop(root,*args,**kwargs):
    root.report_callback_exception=lambda kind,error,tb:errors.append(error)
    def check():
        try:
            started=time.perf_counter()
            button(root,'打开需求输入框').invoke();root.update()
            dialogs=[w for w in root.winfo_children() if isinstance(w,tk.Toplevel)]
            assert len(dialogs)==1
            dialog=dialogs[0]
            elapsed=time.perf_counter()-started
            assert dialog.winfo_viewable() and dialog.tk is root.tk
            pid=ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(window_handle(dialog),ctypes.byref(pid))
            assert pid.value==os.getpid()
            button(root,'打开需求输入框').invoke();root.update()
            assert len([w for w in root.winfo_children() if isinstance(w,tk.Toplevel)])==1
            assert not launch.called,'Opening a composer must not spawn a process'
            picker=next(w for w in walk(root) if isinstance(w,TaskPicker))
            picker.current(1);button(root,'打开需求输入框').invoke();root.update()
            others=[w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and w!=dialog]
            assert len(others)==1 and others[0].tk is root.tk
            button(others[0],'×').invoke();root.update()
            assert dialog.winfo_exists()
            picker.current(0)
            editor=next(w for w in walk(dialog) if isinstance(w,tk.Text))
            editor.insert('1.0','Keep draft')
            editor.focus_force();root.update()
            with patch.object(plan_dialog.ImageGrab,'grabclipboard',return_value=Image.new('RGB',(80,60),'green')):
                editor.event_generate('<Control-v>');root.update()
            button(dialog,'+ 添加').invoke();root.update()
            with patch.object(plan_dialog.filedialog,'askopenfilenames',return_value=[str(source)]):
                button(dialog,'添加文件').invoke()
            minimize(dialog);root.update()
            button(root,'打开需求输入框').invoke();root.update()
            assert not ctypes.windll.user32.IsIconic(window_handle(dialog))
            assert editor.get('1.0','end').strip()=='Keep draft'
            button(root,'×').invoke();root.update()
            assert root.state()=='withdrawn' and dialog.winfo_exists()
            button(dialog,'保存后续任务 ↑').invoke()
            data=json.loads((folder/'followups'/f'{thread}.json').read_text(encoding='utf-8'))
            assert data['text']=='Keep draft' and len(data['images'])==len(data['files'])==1
            print(f'INPROCESS_OK: {elapsed*1000:.0f} ms, same PID, no spawn, reuse, restore, attachments, close/save')
        except Exception as error:
            errors.append(error)
            try:root.destroy()
            except tk.TclError:pass
    root.after(2500,check)
    return original(root,*args,**kwargs)
with tempfile.TemporaryDirectory() as directory:
    folder=Path(directory);source=folder/'sample.txt';source.write_text('local file',encoding='utf-8')
    with patch.object(app.w,'APP_DIR',folder),patch.object(app.w,'load_state',return_value={}),patch.object(app.w,'find_codex',return_value='codex'),patch.object(app.w.codex_status,'connection',connection),patch.object(app,'monitor_indicator',return_value=('', '', True)),patch.object(app.subprocess,'Popen') as launch,patch.object(tk.Tk,'mainloop',loop):
        app.show()
assert not errors,errors
