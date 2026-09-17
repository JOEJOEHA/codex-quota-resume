"""Composer placeholder never becomes saved content; input area is roughly doubled."""
import tempfile
from pathlib import Path
import tkinter as tk
import plan_dialog
import ctypes,sys
from window_ui import rounded_window
if sys.platform=='win32':ctypes.windll.shcore.SetProcessDpiAwareness(1)
root=tk.Tk();rounded_window(root,430,535);root.update()
with tempfile.TemporaryDirectory() as folder:
 dialog=plan_dialog.show('00000000-0000-0000-0000-000000000001',Path(folder)/'plan.json',lambda *a:None,parent=root,task_name='Placeholder test')
 for _ in range(4):root.update()
 def walk(widget):
  yield widget
  for child in widget.winfo_children():yield from walk(child)
 editor=next(w for w in walk(dialog) if isinstance(w,tk.Text))
 hint=next(w for w in walk(dialog) if w.winfo_name()=='placeholder')
 dialog.focus_force();root.update()
 assert hint.winfo_ismapped()
 assert editor.get('1.0','end-1c')==''
 height=editor.master.winfo_height()
 assert height>=280,height
 hint.event_generate('<Button-1>',x=5,y=5);root.update()
 assert not hint.winfo_ismapped()
 editor.insert('1.0','saved text');dialog.focus_force();root.update()
 assert not hint.winfo_ismapped()
 editor.delete('1.0','end');root.update()
 assert hint.winfo_ismapped()
 assert editor.get('1.0','end-1c')==''
 buttons=[w for w in walk(dialog) if isinstance(w,tk.Button)]
 add=next(w for w in buttons if w.cget('text')=='+')
 assert add.master.cget('bg')=='#181818'
 assert add.winfo_rooty()>editor.winfo_rooty()+editor.winfo_height()
 assert not any(w.cget('text')=='\u622a\u56fe' for w in buttons)
 actions=[w for w in buttons if w.cget('text') in ('\u4fdd\u5b58','\u53d1\u9001')]
 assert len(actions)==2
 assert actions[0].winfo_rooty()==actions[1].winfo_rooty()
 assert actions[0].winfo_width()==actions[1].winfo_width()
 assert 'Placeholder test' in hint.cget('text')
 assert all(w.winfo_rooty()>=editor.winfo_rooty()+editor.winfo_height() for w in actions)
 expand=next(w for w in buttons if w.cget('text')=='\u2197')
 assert add.winfo_height()==expand.winfo_height()
 assert expand.winfo_rootx()+expand.winfo_width()<actions[0].winfo_rootx()
 print('COMPOSER_LAYOUT_OK',height,dialog.winfo_height())
 dialog.destroy()
root.destroy()
