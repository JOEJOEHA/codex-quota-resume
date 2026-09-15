"""Windows desktop entry point; frozen builds include Python, Tk and Pillow."""
import argparse
import ctypes
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import tempfile
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import quota_watcher as w
from window_ui import rounded_window, bind_drag, window_controls, RoundedButton, TaskPicker


TASK_NAMES=('Codex Quota Resume Watcher','Codex Quota Resume Backup')


def run_command(command):
    result = subprocess.run(command,
                            capture_output=True,text=True,encoding='utf-8',errors='replace',
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout


def task_xml(executable, minutes, args):
    task=ET.Element('Task',version='1.2',xmlns='http://schemas.microsoft.com/windows/2004/02/mit/task')
    def add(parent,name,text=None,**attributes):
        node=ET.SubElement(parent,name,attributes);node.text=text;return node
    trigger=add(add(task,'Triggers'),'TimeTrigger')
    repetition=add(trigger,'Repetition');add(repetition,'Interval',f'PT{minutes}M')
    add(trigger,'StartBoundary',(datetime.now()+timedelta(minutes=1)).isoformat(timespec='seconds'))
    add(trigger,'Enabled','true')
    principal=add(add(task,'Principals'),'Principal',id='Author')
    add(principal,'UserId',os.environ['USERDOMAIN']+'\\'+os.environ['USERNAME'])
    add(principal,'LogonType','InteractiveToken');add(principal,'RunLevel','LeastPrivilege')
    settings=add(task,'Settings')
    for key,value in [('MultipleInstancesPolicy','IgnoreNew'),('DisallowStartIfOnBatteries','false'),
                      ('StopIfGoingOnBatteries','false'),('StartWhenAvailable','true'),
                      ('Enabled','true'),('ExecutionTimeLimit','PT0S')]:add(settings,key,value)
    action=add(add(task,'Actions',Context='Author'),'Exec')
    add(action,'Command',str(executable));add(action,'Arguments',args)
    add(action,'WorkingDirectory',str(Path(executable).parent))
    return ET.tostring(task,encoding='unicode')


def pause():
    for name in TASK_NAMES:run_command(['schtasks.exe','/Change','/TN',name,'/DISABLE'])
    (w.APP_DIR/'paused.flag').touch()
    return '已暂停后续调度；正在执行的任务不受影响。'


def monitor_indicator():
    try:
        command="$ErrorActionPreference='Stop';$s=New-Object -ComObject Schedule.Service;$s.Connect();"
        command+="@('Codex Quota Resume Watcher','Codex Quota Resume Backup') | ForEach-Object {$s.GetFolder('\\').GetTask($_).Enabled} | ConvertTo-Json -Compress"
        enabled=json.loads(run_command(['powershell.exe','-NoProfile','-NonInteractive','-Command',command]))
        if not isinstance(enabled,list) or len(enabled)!=2 or any(type(x) is not bool for x in enabled):
            raise ValueError('Unknown task state')
        if all(enabled):return ('● 监控已启用（主备）','#43c77a',True)
        if not any(enabled):return ('● 监控已暂停','#999999',False)
        return ('● 监控未全部启用','#e5b454',False)
    except (RuntimeError,ValueError,ET.ParseError,OSError):
        return ('● 未启用或无法确认监控状态','#e5b454',False)


def install():
    if not getattr(sys,'frozen',False):
        raise RuntimeError('请使用打包后的 EXE 启用后台监控，源码用户运行 install_windows.ps1。')
    w.codex_status.available(w.find_codex())
    w.APP_DIR.mkdir(parents=True,exist_ok=True)
    destination=w.APP_DIR/Path(sys.executable).name
    if Path(sys.executable).resolve()!=destination.resolve():
        shutil.copy2(sys.executable,destination)
    state=w.load_state()
    state.setdefault('monitoringSince',time.time())
    w.save_state(state)
    with tempfile.TemporaryDirectory() as directory:
        xml=Path(directory)/'task.xml'
        for name,minutes,args in zip(TASK_NAMES,(1,5),('--monitor','--monitor --backup')):
            xml.write_text(task_xml(destination,minutes,args),encoding='utf-16')
            run_command(['schtasks.exe','/Create','/TN',name,'/XML',str(xml),'/F'])
            run_command(['schtasks.exe','/Run','/TN',name])
    (w.APP_DIR/'paused.flag').unlink(missing_ok=True)
    target=str(destination).replace("'","''")
    run_command(['powershell.exe','-NoProfile','-NonInteractive','-Command',
                 "$p=Join-Path ([Environment]::GetFolderPath('Desktop')) 'Codex Quota Resume.lnk';"
                 "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($p);"
                 f"$s.TargetPath='{target}';$s.IconLocation='{target},0';$s.Save()"])
    return '已启用主备监控，并创建桌面快捷方式。'


def show():
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root=tk.Tk()
    root.title('Codex Quota Resume')
    frame=rounded_window(root,430,535)
    style=ttk.Style(root); style.theme_use('clam')
    style.configure('TScrollbar',background='#383838',troughcolor='#242424',
                    bordercolor='#242424',arrowcolor='#aaaaaa',lightcolor='#383838',darkcolor='#383838')
    style.map('TScrollbar',background=[('active','#494949')])

    font=('Microsoft YaHei UI',11)
    def label(text,color='#eeeeee',size=11):
        item=tk.Label(frame,text=text,bg='#181818',fg=color,font=('Microsoft YaHei UI',size),anchor='w',justify='left',wraplength=374)
        item.pack(fill='x',pady=(0,8));bind_drag(root,item);return item
    top=tk.Frame(frame,bg='#181818');top.pack(fill='x',pady=(0,10))
    title=tk.Label(top,text='Codex 自动续跑',bg='#181818',fg='#eeeeee',font=('Microsoft YaHei UI',16))
    title.pack(side='left')
    window_controls(root,top,font)
    monitor_dot=tk.Canvas(top,width=36,height=36,bg='#181818',highlightthickness=0)
    monitor_dot.pack(side='right',padx=(0,8))
    dot=monitor_dot.create_oval(3,3,33,33,fill='#ef5350',outline='')
    bind_drag(root,top,title,monitor_dot)
    label('有额度就继续 · 本地监控 · 后续任务支持截图', '#aaaaaa')
    status=label('正在读取运行状态…',size=14)
    detail=label('', '#aaaaaa',10)
    note=label('首次使用请点击“启用 / 更新监控”。关闭此窗口后，计划任务仍会运行。','#aaaaaa',10)
    actions=tk.Frame(frame,bg='#181818');actions.pack(fill='x',pady=(2,18))
    results=queue.Queue();busy=[False];threads=[]
    def background(job):
        if busy[0]:return
        busy[0]=True;note.configure(text='处理中…')
        def work():
            try:results.put(('ok',job()))
            except Exception as error:results.put(('error',str(error)))
        threading.Thread(target=work,daemon=True).start()
    def button(parent,text,command,blue=False):
        b=RoundedButton(parent,text=text,command=command,bg='#2d6acb' if blue else '#2b2b2b',font=('Microsoft YaHei UI',10),padx=10)
        b.pack(side='left',padx=(0,6));return b
    enable_button=button(actions,'启用 / 更新监控',lambda:background(install),True)
    button(actions,'暂停监控',lambda:background(pause))
    button(actions,'打开运行记录',lambda:os.startfile(w.APP_DIR))
    label('选择任务，填写后续需求',size=13)
    select=TaskPicker(frame,font=font);select.pack(fill='x',pady=(0,12))
    def get_threads():
        with w.codex_status.connection(w.find_codex()) as request:
            data=request('thread/list',{'limit':30,'sortKey':'updated_at','sortDirection':'desc'})['data']
        return data
    def load_threads():
        background(get_threads)
    def compose():
        index=select.current()
        if index<0:
            messagebox.showinfo('选择任务','先刷新并选择一个任务。',parent=root);return
        command=w.self_command('--plan',threads[index]['id'])
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=1
        subprocess.Popen(command,startupinfo=startup,
                         env={**os.environ,'PYINSTALLER_RESET_ENVIRONMENT':'1'})
    plan_actions=tk.Frame(frame,bg='#181818');plan_actions.pack(fill='x')
    button(plan_actions,'打开需求输入框',compose,True)
    button(plan_actions,'刷新任务',load_threads)
    label('后续需求会在监控器恢复的原任务完成后发送。', '#999999',10)
    names={'waiting-quota':'等待额度恢复','no-quota-stall':'未发现需要续跑的额度中断任务',
           'resuming':'正在续跑','resumed':'本次续跑已返回','queued-awaiting-start':'已交给 Codex，等待开始',
           'waiting-start':'等待任务开始确认','dispatch-unconfirmed':'任务尚未确认开始，请查看运行记录',
           'dispatch-active':'原任务正在执行','resume-failed':'续跑失败，请查看运行记录',
           'retry-backoff':'上次启动失败，等待重试','task-changed':'任务状态已变化',
           'followup-sent':'后续需求已发送','followup-waiting-completion':'等待原任务完成验收'}
    def tick():
        state=w.load_state();code=state.get('status','not-installed')
        stamp=state.get('lastCheckedAt')
        status.configure(text=names.get(code,'尚未启用监控' if code=='not-installed' else code))
        detail.configure(text=('最近检查 '+time.strftime('%m-%d %H:%M:%S',time.localtime(stamp)) if stamp else '尚无检查记录')+'  ·  '+{'primary':'主监控','backup':'备用监控'}.get(state.get('lastMonitor'),''))
        try:
            kind,value=results.get_nowait()
            if kind=='monitor':
                text,color,enabled=value
                monitor_dot.itemconfigure(dot,fill='#43c77a' if enabled else '#ef5350')
                enable_button.configure(text='更新监控' if enabled else '启用 / 更新监控',
                                        bg='#21854d' if enabled else '#2d6acb')
            elif kind=='error':
                busy[0]=False
                note.configure(text='操作失败，详情已显示');messagebox.showerror('操作失败',value,parent=root)
            elif isinstance(value,list):
                busy[0]=False
                threads[:]=value
                select.set_values([(x.get('name') or x.get('preview') or x['id']).replace('\n',' ')[:65] for x in value])
                if threads:select.current(0)
                note.configure(text='任务列表已更新。')
            else:
                busy[0]=False
                note.configure(text=value.strip() or '操作完成。')
                threading.Thread(target=lambda:results.put(('monitor',monitor_indicator())),daemon=True).start()
        except queue.Empty:pass
        root.after(1000,tick)
    def refresh_monitor():
        while True:
            results.put(('monitor',monitor_indicator()))
            time.sleep(5)
    tick();load_threads()
    threading.Thread(target=refresh_monitor,daemon=True).start()
    root.lift()
    root.mainloop()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--monitor',action='store_true')
    parser.add_argument('--backup',action='store_true')
    parser.add_argument('--plan')
    parser.add_argument('--plan-key')
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--install',action='store_true')
    args=parser.parse_args()
    if args.install:
        install()
    elif args.self_test:
        w.self_test()
    elif args.plan:
        w.plan_dialog(args.plan,args.plan_key)
    elif args.monitor:
        w.run_once(backup=args.backup)
    else:show()


if __name__=='__main__':
    try:main()
    except Exception as error:
        w.log(f'app error {type(error).__name__}: {error}')
        sys.exit(1)
