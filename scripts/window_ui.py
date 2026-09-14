"""Shared rounded desktop window and draggable non-input surfaces."""
import tkinter as tk
import ctypes
from pathlib import Path


def window_handle(root):
    user32=ctypes.windll.user32
    user32.GetParent.restype=ctypes.c_void_p
    return ctypes.c_void_p(user32.GetParent(root.winfo_id()))


def minimize(root):
    ctypes.windll.user32.ShowWindow(window_handle(root),6)


def window_controls(root,parent,font):
    for text,command in [('×',root.destroy),('—',lambda:minimize(root))]:
        tk.Button(parent,text=text,command=command,bg='#383838',fg='white',
                  activebackground='#494949',activeforeground='white',relief='flat',bd=0,
                  font=font,padx=16,pady=8,takefocus=True).pack(side='right',padx=(6,0))


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
                          smooth=True,fill='#292929',outline='#414141',width=1)
    body=tk.Frame(canvas,bg='#292929')
    canvas.create_window(28,22,anchor='nw',width=width-56,height=height-44,window=body)
    bind_drag(root,canvas,body)
    root.after(0,lambda:configure_taskbar(root))
    return body
