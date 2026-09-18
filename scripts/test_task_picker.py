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
    from AppKit import NSObject
    from Foundation import NSTimer,NSRunLoop,NSRunLoopCommonModes
    class MenuProbe(NSObject):
        def fire_(self,timer):
            try:
                assert self.native.active
                if self.capture and os.environ.get('QUOTA_RESUME_SKIP_SCREEN_CAPTURE')!='1':
                    from PIL import ImageGrab
                    folder=Path('build');folder.mkdir(exist_ok=True)
                    ImageGrab.grab().save(folder/('macos-task-menu-'+self.native.theme+'.png'))
                if self.selection is not None:self.native.menu.performActionForItemAtIndex_(self.selection)
            except BaseException as error:self.errors.append(error)
            finally:self.native.dismiss()
    def track(selection,capture=False):
        probe=MenuProbe.alloc().init()
        probe.native=picker.native_menu;probe.selection=selection;probe.capture=capture;probe.errors=[]
        timer=NSTimer.timerWithTimeInterval_target_selector_userInfo_repeats_(.4,probe,'fire:',None,False)
        NSRunLoop.mainRunLoop().addTimer_forMode_(timer,NSRunLoopCommonModes)
        try:picker.toggle()
        finally:timer.invalidate()
        assert not probe.errors,probe.errors
        assert not picker.native_menu.active
    for _ in range(3):track(1);assert picker.current()==1
    for name in ('light','dark'):
        picker.native_menu.theme=name
        track(None,capture=True)
        assert picker.current()==1
    assert not hasattr(picker,'panel'), 'macOS must not create a transparent Tk popup'
    root.withdraw();root.update();assert not picker.native_menu.active
    root.deiconify();root.update();assert not picker.native_menu.active
    print('TASK_PICKER_OK: actual NSMenu, repeated selection, cancellation, both themes, parent hide/restore, no Tk transparent window')
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
