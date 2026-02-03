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
from copy import deepcopy

from transcendence_effect_placer.common.validation import validate_numeral, validate_numeral_non_negative, validate_null
from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
from transcendence_effect_placer.data.points import Point, PointGeneric, PointDevice, PointDock, PointThuster, PointType, PT_DEVICE, PT_DOCK, PT_GENERIC, PT_THRUSTER, SpriteCoord, PILCoord
from transcendence_effect_placer.data.math import a_d, d180, d360
from transcendence_effect_placer.ui.load_file import SpriteOpener
from transcendence_effect_placer.ui.sprite_settings import SpriteSettingsDialogue
from transcendence_effect_placer.ui.elements.slider_entry import SliderEntryUI

#set PIL max pixels
Image.MAX_IMAGE_PIXELS = 2 ** 34 #this is 2**36, which is 64GB - should be plenty big for current transcendence ships

RED = "#FF0000"
BLACK = "#000000"

SV_WRITE = "write"

TRANSCENDENCE_ANGULAR_OFFSET = 90

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
        self._mode: SpriteMode = _MODE_SHIP
        self._main_menu: MainMenuBar = MainMenuBar(root, self)
        self._selected_idx: int = -1
        self._point_controls_locked: bool = False
        self._init_wnd()
        self.load_image()

    def _init_wnd(self):
        self._root.title("Transcendence Effect Placer")
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

        r = 0
        self._ui_anim = SliderEntryUI(self._root, slider_frame, "Anim Frame", 0, 0, self.display_sprite, validate_numeral_non_negative)
        self._ui_anim.frame.grid(row=r, column=0, columnspan=4)
        r += 1
        self._ui_rot = SliderEntryUI(self._root, slider_frame, "Rotation Frame", 0, 0, self.display_sprite, validate_numeral_non_negative)
        self._ui_rot.frame.grid(row=r, column=0, columnspan=4)

        self._image_display.bind("<Button-1>", self.add_point)

    def _init_control_frame(self):        
        def make_sv_callback_arc(sv: StringVar, entry: Entry, validation_fn: Callable[[str], bool] = validate_null):
            def sv_callback(var_name, index, mode):
                s = sv.get()
                valid = validation_fn(s)
                if valid:
                    entry.configure(fg=BLACK)
                    self.update_point_arcs() #does a general validation check on all inputs, in event a bad input was left
                elif isinstance(entry, Entry) and not valid:
                    entry.configure(fg=RED)
            return sv_callback

        self.points_listbox = Listbox(self.control_frame)
        self.points_listbox.pack(fill=BOTH, expand=True)
        self.points_listbox.bind('<<ListboxSelect>>', self.select_point)

        self.update_point_frame = Frame(self.control_frame)
        self.update_point_frame.pack()

        r = 0

        point_type_label = Label(self.update_point_frame, text="Type")

        self.sv_point_type = StringVar()
        self.sv_point_type.set(PT_GENERIC)
        self.point_type_device = Radiobutton(self.update_point_frame, text="Device", value=PT_DEVICE, variable=self.sv_point_type, command=self._change_point_type, state=DISABLED)
        self.point_type_thruster = Radiobutton(self.update_point_frame, text="Thruster", value=PT_THRUSTER, variable=self.sv_point_type, command=self._change_point_type, state=DISABLED)
        self.point_type_dock = Radiobutton(self.update_point_frame, text="Dock", value=PT_DOCK, variable=self.sv_point_type, command=self._change_point_type, state=DISABLED)

        point_type_label.grid(row=r, column=0)
        self.point_type_device.grid(row=r, column=1)
        self.point_type_thruster.grid(row=r, column=2)
        self.point_type_dock.grid(row=r, column=3)

        r += 1
        self._ui_x = SliderEntryUI(self._root, self.update_point_frame, "Pos X", -1, 1, self.update_point, validate_numeral)
        self._ui_x.frame.grid(row=r, column=0, columnspan=4)
        r += 1
        self._ui_y = SliderEntryUI(self._root, self.update_point_frame, "Pos Y", -1, 1, self.update_point, validate_numeral)
        self._ui_y.frame.grid(row=r, column=0, columnspan=4)
        r += 1
        self._ui_z = SliderEntryUI(self._root, self.update_point_frame, "Pos Z", -1, 1, self.update_point_z, validate_numeral)
        self._ui_z.frame.grid(row=r, column=0, columnspan=4)
        r += 1
        self._ui_a = SliderEntryUI(self._root, self.update_point_frame, "Pos Angle", -179, 180, self.update_point_polar, validate_numeral)
        self._ui_a.frame.grid(row=r, column=0, columnspan=4)
        r += 1
        self._ui_r = SliderEntryUI(self._root, self.update_point_frame, "Pos Radius", 0, 1, self.update_point_polar, validate_numeral_non_negative)
        self._ui_r.frame.grid(row=r, column=0, columnspan=4)

        r += 1

        self.iv_mirror_x = IntVar()
        self.iv_mirror_y = IntVar()
        self.iv_mirror_z = IntVar()

        self.mirror_x_check = Checkbutton(self.update_point_frame, text="Mirror X", variable=self.iv_mirror_x, command=self.update_point_mirror, state=DISABLED)
        self.mirror_y_check = Checkbutton(self.update_point_frame, text="Mirror Y", variable=self.iv_mirror_y, command=self.update_point_mirror, state=DISABLED)
        self.mirror_z_check = Checkbutton(self.update_point_frame, text="Mirror Z", variable=self.iv_mirror_z, command=self.update_point_mirror, state=DISABLED)

        self.mirror_x_check.grid(row=r, column=0)
        self.mirror_y_check.grid(row=r, column=1)
        self.mirror_z_check.grid(row=r, column=2)

        r += 1

        pos_dir_label = Label(self.update_point_frame, text="Direction")

        self.sv_pos_dir = StringVar()
        self.pos_dir_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_dir, state=DISABLED)
        self.sv_pos_dir.trace_add(SV_WRITE, make_sv_callback_arc(self.sv_pos_dir, self.pos_dir_entry, validate_numeral))

        pos_arc_label = Label(self.update_point_frame, text="Arc")

        self.sv_pos_arc = StringVar()
        self.pos_arc_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_arc, state=DISABLED)
        self.sv_pos_arc.trace_add(SV_WRITE, make_sv_callback_arc(self.sv_pos_arc, self.pos_arc_entry, validate_numeral))

        pos_dir_label.grid(row=r, column=0)
        self.pos_dir_entry.grid(row=r, column=1)
        pos_arc_label.grid(row=r, column=2)
        self.pos_arc_entry.grid(row=r, column=3)

        r += 1

        pos_arc_st_label = Label(self.update_point_frame, text="Arc Start")

        self.sv_pos_arc_st = StringVar()
        self.pos_arc_st_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_arc_st, state=DISABLED)
        self.sv_pos_arc_st.trace_add(SV_WRITE, make_sv_callback_arc(self.sv_pos_arc_st, self.pos_arc_st_entry, validate_numeral))

        pos_arc_en_label = Label(self.update_point_frame, text="Arc End")

        self.sv_pos_arc_en = StringVar()
        self.pos_arc_en_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_arc_en, state=DISABLED)
        self.sv_pos_arc_en.trace_add(SV_WRITE, make_sv_callback_arc(self.sv_pos_arc_en, self.pos_arc_en_entry, validate_numeral))

        pos_arc_st_label.grid(row=r, column=0)
        self.pos_arc_st_entry.grid(row=r, column=1)
        pos_arc_en_label.grid(row=r, column=2)
        self.pos_arc_en_entry.grid(row=r, column=3)

        r += 1

        self.delete_button = Button(self.update_point_frame, text="Delete Point", command=self.delete_point, state=DISABLED)
        self.delete_button.grid(row=r, column=0)

        self.clone_button = Button(self.update_point_frame, text="Clone Point", command=self.clone_point, state=DISABLED)
        self.clone_button.grid(row=r, column=3)

    def load_sprite_cfg(self):
        self._wnd_sprite_settings.open_dialogue(self._sprite_cfg)

        if self._wnd_sprite_settings._sprite_cfg.real:
            self._sprite_cfg = self._wnd_sprite_settings._sprite_cfg
            self.refresh_main_window()
        elif self._sprite_cfg.real:
            return
        else:
            self._root.quit()
            quit()

    def load_image(self):
        can_continue = False

        self._wnd_image_loader.load_image()
        self._image_path = self._wnd_image_loader.get_path()

        if not self._image_path:
            if self._wnd_sprite_settings._sprite_cfg.real:
                return
            else:
                self._root.quit()
                quit()

        self._image = PIL.Image.open(self._image_path)
        self._sprite_cfg.w = int(self._image.size[0] / 20)
        self._sprite_cfg.h = int(self._image.size[1] / 18)
        self._sprite_cfg.real = False

        path = self._image_path.replace("\\","/")
        file = path.split("/")[-1]
        self._root.title(f"Transcendence Effect Placer: {file}")

        self.load_sprite_cfg()

    def display_sprite(self, event: Event|None = None):
        if self._image is None:
            return
        
        anim_frame = self._ui_anim.get()
        rot_frame = self._ui_rot.get()
        #print(f'anim: {anim_frame}\trot: {rot_frame}')

        ul = self._sprite_cfg.frame(rot_frame, anim_frame)
        lr = ICoord(ul.x + self._sprite_cfg.w, ul.y + self._sprite_cfg.h)
        crop_rect = (ul.x, ul.y, lr.x, lr.y)
        cropped_image = self._image.crop(crop_rect)
        
        direction = round(rot_frame * (360 / self._sprite_cfg.rot_frames))

        for pt in self._points:
            drawable_frame = ImageDraw(cropped_image, mode="RGBA")
            pt.render_to_image(drawable_frame, direction)

        self._sprite_image = ImageTk.PhotoImage(cropped_image)
        if self._image_display is None:
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
            export_str += f'<DockingPorts>{export_str_thrusters}\n</DockingPorts>\n'
        if export_str_devices:
            export_str += f'<DeviceSlots>{export_str_devices}\n</DeviceSlots>\n'
        if export_str_thrusters:
            export_str += f'<Effects>{export_str_thrusters}\n</EffectS>\n'
        print(export_str)

    def set_point_control_limits(self):
        self._ui_x.update_min_max(self._sprite_cfg.w * -.5, self._sprite_cfg.w * .5)
        self._ui_y.update_min_max(self._sprite_cfg.h * -.5, self._sprite_cfg.h * .5)
        self._ui_z.update_min_max(self._sprite_cfg.h * -.5, self._sprite_cfg.h * .5)
        self._ui_a.update_min_max(-179, 180)
        self._ui_r.update_min_max(0, max(self._sprite_cfg.h, self._sprite_cfg.w))

    def reset_point_controls(self):
        self._point_controls_locked = True
        i = self._selected_idx
        self._selected_idx = -1
        self.sv_point_type.set(PT_GENERIC)
        self.point_type_device.configure(state = DISABLED)
        self.point_type_thruster.configure(state = DISABLED)
        self.point_type_dock.configure(state = DISABLED)
        self._ui_x.disable()
        self._ui_x.reset()
        self._ui_y.disable()
        self._ui_y.reset()
        self._ui_z.disable()
        self._ui_z.set(0)
        self._ui_a.disable()
        self._ui_a.set(0)
        self._ui_r.disable()
        self._ui_r.reset_min()
        self.pos_dir_entry.configure(fg=BLACK)
        self.pos_dir_entry.delete(0, END)
        self.pos_dir_entry.configure(state=DISABLED)
        self.pos_arc_entry.configure(fg=BLACK)
        self.pos_arc_entry.delete(0, END)
        self.pos_arc_entry.configure(state=DISABLED)
        self.pos_arc_st_entry.configure(fg=BLACK)
        self.pos_arc_st_entry.delete(0, END)
        self.pos_arc_st_entry.configure(state=DISABLED)
        self.pos_arc_en_entry.configure(fg=BLACK)
        self.pos_arc_en_entry.delete(0, END)
        self.pos_arc_en_entry.configure(state=DISABLED)
        self.mirror_x_check.deselect()
        self.mirror_x_check.configure(state=DISABLED)
        self.mirror_y_check.deselect()
        self.mirror_y_check.configure(state=DISABLED)
        self.mirror_z_check.deselect()
        self.mirror_z_check.configure(state=DISABLED)
        self.delete_button.configure(state=DISABLED)
        self.clone_button.configure(state=DISABLED)
        self._selected_idx = i
        self._point_controls_locked = False

    def get_cur_rot_frame(self) -> int:
        if self._mode == _MODE_STATION:
            return 0
        else:
            return int(self._ui_rot.get())
        
    def refresh_polar_point_info(self):
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            return

        point: Point = self._points[i]
        polar = point.polar_coord
        a = d180(math.degrees(polar.a) + TRANSCENDENCE_ANGULAR_OFFSET)
        r = round(polar.r)
        self._ui_a.set(a)
        self._ui_r.set(r)

    def set_current_point_controls(self):
        self._point_controls_locked = True
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            return

        point: Point = self._points[i]
        projected = point.sprite_coord #point.get_projection_coord_at_direction(self.get_cur_rot_frame())
        x = projected.x
        y = projected.y
        polar = point.polar_coord
        z = polar.z

        pt = point.point_type

        #print(i, type(point), pt, x, y, a, r, z)
        self.set_point_control_limits()
        self.reset_point_controls()

        self.sv_point_type.set(pt)
        self.point_type_device.configure(state = NORMAL)
        self.point_type_thruster.configure(state = NORMAL)
        self.point_type_dock.configure(state = NORMAL)

        self._ui_x.set(x)
        self._ui_x.set_state(DISABLED if point.uses_polar_inputs else NORMAL)
        self._ui_y.set(y)
        self._ui_y.set_state(DISABLED if point.uses_polar_inputs else NORMAL)
        self._ui_z.set(z)
        self._ui_z.set_state(NORMAL if point.uses_z_input else DISABLED)

        self.refresh_polar_point_info()
        self._ui_a.set_state(NORMAL if point.uses_polar_inputs else DISABLED)
        self._ui_r.set_state(NORMAL if point.uses_polar_inputs else DISABLED)

        if isinstance(point, PointDevice) or isinstance(point, PointThuster):
            direction = point.direction
            self.sv_pos_dir.set(str(direction))
            self.pos_dir_entry.configure(state = NORMAL)
        else:
            self.sv_pos_dir.set("")
            self.pos_dir_entry.configure(state = DISABLED)

        if isinstance(point, PointDevice):
            arc = point.arc
            arc_st = point.arc_start
            arc_en = point.arc_end
            self.sv_pos_arc.set(str(arc))
            self.pos_arc_entry.configure(state = NORMAL)
            self.sv_pos_arc_st.set(str(arc_st))
            self.pos_arc_st_entry.configure(state = NORMAL)
            self.sv_pos_arc_en.set(str(arc_en))
            self.pos_arc_en_entry.configure(state = NORMAL)
        else:
            self.sv_pos_arc.set("")
            self.sv_pos_arc_en.set("")
            self.sv_pos_arc_st.set("")
            self.pos_arc_entry.configure(state = DISABLED)
            self.pos_arc_st_entry.configure(state = DISABLED)
            self.pos_arc_en_entry.configure(state = DISABLED)

        #print(point.mirror.x, point.mirror.y, point.mirror.z)
        if point.mirror.x:
            self.mirror_x_check.select()
        else:
            self.mirror_x_check.deselect()
        if point.mirror.y:
            self.mirror_y_check.select()
        else:
            self.mirror_y_check.deselect()
        if point.mirror.z:
            self.mirror_z_check.select()
        else:
            self.mirror_z_check.deselect()
        self.mirror_x_check.configure(state=NORMAL if point.mirror_support.x else DISABLED)
        self.mirror_y_check.configure(state=NORMAL if point.mirror_support.y else DISABLED)
        self.mirror_z_check.configure(state=NORMAL if point.mirror_support.z else DISABLED)

        self.delete_button.configure(state=NORMAL)
        self.clone_button.configure(state=NORMAL)
        self._point_controls_locked = False

    def select_point(self, event: Event):
        #the index is actually a tuple of all selected items in the list
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            return
        self._selected_idx = selected_index[0]

        self.reset_point_controls()
        self.set_current_point_controls()

    def update_point(self, event: Event|None = None):
        if self._point_controls_locked:
            return
        #the index is actually a tuple of all selected items in the list
        #but our list only selects 1 so it doesnt matter
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            return

        xs = self._ui_x.get_raw()
        ys = self._ui_y.get_raw()
        zs = self._ui_z.get_raw()

        #fail if any are not parsable
        failed = False

        if not xs.strip('-').isnumeric():
            failed = True

        if not ys.strip('-').isnumeric():
            failed = True

        if not zs.strip('-').isnumeric():
            failed = True

        if failed:
            return
        
        x = int(xs)
        y = int(ys)
        z = int(zs)

        point: Point = self._points[i]
        updated = False
        if z != point.scene_coord.z:
            point.set_z(z)
            updated = True
        elif x != point.sprite_coord.x or y != point.sprite_coord.y:
            z = point.scene_coord.z
            point.update_from_projection(SpriteCoord(x, y))
            point.set_z(round(z))
            updated = True

        if updated:
            self.points_listbox.delete(i)
            self.points_listbox.insert(i, str(point))

        #self.set_current_point_controls()
        self.display_sprite()

    def update_point_z(self, event: Event|None = None):
        if self._point_controls_locked:
            return
        #the index is actually a tuple of all selected items in the list
        #but our list only selects 1 so it doesnt matter
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            return
        
        point: Point = self._points[i]
        if point.uses_polar_inputs:
            self.update_point_polar(event)
        else:
            self.update_point(event)

    def update_point_polar(self, event: Event|None = None):
        if self._point_controls_locked:
            return
        #the index is actually a tuple of all selected items in the list
        #but our list only selects 1 so it doesnt matter
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            return

        as_ = self._ui_a.get_raw()
        rs = self._ui_r.get_raw()
        zs = self._ui_z.get_raw()

        #fail if any are not parsable
        failed = False

        if not as_.strip('-').isnumeric():
            failed = True

        if not rs.strip('-').isnumeric():
            failed = True

        if not zs.strip('-').isnumeric():
            failed = True

        if failed:
            return
        
        a = int(as_)
        a -= TRANSCENDENCE_ANGULAR_OFFSET
        ar = math.radians(a)
        r = int(rs)
        z = int(zs)

        point: Point = self._points[i]
        updated = False
        if z != point.scene_coord.z:
            point.update_from_polar(PCoord(point.polar_coord.a,point.polar_coord.r,z))
            updated = True
        elif ar != point.polar_coord.a or r != point.polar_coord.r:
            z = point.scene_coord.z
            point.update_from_polar(PCoord(ar,r,z))
            updated = True

        if updated:
            self.points_listbox.delete(i)
            self.points_listbox.insert(i, str(point))

        #self.set_current_point_controls()
        self.display_sprite()


    def update_point_arcs(self, event: Event|None = None):
        if self._point_controls_locked:
            return
        #the index is actually a tuple of all selected items in the list
        #but our list only selects 1 so it doesnt matter
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            return
        
        point: Point = self._points[i]

        if isinstance(point, PointThuster) or isinstance(point, PointDevice):
            #handle direction
            point.direction = int(self.sv_pos_dir.get())
        if isinstance(point, PointDevice):
            #handle arcs
            use_range = False
            use_arc = False
            old_arc = point.arc
            old_start = point.arc_start
            old_end = point.arc_end
            new_arc_s = self.sv_pos_arc.get()
            new_arc = int(new_arc_s if new_arc_s else -2)
            new_start_s = self.sv_pos_arc_st.get()
            new_start = int(new_start_s if new_start_s else -2)
            new_end_s = self.sv_pos_arc_en.get()
            new_end = int(new_end_s if new_end_s else -2)

            if old_arc != new_arc:
                use_arc = new_arc != -2
            if old_start != new_start or old_end != new_end:
                use_range = new_start != -2 and new_end != -2

            if use_range:
                point.arc_end = new_end
                point.arc_start = new_start
            elif use_arc:
                point.arc = new_arc

        #self.set_current_point_controls()
        self.display_sprite()

    def update_point_mirror(self, event: Event|None = None):
        if self._point_controls_locked:
            return
        #the index is actually a tuple of all selected items in the list
        #but our list only selects 1 so it doesnt matter
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            return
        
        m_x = bool(self.iv_mirror_x.get())
        m_y = bool(self.iv_mirror_y.get())
        m_z = bool(self.iv_mirror_z.get())

        point: Point = self._points[i]
        point.set_mirror_x(m_x)
        point.set_mirror_y(m_y)
        point.set_mirror_z(m_z)

        self.display_sprite()

    def _change_point_type(self):
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            return

        pt: PointType = PointType(self.sv_point_type.get())

        old_point = self._points[i]
        if old_point.point_type == pt:
            return

        if pt == PT_DEVICE:
            new_point = PointDevice(clone_point=old_point)
        elif pt == PT_THRUSTER:
            new_point = PointThuster(clone_point=old_point)
        elif pt == PT_DOCK:
            new_point = PointDock(clone_point=old_point)
        else:
            print(f"Err: unexpectedly got point type {pt} of type {type(pt)}")
            assert False
        
        self._points[i] = new_point
        self.points_listbox.delete(i)
        self.points_listbox.insert(i, str(new_point))
        self.set_current_point_controls()
        self.display_sprite()

    def add_point(self, event: Event[Label]):
        if self._point_controls_locked:
            return
        coord = PILCoord(event.x, event.y)
        point = PointGeneric(coord, str(len(self._points)), self._sprite_cfg, self.get_cur_rot_frame())
        self._points.append(point)
        self.points_listbox.insert(END, str(point))
        self._selected_idx = len(self._points) - 1
        self.set_current_point_controls()
        self.display_sprite()

    def delete_point(self):
        if self._point_controls_locked:
            return
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

        if self._selected_idx >= 0:
            self.set_current_point_controls()
        self.display_sprite()

    def clone_point(self):
        if self._point_controls_locked:
            return
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
            return

        self.reset_point_controls()

        point = deepcopy(self._points[i])
        self._points.insert(i+1, point)
        self.points_listbox.insert(i+1, str(point))

        self._selected_idx = i + 1
        self.points_listbox.select_set(i+1)

        self.set_current_point_controls()
        self.display_sprite()

    def refresh_main_window(self):
        #reset collected points
        self._points = []
        self.points_listbox.delete(0, END)

        #reset frame sliders
        self._ui_anim.set(0)
        num_anim_frames = self._sprite_cfg.anim_frames
        self._ui_anim.update_min_max(0, num_anim_frames)
        self._ui_anim.set_state(NORMAL if num_anim_frames else DISABLED)
        self._ui_rot.set(0)
        num_rot_frames = self._sprite_cfg.rot_frames - 1
        self._ui_rot.update_min_max(0, num_rot_frames)
        self._ui_rot.set_state(NORMAL if num_rot_frames else DISABLED)

        #reset point editing
        self.reset_point_controls()

        #draw whatever sprite is now selected
        self.display_sprite()

        if self._sprite_image is None:
            #error
            print('Err: sprite_image was none')
            self._root.quit()
            return
        
        if self._image_display:
            self._image_display.config(image=self._sprite_image)
