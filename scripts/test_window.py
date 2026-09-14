import tkinter as tk
from window_ui import rounded_window,bind_drag
root=tk.Tk();body=rounded_window(root,500,320)
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
root.destroy()
print('WINDOW_DRAG_OK: header moves window; negative monitor coordinates supported')
