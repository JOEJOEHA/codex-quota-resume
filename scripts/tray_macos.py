"""NSStatusItem callbacks enqueue actions; only Tk's timer operates on widgets."""
from queue import SimpleQueue
from AppKit import (NSObject, NSApplication, NSStatusBar, NSVariableStatusItemLength,
                    NSMenu, NSMenuItem, NSEventMaskLeftMouseUp, NSEventMaskRightMouseUp,
                    NSEventTypeRightMouseUp)


class StatusTarget(NSObject):
    def clicked_(self, sender):
        event = NSApplication.sharedApplication().currentEvent()
        self.events.put('menu' if event.type() == NSEventTypeRightMouseUp else 'show')

    def open_(self, sender):
        self.events.put('show')

    def exit_(self, sender):
        self.events.put('exit')


class TrayIcon:
    def __init__(self, root, on_exit):
        self.root, self.on_exit = root, on_exit
        self.events = SimpleQueue()
        self.target = StatusTarget.alloc().init()
        self.target.events = self.events
        self.bar = NSStatusBar.systemStatusBar()
        self.item = self.bar.statusItemWithLength_(NSVariableStatusItemLength)
        button = self.item.button()
        button.setTitle_('↻')
        button.setToolTip_('Codex 自动续跑 — 点击打开，右键菜单')
        button.setTarget_(self.target)
        button.setAction_('clicked:')
        button.sendActionOn_(NSEventMaskLeftMouseUp | NSEventMaskRightMouseUp)
        self.menu = NSMenu.alloc().init()
        for text, action in [('打开主窗口', 'open:'), ('退出界面（后台监控继续）', 'exit:')]:
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(text, action, '')
            item.setTarget_(self.target)
            self.menu.addItem_(item)
        self.active = True
        root.createcommand('tk::mac::Quit', lambda: self.events.put('exit'))
        root.createcommand('tk::mac::ReopenApplication', lambda: self.events.put('show'))
        root.bind('<Destroy>', self.close, add='+')
        self.poll()

    def restore(self):
        self.root.deiconify()
        self.root.lift()
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.root.focus_force()

    def poll(self):
        while not self.events.empty():
            action = self.events.get()
            if action == 'show':self.restore()
            elif action == 'menu':self.item.popUpStatusItemMenu_(self.menu)
            elif action == 'exit':self.on_exit()
            if not self.active:return
        self.timer = self.root.after(100, self.poll)

    def close(self, event=None):
        if event is not None and event.widget != self.root:return
        if self.active:
            self.active = False
            self.root.after_cancel(self.timer)
            self.bar.removeStatusItem_(self.item)
