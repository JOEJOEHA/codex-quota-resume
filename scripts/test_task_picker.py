"""Native macOS menu tracking/selection plus retained Windows popup lifecycle."""
import os
import sys
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from window_ui import TaskPicker,rounded_window,FONT_FAMILY
root=tk.Tk();body=rounded_window(root,430,535,surface='#ffffff',border='#dfe3e8')
tk.Frame(body,height=260,bg='white').pack()
picker=TaskPicker(body,(FONT_FAMILY,11),light=True);picker.pack()
picker.set_values(['First task','Second task'])
root.update();root.focus_force()
assert body.cget('bg')=='#ffffff'
if sys.platform=='darwin':
    # A native Aqua tracking loop blocks unattended timer callbacks in CI.
    # Verify the exact menu items and Tk-owned callback without opening a
    # menu that no human can close on a hosted runner.
    for theme in ('light','dark'):
        picker.native_menu.theme=theme
        for _ in range(3):
            picker.native_menu.configure(picker.values,picker.current(),picker.button.winfo_width(),picker.current)
            assert picker.native_menu.menu.index('end')==1
            picker.native_menu.menu.invoke(1)
            assert picker.current()==1 and not picker.native_menu.active
        picker.native_menu.dismiss()
        assert not picker.native_menu.active
    assert not hasattr(picker,'panel')
    root.withdraw();root.update();assert not picker.native_menu.active
    root.deiconify();root.update()
    print('TASK_PICKER_OK: Tcl/Aqua menu items and callbacks, both themes, no AppKit tracking or transparent Tk popup; physical tracking requires manual QA')

else:
    for _ in range(3):
        picker.toggle();root.update()
        assert picker.panel.winfo_viewable()
        assert picker.panel.winfo_width()==picker.button.winfo_width()
        picker.listing.selection_clear(0,'end');picker.listing.selection_set(1)
        picker.choose();root.update()
        assert picker.current()==1 and not picker.panel.winfo_ismapped()
    picker.toggle();root.update();picker.listing.event_generate('<Escape>');root.update()
    assert not picker.panel.winfo_ismapped()
    picker.toggle();root.update();picker.dismiss(SimpleNamespace(widget=body));root.update()
    assert not picker.panel.winfo_ismapped()
    picker.toggle();root.update();root.withdraw();root.update();assert not picker.panel.winfo_ismapped()
    root.deiconify();root.update();assert not picker.panel.winfo_ismapped()
root.destroy()
