"""Local follow-up composer; no network or model calls."""
import json
import subprocess
import time
import uuid
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageGrab, ImageTk
from window_ui import rounded_window, bind_drag, window_controls, RoundedButton


def show(thread, path, write_plan, on_ready=None):
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    saved = old.get('status') == 'saved'
    attachments = list(old.get('images', [])) if saved else []
    root = tk.Tk()
    root.title('续跑后还想跑什么任务')
    body = rounded_window(root, 860, 580)
    font = ('Microsoft YaHei UI', 11)
    def label(parent, text, color='#eeeeee', size=11):
        item = tk.Label(parent, text=text, bg='#181818', fg=color, font=('Microsoft YaHei UI', size))
        bind_drag(root, item)
        return item
    def button(parent, text, command, accent=False):
        return RoundedButton(parent,text=text,command=command,bg='#2d6acb' if accent else '#2b2b2b',font=font)
    top = tk.Frame(body, bg='#181818'); top.pack(fill='x')
    title = label(top, '续跑后还想跑什么任务', size=16); title.pack(side='left')
    window_controls(root,top,font)
    bind_drag(root, top, title)
    label(body, '原任务完成后发送 · 仅保存到本机', '#aaaaaa').pack(anchor='w', pady=(8, 2))
    label(body, '任务 ' + thread, '#888888', 9).pack(anchor='w')
    bottom = tk.Frame(body, bg='#181818'); bottom.pack(side='bottom', fill='x', pady=(12, 0))
    hint = label(body, 'Ctrl+V 粘贴截图 · Ctrl+Enter 保存 · 点击缩略图移除', '#aaaaaa', 9)
    hint.pack(side='bottom', anchor='w', pady=(8, 0))
    previews = tk.Frame(body, bg='#181818'); previews.pack(side='bottom', fill='x')
    editor = tk.Text(body, bg='#2b2b2b', fg='#f3f3f3', insertbackground='white',
                     selectbackground='#365c91', relief='flat', highlightthickness=0,
                     wrap='word', font=font, undo=True, height=8, padx=12, pady=12)
    editor.pack(fill='both', expand=True, pady=18)
    if saved:
        editor.insert('1.0', old.get('text', ''))
    photos = []
    def refresh():
        for child in previews.winfo_children(): child.destroy()
        photos.clear()
        for item in attachments:
            try:
                with Image.open(item) as im:
                    im.thumbnail((92, 68))
                    photo = im.copy()
                photos.append(photo)
                b = RoundedButton(previews, image=photo, padx=6, pady=6,
                              command=lambda p=item: remove(p))
                b.pack(side='left', padx=(0, 8))
            except (OSError, ValueError):
                label(previews, '图片无法读取', '#ff9a9a').pack(side='left')
    def remove(item):
        attachments.remove(item); refresh()
    def add_image(im):
        if len(attachments) >= 6:
            messagebox.showinfo('图片数量', '每个任务最多添加 6 张截图。', parent=root); return
        folder = path.parent / 'images' / thread
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / (uuid.uuid4().hex + '.png')
        im.convert('RGB').save(target)
        attachments.append(str(target)); refresh()
    def choose():
        for item in filedialog.askopenfilenames(parent=root, filetypes=[('图片', '*.png *.jpg *.jpeg *.webp *.bmp')]):
            try:
                with Image.open(item) as im: add_image(im)
            except (OSError, ValueError) as error:
                messagebox.showerror('无法添加图片', str(error), parent=root)
    def paste(event=None):
        try:
            clip = ImageGrab.grabclipboard()
            if isinstance(clip, Image.Image):
                add_image(clip); return 'break'
            if isinstance(clip, list):
                for item in clip:
                    with Image.open(item) as im: add_image(im)
                return 'break'
        except (OSError, ValueError) as error:
            messagebox.showerror('无法粘贴图片', str(error), parent=root)
    def screenshot():
        root.withdraw()
        subprocess.Popen(['explorer.exe', 'ms-screenclip:'])
        root.after(1800, root.deiconify)
        hint.configure(text='截图后回到这里，按 Ctrl+V 添加截图')
    def save(event=None):
        text = editor.get('1.0', 'end').strip()
        if not text and not attachments:
            messagebox.showinfo('请输入需求', '填写需求或添加截图后保存。', parent=root); return
        if any(not Path(p).is_file() for p in attachments):
            messagebox.showerror('图片不存在', '请移除无法读取的图片后重新添加。', parent=root); return
        try:
            write_plan(path, {'threadId': thread, 'text': text, 'images': attachments,
                              'status': 'saved', 'savedAt': time.time()})
        except OSError as error:
            messagebox.showerror('保存失败', str(error), parent=root); return
        root.destroy()
    button(bottom, '+ 图片', choose).pack(side='left')
    button(bottom, '截图', screenshot).pack(side='left', padx=8)
    button(bottom, '保存后续任务 ↑', save, True).pack(side='right')
    editor.bind('<Control-v>', paste)
    root.bind('<Control-Return>', save)
    root.bind('<Escape>', lambda e: root.destroy())
    refresh()
    editor.focus_set()
    def reveal():
        root.deiconify()
        root.lift()
        root.attributes('-topmost', True)
        root.update_idletasks()
        if on_ready and root.winfo_viewable():
            on_ready()
        root.after(5000, lambda: root.attributes('-topmost', False))
    root.after(100, reveal)
    root.mainloop()
