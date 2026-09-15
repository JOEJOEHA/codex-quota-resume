"""Check registration with Explorer, hide/restore and icon cleanup."""
import ctypes as c
from ctypes import wintypes as w
import tkinter as tk
from tray import TrayIcon
from window_ui import rounded_window

class Identifier(c.Structure):
    _fields_=[('cbSize',w.DWORD),('hWnd',w.HWND),('uID',w.UINT),('guidItem',c.c_byte*16)]

root=tk.Tk();rounded_window(root,430,535);root.update()
tray=TrayIcon(root,root.destroy)
assert tray.active and tray.data.hIcon
ready=tk.BooleanVar();root.after(1000,lambda:ready.set(True));root.wait_variable(ready)
identity=Identifier(cbSize=c.sizeof(Identifier),hWnd=tray.hwnd.value,uID=1)
rect=w.RECT()
result=c.windll.shell32.Shell_NotifyIconGetRect(c.byref(identity),c.byref(rect))
assert result>=0,result
assert rect.right>rect.left and rect.bottom>rect.top
root.withdraw();root.update()
c.windll.user32.SendMessageW(tray.hwnd,tray.message,1,0x202)
root.update()
assert root.winfo_viewable()
tray.on_exit()
assert not tray.active
assert c.windll.shell32.Shell_NotifyIconGetRect(c.byref(identity),c.byref(rect))<0
print('TRAY_OK: Explorer icon registered, click restores hidden window, exit removes icon')
