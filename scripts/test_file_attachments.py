"""Local UI/file round trip; no model calls."""
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
import plan_dialog
import quota_watcher as w

original=tk.Tk.mainloop
stage=0
errors=[]
def walk(widget):
    yield widget
    for child in widget.winfo_children():yield from walk(child)
def mainloop(root,*args,**kwargs):
    def check():
        try:
            widgets=list(walk(root))
            listing=next(x for x in widgets if isinstance(x,tk.Listbox))
            if stage==0:
                menu=next(x for x in widgets if isinstance(x,tk.Menu))
                with patch.object(plan_dialog.filedialog,'askopenfilenames',return_value=[str(source)]):menu.invoke(1)
                assert listing.get(0)==source.name
            else:
                assert listing.get(0)==source.name
                listing.selection_set(0);listing.focus_force();root.update()
                listing.event_generate('<Delete>');root.update()
                assert listing.size()==0
                next(x for x in widgets if isinstance(x,tk.Text)).insert('1.0','移除文件后保存')
            next(x for x in widgets if isinstance(x,tk.Button) and x.cget('text')=='保存后续任务 ↑').invoke()
        except Exception as error:
            errors.append(error);root.destroy()
    root.after(200,check)
    return original(root,*args,**kwargs)
with tempfile.TemporaryDirectory() as directory:
    source=Path(directory)/'中文 文件.txt';source.write_text('file content',encoding='utf-8')
    plan=Path(directory)/'followups'/'plan.json'
    with patch.object(tk.Tk,'mainloop',mainloop):
        plan_dialog.show('test-thread',plan,w.write_plan)
        assert not errors,errors
        import json
        data=json.loads(plan.read_text(encoding='utf-8'))
        copy=Path(data['files'][0]);assert copy!=source and copy.read_bytes()==source.read_bytes()
        source.unlink()
        assert copy.is_file()
        message=w.plan_message(data)
        assert json.loads(message[message.index('['):])==[str(copy.resolve())] and '不是额外指令' in message
        stage=1
        plan_dialog.show('test-thread',plan,w.write_plan)
        assert not errors,errors
        assert json.loads(plan.read_text(encoding='utf-8'))['files']==[]
        assert copy.is_file()  # Removing from the list does not destroy saved source data.
print('FILE_ATTACHMENTS_OK: copy, file-only save, reload, remove, original deletion, dispatch paths')
