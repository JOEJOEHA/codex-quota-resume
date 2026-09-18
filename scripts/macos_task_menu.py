"""Native task menu. Cocoa actions only enqueue; Tk changes after tracking ends."""
from queue import SimpleQueue
from AppKit import NSObject,NSMenu,NSMenuItem,NSScreen,NSMakePoint,NSFont,NSFontAttributeName,NSAppearance
from Foundation import NSString


class TaskMenuTarget(NSObject):
    def selected_(self,sender):
        self.events.put(int(sender.representedObject()))


class NativeTaskMenu:
    def __init__(self):
        self.menu=NSMenu.alloc().initWithTitle_('选择任务')
        self.menu.setAutoenablesItems_(False)
        self.target=TaskMenuTarget.alloc().init()
        self.target.events=SimpleQueue()
        self.active=False
        self.theme='light'

    def configure(self,values,index,width):
        self.menu.removeAllItems()
        font=NSFont.menuFontOfSize_(0)
        self.menu.setFont_(font)
        self.menu.setMinimumWidth_(float(width))
        attributes={NSFontAttributeName:font}
        budget=max(80,width-64)
        for i,value in enumerate(values):
            full=' '.join(value.split())
            text=full
            while len(text)>1 and NSString.stringWithString_(text).sizeWithAttributes_(attributes).width>budget:
                text=text[:-2]+'…'
            item=NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(text,'selected:','')
            item.setTarget_(self.target);item.setRepresentedObject_(i)
            item.setState_(1 if i==index else 0)
            item.setToolTip_(full)
            self.menu.addItem_(item)

    def present(self,values,index,x,y,width):
        if not values:return None
        while not self.target.events.empty():self.target.events.get()
        self.configure(values,index,width)
        # Tk's desktop origin is at the top of the primary display; AppKit is below it.
        top=NSScreen.screens()[0].frame().size.height
        previous=NSAppearance.currentAppearance()
        appearance=NSAppearance.appearanceNamed_('NSAppearanceNameDarkAqua' if self.theme=='dark' else 'NSAppearanceNameAqua')
        self.active=True
        try:
            NSAppearance.setCurrentAppearance_(appearance)
            self.menu.popUpMenuPositioningItem_atLocation_inView_(None,NSMakePoint(x,top-y),None)
        finally:
            self.active=False
            NSAppearance.setCurrentAppearance_(previous)
        return self.target.events.get() if not self.target.events.empty() else None

    def dismiss(self):
        if self.active:self.menu.cancelTracking()
