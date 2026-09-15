"""Shared rounded desktop window and draggable non-input surfaces."""
import tkinter as tk
import ctypes
from pathlib import Path
from tkinter import font as tkfont
from PIL import Image, ImageDraw, ImageTk


class RoundedButton(tk.Button):
    """Keep native button keyboard/command behavior with a rounded image surface."""
    def __init__(self, parent, *, text='', command=None, bg='#2b2b2b', fg='#eeeeee',
                 font=('Microsoft YaHei UI', 11), padx=14, pady=10, image=None):
        self.fill=bg
        self.padding=(padx,pady)
        self.content_image=image
        super().__init__(parent,text=text,command=command,font=font,fg=fg,
                         bg=parent.cget('bg'),activebackground=parent.cget('bg'),
                         activeforeground=fg,relief='flat',bd=0,highlightthickness=0,
                         padx=0,pady=0,cursor='hand2',compound='center',takefocus=True)
        self.bind('<Enter>',lambda e:self.redraw(True))
        self.bind('<Leave>',lambda e:self.redraw())
        self.bind('<FocusIn>',lambda e:self.redraw())
        self.bind('<FocusOut>',lambda e:self.redraw())
        self.redraw()

    def redraw(self,hover=False):
        font=tkfont.Font(font=self.cget('font'))
        px,py=self.padding
        content=self.content_image
        width=(content.width if content else font.measure(self.cget('text')))+2*px
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
    def __init__(self,parent,font):
        super().__init__(parent,bg=parent.cget('bg'))
        self.values=[]
        self.index=-1
        self.button=RoundedButton(self,text='选择任务  ▾',font=font,command=self.toggle)
        self.button.pack(fill='x')
        self.panel=tk.Canvas(parent,width=374,height=212,bg=parent.cget('bg'),highlightthickness=0)
        self.panel.create_polygon(20,1,354,1,373,1,373,20,373,192,373,211,354,211,
                                  20,211,1,211,1,192,1,20,1,1,smooth=True,
                                  fill='#242424',outline='#383838')
        interior=tk.Frame(self.panel,bg='#242424')
        self.panel.create_window(10,10,anchor='nw',width=354,height=192,window=interior)
        self.listing=tk.Listbox(interior,bg='#242424',fg='#eeeeee',selectbackground='#383838',
                               selectforeground='white',font=font,relief='flat',bd=0,
                               highlightthickness=0,exportselection=False,activestyle='none')
        from tkinter import ttk
        scroll=ttk.Scrollbar(interior,command=self.listing.yview)
        scroll.pack(side='right',fill='y')
        self.listing.configure(yscrollcommand=scroll.set)
        self.listing.pack(fill='both',expand=True)
        self.listing.bind('<ButtonRelease-1>',self.choose)
        self.listing.bind('<Return>',self.choose)
        self.listing.bind('<Escape>',lambda e:self.hide())
        self.winfo_toplevel().bind('<Button-1>',self.dismiss,add='+')

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
        while font.measure(text)>306:text=text[:-2]+'…'
        self.button.configure(text=text+'  ▾')

    def toggle(self):
        if self.panel.winfo_ismapped():self.hide();return
        self.panel.place(x=self.winfo_x(),y=max(0,self.winfo_y()-220))
        tk.Misc.lift(self.panel)
        self.listing.selection_clear(0,'end')
        if self.index>=0:
            self.listing.selection_set(self.index);self.listing.activate(self.index);self.listing.see(self.index)
        self.listing.focus_set()

    def hide(self):
        self.panel.place_forget()
        self.button.focus_set()

    def choose(self,event=None):
        selection=self.listing.curselection()
        if selection:self.current(selection[0])
        self.hide()
        return 'break'

    def dismiss(self,event):
        widget=event.widget
        while widget is not None:
            if widget in (self,self.panel):return
            widget=getattr(widget,'master',None)
        if self.panel.winfo_ismapped():self.panel.place_forget()


def window_handle(root):
    user32=ctypes.windll.user32
    user32.GetParent.restype=ctypes.c_void_p
    return ctypes.c_void_p(user32.GetParent(root.winfo_id()))


def minimize(root):
    ctypes.windll.user32.ShowWindow(window_handle(root),6)


def window_controls(root,parent,font):
    for text,command in [('×',root.destroy),('—',lambda:minimize(root))]:
        RoundedButton(parent,text=text,command=command,font=font,padx=16,pady=8).pack(side='right',padx=(6,0))


def configure_taskbar(root):
    user32=ctypes.windll.user32
    hwnd=window_handle(root)
    style=user32.GetWindowLongW(hwnd,-20)
    user32.SetWindowLongW(hwnd,-20,(style | 0x40000) & ~0x80)
    user32.SetWindowPos(hwnd,None,0,0,0,0,0x37)
    icon=Path(__file__).with_name('app-icon.ico')
    if not icon.exists():icon=Path(__file__).parent.parent/'assets'/'app-icon.ico'
    if icon.exists():root.iconbitmap(str(icon))


def bind_drag(root, *widgets):
    offset=[0,0]
    def start(event):
        offset[:]=[event.x_root-root.winfo_x(),event.y_root-root.winfo_y()]
    def move(event):
        ctypes.windll.user32.SetWindowPos(window_handle(root),None,event.x_root-offset[0],event.y_root-offset[1],0,0,0x15)
    for widget in widgets:
        widget.bind('<ButtonPress-1>',start)
        widget.bind('<B1-Motion>',move)


def rounded_window(root,width,height):
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('CodexQuotaResume.Desktop')
    root.overrideredirect(True)
    root.configure(bg='#010203')
    root.wm_attributes('-transparentcolor','#010203')
    root.geometry(f'{width}x{height}+{max(0,(root.winfo_screenwidth()-width)//2)}+{max(0,(root.winfo_screenheight()-height)//2)}')
    canvas=tk.Canvas(root,bg='#010203',highlightthickness=0)
    canvas.pack(fill='both',expand=True)
    radius=48
    canvas.create_polygon(radius,1,width-radius,1,width-1,1,width-1,radius,
                          width-1,height-radius,width-1,height-1,width-radius,height-1,
                          radius,height-1,1,height-1,1,height-radius,1,radius,1,1,
                          smooth=True,fill='#181818',outline='#383838',width=1)
    body=tk.Frame(canvas,bg='#181818')
    canvas.create_window(28,22,anchor='nw',width=width-56,height=height-44,window=body)
    bind_drag(root,canvas,body)
    root.after(0,lambda:configure_taskbar(root))
    return body
