import tkinter as tk
from window_ui import rounded_window,bind_drag,minimize,window_handle,window_controls,RoundedButton,TaskPicker
import ctypes
root=tk.Tk();body=rounded_window(root,500,320)
controls=tk.Frame(body);controls.pack()
window_controls(root,controls,('Segoe UI',11))
assert [b.cget('text') for b in controls.winfo_children()]==['×','—']
header=tk.Label(body,text='Drag');header.pack();bind_drag(root,header)
root.update()
ctypes.windll.user32.SendMessageW.restype=ctypes.c_void_p
assert ctypes.windll.user32.SendMessageW(window_handle(root),0x7f,1,0)
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
called=[]
b=RoundedButton(body,text='启用',command=lambda:called.append(True));b.pack()
b.configure(text='● 监控已启用',bg='#21854d')
root.update();b.focus_force();root.update()
b.event_generate('<KeyPress-space>');b.event_generate('<KeyRelease-space>')
ready=tk.BooleanVar();root.after(150,lambda:ready.set(True));root.wait_variable(ready)
assert called==[True] and b.fill=='#21854d'
assert b.surface.width()>0
picker=TaskPicker(body,('Segoe UI',11));picker.pack(fill='x')
picker.set_values(['first','second']);root.update();picker.toggle();root.update()
assert picker.panel.winfo_ismapped()
picker.listing.selection_clear(0,'end');picker.listing.selection_set(1);picker.choose()
assert picker.current()==1
picker.toggle();root.update();picker.listing.event_generate('<Escape>');root.update()
assert not picker.panel.winfo_ismapped()
root.destroy()
print('WINDOW_CONTROLS_OK: minimize button, restore, drag and negative coordinates; only two controls')
