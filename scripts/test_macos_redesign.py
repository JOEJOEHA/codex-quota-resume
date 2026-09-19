"""Native appearance/lifecycle regressions with isolated files and no Codex calls."""
import json
import os
import tempfile
import tkinter as tk
from pathlib import Path
from unittest.mock import patch
from macos_appearance import PALETTES,status_presentation,status_detail
from macos_main_ui import build
import plan_dialog

assert status_presentation('waiting-quota',True)==('● 等待额度恢复','wait')
assert status_presentation('resuming',True)==('● 正在续跑','good')
assert status_presentation('resume-failed',True)==('! 异常','error')
assert status_presentation('resuming',True,True)==('Ⅱ 已暂停','neutral')
assert status_presentation('waiting-quota',False)==('● 尚未启用','neutral')

def walk(widget):
    yield widget
    for child in widget.winfo_children():yield from walk(child)

def button(root,text):return next(w for w in walk(root) if isinstance(w,tk.Button) and w.cget('text')==text)

with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,QUOTA_RESUME_THEME='light'):
    root=tk.Tk();ui=build(root,'3.1.5beta',root.withdraw);root.update()
    assert not root.overrideredirect()
    ui.select.set_values(['A very long task title '*15,'Second task'])
    root.update()
    clicked=[]
    ui.compose.configure(command=lambda:clicked.append('compose'))
    ui.compose.mac_surface.event_generate('<ButtonRelease-1>',x=10,y=10);root.update()
    assert clicked==['compose']
    ui.send.configure(command=lambda:clicked.append('send'))
    ui.saved({});assert ui.send.cget('state')=='disabled'
    ui.send.mac_surface.event_generate('<ButtonRelease-1>',x=10,y=10);root.update()
    assert clicked==['compose']
    ui.saved({'status':'saved','text':'Continue developing'})
    assert ui.compose.cget('text')=='编辑后续任务' and ui.send.cget('state')=='normal'
    ui.saved({'status':'saved','text':'Continue developing','sendRequested':True})
    assert ui.send.cget('state')=='disabled' and ui.send.cget('text')=='已请求发送'
    ui.saved({'status':'saved','text':'Continue developing','sendRequested':True},paused=True)
    assert any(w.cget('text').startswith('已请求发送 · 监控已暂停') for w in walk(root) if isinstance(w,tk.Label))
    ui.saved({'status':'saved','text':'Continue developing'})
    ui.state('waiting-quota',True,False)
    ui.status.configure(text=status_detail('waiting-quota','等待额度恢复'))
    ui.detail.configure(text='最近检查：21:27:18')
    os.environ['QUOTA_RESUME_THEME']='dark'
    ui.appearance.apply('dark');root.update()
    assert ui.frame.cget('bg')==PALETTES['dark']['window']
    assert ui.select.native_menu.theme=='dark'
    ui.select.native_menu.configure(ui.select.values,0,380,ui.select.current)
    ui.select.native_menu.menu.invoke(1)
    assert ui.select.current()==1
    ui.select.hide()
    assert not ui.select.native_menu.active
    root.geometry('620x760');root.update()
    assert ui.select.button.winfo_width()<=ui.select.winfo_width()
    for w in (ui.compose,ui.send,ui.update):
        assert w.winfo_viewable() and w.winfo_rooty()+w.winfo_height()<=root.winfo_rooty()+root.winfo_height()
    root.geometry(str(root.winfo_screenwidth()-40)+'x650');root.update()
    path=Path(folder)/'plan.json'
    dialog=plan_dialog.show('test-thread',path,lambda p,v:p.write_text(json.dumps(v)),parent=root,task_name='Test task')
    root.update();assert not dialog.overrideredirect()
    assert root.winfo_width()==root.winfo_screenwidth()-40
    root.geometry('480x620');root.update()
    from window_ui import place_beside
    place_beside(dialog,root);root.update()
    editor=next(w for w in walk(dialog) if isinstance(w,tk.Text))
    dialog_theme=dialog.appearance
    for name in ('dark','light'):
        os.environ['QUOTA_RESUME_THEME']=name
        ui.appearance.apply(name);dialog_theme.apply(name);root.update()
        assert editor.cget('bg')==PALETTES[name]['field']
        assert editor.cget('fg')==PALETTES[name]['text']
        if os.environ.get('QUOTA_RESUME_SKIP_SCREEN_CAPTURE')!='1':
            from PIL import ImageGrab
            output=Path('build');output.mkdir(exist_ok=True)
            ImageGrab.grab().save(output/('macos-redesign-'+name+'.png'))
    source=Path(folder)/'report.txt';source.write_text('attachment')
    image=Path(folder)/'picture.png'
    from PIL import Image
    Image.new('RGB',(80,60),'green').save(image)
    with patch.object(plan_dialog.filedialog,'askopenfilenames',return_value=[str(source),str(image)]):
        button(dialog,'+ 添加附件').invoke()
    root.update()
    editor.insert('1.0','Saved follow-up')
    button(dialog,'保存').invoke();root.update()
    data=json.loads(path.read_text());assert not data['sendRequested']
    assert len(data['files'])==1 and len(data['images'])==1
    dialog=plan_dialog.show('test-thread',path,lambda p,v:p.write_text(json.dumps(v)),parent=root,task_name='Test task')
    root.update()
    editor=next(w for w in walk(dialog) if isinstance(w,tk.Text))
    assert editor.get('1.0','end-1c')=='Saved follow-up'
    button(dialog,'请求发送').invoke();root.update()
    assert json.loads(path.read_text())['sendRequested']
    root.destroy()
print('MACOS_REDESIGN_OK: native titles, theme transition, saved/empty card, resized layout, mixed attachments, save/reload/send')
