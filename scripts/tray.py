"""Windows notification-area icon, using the Tk window's message loop."""
import ctypes as c
from ctypes import wintypes as w
from queue import SimpleQueue
from window_ui import window_handle

GROUP='CodexQuotaResume.Tray.v1'
ENUM_WINDOWS=c.WINFUNCTYPE(w.BOOL,w.HWND,w.LPARAM)


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
        self.active=False
        self.closed=False
        self.timer=None
        self.group=GROUP
        self.kernel=c.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateMutexW.argtypes=[c.c_void_p,w.BOOL,w.LPCWSTR]
        self.kernel.CreateMutexW.restype=c.c_void_p
        self.kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]
        self.kernel.WaitForSingleObject.restype=w.DWORD
        self.kernel.ReleaseMutex.argtypes=[w.HANDLE]
        self.kernel.CloseHandle.argtypes=[c.c_void_p]
        self.mutex=self.kernel.CreateMutexW(None,False,'Local\\'+self.group)
        if not self.mutex:raise c.WinError(c.get_last_error())
        self.user=c.WinDLL('user32',use_last_error=True)
        self.shell=c.windll.shell32
        self.user.SendMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
        self.user.SendMessageW.restype=c.c_ssize_t
        self.user.CallWindowProcW.argtypes=[c.c_void_p,w.HWND,w.UINT,w.WPARAM,w.LPARAM]
        self.user.CallWindowProcW.restype=c.c_ssize_t
        self.user.SetWindowLongPtrW.argtypes=[w.HWND,c.c_int,c.c_void_p]
        self.user.SetWindowLongPtrW.restype=c.c_void_p
        self.user.CreatePopupMenu.restype=w.HMENU
        self.user.AppendMenuW.argtypes=[w.HMENU,w.UINT,c.c_size_t,w.LPCWSTR]
        self.user.TrackPopupMenu.argtypes=[w.HMENU,w.UINT,c.c_int,c.c_int,c.c_int,w.HWND,c.c_void_p]
        self.user.DestroyMenu.argtypes=[w.HMENU]
        self.user.SetPropW.argtypes=[w.HWND,w.LPCWSTR,w.HANDLE]
        self.user.GetPropW.argtypes=[w.HWND,w.LPCWSTR]
        self.user.GetPropW.restype=w.HANDLE
        self.user.RemovePropW.argtypes=[w.HWND,w.LPCWSTR]
        self.user.RemovePropW.restype=w.HANDLE
        self.user.EnumWindows.argtypes=[ENUM_WINDOWS,w.LPARAM]
        self.user.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
        self.user.RegisterWindowMessageW.argtypes=[w.LPCWSTR]
        root.update()
        self.hwnd=window_handle(root)
        self.message=0x8001
        self.restart=self.user.RegisterWindowMessageW('TaskbarCreated')
        self.command=self.user.RegisterWindowMessageW(self.group)
        self.data=IconData(cbSize=c.sizeof(IconData),hWnd=self.hwnd.value,uID=1,
                           uFlags=7,uCallbackMessage=self.message,
                           hIcon=self.user.SendMessageW(self.hwnd,0x7f,1,0),
                           szTip='Codex 自动续跑 — 点击打开所有主窗口')
        callback=c.WINFUNCTYPE(c.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM)
        self.callback=callback(self.handle)
        self.previous=self.user.SetWindowLongPtrW(self.hwnd,-4,c.cast(self.callback,c.c_void_p))
        root.bind('<Destroy>',self.close,add='+')
        try:
            if not self.user.SetPropW(self.hwnd,self.group,1):raise c.WinError(c.get_last_error())
            self.poll()
        except Exception:
            self.close()
            raise

    def claim(self):
        if self.active:return
        result=self.kernel.WaitForSingleObject(self.mutex,0)
        if result==258:return  # Another process owns the tray.
        if result not in (0,0x80):raise c.WinError(c.get_last_error())
        # WAIT_ABANDONED also grants ownership after the previous owner crashed.
        self.active=bool(self.shell.Shell_NotifyIconW(0,c.byref(self.data)))
        if not self.active:
            self.kernel.ReleaseMutex(self.mutex)
            raise OSError('无法创建系统托盘图标')

    def poll(self):
        if self.closed:return
        while not self.events.empty():
            action=self.events.get()
            if action=='show':self.restore()
            elif action=='hide':self.root.withdraw()
            elif action=='menu':self.menu()
            elif action=='show-all':self.broadcast(1)
            elif action=='exit':self.on_exit()
            elif action=='restart' and self.active:self.shell.Shell_NotifyIconW(0,c.byref(self.data))
            if self.closed:return
        self.claim()
        self.timer=self.root.after(100,self.poll)

    def broadcast(self,action):
        def visit(hwnd,_):
            if self.user.GetPropW(hwnd,self.group):self.user.PostMessageW(hwnd,self.command,action,0)
            return True
        self.user.EnumWindows(ENUM_WINDOWS(visit),0)

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
            self.events.put('restart')
        elif message==self.command:
            if wp==1:self.events.put('show')
            elif wp==2:self.events.put('exit')
            return 0
        elif message==self.message:
            if lp==0x202:self.events.put('show-all')  # Never reenter Tcl from WndProc.
            elif lp==0x205:self.events.put('menu')
            return 0
        return self.user.CallWindowProcW(self.previous,hwnd,message,wp,lp)

    def menu(self):
        menu=self.user.CreatePopupMenu()
        try:
            self.user.AppendMenuW(menu,0,1,'打开所有主窗口')
            self.user.AppendMenuW(menu,0,2,'退出所有界面（后台监控继续）')
            point=w.POINT();self.user.GetCursorPos(c.byref(point))
            self.user.SetForegroundWindow(self.hwnd)
            action=self.user.TrackPopupMenu(menu,0x100|0x2,point.x,point.y,0,self.hwnd,None)
            if action in (1,2):self.broadcast(action)
        finally:self.user.DestroyMenu(menu)

    def close(self,event=None):
        if event is not None and event.widget!=self.root:return
        if self.closed:return
        self.closed=True
        if self.timer:self.root.after_cancel(self.timer)
        self.user.RemovePropW(self.hwnd,self.group)
        self.user.SetWindowLongPtrW(self.hwnd,-4,self.previous)
        if self.active:
            self.shell.Shell_NotifyIconW(2,c.byref(self.data))
            self.kernel.ReleaseMutex(self.mutex)
            self.active=False
        if self.mutex:
            self.kernel.CloseHandle(self.mutex)
            self.mutex=None
