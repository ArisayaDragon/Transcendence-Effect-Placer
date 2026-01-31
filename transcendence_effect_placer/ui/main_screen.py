from __future__ import annotations
import tkinter as tk
from tkinter import LEFT, RIGHT, TOP, BOTTOM, X, Y, VERTICAL, HORIZONTAL, BOTH, END, Toplevel, Tk, Scale, Label, Event, StringVar, Entry, Frame, Listbox, Button
from tkinter import filedialog, messagebox
from PIL import ImageTk
import PIL
from PIL.ImageFile import ImageFile
from PIL.ImageDraw import ImageDraw
from PIL.Image import Image
import numpy as np
from time import sleep
import math

from transcendence_effect_placer.common.validation import validate_numeral, validate_numeral_non_negative, validate_null
from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
from transcendence_effect_placer.data.math import convert_polar_to_projection, convert_projection_to_polar
from transcendence_effect_placer.data.points import Point, PointGeneric, PointDevice, PointDock, PointThuster, PointType, PT_DEVICE, PT_DOCK, PT_GENERIC, PT_THRUSTER
from transcendence_effect_placer.ui.load_file import SpriteOpener
from transcendence_effect_placer.ui.sprite_settings import SpriteSettingsDialogue

#set PIL max pixels
Image.MAX_IMAGE_PIXELS = 2 ** 34 #this is 2**36, which is 64GB - should be plenty big for current transcendence ships

RED = "#FF0000"
BLACK = "#000000"

SV_WRITE = "write"

class SpriteMode(str): pass

_MODE_SHIP = SpriteMode("Ship")
_MODE_STATION = SpriteMode("Station")

class MainMenuBar:
    def __init__(self, root: Tk, viewer: SpriteViewer):
        self._root = root
        self.viewer = viewer

    def display(self):
        menubar = tk.Menu(self._root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Load", command=self.viewer.load_image)
        file_menu.add_command(label="Change Sprite Parameters", command=self.viewer.load_sprite_cfg)
        file_menu.add_command(label="Export", command=self.viewer.export)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        self._root.config(menu=menubar)
        


class SpriteViewer:
    def __init__(self, root: Tk):
        self._root = root
        self._image_path: str|None = None
        self._image: ImageFile|None = None
        self._sprite_image: ImageTk.PhotoImage|None = None
        self._image_display: Label|None = None
        self._sprite_cfg = SpriteConfig()
        self._points: list[Point] = []
        self._wnd_image_loader = SpriteOpener(root)
        self._wnd_sprite_settings = SpriteSettingsDialogue(root)
        self._anim_slider: Scale|None = None
        self._rot_slider: Scale|None = None
        self._mode: SpriteMode = _MODE_SHIP
        self._main_menu: MainMenuBar = MainMenuBar(root, self)
        self._selected_idx: int = -1
        self._init_wnd()
        self.load_image()

    def _init_wnd(self):
        self._main_menu.display()

        self.control_frame = Frame(self._root, width=int(self._root.winfo_screenwidth() * 0.2))
        self.control_frame.pack(side=LEFT, fill=Y)

        self.display_frame = Frame(self._root, width=int(self._root.winfo_screenwidth() * 0.8))
        self.display_frame.pack(side=RIGHT, fill=BOTH, expand=True)
        self._init_control_frame()
        self._init_display_frame()

    def _init_display_frame(self):
        self._image_display = Label(self.display_frame)
        self._image_display.pack()

        slider_frame = Frame(self.display_frame)
        slider_frame.pack(fill=X)

        self._anim_slider = Scale(slider_frame, from_=0, to=self._sprite_cfg.anim_frames, orient=tk.HORIZONTAL, length=200, command=self.display_sprite)
        self._anim_slider.set(0)
        self._anim_slider.pack(side=LEFT)

        self._rot_slider = Scale(slider_frame, from_=0, to=self._sprite_cfg.rot_frames - 1, orient=tk.HORIZONTAL, length=200, command=self.display_sprite)
        self._rot_slider.set(0)
        self._rot_slider.pack(side=RIGHT)

        self._image_display.bind("<Button-1>", self.add_coordinate)

    def _init_control_frame(self):
        def make_sv_callback(sv: StringVar, entry: Entry, validation_fn: function[str] = validate_null):
            def sv_callback(var_name, index, mode):
                s = sv.get()
                valid = validation_fn(s)
                if valid:
                    entry.configure(fg=BLACK)
                    self.update_point() #does a general validation check on all inputs, in event a bad input was left
                elif isinstance(entry, Entry) and not valid:
                    entry.configure(fg=RED)
            return sv_callback

        self.points_listbox = Listbox(self.control_frame)
        self.points_listbox.pack(fill=BOTH, expand=True)
        self.points_listbox.bind('<<ListboxSelect>>', self.select_point)

        self.update_point_frame = Frame(self.control_frame)
        self.update_point_frame.pack()

        pos_x_label = Label(self.update_point_frame, text="Pos X")
        pos_x_label.pack(side=LEFT)

        self.sv_pos_x = StringVar()
        self.pos_x_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_x)
        self.pos_x_entry.pack(side=LEFT)
        self.sv_pos_x.trace_add(SV_WRITE, make_sv_callback(self.sv_pos_x, self.pos_x_entry, validate_numeral))

        pos_y_label = Label(self.update_point_frame, text="Pos Y")
        pos_y_label.pack(side=RIGHT)

        self.sv_pos_y = StringVar()
        self.pos_y_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_y)
        self.pos_y_entry.pack(side=RIGHT)
        self.sv_pos_y.trace_add(SV_WRITE, make_sv_callback(self.sv_pos_y, self.pos_y_entry, validate_numeral))

        delete_button = Button(self.update_point_frame, text="Delete Point", command=self.delete_point)
        delete_button.pack(side=BOTTOM)

    def load_sprite_cfg(self):
        self._wnd_sprite_settings.open_dialogue(self._sprite_cfg)

        if self._wnd_sprite_settings._sprite_cfg.real:
            self._sprite_cfg = self._wnd_sprite_settings._sprite_cfg
            self.refresh_main_window()
            print('creating main window')
        elif self._sprite_cfg.real:
            print('cancelled')
            return
        else:
            print('exiting')
            self._root.quit()
            quit()

    def load_image(self):
        can_continue = False

        self._wnd_image_loader.load_image()
        self._image_path = self._wnd_image_loader.get_path()

        if not self._image_path:
            if self._wnd_sprite_settings._sprite_cfg.real:
                print('cancelled opening')
                return
            else:
                print('exiting')
                self._root.quit()
                quit()

        self._image = PIL.Image.open(self._image_path)
        self._sprite_cfg.w = int(self._image.size[0] / 20)
        self._sprite_cfg.h = int(self._image.size[1] / 18)
        self._sprite_cfg.real = False
        self.load_sprite_cfg()

    def display_sprite(self, event: Event|None = None):
        print('cropping sprite to display')
        if self._image is None:
            return
        print(f'image is {self._image}')
        
        anim_frame = 0 if self._anim_slider is None else int(self._anim_slider.get())
        rot_frame = 0 if self._rot_slider is None else int(self._rot_slider.get())
        print(f'anim: {anim_frame}\trot: {rot_frame}')

        ul = self._sprite_cfg.frame(rot_frame, anim_frame)
        lr = ICoord(ul.x + self._sprite_cfg.w, ul.y + self._sprite_cfg.h)
        crop_rect = (ul.x, ul.y, lr.x, lr.y)
        print(f'cropping to {crop_rect}')
        cropped_image = self._image.crop(crop_rect)
        
        direction = round(rot_frame * (360 / self._sprite_cfg.rot_frames))

        for pt in self._points:
            drawable_frame = ImageDraw(cropped_image, mode="RGBA")
            pt.render_to_image(drawable_frame, direction)

        self._sprite_image = ImageTk.PhotoImage(cropped_image)
        if self._image_display is None:
            print('Err: Label storing image was not initialized')
            return
        self._image_display.config(image=self._sprite_image)

    def export(self):
        export_str_docking = ""
        export_str_devices = ""
        export_str_thrusters = ""
        for pt in self._points:
            if pt.point_type == PT_DEVICE:
                export_str_devices += '\n' +pt.to_xml()
            elif pt.point_type == PT_DOCK:
                export_str_docking += '\n' +pt.to_xml()
            elif pt.point_type == PT_THRUSTER:
                export_str_thrusters += '\n' +pt.to_xml()
        export_str_thrusters = export_str_thrusters.replace('\n','\n\t')
        export_str_devices = export_str_devices.replace('\n','\n\t')
        export_str_docking = export_str_docking.replace('\n','\n\t')
        export_str = ""
        if export_str_docking:
            export_str += f'<DockingPorts>{export_str_thrusters}</DockingPorts>\n'
        if export_str_devices:
            export_str += f'<DeviceSlots>{export_str_devices}</DeviceSlots>\n'
        if export_str_thrusters:
            export_str += f'<Effects>{export_str_thrusters}</EffectS>'
        print(export_str)

    def reset_point_controls(self):
        self.pos_x_entry.configure(fg=BLACK)
        self.pos_x_entry.delete(0, END)
        self.pos_y_entry.configure(fg=BLACK)
        self.pos_y_entry.delete(0, END)

    def get_cur_rot_frame(self) -> int:
        if self._mode == _MODE_STATION:
            return 0
        else:
            return self._rot_slider.get()

    def set_current_point_controls(self):
        #the index is actually a tuple of all selected items in the list
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            return
        
        #we can only edit one at a time, so we only take the first
        i = selected_index[0]

        point: Point = self._points[i]
        projected = point.get_projection_coord_at_direction(self.get_cur_rot_frame())
        x = projected.x
        y = projected.y

        self.reset_point_controls()

        self.pos_x_entry.delete(0, END)
        self.pos_x_entry.insert(0, str(x))
        self.pos_y_entry.delete(0, END)
        self.pos_y_entry.insert(0, str(y))

    def select_point(self, event: Event):
        #the index is actually a tuple of all selected items in the list
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            return
        
        #we can only edit one at a time, so we only take the first
        i = selected_index[0]
        self._selected_idx = i

        point: Point = self._points[i]

        x = point.projection_coord.x
        y = point.projection_coord.y

        self.reset_point_controls()

        self.pos_x_entry.delete(0, END)
        self.pos_x_entry.insert(0, str(x))
        self.pos_y_entry.delete(0, END)
        self.pos_y_entry.insert(0, str(y))

    def update_point(self, event: Event|None = None):
        #the index is actually a tuple of all selected items in the list
        #but our list only selects 1 so it doesnt matter
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            print("no valid index selected")
            return

        xs = self.pos_x_entry.get()
        ys = self.pos_y_entry.get()

        #fail if any are not parsable
        failed = False

        if not xs.strip('-').isnumeric():
            self.pos_x_entry.configure(fg=RED)
            failed = True
        else:
            self.pos_x_entry.configure(fg=BLACK)

        if not ys.strip('-').isnumeric():
            self.pos_y_entry.configure(fg=RED)
            failed = True
        else:
            self.pos_y_entry.configure(fg=BLACK)

        if failed:
            return
        
        x = int(xs)
        y = int(ys)

        point: Point = self._points[i]
        point.update_from_projection(ICoord(x, y), 0)
        self.points_listbox.delete(i)
        self.points_listbox.insert(i, str(point))

        self.display_sprite()

    def delete_point(self):
        #the index is actually a tuple of all selected items in the list
        #but our list only selects 1 so it doesnt matter
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
            if i >= 0:
                self.points_listbox.select_set(self._selected_idx)
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            print("no valid index selected")
            return

        self.reset_point_controls()

        self._points.pop(i)
        self.points_listbox.delete(i)

        if len(self._points) == i:
            self._selected_idx = i - 1
            #if we have any left select the last one
            if self._selected_idx >= 0:
                self.points_listbox.select_set(self._selected_idx)
            else:
                self.reset_point_controls()
        elif len(self._points):
            #we just have the next one selected
            self.points_listbox.select_set(i)

        
        self.display_sprite()

    def add_coordinate(self, event: Event[Label]):
        x = event.x - self._sprite_cfg.w // 2
        y = event.y - self._sprite_cfg.h // 2
        
        coord = ICoord(x, y)
        point = PointGeneric(coord, str(len(self._points)), self._sprite_cfg, self._rot_slider.get())
        self._points.append(point)
        self.points_listbox.insert(END, str(point))
        self.display_sprite()

    def refresh_main_window(self):
        #reset collected points
        self._points = []
        self.points_listbox.delete(0, END)

        #reset sliders
        self._anim_slider.set(0)
        self._anim_slider.configure(from_=0, to=self._sprite_cfg.anim_frames)
        self._rot_slider.set(0)
        self._rot_slider.configure(from_=0, to=self._sprite_cfg.rot_frames - 1)

        #reset point editing
        self.reset_point_controls()

        #draw whatever sprite is now selected
        self.display_sprite()

        if self._sprite_image is None:
            #error
            print('Err: sprite_image was none')
            self._root.quit()
            return
        
        self._image_display.config(image=self._sprite_image)
