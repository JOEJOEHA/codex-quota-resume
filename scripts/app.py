"""Desktop entry point; frozen builds include Python, Tk and Pillow."""
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
import webbrowser
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw, ImageTk
import quota_watcher as w
import updater
import plan_dialog  # Load the composer once with the application.
if sys.platform == 'darwin':
    from tray_macos import TrayIcon
else:
    from tray import TrayIcon
from window_ui import rounded_window, bind_drag, window_controls, RoundedButton, TaskPicker, window_handle, place_beside
from window_ui import FONT_FAMILY


TASK_NAMES=('Codex Quota Resume Watcher','Codex Quota Resume Backup')


def run_command(command):
    result = subprocess.run(command,
                            capture_output=True,text=True,encoding='utf-8',errors='replace',
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
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
    if sys.platform == 'darwin':
        import macos
        return macos.pause(w)
    for name in TASK_NAMES:run_command(['schtasks.exe','/Change','/TN',name,'/DISABLE'])
    (w.APP_DIR/'paused.flag').touch()
    return '已暂停后续调度；正在执行的任务不受影响。'


def monitor_indicator():
    if sys.platform == 'darwin':
        import macos
        return macos.monitor_indicator(w)
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
    if sys.platform == 'darwin':
        import macos
        return macos.install(w)
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
    if os.name == 'nt':ctypes.windll.shcore.SetProcessDpiAwareness(1)
    root=tk.Tk()
    root.title('Codex Quota Resume')
    open_plans={}
    exiting=[False]
    def close_main():
        select.hide(restore_focus=False)
        root.withdraw()
    def exit_interface():
        exiting[0]=True
        if open_plans:root.withdraw()
        else:root.destroy()
    root.protocol('WM_DELETE_WINDOW',close_main)
    mac_ui=None
    if sys.platform=='darwin':
        from macos_main_ui import build
        mac_ui=build(root,updater.VERSION,close_main)
        frame,status,detail,note=mac_ui.frame,mac_ui.status,mac_ui.detail,mac_ui.note
    else:
        frame=rounded_window(root,430,535,surface='#ffffff',border='#dfe3e8')
        footer=tk.Frame(frame,bg='#ffffff');footer.pack(side='bottom',fill='x',pady=(8,0))
        tk.Label(footer,text='v'+updater.VERSION,bg='#ffffff',fg='#6b7280',font=(FONT_FAMILY,9)).pack(side='left')
        style=ttk.Style(root); style.theme_use('clam')
        style.configure('TScrollbar',background='#d1d5db',troughcolor='#f3f4f6',
                        bordercolor='#f3f4f6',arrowcolor='#5f6368',lightcolor='#d1d5db',darkcolor='#d1d5db')
        style.map('TScrollbar',background=[('active','#9ca3af')])

        font=(FONT_FAMILY,11)
        def label(text,color='#202124',size=11):
            item=tk.Label(frame,text=text,bg='#ffffff',fg=color,font=(FONT_FAMILY,size),anchor='w',justify='left',wraplength=374)
            item.pack(fill='x',pady=(0,8));bind_drag(root,item);return item
        top=tk.Frame(frame,bg='#ffffff');top.pack(fill='x',pady=(0,10))
        title=tk.Label(top,text='Codex 自动续跑',bg='#ffffff',fg='#202124',font=(FONT_FAMILY,16))
        title.pack(side='left')
        window_controls(root,top,font,on_close=close_main,on_minimize=close_main,light=True)
        monitor_dot=tk.Canvas(top,width=36,height=36,bg='#ffffff',highlightthickness=0)
        monitor_dot.pack(side='right',padx=(0,8))
        dot_images={}
        for enabled,color in ((True,'#43c77a'),(False,'#ef5350')):
            image=Image.new('RGB',(144,144),'#ffffff')
            ImageDraw.Draw(image).ellipse((12,12,131,131),fill=color)
            dot_images[enabled]=ImageTk.PhotoImage(image.resize((36,36),Image.Resampling.LANCZOS),master=root)
        dot=monitor_dot.create_image(0,0,anchor='nw',image=dot_images[False])
        bind_drag(root,top,title,monitor_dot)
        label('有额度就继续 · 本地监控 · 后续任务支持截图', '#5f6368')
        status=label('正在读取运行状态…',size=14)
        detail=label('', '#5f6368',10)
        note=label('首次使用请点击“启用 / 更新监控”。关闭此窗口后，计划任务仍会运行。','#5f6368',10)
        actions=tk.Frame(frame,bg='#ffffff');actions.pack(fill='x',pady=(2,18))
    results=queue.Queue();busy=[False];threads=[]
    def background(job):
        if busy[0]:return
        busy[0]=True;note.configure(text='处理中…')
        def work():
            try:results.put(('ok',job()))
            except Exception as error:results.put(('error',str(error)))
        threading.Thread(target=work,daemon=True).start()
    def check_update():
        if busy[0]:return
        update_button.configure(text='检查中…')
        if sys.platform=='darwin':background(updater.check_macos_update)
        else:background(lambda:updater.update(w.APP_DIR,lambda text:results.put(('update-progress',text))))
    if mac_ui:
        update_button=mac_ui.update;update_button.configure(command=check_update)
        enable_button=mac_ui.enable;enable_button.configure(command=lambda:background(install))
        mac_ui.pause.configure(command=lambda:background(pause))
        mac_ui.logs.configure(command=lambda:subprocess.Popen(['/usr/bin/open',str(w.APP_DIR)]))
        mac_ui.github.configure(command=lambda:webbrowser.open('https://github.com/joejoeha/codex-quota-resume'))
        select=mac_ui.select
    else:
        update_button=RoundedButton(footer,text='检查更新',command=check_update,font=(FONT_FAMILY,9),padx=10,pady=5,bg='#f3f4f6',fg='#3c4043')
        update_button.pack(side='right')
        github_path=Path(__file__).with_name('github-mark.png')
        if not github_path.exists():github_path=Path(__file__).parent.parent/'assets'/'github-mark.png'
        with Image.open(github_path) as icon:
            ink=Image.new('RGBA',icon.size,'#24292f')
            ink.putalpha(icon.convert('RGBA').getchannel('A'))
            github_icon=ImageTk.PhotoImage(ink.resize((16,16),Image.Resampling.LANCZOS),master=root)
        github_button=tk.Button(footer,name='github_link',image=github_icon,
            command=lambda:webbrowser.open('https://github.com/joejoeha/codex-quota-resume'),
            bg='#ffffff',activebackground='#f3f4f6',bd=0,highlightthickness=0,
            padx=8,pady=7,cursor='hand2',takefocus=True)
        github_button.image=github_icon
        github_button.pack(side='right',padx=(0,12))
        def button(parent,text,command,blue=False):
            b=RoundedButton(parent,text=text,command=command,bg='#2563eb' if blue else '#f3f4f6',fg='white' if blue else '#202124',font=(FONT_FAMILY,10),padx=10)
            b.pack(side='left',padx=(0,6));return b
        enable_button=button(actions,'启用 / 更新监控',lambda:background(install),True)
        button(actions,'暂停监控',lambda:background(pause))
        button(actions,'打开运行记录',lambda:subprocess.Popen(['/usr/bin/open',str(w.APP_DIR)]) if sys.platform=='darwin' else os.startfile(w.APP_DIR))
        label('选择任务，填写后续需求',size=13)
        select=TaskPicker(frame,font=font,light=True);select.pack(fill='x',pady=(0,12))
    def refresh_pending(blink=False):
        index=select.current()
        pending=False
        plan={}
        if 0<=index<len(threads):
            try:
                plan=json.loads(w.plan_path(threads[index]['id']).read_text(encoding='utf-8'))
                pending=plan.get('status') in ('saved','sending','send-failed','cancelled')
            except (OSError,ValueError):pass
        select.set_pending(pending,blink=blink)
        if mac_ui:mac_ui.saved(plan)
    def saved_feedback(thread):
        note.configure(text='已收到并保存后续任务。')
        index=select.current()
        if 0<=index<len(threads) and threads[index]['id']==thread:refresh_pending(blink=True)
    def get_threads():
        with w.codex_status.connection(w.find_codex()) as request:
            data=request('thread/list',{'limit':30,'sortKey':'updated_at','sortDirection':'desc'})['data']
        return data
    def load_threads():
        background(get_threads)
    def compose(thread=None):
        if thread:
            index=next((i for i,item in enumerate(threads) if item['id']==thread),None)
            if index is None:
                threads.append({'id':thread,'name':'额度中断任务'})
                select.set_values([(x.get('name') or x.get('preview') or x['id']).replace('\n',' ')[:65] for x in threads])
                index=len(threads)-1
            select.current(index)
        index=select.current()
        if index<0:
            messagebox.showinfo('选择任务','先刷新并选择一个任务。',parent=root);return
        thread=threads[index]['id']
        try:place_beside(open_plans.get(thread),root)
        except ValueError as error:
            messagebox.showinfo('输入窗排放',str(error),parent=root);return
        if thread in open_plans:
            dialog=open_plans[thread]
            place_beside(dialog,root)
            if os.name == 'nt':ctypes.windll.user32.ShowWindow(window_handle(dialog),9)
            dialog.deiconify();place_beside(dialog,root);dialog.lift();dialog.focus_force()
            return
        task_name=(threads[index].get('name') or threads[index].get('preview') or '当前任务').replace('\n',' ')
        dialog=w.plan_dialog(thread,parent=root,task_name=task_name,on_saved=saved_feedback)
        open_plans[thread]=dialog
        def closed(event):
            if event.widget!=dialog:return
            open_plans.pop(thread,None)
            if not open_plans and exiting[0]:root.destroy()
        dialog.bind('<Destroy>',closed,add='+')
    if mac_ui:
        mac_ui.compose.configure(command=compose)
        mac_ui.refresh.configure(command=load_threads)
    else:
        plan_actions=tk.Frame(frame,bg='#ffffff');plan_actions.pack(fill='x')
        button(plan_actions,'打开需求输入框',compose,True)
        button(plan_actions,'刷新任务',load_threads)
    def send_saved():
        index=select.current()
        if index<0:return
        thread=threads[index]['id']
        background(lambda:w.request_plan_send(thread))
    if mac_ui:mac_ui.send.configure(command=send_saved)
    else:button(plan_actions,'发送已存任务',send_saved)

    names={'followup-waiting-delay':'续跑已请求，等待 10 秒发送后续需求','waiting-quota':'等待额度恢复','no-quota-stall':'未发现需要续跑的额度中断任务',
           'resuming':'正在续跑','resumed':'本次续跑已返回','queued-awaiting-start':'已交给 Codex，等待开始',
           'waiting-start':'等待任务开始确认','dispatch-unconfirmed':'任务尚未确认开始，请查看运行记录',
           'dispatch-active':'原任务正在执行','resume-failed':'续跑失败，请查看运行记录',
           'retry-backoff':'上次启动失败，等待重试','task-changed':'任务状态已变化',
           'followup-sent':'后续需求已发送','followup-waiting-completion':'已保存，等待原任务的验收完成标记',
           'followup-waiting-resume':'已保存，等待原任务续跑并完成验收',
           'followup-waiting-idle':'已保存，等待原任务结束',
           'followup-waiting-quota':'已保存，等待额度可用',
           'followup-queued':'已交给 Codex，等待后续任务开始',
           'followup-cancelled':'原任务已取消，后续需求保留为草稿，等待手动确认',
           'paused':'监控已暂停',
           'followup-waiting-evidence':'已保存，暂时无法读取原任务记录',
           'followup-send-failed':'后续任务发送失败，请查看记录',
           'followup-unconfirmed':'发送结果待确认，请勿重复发送',
           'followup-missing-image':'图片丢失，请重新添加',
           'followup-missing-file':'附件丢失，请重新添加'}
    monitor_enabled=[None]
    def tick():
        w.APP_DIR.mkdir(parents=True,exist_ok=True)
        (w.APP_DIR/'ui-heartbeat').touch()
        refresh_pending()
        state=w.load_state();code=state.get('status','not-installed')
        stamp=state.get('lastCheckedAt')
        if mac_ui:mac_ui.state(code,monitor_enabled[0],(w.APP_DIR/'paused.flag').exists())
        status.configure(text=names.get(code,'尚未启用监控' if code=='not-installed' else code))
        detail.configure(text=('最近检查 '+time.strftime('%m-%d %H:%M:%S',time.localtime(stamp)) if stamp else '尚无检查记录')+'  ·  '+{'primary':'主监控','backup':'备用监控'}.get(state.get('lastMonitor'),''))
        try:
            kind,value=results.get_nowait()
            if kind=='quota-popup':
                claim=w.claim_popup(value)
                if claim:
                    try:
                        root.deiconify()
                        compose(value['threadId'])
                        if value['threadId'] not in open_plans:claim.unlink(missing_ok=True)
                    except Exception:
                        claim.unlink(missing_ok=True)
                        raise
            elif kind=='monitor':
                text,color,enabled=value
                monitor_enabled[0]=enabled
                if mac_ui:
                    enable_button.configure(text='更新状态' if enabled else '启用监控')
                    mac_ui.state(code,enabled,(w.APP_DIR/'paused.flag').exists())
                else:
                    monitor_dot.itemconfigure(dot,image=dot_images[enabled])
                    enable_button.configure(text='更新监控' if enabled else '启用 / 更新监控',bg='#21854d' if enabled else '#2d6acb')
            elif kind=='update-progress':
                note.configure(text=value)
            elif isinstance(value,dict) and value.get('macosUpdate'):
                busy[0]=False
                update_button.configure(text='检查更新')
                if value['available']:
                    note.configure(text='发现新版 '+value['version']+'，可从发布页下载。')
                    availability=('包含当前 Mac 架构的下载包。' if value.get('downloadUrl') else
                                  '尚未确认当前 Mac 架构的附件，请在发布页查看。')
                    notes=value.get('notes','').strip()
                    if len(notes)>600:notes=notes[:600]+'…'
                    message='发现 '+value['version']+'\n'+availability
                    if notes:message+='\n\n'+notes
                    message+='\n\n打开 GitHub 下载页？'
                    if messagebox.askyesno('发现新版本',message,parent=root):
                        webbrowser.open(value['releaseUrl'])
                else:
                    note.configure(text=('GitHub API 限流；未发现更新的正式版，预览版请查看发布页。'
                                         if value.get('limited') else '未发现更新的发布版本。'))
            elif isinstance(value,dict) and 'updated' in value:
                busy[0]=False
                update_button.configure(text='检查更新')
                note.configure(text=('已安装 '+value['version'] if value['updated'] else '当前已是最新版本。'))
                if value['updated']:
                    exit_interface()
                    if not open_plans:return
            elif kind=='error':
                update_button.configure(text='检查更新')
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
    popup_since=time.time()
    def refresh_monitor():
        while True:
            try:
                state=w.load_state()
                if not (w.APP_DIR/'paused.flag').exists():
                    candidate=w.latest_candidate(time.time(),state.get('sent',{}),state.get('monitoringSince',popup_since))
                    if candidate:results.put(('quota-popup',candidate))
            except (OSError,ValueError):pass
            results.put(('monitor',monitor_indicator()))
            time.sleep(5)
    tick();load_threads()
    threading.Thread(target=refresh_monitor,daemon=True).start()
    root.lift()
    if sys.platform=='darwin':
        def quit_application():
            try:pause()
            except OSError as error:
                messagebox.showerror('无法退出','暂停监控失败：'+str(error),parent=root)
                return
            exit_interface()
        root.tray=TrayIcon(root,exit_interface,on_quit=quit_application)
    else:root.tray=TrayIcon(root,exit_interface)
    root.mainloop()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--monitor',action='store_true')
    parser.add_argument('--backup',action='store_true')
    parser.add_argument('--plan')
    parser.add_argument('--plan-key')
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--install',action='store_true')
    parser.add_argument('--doctor',action='store_true')
    parser.add_argument('--apply-update',action='store_true')
    args=parser.parse_args()
    if args.doctor:
        try:
            if sys.platform != 'darwin':
                result={'ok':False,'errors':{'platform':{'message':'--doctor requires macOS'}}}
            else:
                import macos
                result=macos.doctor(w)
        except Exception as error:
            result={'ok':False,'errors':{'doctor':{'message':'Diagnostics could not be completed.',
                                               'type':type(error).__name__}}}
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if not result['ok']:raise SystemExit(1)
    elif args.apply_update:
        if sys.platform != 'win32':raise RuntimeError('Automatic installation currently requires Windows')
        w.self_test()
        updater.activate(sys.executable,run_command)
    elif args.install:
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
