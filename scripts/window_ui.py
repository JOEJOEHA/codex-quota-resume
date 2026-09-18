"""Shared rounded desktop window and draggable non-input surfaces."""
import tkinter as tk
import ctypes
import sys
from ctypes import wintypes
from pathlib import Path
from tkinter import font as tkfont
from PIL import Image, ImageDraw, ImageTk

FONT_FAMILY = '.AppleSystemUIFont' if sys.platform == 'darwin' else 'Microsoft YaHei UI'


class RoundedButton(tk.Button):
    """Keep native button keyboard/command behavior with a rounded image surface."""
    def __init__(self, parent, *, text='', command=None, bg='#2b2b2b', fg='#eeeeee',
                 font=(FONT_FAMILY, 11), padx=14, pady=10, image=None, width_px=None):
        self.fixed_width=width_px
        self.fill=bg
        self.padding=(padx,pady)
        self.content_image=image
        super().__init__(parent,text=text,command=command,font=font,fg=fg,
                         bg=parent.cget('bg'),activebackground=parent.cget('bg'),
                         activeforeground=fg,relief='flat',bd=0,highlightthickness=0,
                         highlightbackground=parent.cget('bg'),
                         padx=0,pady=0,cursor='hand2',compound='center',takefocus=True)
        self.bind('<ButtonPress-1>',lambda e:self.winfo_toplevel().focus_set())
        self.bind('<Enter>',lambda e:self.redraw(True))
        self.bind('<Leave>',lambda e:self.redraw())
        self.bind('<FocusIn>',lambda e:self.redraw())
        self.bind('<FocusOut>',lambda e:self.redraw())
        self.redraw()

    def redraw(self,hover=False):
        font=tkfont.Font(font=self.cget('font'))
        px,py=self.padding
        content=self.content_image
        width=self.fixed_width or (content.width if content else font.measure(self.cget('text')))+2*px
        height=(content.height if content else font.metrics('linespace'))+2*py
        color=self.fill
        if hover:
            color='#'+''.join(f'{min(255,int(color[i:i+2],16)+16):02x}' for i in (1,3,5))
        background=tuple(v//257 for v in self.winfo_rgb(self.master.cget('bg')))
        surface=Image.new('RGB',(width*3,height*3),background)
        draw=ImageDraw.Draw(surface)
        draw.rounded_rectangle((1,1,width*3-2,height*3-2),radius=30,fill=color,
                               outline='#8ab4f8' if self.focus_get()==self else color,width=3)
        surface=surface.resize((width,height),Image.Resampling.LANCZOS)
        if content:surface.paste(content,(px,py))
        self.surface=ImageTk.PhotoImage(surface,master=self)
        super().configure(image=self.surface)

    def configure(self,cnf=None,**kwargs):
        if cnf is not None:return super().configure(cnf,**kwargs)
        if 'bg' in kwargs:self.fill=kwargs.pop('bg')
        result=super().configure(**kwargs)
        self.redraw()
        return result

    config=configure


class TaskPicker(tk.Frame):
    """Task list using the same rounded surfaces as the composer."""
    def __init__(self,parent,font,light=False):
        super().__init__(parent,bg=parent.cget('bg'))
        surface='#f3f4f6' if light else '#2b2b2b'
        foreground='#202124' if light else '#eeeeee'
        menu_surface='#ffffff' if light else '#242424'
        self.values=[]
        self.index=-1
        self.button=RoundedButton(self,text='选择任务  ▾',font=font,command=self.toggle,width_px=374,bg=surface,fg=foreground)
        self.button.pack(fill='x')
        self.bind('<Configure>',self.fit_width,add='+')
        self.flag=tk.Canvas(self,width=24,height=26,bg=surface,highlightthickness=0)
        self.flag.create_line(5,3,5,24,fill='#dddddd',width=2)
        self.flag_shape=self.flag.create_polygon(6,3,21,3,17,9,21,15,6,15,fill='#ef5350',outline='')
        self.flag_timer=None
        self.pending=False
        self.bind('<Destroy>',self.cancel_flag,add='+')
        # A separate native popup is removed by the window compositor on hide.
        # Embedded Canvas windows can leave stale Aqua backing-store pixels.
        self.panel=tk.Toplevel(self)
        self.panel.withdraw()
        self.panel.overrideredirect(True)
        self.panel.transient(self.winfo_toplevel())
        self.panel.configure(bg='systemTransparent' if sys.platform=='darwin' else menu_surface)
        if sys.platform=='darwin':self.panel.wm_attributes('-transparent',True)
        canvas=tk.Canvas(self.panel,bg=self.panel.cget('bg'),highlightthickness=0)
        canvas.pack(fill='both',expand=True)
        paint_rounded_surface(canvas,374,212,menu_surface,'#dfe3e8' if light else '#383838',14)
        self.popup_canvas=canvas
        interior=tk.Frame(self.panel,bg=menu_surface)
        self.popup_interior=interior
        interior.place(x=10,y=10,width=354,height=192)
        self.listing=tk.Listbox(interior,bg=menu_surface,fg=foreground,
                               selectbackground='#e8f0fe' if light else '#383838',
                               selectforeground='#174ea6' if light else 'white',font=font,relief='flat',bd=0,
                               highlightthickness=0,exportselection=False,activestyle='none')
        from tkinter import ttk
        scroll=ttk.Scrollbar(interior,command=self.listing.yview)
        scroll.pack(side='right',fill='y')
        self.listing.configure(yscrollcommand=scroll.set)
        self.listing.pack(fill='both',expand=True)
        self.listing.bind('<ButtonRelease-1>',self.choose)
        self.listing.bind('<Return>',self.choose)
        self.listing.bind('<Escape>',lambda e:self.hide(keyboard=True))
        self.winfo_toplevel().bind('<Button-1>',self.dismiss,add='+')
        self.winfo_toplevel().bind('<Unmap>',self.parent_hidden,add='+')
        self.panel.bind('<FocusOut>',self.focus_left,add='+')
        self.panel.protocol('WM_DELETE_WINDOW',self.hide)

    def fit_width(self,event):
        if event.widget != self or sys.platform!='darwin':return
        self.button.fixed_width=max(100,event.width)
        self.current(self.index)
        if self.panel.winfo_ismapped():self.hide(restore_focus=False)

    def apply_appearance(self,appearance):
        appearance.bind(self,bg='card')
        appearance.bind(self.button,bg='field',fg='text')
        appearance.bind(self.popup_interior,bg='card')
        appearance.bind(self.listing,bg='card',fg='text',selectbackground='blue',selectforeground='white')
        def repaint():
            if not self.winfo_exists():return
            self.popup_canvas.delete('all')
            colors=appearance.colors
            paint_rounded_surface(self.popup_canvas,max(100,self.button.fixed_width),212,colors['card'],colors['separator'],14)
        appearance.changed(repaint)
        self.repaint_popup=repaint
        repaint()

    def parent_hidden(self,event):
        if event.widget==self.winfo_toplevel():self.hide(restore_focus=False)

    def focus_left(self,event):
        def check():
            if not self.winfo_exists() or not self.panel.winfo_exists():return
            focused=self.focus_get()
            if focused is None or focused.winfo_toplevel()!=self.panel:
                self.hide(restore_focus=False)
        self.after_idle(check)

    def cancel_flag(self,event=None):
        if event is not None and event.widget!=self:return
        if self.flag_timer:self.after_cancel(self.flag_timer);self.flag_timer=None

    def set_pending(self,pending,blink=False):
        self.pending=pending
        if sys.platform == 'darwin':
            self.cancel_flag();self.flag.place_forget();return
        if not pending:
            self.cancel_flag();self.flag.place_forget();return
        self.flag.place(relx=1,x=-35,y=8)
        tk.Misc.lift(self.flag)
        if blink:
            self.cancel_flag()
            self.flash_flag(0)
        elif self.flag_timer is None:self.flag.itemconfigure(self.flag_shape,fill='#ef5350')

    def flash_flag(self,step):
        self.flag_timer=None
        if not self.pending:return
        self.flag.itemconfigure(self.flag_shape,fill='#43c77a' if step%2==0 and step<10 else '#ef5350')
        if step<10:self.flag_timer=self.after(250,lambda:self.flash_flag(step+1))

    def set_values(self,values):
        self.values=list(values)
        self.listing.delete(0,'end')
        for value in self.values:self.listing.insert('end',value)
        self.current(0 if self.values else -1)

    def current(self,index=None):
        if index is None:return self.index
        self.index=index
        text=self.values[index] if 0<=index<len(self.values) else '选择任务'
        font=tkfont.Font(font=self.button.cget('font'))
        while len(text)>1 and font.measure(text)>(max(30,self.button.fixed_width-48) if sys.platform=='darwin' else 260):text=text[:-2]+'…'
        self.button.configure(text=text+'  ▾')

    def toggle(self):
        if self.panel.winfo_ismapped():self.hide();return
        self.update_idletasks()
        x=self.winfo_rootx()
        y=self.winfo_rooty()-220
        if y<0:y=self.winfo_rooty()+self.winfo_height()+6
        width=max(100,self.button.winfo_width())
        self.popup_interior.place_configure(width=max(1,width-20))
        self.panel.geometry(f'{width}x212{x:+d}{y:+d}')
        if hasattr(self,'repaint_popup'):self.repaint_popup()
        self.panel.deiconify()
        self.panel.lift()
        self.listing.selection_clear(0,'end')
        if self.index>=0:
            self.listing.selection_set(self.index);self.listing.activate(self.index);self.listing.see(self.index)
        self.listing.focus_set()

    def hide(self,keyboard=False,restore_focus=True):
        if not self.panel.winfo_exists():return
        self.panel.withdraw()
        if restore_focus:(self.button if keyboard else self.winfo_toplevel()).focus_set()

    def choose(self,event=None):
        selection=self.listing.curselection()
        if selection:self.current(selection[0])
        self.hide(keyboard=event is not None and event.type==tk.EventType.KeyPress)
        return 'break'

    def dismiss(self,event):
        widget=event.widget
        while widget is not None:
            if widget in (self,self.panel):return
            widget=getattr(widget,'master',None)
        if self.panel.winfo_ismapped():self.hide(restore_focus=False)


def window_handle(root):
    user32=ctypes.windll.user32
    user32.GetParent.restype=ctypes.c_void_p
    return ctypes.c_void_p(user32.GetParent(root.winfo_id()))


def adjacent_positions(main,child_size,work,gap=6):
    main,children=group_positions(main,child_size,work,1,gap)
    return main,children[0]


def group_positions(main,child_size,work,count,gap=6):
    """Tile composers on one side; reject layouts that cannot fit the work area."""
    x,y,width,height=main
    cw,ch=child_size
    left,top,right,bottom=work
    columns=min(count,(right-left-width)//(cw+gap))
    rows=(bottom-top+gap)//(ch+gap)
    if columns<1 or rows<1 or count>columns*rows or height>bottom-top:
        raise ValueError('当前屏幕放不下更多输入窗。请先保存并关闭一个输入窗，或最小化暂时不用的输入窗。')
    span=columns*(cw+gap)
    side=1 if x+width+span<=right else -1 if x-span>=left else (1 if right-x-width>=x-left else -1)
    x=max(left if side==1 else left+span,min(x,right-width-span if side==1 else right-width))
    used_rows=(count+columns-1)//columns
    y=max(top,min(y,bottom-max(height,used_rows*(ch+gap)-gap)))
    children=[]
    for index in range(count):
        row,column=divmod(index,columns)
        cx=x+width+gap+column*(cw+gap) if side==1 else x-(column+1)*(cw+gap)
        children.append((cx,y+row*(ch+gap)))
    return (x,y),children


def place_beside(dialog,parent):
    """Arrange all visible composers; dialog=None only checks room for a new one."""
    if sys.platform == 'darwin':
        from macos import work_area
        parent.update_idletasks()
        x,y=parent.winfo_x(),parent.winfo_y()
        width,height=parent.winfo_width(),parent.winfo_height()
        dialogs=[item for item in parent.winfo_children() if getattr(item,'is_task_composer',False)
                 and (item is dialog or item.state()=='normal')]
        if dialog not in dialogs:dialogs.append(dialog)
        size=(dialog.winfo_width(),dialog.winfo_height()) if dialog is not None else (480,650)
        main,children=group_positions((x,y,width,height),size,
                                       work_area(x+width//2,y+height//2),len(dialogs))
        if dialog is None:return
        parent.geometry(f'+{main[0]}+{main[1]}')
        for item,position in zip(dialogs,children):
            item.geometry(f'+{position[0]}+{position[1]}')
        return
    class MonitorInfo(ctypes.Structure):
        _fields_=[('cbSize',wintypes.DWORD),('rcMonitor',wintypes.RECT),
                  ('rcWork',wintypes.RECT),('dwFlags',wintypes.DWORD)]
    user32=ctypes.windll.user32
    user32.MonitorFromWindow.restype=ctypes.c_void_p
    parent_handle=window_handle(parent)
    rect=wintypes.RECT()
    if not user32.GetWindowRect(parent_handle,ctypes.byref(rect)):raise ctypes.WinError()
    monitor=ctypes.c_void_p(user32.MonitorFromWindow(parent_handle,2))
    info=MonitorInfo();info.cbSize=ctypes.sizeof(info)
    if not user32.GetMonitorInfoW(monitor,ctypes.byref(info)):raise ctypes.WinError()
    work=info.rcWork
    original=(rect.left,rect.top)
    dialogs=[item for item in parent.winfo_children() if getattr(item,'is_task_composer',False)
             and (item is dialog or (item.state()!='withdrawn' and not user32.IsIconic(window_handle(item))))]
    if dialog not in dialogs:dialogs.append(dialog)
    size=dialog.window_size if dialog is not None else (430,535)
    main,children=group_positions((*original,rect.right-rect.left,rect.bottom-rect.top),
                                  size,(work.left,work.top,work.right,work.bottom),len(dialogs))
    if dialog is None:return
    if main!=original:user32.SetWindowPos(parent_handle,None,*main,0,0,0x15)
    for item,position in zip(dialogs,children):
        user32.SetWindowPos(window_handle(item),None,*position,*item.window_size,0x14)


def minimize(root):
    if sys.platform == 'darwin':
        root.iconify()
        return
    configure_taskbar(root)
    ctypes.windll.user32.ShowWindow(window_handle(root),6)


def window_controls(root,parent,font,on_close=None,on_minimize=None,light=False):
    if sys.platform=='darwin':return
    for text,command in [('×',on_close or root.destroy),('—',on_minimize or (lambda:minimize(root)))]:
        RoundedButton(parent,text=text,command=command,font=font,padx=16,pady=8,bg='#f3f4f6' if light else '#2b2b2b',fg='#3c4043' if light else '#eeeeee').pack(side='right',padx=(6,0))


def configure_taskbar(root):
    if sys.platform == 'darwin':return
    user32=ctypes.windll.user32
    hwnd=window_handle(root)
    style=user32.GetWindowLongW(hwnd,-20)
    user32.SetWindowLongW(hwnd,-20,(style | 0x40000) & ~0x80)
    user32.SetWindowPos(hwnd,None,0,0,0,0,0x37)
    icon=Path(__file__).with_name('app-icon.ico')
    if not icon.exists():icon=Path(__file__).parent.parent/'assets'/'app-icon.ico'
    if icon.exists():root.iconbitmap(str(icon))


def bind_drag(root, *widgets):
    if sys.platform=='darwin':return
    offset=[0,0]
    def start(event):
        offset[:]=[event.x_root-root.winfo_x(),event.y_root-root.winfo_y()]
    def move(event):
        if sys.platform == 'darwin':
            root.geometry(f'+{event.x_root-offset[0]}+{event.y_root-offset[1]}')
            return
        ctypes.windll.user32.SetWindowPos(window_handle(root),None,event.x_root-offset[0],event.y_root-offset[1],0,0,0x15)
    for widget in widgets:
        widget.bind('<ButtonPress-1>',start)
        widget.bind('<B1-Motion>',move)


def paint_rounded_surface(canvas,width,height,fill,border,radius=26):
    scale=3
    image=Image.new('RGBA',(width*scale,height*scale),(0,0,0,0))
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((scale,scale,(width-1)*scale,(height-1)*scale),
                           radius=radius*scale,fill=fill,outline=border,width=scale)
    canvas.rounded_photo=ImageTk.PhotoImage(image.resize((width,height),Image.Resampling.LANCZOS),master=canvas)
    canvas.create_image(0,0,anchor='nw',image=canvas.rounded_photo)


def rounded_window(root,width,height,surface='#181818',border='#383838'):
    root.window_size=(width,height)
    if sys.platform == 'darwin':
        root.overrideredirect(False)
        root.configure(bg=surface)
        root.geometry(f'{width}x{height}')
        root.minsize(width,height)
        root.resizable(True,True)
        body=tk.Frame(root,bg=surface,padx=24,pady=20)
        body.pack(fill='both',expand=True)
        return body
    if sys.platform != 'darwin':ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('CodexQuotaResume.Desktop')
    root.overrideredirect(True)
    background='systemTransparent' if sys.platform == 'darwin' else '#010203'
    root.configure(bg=background)
    if sys.platform == 'darwin':root.wm_attributes('-transparent',True)
    else:root.wm_attributes('-transparentcolor','#010203')
    root.geometry(f'{width}x{height}+{max(0,(root.winfo_screenwidth()-width)//2)}+{max(0,(root.winfo_screenheight()-height)//2)}')
    canvas=tk.Canvas(root,bg=background,highlightthickness=0)
    canvas.pack(fill='both',expand=True)
    paint_rounded_surface(canvas,width,height,surface,border)
    body=tk.Frame(root,bg=surface)
    body.place(x=28,y=22,width=width-56,height=height-44)
    bind_drag(root,canvas,body)
    root.bind('<Map>',lambda event:root.after_idle(lambda:configure_taskbar(root)) if event.widget==root else None,add='+')
    root.after(0,lambda:configure_taskbar(root))
    if sys.platform == 'darwin':
        from macos import repaint_on_layout
        repaint_on_layout(root)
    return body
