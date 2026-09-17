"""Real Windows processes: one tray, restore all, graceful/crash takeover."""
import ctypes as c
from ctypes import wintypes as w
import multiprocessing as mp
import time
import uuid


class Identifier(c.Structure):
    _fields_=[('cbSize',w.DWORD),('hWnd',w.HWND),('uID',w.UINT),('guidItem',c.c_byte*16)]


def window(connection,group):
    import tkinter as tk
    import tray as tray_module
    from window_ui import rounded_window
    tray_module.GROUP=group
    root=tk.Tk()
    rounded_window(root,300,150)
    root.update()
    tray=tray_module.TrayIcon(root,root.destroy)
    errors=[]
    root.report_callback_exception=lambda kind,error,tb:errors.append(str(error))
    identity=Identifier(cbSize=c.sizeof(Identifier),hWnd=tray.hwnd.value,uID=1)

    def receive():
        if connection.poll():
            action=connection.recv()
            if action=='state':
                rect=w.RECT()
                registered=tray.shell.Shell_NotifyIconGetRect(c.byref(identity),c.byref(rect))>=0
                connection.send((tray.active,bool(root.winfo_viewable()),registered,errors[:]))
            else:
                if action=='hide':tray.user.PostMessageW(tray.hwnd,0x10,0,0)
                elif action=='click':tray.user.PostMessageW(tray.hwnd,tray.message,1,0x202)
                elif action=='exit-all':tray.broadcast(2)
                elif action=='restart':
                    if tray.active:tray.shell.Shell_NotifyIconW(2,c.byref(tray.data))
                    tray.user.PostMessageW(tray.hwnd,tray.restart,0,0)
                elif action=='close':
                    tray.on_exit()
                    assert tray.closed and not tray.active and tray.mutex is None
                    connection.send('ok')
                    return
                connection.send('ok')
        root.after(20,receive)

    connection.send('ready')
    root.after(20,receive)
    root.mainloop()
    assert not errors,errors
    connection.close()


def main():
    context=mp.get_context('spawn')
    group='CodexQuotaResume.Test.'+uuid.uuid4().hex
    workers=[]

    def launch():
        parent,child=context.Pipe()
        process=context.Process(target=window,args=(child,group))
        process.start()
        child.close()
        worker=(process,parent)
        workers.append(worker)
        return worker

    def request(worker,action):
        process,connection=worker
        connection.send(action)
        assert connection.poll(10),(action,process.exitcode)
        return connection.recv()

    def check(live,visible=None):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            states=[request(worker,'state') for worker in live]
            assert not any(state[3] for state in states),states
            assert sum(state[0] for state in states)<=1,states
            if (sum(state[0] for state in states)==1 and
                all(state[0]==state[2] for state in states) and
                (visible is None or all(state[1]==visible for state in states))):
                return next(worker for worker,state in zip(live,states) if state[0])
            time.sleep(.05)
        raise AssertionError(states)

    try:
        live=[launch() for _ in range(3)]
        for process,connection in live:
            assert connection.poll(15) and connection.recv()=='ready',process.exitcode
        owner=check(live,True)
        for worker in live:assert request(worker,'hide')=='ok'
        check(live,False)
        assert request(owner,'click')=='ok'
        check(live,True)
        for worker in live:assert request(worker,'restart')=='ok'
        owner=check(live,True)
        # Closing a non-owner must not remove the shared icon or leave callbacks.
        follower=next(worker for worker in live if worker!=owner)
        assert request(follower,'close')=='ok'
        follower[0].join(10)
        assert follower[0].exitcode==0
        live.remove(follower)
        assert check(live,True)==owner
        replacement=launch()
        assert replacement[1].poll(15) and replacement[1].recv()=='ready'
        live.append(replacement)
        check(live,True)
        assert request(owner,'close')=='ok'
        owner[0].join(10)
        assert owner[0].exitcode==0
        live.remove(owner)
        owner=check(live,True)
        # Only terminate our disposable test process to exercise an abandoned mutex.
        owner[0].terminate();owner[0].join(10)
        live.remove(owner)
        owner=check(live,True)
        replacement=launch()
        assert replacement[1].poll(15) and replacement[1].recv()=='ready'
        live.append(replacement)
        check(live,True)
        assert request(owner,'exit-all')=='ok'
        for process,connection in live:
            process.join(10)
            assert process.exitcode==0,process.exitcode
        print('MULTI_TRAY_OK: one Explorer icon, restore all, restart, close, takeover, crash, exit all')
    finally:
        for process,connection in workers:
            if process.is_alive():process.terminate()
            process.join(10)
            connection.close()


if __name__=='__main__':main()
