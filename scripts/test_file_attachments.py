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
                add=next(x for x in widgets if isinstance(x,tk.Button) and x.cget('text') in ('+','+ 添加附件'))
                if plan_dialog.sys.platform=='darwin':
                    with patch.object(plan_dialog.filedialog,'askopenfilenames',return_value=[str(source)]):add.invoke()
                    root.update()
                    assert listing.get(0)==('▤  ' if plan_dialog.sys.platform=='darwin' else '')+source.name
                else:
                    add.invoke();root.update()
                if plan_dialog.sys.platform!='darwin':
                    choose=next(x for x in widgets if isinstance(x,tk.Button) and x.cget('text')=='添加文件')
                    assert choose.winfo_viewable()
                    with patch.object(plan_dialog.filedialog,'askopenfilenames',return_value=[str(source)]):choose.invoke()
                    root.update();assert not choose.winfo_viewable()
                    assert listing.get(0)==('▤  ' if plan_dialog.sys.platform=='darwin' else '')+source.name
            elif stage==1:
                assert listing.get(0)==('▤  ' if plan_dialog.sys.platform=='darwin' else '')+source.name
                listing.selection_set(0);listing.focus_force();root.update()
                listing.event_generate('<Delete>');root.update()
                assert listing.size()==0
                next(x for x in widgets if isinstance(x,tk.Text)).insert('1.0','移除文件后保存')
            else:
                next(x for x in widgets if isinstance(x,tk.Text)).insert('1.0','明确请求发送')
            action=('请求发送' if plan_dialog.sys.platform=='darwin' else '发送') if stage==2 else '保存'
            target=next(x for x in widgets if isinstance(x,tk.Button) and x.cget('text')==action)
            assert target.winfo_viewable()
            assert target.winfo_rooty()+target.winfo_height()<=root.winfo_rooty()+root.winfo_height()
            target.invoke()
        except Exception as error:
            __import__('traceback').print_exc();errors.append(error);root.destroy()
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
        assert data['sendRequested'] is False
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
        stage=2
        plan_dialog.show('test-thread',plan,w.write_plan)
        assert not errors,errors
        assert json.loads(plan.read_text(encoding='utf-8'))['sendRequested'] is True
print('FILE_ATTACHMENTS_OK: copy, file-only save, reload, remove, original deletion, dispatch paths')
