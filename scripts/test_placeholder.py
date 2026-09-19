"""Composer placeholder never becomes saved content; input area is roughly doubled."""
import json,tempfile
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
 dialog.event_generate('<Button-1>',x=10,y=10);root.update()
 assert hint.winfo_ismapped()
 height=editor.master.winfo_height()
 assert height>=280,height
 hint.event_generate('<Button-1>',x=5,y=5);root.update()
 assert not hint.winfo_ismapped()
 editor.insert('1.0','saved text');dialog.focus_force();root.update()
 assert not hint.winfo_ismapped()
 if sys.platform=='win32':
  assert not any(w.winfo_name()=='task_caption' for w in walk(dialog))
  assert any(isinstance(w,tk.Label) and w.cget('text')=='Placeholder test' and w.winfo_ismapped() for w in walk(dialog))
 else:
  caption=next(w for w in walk(dialog) if w.winfo_name()=='task_caption')
  assert caption.winfo_ismapped() and caption.cget('text')=='Placeholder test'
 assert 'Placeholder test' in dialog.title()
 assert any(isinstance(w,tk.Label) and ('保存：续跑后 10 秒投递' in w.cget('text') or '保存后等待自动发送' in w.cget('text')) and w.winfo_ismapped() for w in walk(dialog)) == (sys.platform!='win32')
 editor.focus_force();editor.mark_set('insert','end-1c');root.update()
 before=editor.index('insert')
 x,y,width,height=editor.bbox('1.1')
 editor.event_generate('<Button-1>',x=x+1,y=y+height//2)
 editor.event_generate('<ButtonRelease-1>',x=x+1,y=y+height//2);root.update()
 assert editor.index('insert')!=before,'Mouse click did not move caret'
 x2,y2,width2,height2=editor.bbox('1.5')
 editor.event_generate('<Button-1>',x=x+1,y=y+height//2)
 editor.event_generate('<B1-Motion>',x=x2+1,y=y2+height2//2)
 editor.event_generate('<ButtonRelease-1>',x=x2+1,y=y2+height2//2);root.update()
 assert editor.tag_ranges('sel'),'Mouse drag did not select text'
 dialog.focus_force();root.update()
 editor.delete('1.0','end');root.update()
 assert hint.winfo_ismapped()
 assert editor.get('1.0','end-1c')==''
 buttons=[w for w in walk(dialog) if isinstance(w,tk.Button)]
 add=next(w for w in buttons if w.cget('text') in ('+','+ 添加附件'))
 if sys.platform=='win32':assert add.master.cget('bg')=='#2b2b2b'
 assert add.winfo_rooty()>editor.winfo_rooty()+editor.winfo_height()
 assert not any(w.cget('text')=='\u622a\u56fe' for w in buttons)
 actions=[w for w in buttons if w.cget('text') in ('\u4fdd\u5b58','\u53d1\u9001')]
 assert len(actions)==2
 assert actions[0].winfo_rooty()==actions[1].winfo_rooty()
 assert actions[0].winfo_width()==actions[1].winfo_width()
 if sys.platform=='win32':assert 'Placeholder test' in hint.cget('text')
 assert all(w.winfo_rooty()>=editor.winfo_rooty()+editor.winfo_height() for w in actions)
 expand=next(w for w in buttons if w.cget('text') in ('\u2197','↗ 展开'))
 if sys.platform=='win32':assert add.winfo_height()==expand.winfo_height()
 if sys.platform=='win32':assert expand.winfo_rootx()+expand.winfo_width()<actions[0].winfo_rootx()
 print('COMPOSER_LAYOUT_OK',height,dialog.winfo_height())
 dialog.destroy()
 path=Path(folder)/'cancelled.json'
 path.write_text(json.dumps({'status':'cancelled','taskName':'Cancelled task','text':'retained draft','images':[],'files':[]}))
 dialog=plan_dialog.show('00000000-0000-0000-0000-000000000001',path,lambda p,v:p.write_text(json.dumps(v)),parent=root)
 root.update()
 editor=next(w for w in walk(dialog) if isinstance(w,tk.Text))
 assert editor.get('1.0','end-1c')=='retained draft'
 assert 'Cancelled task' in dialog.title()
 assert any(isinstance(w,tk.Label) and '原任务已取消' in w.cget('text') and w.winfo_ismapped() for w in walk(dialog))
 next(w for w in walk(dialog) if isinstance(w,tk.Button) and w.cget('text')==('请求发送' if sys.platform=='darwin' else '发送')).invoke()
 data=json.loads(path.read_text())
 assert data['status']=='saved' and data['sendRequested'] and data['text']=='retained draft'
root.destroy()
