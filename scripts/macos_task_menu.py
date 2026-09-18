"""Aqua task menu via Tcl/Tk, which owns Python callback/GIL transitions.

Never enter AppKit menu tracking directly from a Python Tk callback: on
Python 3.14 / Tk 9, nested Tcl callbacks can abort in PyEval_RestoreThread.
"""
import tkinter as tk
from tkinter import font as tkfont


class NativeTaskMenu:
    def __init__(self,owner):
        self.owner=owner
        self.menu=tk.Menu(owner,tearoff=False)
        self.active=False
        self.theme='light'
        self.menu.bind('<Unmap>',lambda event:setattr(self,'active',False),add='+')

    def configure(self,values,index,width,on_select):
        self.menu.delete(0,'end')
        font=tkfont.nametofont('TkMenuFont',root=self.owner)
        self.menu.configure(font=font)
        for i,value in enumerate(values):
            text=' '.join(value.split())
            while len(text)>1 and font.measure(text)>max(80,width-64):
                text=text[:-2]+'…'
            def choose(position=i):
                self.dismiss()
                on_select(position)
            self.menu.add_command(label=('✓ ' if i==index else '   ')+text,command=choose)

    def present(self,values,index,x,y,width,on_select):
        if not values:return
        self.dismiss()
        self.configure(values,index,width,on_select)
        self.active=True
        try:
            # Tcl/Tk performs native Aqua tracking with its own thread state.
            # Coordinates remain in Tk's desktop space, including other displays.
            self.menu.tk_popup(x,y)
        finally:
            if self.menu.grab_current()==self.menu:self.menu.grab_release()

    def dismiss(self):
        if not self.menu.winfo_exists():return
        self.menu.unpost()
        if self.menu.grab_current()==self.menu:self.menu.grab_release()
        self.active=False
