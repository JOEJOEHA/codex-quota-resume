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


def show(thread, path, write_plan):
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    saved = old.get('status') == 'saved'
    attachments = list(old.get('images', [])) if saved else []
    root = tk.Tk()
    root.title('续跑后还想跑什么任务')
    root.overrideredirect(True)
    root.configure(bg='#010203')
    root.wm_attributes('-transparentcolor', '#010203')
    width, height = 860, 580
    root.geometry(f'{width}x{height}+{(root.winfo_screenwidth()-width)//2}+{(root.winfo_screenheight()-height)//2}')
    canvas = tk.Canvas(root, bg='#010203', highlightthickness=0)
    canvas.pack(fill='both', expand=True)
    r = 48
    canvas.create_polygon(r, 1, width-r, 1, width-1, 1, width-1, r,
                          width-1, height-r, width-1, height-1, width-r, height-1,
                          r, height-1, 1, height-1, 1, height-r, 1, r, 1, 1,
                          smooth=True, fill='#292929', outline='#414141', width=1)
    body = tk.Frame(canvas, bg='#292929')
    canvas.create_window(24, 20, anchor='nw', width=width-48, height=height-40, window=body)
    font = ('Microsoft YaHei UI', 11)
    def label(parent, text, color='#eeeeee', size=11):
        return tk.Label(parent, text=text, bg='#292929', fg=color, font=('Microsoft YaHei UI', size))
    def button(parent, text, command, accent=False):
        return tk.Button(parent, text=text, command=command, bg='#2864cb' if accent else '#383838',
                         fg='white', activebackground='#454545', activeforeground='white',
                         relief='flat', bd=0, padx=14, pady=8, cursor='hand2', font=font)
    top = tk.Frame(body, bg='#292929'); top.pack(fill='x')
    title = label(top, '续跑后还想跑什么任务', size=16); title.pack(side='left')
    button(top, '×', root.destroy).pack(side='right')
    drag = [0, 0]
    title.bind('<Button-1>', lambda e: drag.__setitem__(slice(None), [e.x_root-root.winfo_x(), e.y_root-root.winfo_y()]))
    title.bind('<B1-Motion>', lambda e: root.geometry(f'+{e.x_root-drag[0]}+{e.y_root-drag[1]}'))
    label(body, '原任务完成后发送 · 仅保存到本机', '#aaaaaa').pack(anchor='w', pady=(8, 2))
    label(body, '任务 ' + thread, '#888888', 9).pack(anchor='w')
    bottom = tk.Frame(body, bg='#292929'); bottom.pack(side='bottom', fill='x', pady=(12, 0))
    hint = label(body, 'Ctrl+V 粘贴截图 · Ctrl+Enter 保存 · 点击缩略图移除', '#aaaaaa', 9)
    hint.pack(side='bottom', anchor='w', pady=(8, 0))
    previews = tk.Frame(body, bg='#292929'); previews.pack(side='bottom', fill='x')
    editor = tk.Text(body, bg='#292929', fg='#f3f3f3', insertbackground='white',
                     selectbackground='#365c91', relief='flat', highlightthickness=0,
                     wrap='word', font=font, undo=True, height=8)
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
                    photo = ImageTk.PhotoImage(im.copy())
                photos.append(photo)
                b = tk.Button(previews, image=photo, bg='#383838', relief='flat', bd=2,
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
    root.mainloop()
