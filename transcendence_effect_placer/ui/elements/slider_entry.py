from __future__ import annotations
import tkinter as tk
from tkinter import LEFT, RIGHT, TOP, BOTTOM, X, Y, VERTICAL, HORIZONTAL, BOTH, END, NORMAL, ACTIVE, DISABLED, Toplevel, Tk, Scale, Label, Event, StringVar, Entry, Frame, Listbox, Checkbutton, Radiobutton, Button, IntVar
from PIL import ImageTk
import PIL
from PIL.ImageFile import ImageFile
from PIL.ImageDraw import ImageDraw
from PIL.Image import Image
import math
import numpy as np
from time import sleep
from typing import Callable, Literal

from transcendence_effect_placer.common.validation import validate_numeral, validate_numeral_non_negative, validate_null
from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
from transcendence_effect_placer.data.points import Point, PointGeneric, PointDevice, PointDock, PointThuster, PointType, PT_DEVICE, PT_DOCK, PT_GENERIC, PT_THRUSTER, SpriteCoord, PILCoord
from transcendence_effect_placer.data.math import a_d, d180, d360
from transcendence_effect_placer.ui.load_file import SpriteOpener
from transcendence_effect_placer.ui.sprite_settings import SpriteSettingsDialogue

RED = "#FF0000"
BLACK = "#000000"

SV_WRITE = "write"

class SliderEntryUI:
    def __init__(self, root: Tk, frame: Frame, label:str, min: float|int, max: float|int, cb: Callable[[Event|None], None], validation_cb: Callable[[str], bool] = validate_numeral):
        self._root = root
        self.parent = frame
        self._cb = cb
        self._validation = validation_cb
        self._min = min
        self._max = max
        self.value: str = str(min)
        self.frame = Frame(self.parent)
        pos_x_label = Label(self.frame, text=label)
        pos_x_label.pack(side=LEFT)
        if max < min: max = min
        self._slider = Scale(self.frame, from_=min, to=max, orient=tk.HORIZONTAL, length=200, command=self._slider_cb)
        self._slider.pack(side=LEFT)
        self._var = StringVar()
        self._entry = Entry(self.frame, textvariable=self._var, state=DISABLED)
        self._var.trace_add(SV_WRITE, self._trace_cb)
        self._entry.pack(side=LEFT)
        self._state: Literal['disabled', 'normal'] = DISABLED
        self.set_state(DISABLED)

    def set_state(self, state: Literal['disabled', 'normal']):
        self._entry.configure(state= state)
        self._slider.configure(state= state)
        self._state = state

    def set(self, v: int|float):
        is_disabled = self._state == DISABLED
        if is_disabled:
            self.enable()
        v = max(self._min, min(self._max, v))
        self._slider.set(v)
        s = str(v)
        self._var.set(s)
        print(f"v: {self._slider.get()} vs {v}, s: {self._var.get()} vs {s}, disabled: {is_disabled}")
        self._entry.configure(fg=BLACK)
        if is_disabled:
            self.disable()

    def get(self):
        return float(self.value)
    
    def get_raw(self):
        return self._var.get()

    def disable(self):
        self.set_state(DISABLED)
    def enable(self):
        self.set_state(NORMAL)

    def update_min_max(self, min_: float|int, max_: float|int):
        self._min = min_
        self._max = max_
        self._slider.configure(from_=min_, to=max_)
        s = self._var.get()
        valid = self._validation(s)
        if valid:
            v = float(s)
            self.set(v)
        else:
            v = min_
            self.set(v)

    def reset(self):
        self.set((self._max + self._min) / 2)

    def reset_min(self):
        self.set(self._min)

    def reset_max(self):
        self.set(self._max)

    def _trace_cb(self, var_name, index, mode):
        s = self._var.get()
        valid = self._validation(s)
        if valid:
            v = float(s)
            if v > self._max:
                s = str(self._max)
            elif v < self._min:
                s = str(self._min)
            self._entry.configure(fg=BLACK) 
            v = int(s)
            self.set(v)
            self.value = s
            self._cb(None) #must do a general validation check on all inputs, in event a bad input was left elsewhere
        elif not valid:
            self._entry.configure(fg=RED)

    def _slider_cb(self, _:str):
        v = self._slider.get()
        s = str(v)
        self.value = s
        self.set(v)
        self._entry.configure(fg=BLACK) 
        self._cb(None)

