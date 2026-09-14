import tkinter as tk
from window_ui import rounded_window,bind_drag,minimize,window_handle,window_controls
import ctypes
root=tk.Tk();body=rounded_window(root,500,320)
controls=tk.Frame(body);controls.pack()
window_controls(root,controls,('Segoe UI',11))
assert [b.cget('text') for b in controls.winfo_children()]==['×','—']
header=tk.Label(body,text='Drag');header.pack();bind_drag(root,header)
root.update()
x,y=root.winfo_x(),root.winfo_y()
header.event_generate('<ButtonPress-1>',rootx=x+10,rooty=y+10)
header.event_generate('<B1-Motion>',rootx=x+130,rooty=y+90)
root.update()
assert (root.winfo_x(),root.winfo_y())==(x+120,y+80)
header.event_generate('<B1-Motion>',rootx=-30,rooty=60)
root.update()
assert root.winfo_x()==-40
controls.winfo_children()[1].invoke();root.update()
assert ctypes.windll.user32.IsIconic(window_handle(root))
ctypes.windll.user32.ShowWindow(window_handle(root),9);root.update()
assert not ctypes.windll.user32.IsIconic(window_handle(root))
assert root.winfo_viewable()
root.destroy()
print('WINDOW_CONTROLS_OK: minimize button, restore, drag and negative coordinates; only two controls')
