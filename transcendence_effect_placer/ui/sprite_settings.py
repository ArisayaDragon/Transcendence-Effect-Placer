from __future__ import annotations
import tkinter as tk
from tkinter import LEFT, RIGHT, TOP, BOTTOM, X, Y, VERTICAL, HORIZONTAL, BOTH, END, Toplevel, Tk, Label, Entry, Button

from transcendence_effect_placer.data.data import SpriteConfig
    
class SpriteSettingsDialogue:
    def __init__(self, root: Tk):
        self._root = root
        self._sprite_cfg = SpriteConfig()
        self._wnd: Toplevel|None = None

    def is_open(self):
        return not self._wnd is None

    def open_dialogue(self, defaults: SpriteConfig|None = None):
        defaults = self._sprite_cfg if defaults is None else defaults

        self._wnd = Toplevel()
        self._wnd.title("Sprite Settings")

        c = 0

        Label(self._wnd, text="Sprite Pos X").grid(row=c, column=0)
        self.sprite_pos_x_entry = Entry(self._wnd)
        self.sprite_pos_x_entry.insert(END, str(defaults.x))
        self.sprite_pos_x_entry.grid(row=c, column=1)
        c += 1

        Label(self._wnd, text="Sprite Pos Y").grid(row=c, column=0)
        self.sprite_pos_y_entry = Entry(self._wnd)
        self.sprite_pos_y_entry.insert(END, str(defaults.y))
        self.sprite_pos_y_entry.grid(row=c, column=1)
        c += 1

        Label(self._wnd, text="Sprite Width").grid(row=c, column=0)
        self.sprite_width_entry = Entry(self._wnd)
        self.sprite_width_entry.insert(END, str(defaults.w))
        self.sprite_width_entry.grid(row=c, column=1)
        c += 1

        Label(self._wnd, text="Sprite Height").grid(row=c, column=0)
        self.sprite_height_entry = Entry(self._wnd)
        self.sprite_height_entry.insert(END, str(defaults.h))
        self.sprite_height_entry.grid(row=c, column=1)
        c += 1

        Label(self._wnd, text="Animation Frames").grid(row=c, column=0)
        self.animation_frames_entry = Entry(self._wnd)
        self.animation_frames_entry.insert(END, str(defaults.anim_frames))
        self.animation_frames_entry.grid(row=c, column=1)
        c += 1

        Label(self._wnd, text="Rotation Frames").grid(row=c, column=0)
        self.rotation_frames_entry = Entry(self._wnd)
        self.rotation_frames_entry.insert(END, str(defaults.rot_frames))
        self.rotation_frames_entry.grid(row=c, column=1)
        c += 1

        Label(self._wnd, text="Rotation Columns").grid(row=c, column=0)
        self.rotation_columns_entry = Entry(self._wnd)
        self.rotation_columns_entry.insert(END, str(defaults.rot_cols))
        self.rotation_columns_entry.grid(row=c, column=1)
        c += 1

        Label(self._wnd, text="Viewport Ratio").grid(row=c, column=0)
        self.viewport_ratio_entry = Entry(self._wnd)
        self.viewport_ratio_entry.insert(END, str(defaults.viewport_ratio))
        self.viewport_ratio_entry.grid(row=c, column=1)
        c += 1

        self.accept_button = Button(self._wnd, text="Accept", command=self.accept)
        self.accept_button.grid(row=c, column=0, columnspan=2)
        c += 1

        self.accept_button = Button(self._wnd, text="Cancel", command=self.cancel)
        self.accept_button.grid(row=c, column=0, columnspan=2)

        self._root.wait_window(self._wnd)

    def accept(self):
        self._sprite_cfg.x = int(self.sprite_pos_x_entry.get())
        self._sprite_cfg.y = int(self.sprite_pos_y_entry.get())
        self._sprite_cfg.w = int(self.sprite_width_entry.get())
        self._sprite_cfg.h = int(self.sprite_height_entry.get())
        self._sprite_cfg.anim_frames = int(self.animation_frames_entry.get())
        self._sprite_cfg.rot_frames = int(self.rotation_frames_entry.get())
        self._sprite_cfg.rot_cols = int(self.rotation_columns_entry.get())
        self._sprite_cfg.viewport_ratio = float(self.viewport_ratio_entry.get())
        self._sprite_cfg.real = True

        if self._wnd is None: return
        self._wnd.destroy()
        self._wnd = None

    def cancel(self):
        if self._wnd is None: return
        self._wnd.destroy()
        self._wnd = None