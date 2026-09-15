"""Exercise the real compose button without starting Codex or child processes."""
import ctypes
from ctypes import wintypes
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
            labels=[w.cget('text') for w in walk(dialog) if isinstance(w,tk.Label)]
            assert 'Integration task' in labels and thread not in labels
            elapsed=time.perf_counter()-started
            assert dialog.winfo_viewable() and dialog.tk is root.tk
            main_rect=wintypes.RECT();child_rect=wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(window_handle(root),ctypes.byref(main_rect))
            ctypes.windll.user32.GetWindowRect(window_handle(dialog),ctypes.byref(child_rect))
            assert child_rect.top==main_rect.top
            assert child_rect.left==main_rect.right+6 or child_rect.right==main_rect.left-6
            pid=ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(window_handle(dialog),ctypes.byref(pid))
            assert pid.value==os.getpid()
            button(root,'打开需求输入框').invoke();root.update()
            assert len([w for w in root.winfo_children() if isinstance(w,tk.Toplevel)])==1
            assert not launch.called,'Opening a composer must not spawn a process'
            picker=next(w for w in walk(root) if isinstance(w,TaskPicker))
            picker.toggle();root.update()
            assert picker.button.winfo_width()==picker.panel.winfo_width(),(picker.button.winfo_width(),picker.panel.winfo_width())
            picker.hide()
            picker.current(1);button(root,'打开需求输入框').invoke();root.update()
            others=[w for w in root.winfo_children() if isinstance(w,tk.Toplevel) and w!=dialog]
            assert len(others)==1 and others[0].tk is root.tk
            button(others[0],'×').invoke();root.update()
            assert dialog.winfo_exists()
            picker.current(0)
            editor=next(w for w in walk(dialog) if isinstance(w,tk.Text))
            editor.insert('1.0','Keep draft')
            button(dialog,'↗').invoke();root.update()
            expanded=next(w for w in dialog.winfo_children() if isinstance(w,tk.Toplevel))
            large=next(w for w in walk(expanded) if isinstance(w,tk.Text))
            assert large.get('1.0','end-1c')=='Keep draft' and editor.cget('state')=='disabled'
            large.insert('end',' expanded')
            button(expanded,'×').invoke();root.update()
            assert editor.get('1.0','end-1c')=='Keep draft expanded'
            editor.focus_force();root.update()
            with patch.object(plan_dialog.ImageGrab,'grabclipboard',return_value=Image.new('RGB',(80,60),'green')):
                for _ in range(8):editor.event_generate('<Control-v>');root.update()
            button(dialog,'+ 添加').invoke();root.update()
            with patch.object(plan_dialog.filedialog,'askopenfilenames',return_value=[str(source)]):
                button(dialog,'添加文件').invoke()
            minimize(dialog);root.update()
            button(root,'打开需求输入框').invoke();root.update()
            assert not ctypes.windll.user32.IsIconic(window_handle(dialog))
            assert editor.get('1.0','end').strip()=='Keep draft expanded'
            button(dialog,'↗').invoke();root.update()
            colors=[]
            configure=picker.flag.itemconfigure
            def record_flag(item,**options):
                if 'fill' in options:colors.append(options['fill'])
                return configure(item,**options)
            picker.flag.itemconfigure=record_flag
            button(dialog,'保存后续任务 ↑').invoke()
            data=json.loads((folder/'followups'/f'{thread}.json').read_text(encoding='utf-8'))
            assert data['text']=='Keep draft expanded' and len(data['images'])==8 and len(data['files'])==1
            assert data['taskName']=='Integration task' and picker.pending
            ready=tk.BooleanVar();root.after(2800,lambda:ready.set(True));root.wait_variable(ready)
            assert picker.pending and picker.flag.itemcget(picker.flag_shape,'fill')=='#ef5350'
            assert picker.flag_timer is None and picker.flag.winfo_ismapped()
            assert colors.count('#43c77a')==5,colors
            data['status']='sent'
            (folder/'followups'/f'{thread}.json').write_text(json.dumps(data),encoding='utf-8')
            root.after(1100,lambda:ready.set(False));root.wait_variable(ready)
            assert not picker.pending and not picker.flag.winfo_ismapped()
            button(root,'打开需求输入框').invoke();root.update()
            dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
            button(root,'×').invoke();root.update()
            assert root.state()=='withdrawn' and dialog.winfo_exists()
            button(dialog,'×').invoke()
            print(f'INPROCESS_OK: {elapsed*1000:.0f} ms, same PID, task name, fixed width, expanded editor, 8 images, saved/sent flag, close/save')
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
