"""macOS GUI smoke test with native menu bar and mocked Codex responses."""
import json
import sys
import tempfile
import tkinter as tk
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageGrab
import app
import plan_dialog
from window_ui import minimize

assert sys.platform == 'darwin'
thread = '00000000-0000-0000-0000-000000000001'
errors = []
original = tk.Tk.mainloop


@contextmanager
def connection(*args):
    yield lambda *args: {'data': [{'id': thread, 'name': 'macOS 界面测试'}]}


def walk(widget):
    yield widget
    for child in widget.winfo_children():yield from walk(child)


def button(root, title):
    return next(x for x in walk(root) if isinstance(x, tk.Button) and x.cget('text') == title)


def mainloop(root):
    print('Python:',sys.version,'Tk:',root.tk.call('package','require','Tk'))
    def check():
        try:
            assert root.tray.active
            root.withdraw()
            root.tray.target.open_(None)
            assert not root.winfo_viewable()  # Native callback only enqueues.
            root.after_cancel(root.tray.timer)
            root.tray.poll()
            root.update()
            assert root.winfo_viewable()
            button(root, '打开需求输入框').invoke()
            root.update()
            dialog = next(x for x in root.winfo_children() if isinstance(x, tk.Toplevel))
            assert dialog.winfo_width() == 430 and dialog.winfo_height() == 535
            assert abs(dialog.winfo_y()-root.winfo_y()) <= 2
            editor = next(x for x in walk(dialog) if isinstance(x, tk.Text))
            editor.insert('1.0', '草稿保留')
            with patch.object(plan_dialog.messagebox,'askyesnocancel',return_value=None):
                dialog.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
            assert editor.get('1.0','end-1c')=='草稿保留'
            minimize(dialog);root.update()
            dialog.deiconify();root.update()
            assert dialog.winfo_viewable() and dialog.overrideredirect()
            button(root, '打开需求输入框').invoke()
            assert len([x for x in root.winfo_children() if isinstance(x, tk.Toplevel)]) == 1
            button(dialog, '↗').invoke()
            expanded = next(x for x in dialog.winfo_children() if isinstance(x, tk.Toplevel))
            large = next(x for x in walk(expanded) if isinstance(x, tk.Text))
            large.insert('end', ' + 展开编辑')
            expanded.tk.call(expanded.protocol('WM_DELETE_WINDOW'))
            assert editor.get('1.0','end-1c') == '草稿保留 + 展开编辑'
            with patch.object(plan_dialog,'ImageGrab') as grab, patch('macos.clipboard_files',return_value=[]):
                grab.grabclipboard.return_value = Image.new('RGB',(80,60),'green')
                editor.focus_force();root.update()
                for _ in range(7):editor.event_generate('<Command-v>')
                root.update()
            def finish():
                try:
                    previews=[x for x in walk(dialog) if isinstance(x,tk.Button) and getattr(x,'content_image',None) is not None]
                    assert len(previews)==7 and all(x.winfo_ismapped() for x in previews)
                    print('Preview geometry:',[(x.winfo_rootx(),x.winfo_rooty(),x.winfo_width(),x.winfo_height()) for x in previews])
                    output = Path('build/macos-ui.png')
                    output.parent.mkdir(exist_ok=True)
                    screenshot=ImageGrab.grab()
                    screenshot.save(output)
                    assert dict((color,count) for count,color in screenshot.convert('RGB').getcolors(1920*1080*4)).get((0,128,0),0)>1000, 'Thumbnails were not painted'
                    root.tray.target.exit_(None)
                    root.after_cancel(root.tray.timer)
                    root.tray.poll();root.update()
                    assert root.winfo_exists() and dialog.winfo_exists()  # Exit keeps open draft alive.
                    button(dialog,'保存后续任务 ↑').invoke()
                    plan = json.loads(app.w.plan_path(thread).read_text(encoding='utf-8'))
                    assert plan['text'] == '草稿保留 + 展开编辑' and plan['status'] == 'saved'
                    assert len(plan['images']) == 7
                except Exception as error:
                    errors.append(error)
                    root.destroy()
            root.after(700,finish)  # Let Cocoa finish painting before capturing pixels.
        except Exception as error:
            errors.append(error)
            root.destroy()
    root.after(1600,check)
    original(root)


with tempfile.TemporaryDirectory() as directory:
    with patch.multiple(app.w, APP_DIR=Path(directory), STATE_PATH=Path(directory)/'state.json'), \
         patch.object(app.w.codex_status,'connection',connection),patch.object(app.w,'find_codex',return_value='mock'), \
         patch.object(app,'monitor_indicator',return_value=('test','#43c77a',True)),patch.object(tk.Tk,'mainloop',mainloop):
        app.show()
assert not errors, errors
print('MACOS_UI_OK: native menu queue, hide/restore, docking, draft reuse/exit, expand, seven images, save')
