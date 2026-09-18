"""Presentation-only macOS appearance. No watcher or persistence dependencies."""
import os
import tkinter as tk
from tkinter import ttk

PALETTES = {
 'light': dict(window='#f5f5f7',card='#ffffff',field='#ececef',text='#242426',secondary='#68686d',separator='#dedee3',blue='#0a64d8',white='#ffffff',good='#31734e',good_bg='#e6f1ea',wait='#805d22',wait_bg='#f4eddc',error='#ad3b3b',error_bg='#f8e7e7',neutral_bg='#e8e8ec'),
 'dark': dict(window='#242426',card='#303033',field='#3a3a3e',text='#ededf0',secondary='#a9a9b1',separator='#48484d',blue='#3478da',white='#ffffff',good='#8dc7a3',good_bg='#293d31',wait='#e0c18a',wait_bg='#423a2a',error='#efa3a3',error_bg='#482e2e',neutral_bg='#3a3a3e'),
}


def system_theme():
    override=os.environ.get('QUOTA_RESUME_THEME')
    if override in PALETTES:return override
    try:
        from AppKit import NSApplication
        name=NSApplication.sharedApplication().effectiveAppearance().bestMatchFromAppearancesWithNames_(['NSAppearanceNameAqua','NSAppearanceNameDarkAqua'])
        return 'dark' if name=='NSAppearanceNameDarkAqua' else 'light'
    except (ImportError,AttributeError):return 'light'


class Appearance:
    """Semantic widget bindings preserve roles when colors coincide."""
    def __init__(self,root):
        self.root,self.name=root,system_theme()
        self.bindings={};self.callbacks=[];self.timer=None
        root.bind('<Destroy>',self.destroyed,add='+')
        self.initial_timer=root.after_idle(self.native_appearance)
        self.poll()
    @property
    def colors(self):return PALETTES[self.name]
    def bind(self,widget,**roles):
        self.bindings[widget]=roles;self.paint(widget);return widget
    def paint(self,widget):
        widget.configure(**{option:self.colors[role] for option,role in self.bindings[widget].items()})
    def adopt(self,root):
        roles={'#181818':'window','#2b2b2b':'field','#242424':'card',
               '#eeeeee':'text','#f3f3f3':'text','#dddddd':'text',
               '#aaaaaa':'secondary','#999999':'secondary',
               '#365c91':'blue','#2d6acb':'blue','#ff9a9a':'error',
               '#e7b66a':'wait','white':'text'}
        def visit(widget):
            values={}
            options=widget.keys()
            for option in ('bg','fg','insertbackground','selectbackground','selectforeground'):
                if option not in options:continue
                color=widget.fill if option=='bg' and hasattr(widget,'fill') else widget.cget(option)
                if color in roles:values[option]=roles[color]
            if isinstance(widget,tk.Button) and hasattr(widget,'fill') and widget.fill=='#2d6acb':
                values['fg']='white'
            if isinstance(widget,tk.Frame) and widget==root:values['bg']='window'
            if values.get('selectbackground')=='blue' and 'selectforeground' in options:
                values['selectforeground']='white'
            if values:self.bind(widget,**values)
            for child in widget.winfo_children():visit(child)
        visit(root)

    def changed(self,callback):self.callbacks.append(callback)
    def native_appearance(self):
        self.initial_timer=None
        if not self.root.winfo_exists():return
        from AppKit import NSApplication,NSAppearance
        name='NSAppearanceNameDarkAqua' if self.name=='dark' else 'NSAppearanceNameAqua'
        appearance=NSAppearance.appearanceNamed_(name)
        for window in NSApplication.sharedApplication().windows():
            if str(window.title())==self.root.title():window.setAppearance_(appearance)

    def apply(self,name):
        self.name=name
        self.native_appearance()
        for widget in list(self.bindings):
            if widget.winfo_exists():self.paint(widget)
            else:del self.bindings[widget]
        ttk.Style(self.root).theme_use('aqua')
        for callback in self.callbacks:callback()
    def poll(self):
        name=system_theme()
        if name!=self.name:self.apply(name)
        self.timer=self.root.after(1500,self.poll)
    def destroyed(self,event):
        if event.widget==self.root and self.initial_timer:
            self.root.after_cancel(self.initial_timer);self.initial_timer=None
        if event.widget==self.root and self.timer:
            self.root.after_cancel(self.timer);self.timer=None


def status_presentation(code,enabled=None,paused=False):
    if paused or code=='paused':return 'Ⅱ 已暂停','neutral'
    if any(word in code for word in ('failed','missing','unconfirmed','error')):return '! 异常','error'
    if code in ('waiting-quota','followup-waiting-quota'):return '● 等待额度恢复','wait'
    if code in ('resuming','dispatch-active','followup-queued'):return '● 正在续跑','good'
    if code in ('queued-awaiting-start','waiting-start','followup-waiting-delay'):return '● 准备继续任务','wait'
    if enabled is False:return '● 尚未启用','neutral'
    if enabled is None:return '● 正在读取状态','neutral'
    return '● 监控中','good'


def status_detail(code,fallback,paused=False):
    if paused:return '后续自动检查已暂停，正在执行的任务不受影响。'
    return {
        'waiting-quota':'额度恢复后，将继续原任务。',
        'resuming':'正在接续原任务，请稍候。',
        'dispatch-active':'正在等待当前任务完成。',
        'no-quota-stall':'尚未发现因额度中断的任务。',
        'not-installed':'启用监控后，自动检查额度和中断任务。',
    }.get(code,fallback)
