"""Shared rounded desktop window and draggable non-input surfaces."""
import tkinter as tk
import ctypes


def bind_drag(root, *widgets):
    offset=[0,0]
    def start(event):
        offset[:]=[event.x_root-root.winfo_x(),event.y_root-root.winfo_y()]
    def move(event):
        hwnd=ctypes.windll.user32.GetParent(root.winfo_id())
        ctypes.windll.user32.SetWindowPos(ctypes.c_void_p(hwnd),None,event.x_root-offset[0],event.y_root-offset[1],0,0,0x15)
    for widget in widgets:
        widget.bind('<ButtonPress-1>',start)
        widget.bind('<B1-Motion>',move)


def rounded_window(root,width,height):
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
    return body
