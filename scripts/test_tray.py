"""Check registration with Explorer, hide/restore and icon cleanup."""
import ctypes as c
from ctypes import wintypes as w
import tkinter as tk
import uuid
import tray as tray_module
from tray import TrayIcon
from window_ui import rounded_window

class Identifier(c.Structure):
    _fields_=[('cbSize',w.DWORD),('hWnd',w.HWND),('uID',w.UINT),('guidItem',c.c_byte*16)]

tray_module.GROUP='CodexQuotaResume.Test.'+uuid.uuid4().hex
root=tk.Tk();rounded_window(root,430,535);root.update()
tray=TrayIcon(root,root.destroy)
assert tray.active and tray.data.hIcon
ready=tk.BooleanVar();root.after(1000,lambda:ready.set(True));root.wait_variable(ready)
identity=Identifier(cbSize=c.sizeof(Identifier),hWnd=tray.hwnd.value,uID=1)
rect=w.RECT()
result=c.windll.shell32.Shell_NotifyIconGetRect(c.byref(identity),c.byref(rect))
assert result>=0,result
assert rect.right>rect.left and rect.bottom>rect.top
tray.user.PostMessageW(tray.hwnd,0x10,0,0)
root.after(150,lambda:ready.set(False));root.wait_variable(ready)
assert c.windll.user32.IsWindow(tray.hwnd) and not root.winfo_viewable()
tray.user.PostMessageW(tray.hwnd,tray.message,1,0x202)
root.after(350,lambda:ready.set(True));root.wait_variable(ready)
assert root.winfo_viewable()
tray.on_exit()
assert not tray.active
assert c.windll.shell32.Shell_NotifyIconGetRect(c.byref(identity),c.byref(rect))<0
print('TRAY_OK: Explorer icon registered, click restores hidden window, exit removes icon')
