"""macOS main layout; callbacks and task operations remain in app.py."""
import tkinter as tk
from tkinter import font as tkfont
from PIL import Image,ImageDraw,ImageTk
from types import SimpleNamespace
from window_ui import rounded_window,RoundedButton,TaskPicker,FONT_FAMILY
from macos_appearance import Appearance,status_presentation


def build(root,version,close_main):
    root.title('Codex Quota Resume')
    appearance=Appearance(root);colors=appearance.colors
    frame=rounded_window(root,480,600,surface=colors['window'])
    appearance.bind(root,bg='window');appearance.bind(frame,bg='window')
    def box(parent,role='window'):
        return appearance.bind(tk.Frame(parent,bg=colors[role]),bg=role)
    def label(parent,text='',size=11,role='text',bold=False,bg='window'):
        return appearance.bind(tk.Label(parent,text=text,font=(FONT_FAMILY,size,'bold' if bold else 'normal'),anchor='w',justify='left',bg=colors[bg],fg=colors[role]),bg=bg,fg=role)
    def button(parent,text,primary=False,compact=False):
        return appearance.bind(RoundedButton(parent,text=text,font=(FONT_FAMILY,11),bg=colors['blue' if primary else 'field'],fg=colors['white' if primary else 'text'],padx=12,pady=6 if compact else 10),bg='blue' if primary else 'field',fg='white' if primary else 'text')
    header=box(frame);header.pack(fill='x',pady=(0,20))
    label(header,'Codex Quota Resume',19,bold=True).pack(fill='x')
    label(header,'macOS Developer Preview',9,role='secondary').pack(fill='x',pady=(4,0))
    pill=label(frame,'● 正在读取状态',12,bold=True);pill.configure(padx=12,pady=7);pill.pack(anchor='w',pady=(0,12))
    status=label(frame,'正在读取运行状态…',12);status.configure(wraplength=420);status.pack(fill='x',pady=(0,8))
    detail=label(frame,'',9,role='secondary');detail.pack(fill='x')
    actions=box(frame);actions.pack(fill='x',pady=(16,24))
    enable=button(actions,'更新状态',compact=True);enable.pack(side='left',padx=(0,8))
    pause=button(actions,'暂停监控',compact=True);pause.pack(side='left',padx=(0,8))
    logs=button(actions,'运行记录',compact=True);logs.pack(side='left')
    card=box(frame,'card');card.configure(padx=16,pady=16);card.pack(fill='both',expand=True)
    row=box(card,'card');row.pack(fill='x',pady=(0,12))
    label(row,'后续任务',12,bold=True,bg='card').pack(side='left')
    refresh=button(row,'↻ 刷新',compact=True);refresh.pack(side='right')
    select=TaskPicker(card,(FONT_FAMILY,11),light=appearance.name=='light');select.pack(fill='x')
    select.apply_appearance(appearance)
    summary=label(card,'尚未添加后续要求',10,role='secondary',bg='card');summary.pack(fill='x',pady=(16,8))
    preview=label(card,'保存后，后续要求会在原任务结束且有额度时发送。',11,bg='card');preview.configure(wraplength=380,anchor='nw');preview.pack(fill='both',expand=True,pady=(0,16))
    plan_actions=box(card,'card');plan_actions.pack(fill='x')
    compose=button(plan_actions,'+ 添加后续任务',primary=True);compose.pack(side='left',padx=(0,8))
    send=button(plan_actions,'立即发送');send.pack(side='right')
    note=label(frame,'关闭窗口后，后台监控继续运行。',9,role='secondary');note.configure(wraplength=420);note.pack(fill='x',pady=(12,8))
    footer=box(frame);footer.pack(fill='x')
    label(footer,'v'+version,9,role='secondary').pack(side='left')
    update=button(footer,'检查更新',compact=True);update.pack(side='right')
    github=button(footer,'GitHub',compact=True);github.pack(side='right',padx=(0,8))
    tone_state=['neutral']
    def render_pill():
        if not pill.winfo_exists():return
        tone=tone_state[0];c=appearance.colors
        font=tkfont.Font(font=pill.cget('font'))
        width=font.measure(pill.cget('text'))+24;height=font.metrics('linespace')+14
        surface=Image.new('RGB',(width*3,height*3),c['window'])
        ImageDraw.Draw(surface).rounded_rectangle((0,0,width*3-1,height*3-1),radius=height*1.5,fill=c['neutral_bg' if tone=='neutral' else tone+'_bg'])
        pill.photo=ImageTk.PhotoImage(surface.resize((width,height),Image.Resampling.LANCZOS),master=pill)
        pill.configure(image=pill.photo,compound='center',padx=0,pady=0)
    appearance.changed(render_pill)
    def state(code,enabled,paused):
        text,tone=status_presentation(code,enabled,paused);pill.configure(text=text)
        tone_state[0]=tone
        appearance.bind(pill,bg='window',fg='secondary' if tone=='neutral' else tone)
        render_pill()
    def saved(plan):
        pending=plan.get('status') in ('saved','sending','send-failed','cancelled')
        summary.configure(text=('已保存 1 条后续要求'+(' · 含附件' if plan.get('images') or plan.get('files') else '')) if pending else '尚未添加后续要求')
        content=' '.join(plan.get('text','').split()) if pending else ''
        preview.configure(text=(content[:180]+('…' if len(content)>180 else '')) or ('包含图片或文件附件' if pending else '保存后，后续要求会在原任务结束且有额度时发送。'))
        compose.configure(text='编辑后续任务' if pending else '+ 添加后续任务');send.configure(state='normal' if pending else 'disabled')
    return SimpleNamespace(frame=frame,status=status,detail=detail,note=note,enable=enable,pause=pause,logs=logs,select=select,compose=compose,refresh=refresh,send=send,update=update,github=github,state=state,saved=saved,appearance=appearance)
