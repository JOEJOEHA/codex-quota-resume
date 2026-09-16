"""Local follow-up composer; no network or model calls."""
import json
import shutil
import subprocess
import time
import uuid
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageGrab, ImageTk
from window_ui import rounded_window, bind_drag, window_controls, RoundedButton, place_beside


def show(thread, path, write_plan, on_ready=None, parent=None, task_name=None, on_saved=None):
    if parent is None:ctypes.windll.shcore.SetProcessDpiAwareness(1)
    old = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    saved = old.get('status') in ('saved', 'send-failed')
    attachments = list(old.get('images', [])) if saved else []
    files = list(old.get('files', [])) if saved else []
    root = tk.Toplevel(parent) if parent is not None else tk.Tk()
    if parent is not None:root.withdraw()
    timers=[]
    def cancel_timers(event):
        if event.widget==root:
            for timer in timers:root.after_cancel(timer)
    root.bind('<Destroy>',cancel_timers,add='+')
    root.title('续跑后还想跑什么任务')
    body = rounded_window(root, 430, 535)
    font = ('Microsoft YaHei UI', 11)
    def label(parent, text, color='#eeeeee', size=11):
        item = tk.Label(parent, text=text, bg='#181818', fg=color, font=('Microsoft YaHei UI', size),wraplength=374,justify='left')
        bind_drag(root, item)
        return item
    def button(parent, text, command, accent=False):
        return RoundedButton(parent,text=text,command=command,bg='#2d6acb' if accent else '#2b2b2b',font=font)
    top = tk.Frame(body, bg='#181818'); top.pack(fill='x')
    title = label(top, '续跑后的任务', size=16); title.pack(side='left')
    window_controls(root,top,font)
    bind_drag(root, top, title)
    label(body, '保存：等待验收完成 · 现在发送：空闲且有额度时发送', '#aaaaaa', 10).pack(anchor='w', pady=(8, 2))
    label(body, task_name or old.get('taskName') or '当前任务', '#aaaaaa', 11).pack(anchor='w')
    bottom = tk.Frame(body, bg='#181818'); bottom.pack(side='bottom', fill='x', pady=(12, 0))
    hint = label(body, 'Ctrl+V 粘贴截图 · Ctrl+Enter 保存 · 点击图片 / 双击文件移除', '#aaaaaa', 11)
    hint.pack(side='bottom', anchor='w', pady=(8, 0))
    preview_area=tk.Frame(body,bg='#181818')
    preview_area.pack(side='bottom',fill='x')
    preview_canvas=tk.Canvas(preview_area,height=80,bg='#181818',highlightthickness=0)
    previews=tk.Frame(preview_canvas,bg='#181818')
    preview_canvas.create_window(0,0,anchor='nw',window=previews)
    preview_scroll=ttk.Scrollbar(preview_area,orient='horizontal',command=preview_canvas.xview)
    preview_canvas.configure(xscrollcommand=preview_scroll.set)
    previews.bind('<Configure>',lambda e:preview_canvas.configure(scrollregion=preview_canvas.bbox('all')))
    preview_canvas.bind('<MouseWheel>',lambda e:preview_canvas.xview_scroll(-int(e.delta/120),'units'))
    file_row=tk.Frame(body,bg='#181818')
    file_list=tk.Listbox(file_row,height=2,bg='#2b2b2b',fg='#eeeeee',font=('Microsoft YaHei UI',9),
                         selectbackground='#365c91',relief='flat',highlightthickness=0,exportselection=False)
    file_scroll=tk.Scrollbar(file_row,command=file_list.yview)
    file_list.configure(yscrollcommand=file_scroll.set)
    file_scroll.pack(side='right',fill='y');file_list.pack(side='left',fill='both',expand=True)
    def refresh_files():
        file_list.delete(0,'end')
        for item in files:file_list.insert('end',Path(item).name)
        if files:file_row.pack(side='bottom',fill='x',pady=(4,0),before=preview_area)
        else:file_row.pack_forget()
    def remove_file(event=None):
        selected=file_list.curselection()
        if selected:files.pop(selected[0]);refresh_files()
    file_list.bind('<Double-Button-1>',remove_file)
    file_list.bind('<Delete>',remove_file)
    input_area=tk.Canvas(body,bg='#181818',highlightthickness=0,height=180)
    input_area.pack(fill='both',expand=True,pady=18)
    editor = tk.Text(input_area, bg='#2b2b2b', fg='#f3f3f3', insertbackground='white',
                     selectbackground='#365c91', relief='flat', highlightthickness=0,
                     wrap='word', font=font, undo=True, height=8, padx=12, pady=12)
    def resize_editor(event):
        w,h=event.width,event.height
        r=24
        input_area.delete('surface')
        input_area.create_polygon(r,0,w-r,0,w,0,w,r,w,h-r,w,h,w-r,h,
                                  r,h,0,h,0,h-r,0,r,0,0,smooth=True,
                                  fill='#2b2b2b',outline='',tags='surface')
        editor.place(x=12,y=12,width=max(1,w-24),height=max(1,h-46))
        expand_host.place(x=max(0,w-38),y=max(0,h-32))
    input_area.bind('<Configure>',resize_editor)
    if saved:
        editor.insert('1.0', old.get('text', ''))
    photos = []
    def refresh():
        for child in previews.winfo_children(): child.destroy()
        photos.clear()
        if attachments:
            preview_canvas.pack(fill='x');preview_scroll.pack(fill='x')
        else:
            preview_canvas.pack_forget();preview_scroll.pack_forget()
        for index,item in enumerate(attachments):
            try:
                with Image.open(item) as im:
                    im.thumbnail((92, 68))
                    photo = im.copy()
                photos.append(photo)
                b = RoundedButton(previews, image=photo, padx=6, pady=6,
                              command=lambda p=item: remove(p))
                b.grid(row=0,column=index,padx=(0,8),pady=(0,4))
            except (OSError, ValueError):
                label(previews, '图片无法读取', '#ff9a9a').grid(row=0,column=index)
    def remove(item):
        attachments.remove(item); refresh()
    def add_image(im):
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
    def add_file(item):
        source=Path(item)
        if not source.is_file():raise OSError('请选择文件，不能添加文件夹。')
        folder=path.parent/'files'/thread/uuid.uuid4().hex
        folder.mkdir(parents=True,exist_ok=True)
        target=folder/source.name
        try:shutil.copy2(source,target)
        except OSError:
            target.unlink(missing_ok=True)
            folder.rmdir()
            raise
        files.append(str(target));refresh_files()
    def choose_files():
        for item in filedialog.askopenfilenames(parent=root,title='添加文件',filetypes=[('所有文件','*.*')]):
            try:add_file(item)
            except OSError as error:messagebox.showerror('无法添加文件',str(error),parent=root)
    def paste(event=None):
        try:
            clip = ImageGrab.grabclipboard()
            if isinstance(clip, Image.Image):
                add_image(clip); return 'break'
            if isinstance(clip, list):
                for item in clip:
                    try:
                        with Image.open(item) as im: add_image(im)
                    except (OSError,ValueError):add_file(item)
                return 'break'
        except (OSError, ValueError) as error:
            messagebox.showerror('无法粘贴图片', str(error), parent=root)
    def screenshot():
        root.withdraw()
        subprocess.Popen(['explorer.exe', 'ms-screenclip:'])
        timers.append(root.after(1800, root.deiconify))
        hint.configure(text='截图后回到这里，按 Ctrl+V 添加截图')
    expanded=[None,None]
    def collapse_editor():
        window,large=expanded
        if window is None:return
        text=large.get('1.0','end-1c')
        editor.configure(state='normal')
        editor.delete('1.0','end');editor.insert('1.0',text)
        expanded[:]=[None,None]
        window.destroy();editor.focus_set()
    def expand_editor():
        if expanded[0] is not None:
            expanded[0].deiconify();expanded[0].lift();return
        window=tk.Toplevel(root)
        window.title('编辑后续需求')
        panel=rounded_window(window,760,620)
        header=tk.Frame(panel,bg='#181818');header.pack(fill='x',pady=(0,12))
        heading=label(header,'编辑后续需求',size=16);heading.pack(side='left')
        window_controls(window,header,font,on_close=collapse_editor)
        bind_drag(window,header,heading)
        large=tk.Text(panel,bg='#2b2b2b',fg='#f3f3f3',insertbackground='white',
                      relief='flat',highlightthickness=0,wrap='word',font=font,undo=True,padx=14,pady=14)
        large.pack(fill='both',expand=True)
        large.insert('1.0',editor.get('1.0','end-1c'))
        expanded[:]=[window,large]
        editor.configure(state='disabled')
        window.protocol('WM_DELETE_WINDOW',collapse_editor)
        window.bind('<Escape>',lambda e:collapse_editor())
        window.bind('<Control-Return>',lambda e:collapse_editor())
        large.bind('<Control-v>',paste)
        large.focus_set()
    expand_host=tk.Frame(input_area,bg='#2b2b2b')
    expand_button=RoundedButton(expand_host,text='↗',command=expand_editor,font=font,padx=5,pady=1)
    expand_button.pack()
    def save(event=None, send_now=False):
        collapse_editor()
        text = editor.get('1.0', 'end').strip()
        if not text and not attachments and not files:
            messagebox.showinfo('请输入需求', '填写需求或添加附件后保存。', parent=root); return
        if any(not Path(p).is_file() for p in attachments + files):
            messagebox.showerror('附件不存在', '请移除无法读取的附件后重新添加。', parent=root); return
        try:
            write_plan(path, {'threadId': thread, 'taskName': task_name or old.get('taskName') or '当前任务', 'text': text, 'images': attachments, 'files': files,
                              'status': 'saved', 'savedAt': time.time(), 'sendRequested': send_now})
        except OSError as error:
            messagebox.showerror('保存失败', str(error), parent=root); return
        if on_saved:on_saved(thread)
        root.destroy()
    menu=tk.Canvas(body,width=160,height=110,bg='#181818',highlightthickness=0)
    menu.create_polygon(20,1,140,1,159,1,159,20,159,90,159,109,140,109,
                        20,109,1,109,1,90,1,20,1,1,smooth=True,
                        fill='#242424',outline='#383838')
    menu_body=tk.Frame(menu,bg='#242424')
    menu.create_window(8,8,anchor='nw',width=144,height=94,window=menu_body)
    def hide_menu():
        menu.place_forget()
    def select_attachment(command):
        hide_menu();command()
    menu_items=[]
    for text,command in [('添加图片',choose),('添加文件',choose_files)]:
        item=RoundedButton(menu_body,text=text,command=lambda c=command:select_attachment(c),
                           bg='#242424',font=font,padx=30,pady=8)
        item.pack(fill='x',pady=2)
        item.bind('<Return>',lambda event:event.widget.invoke())
        menu_items.append(item)
    for index,item in enumerate(menu_items):
        for key in ('<Up>','<Down>'):
            item.bind(key,lambda event,i=index:(menu_items[1-i].focus_set(),'break')[-1])
    def toggle_menu():
        if menu.winfo_ismapped():hide_menu();return
        menu.place(x=add_button.winfo_rootx()-body.winfo_rootx(),
                   y=add_button.winfo_rooty()-body.winfo_rooty()-118)
        tk.Misc.lift(menu)
        if root.focus_get()==add_button:menu_items[0].focus_set()
    add_button=button(bottom,'+ 添加',toggle_menu)
    add_button.pack(side='left')
    def dismiss_menu(event):
        widget=event.widget
        while widget is not None:
            if widget in (menu,add_button):return
            widget=getattr(widget,'master',None)
        hide_menu()
    root.bind('<Button-1>',dismiss_menu,add='+')
    def escape(event):
        if menu.winfo_ismapped():hide_menu();add_button.focus_set()
        else:root.destroy()
    button(bottom, '截图', screenshot).pack(side='left', padx=8)
    send_row=tk.Frame(body,bg='#181818')
    send_row.pack(side='bottom',fill='x',before=bottom)
    button(send_row, '现在发送 ↑', lambda:save(send_now=True), True).pack(side='right')
    button(bottom, '保存后续任务 ↑', save).pack(side='right')
    editor.bind('<Control-v>', paste)
    root.bind('<Control-Return>', save)
    root.bind('<Escape>',escape)
    refresh();refresh_files()
    editor.focus_set()
    def reveal():
        if parent is not None:
            root.update_idletasks()
            place_beside(root,parent)
        root.deiconify()
        if parent is not None:place_beside(root,parent)
        root.lift()
        root.attributes('-topmost', True)
        root.update_idletasks()
        if on_ready and root.winfo_viewable():
            on_ready()
        timers.append(root.after(5000, lambda: root.attributes('-topmost', False)))
    timers.append(root.after_idle(reveal))
    if parent is None:root.mainloop()
    return root
