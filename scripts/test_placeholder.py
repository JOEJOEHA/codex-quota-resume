"""Composer placeholder never becomes saved content; input area is roughly doubled."""
import tempfile
from pathlib import Path
import tkinter as tk
import plan_dialog
import ctypes
from window_ui import rounded_window
ctypes.windll.shcore.SetProcessDpiAwareness(1)
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
 assert 280<=height<=330,height
 hint.event_generate('<Button-1>',x=5,y=5);root.update()
 assert not hint.winfo_ismapped()
 editor.insert('1.0','saved text');dialog.focus_force();root.update()
 assert not hint.winfo_ismapped()
 editor.delete('1.0','end');root.update()
 assert hint.winfo_ismapped()
 assert editor.get('1.0','end-1c')==''
 print('COMPOSER_PLACEHOLDER_OK',height,dialog.winfo_height())
 dialog.destroy()
root.destroy()
