"""Native popup lifecycle: no embedded canvas window remains after dismissal."""
import tkinter as tk
from types import SimpleNamespace
from window_ui import TaskPicker,rounded_window,FONT_FAMILY
root=tk.Tk();body=rounded_window(root,430,535,surface='#ffffff',border='#dfe3e8')
tk.Frame(body,height=260,bg='white').pack()
picker=TaskPicker(body,(FONT_FAMILY,11),light=True);picker.pack()
picker.set_values(['First task','Second task'])
root.update();root.focus_force()
assert body.cget('bg')=='#ffffff'
for _ in range(3):
 picker.toggle();root.update()
 assert picker.panel.winfo_viewable()
 assert picker.panel.winfo_width()==picker.button.winfo_width()
 picker.listing.selection_clear(0,'end');picker.listing.selection_set(1)
 picker.choose();root.update()
 assert picker.current()==1 and not picker.panel.winfo_ismapped()
picker.toggle();root.update()
picker.listing.event_generate('<Escape>');root.update()
assert not picker.panel.winfo_ismapped()
picker.toggle();root.update()
picker.dismiss(SimpleNamespace(widget=body));root.update()
assert not picker.panel.winfo_ismapped()
picker.toggle();root.update();root.withdraw();root.update()
assert not picker.panel.winfo_ismapped()
root.deiconify();root.update()
assert not picker.panel.winfo_ismapped()
root.destroy()
print('TASK_PICKER_OK: selection, Escape, outside click, parent hide, restore, repeated use')
