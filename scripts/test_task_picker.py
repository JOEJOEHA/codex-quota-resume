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
    # NSMenu's tracking loop does not reliably service timers on hosted runners.
    # Exercise real native items/actions and the presentation boundary without
    # blocking CI in an unattended menu. Physical menu tracking is manual QA.
    class MenuPresentation:
        def __init__(self,native):self.native=native;self.selection=None;self.cancelled=False
        def __getattr__(self,name):return getattr(self.native,name)
        def popUpMenuPositioningItem_atLocation_inView_(self,item,point,view):
            assert picker.native_menu.active
            if self.selection is not None:self.native.performActionForItemAtIndex_(self.selection)
            picker.native_menu.dismiss()
        def cancelTracking(self):self.cancelled=True
    real=picker.native_menu.menu
    presentation=MenuPresentation(real);picker.native_menu.menu=presentation
    for _ in range(3):
        presentation.selection=1;picker.toggle()
        assert picker.current()==1 and presentation.cancelled and not picker.native_menu.active
        assert real.numberOfItems()==2
        assert str(real.itemAtIndex_(1).toolTip())=='Second task'
    for name in ('light','dark'):
        picker.native_menu.theme=name;presentation.selection=None
        picker.toggle();assert picker.current()==1 and not picker.native_menu.active
    assert not hasattr(picker,'panel'), 'macOS must not create a transparent Tk popup'
    root.withdraw();root.update();assert not picker.native_menu.active
    root.deiconify();root.update();assert not picker.native_menu.active
    print('TASK_PICKER_OK: native items/actions, queued selection, cancellation boundary, both themes, no Tk transparent window; physical tracking requires manual QA')

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
