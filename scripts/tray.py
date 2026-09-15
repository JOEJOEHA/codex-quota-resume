"""Windows notification-area icon, using the Tk window's message loop."""
import ctypes as c
from ctypes import wintypes as w
from queue import SimpleQueue
from window_ui import window_handle


class IconData(c.Structure):
    _fields_=[('cbSize',w.DWORD),('hWnd',w.HWND),('uID',w.UINT),
              ('uFlags',w.UINT),('uCallbackMessage',w.UINT),('hIcon',w.HICON),
              ('szTip',w.WCHAR*128),('dwState',w.DWORD),('dwStateMask',w.DWORD),
              ('szInfo',w.WCHAR*256),('uVersion',w.UINT),('szInfoTitle',w.WCHAR*64),
              ('dwInfoFlags',w.DWORD),('guidItem',c.c_byte*16),('hBalloonIcon',w.HICON)]


class TrayIcon:
    def __init__(self,root,on_exit):
        self.root=root
        self.events=SimpleQueue()
        self.on_exit=on_exit
        self.user=c.windll.user32
        self.shell=c.windll.shell32
        self.user.SendMessageW.restype=c.c_ssize_t
        self.user.CallWindowProcW.argtypes=[c.c_void_p,w.HWND,w.UINT,w.WPARAM,w.LPARAM]
        self.user.CallWindowProcW.restype=c.c_ssize_t
        self.user.SetWindowLongPtrW.argtypes=[w.HWND,c.c_int,c.c_void_p]
        self.user.SetWindowLongPtrW.restype=c.c_void_p
        self.user.CreatePopupMenu.restype=w.HMENU
        self.user.AppendMenuW.argtypes=[w.HMENU,w.UINT,c.c_size_t,w.LPCWSTR]
        self.user.TrackPopupMenu.argtypes=[w.HMENU,w.UINT,c.c_int,c.c_int,c.c_int,w.HWND,c.c_void_p]
        self.user.DestroyMenu.argtypes=[w.HMENU]
        root.update()
        self.hwnd=window_handle(root)
        self.message=0x8001
        self.restart=self.user.RegisterWindowMessageW('TaskbarCreated')
        self.data=IconData(cbSize=c.sizeof(IconData),hWnd=self.hwnd.value,uID=1,
                           uFlags=7,uCallbackMessage=self.message,
                           hIcon=self.user.SendMessageW(self.hwnd,0x7f,1,0),
                           szTip='Codex 自动续跑 — 点击打开')
        callback=c.WINFUNCTYPE(c.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM)
        self.callback=callback(self.handle)
        self.previous=self.user.SetWindowLongPtrW(self.hwnd,-4,c.cast(self.callback,c.c_void_p))
        self.active=bool(self.shell.Shell_NotifyIconW(0,c.byref(self.data)))
        if not self.active:
            self.user.SetWindowLongPtrW(self.hwnd,-4,self.previous)
            raise OSError('无法创建系统托盘图标')
        root.bind('<Destroy>',self.close,add='+')
        self.poll()

    def poll(self):
        while not self.events.empty():
            action=self.events.get()
            if action=='show':self.restore()
            elif action=='hide':self.root.withdraw()
            elif action=='menu':self.menu()
            if not self.active:return
        self.timer=self.root.after(100,self.poll)

    def restore(self):
        self.root.deiconify()
        self.user.ShowWindow(self.hwnd,9)
        self.root.lift()
        self.user.SetForegroundWindow(self.hwnd)

    def handle(self,hwnd,message,wp,lp):
        if message==0x10:  # Also keep the tray alive for Alt+F4 / taskbar Close.
            self.events.put('hide')
            return 0
        if message==self.restart:
            self.shell.Shell_NotifyIconW(0,c.byref(self.data))
        elif message==self.message:
            if lp==0x202:self.events.put('show')  # Never reenter Tcl from WndProc.
            elif lp==0x205:self.events.put('menu')
            return 0
        return self.user.CallWindowProcW(self.previous,hwnd,message,wp,lp)

    def menu(self):
        menu=self.user.CreatePopupMenu()
        try:
            self.user.AppendMenuW(menu,0,1,'打开主窗口')
            self.user.AppendMenuW(menu,0,2,'退出界面（后台监控继续）')
            point=w.POINT();self.user.GetCursorPos(c.byref(point))
            self.user.SetForegroundWindow(self.hwnd)
            action=self.user.TrackPopupMenu(menu,0x100|0x2,point.x,point.y,0,self.hwnd,None)
            if action==1:self.restore()
            elif action==2:self.on_exit()
        finally:self.user.DestroyMenu(menu)

    def close(self,event=None):
        if event is not None and event.widget!=self.root:return
        if self.active:
            self.root.after_cancel(self.timer)
            self.shell.Shell_NotifyIconW(2,c.byref(self.data))
            self.user.SetWindowLongPtrW(self.hwnd,-4,self.previous)
            self.active=False
