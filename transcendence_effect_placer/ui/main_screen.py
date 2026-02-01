from __future__ import annotations
import tkinter as tk
from tkinter import LEFT, RIGHT, TOP, BOTTOM, X, Y, VERTICAL, HORIZONTAL, BOTH, END, NORMAL, ACTIVE, DISABLED, Toplevel, Tk, Scale, Label, Event, StringVar, Entry, Frame, Listbox, Checkbutton, Radiobutton, Button, IntVar
from PIL import ImageTk
import PIL
from PIL.ImageFile import ImageFile
from PIL.ImageDraw import ImageDraw
from PIL.Image import Image
import numpy as np
from time import sleep
from typing import Callable

from transcendence_effect_placer.common.validation import validate_numeral, validate_numeral_non_negative, validate_null
from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
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

        pos_x_label = Label(slider_frame, text="Anim Frame")
        pos_x_label.pack(side=LEFT)
        self._anim_slider = Scale(slider_frame, from_=0, to=self._sprite_cfg.anim_frames, orient=tk.HORIZONTAL, length=200, command=self.display_sprite)
        self._anim_slider.set(0)
        self._anim_slider.pack(side=LEFT)

        self._rot_slider = Scale(slider_frame, from_=0, to=self._sprite_cfg.rot_frames - 1, orient=tk.HORIZONTAL, length=200, command=self.display_sprite)
        self._rot_slider.set(0)
        self._rot_slider.pack(side=RIGHT)
        pos_x_label = Label(slider_frame, text="Rotation Frame")
        pos_x_label.pack(side=RIGHT)

        self._image_display.bind("<Button-1>", self.add_point)

    def _change_point_type(self):
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            print("no valid index selected")
            return

        pt: PointType = PointType(self.sv_point_type.get())

        old_point = self._points[i]
        if old_point.point_type == pt:
            return

        if pt == PT_DEVICE:
            new_point = PointDevice(old_point.projection_coord, old_point.label, self._sprite_cfg, 0)
        elif pt == PT_THRUSTER:
            new_point = PointThuster(old_point.projection_coord, old_point.label, self._sprite_cfg, 0)
        elif pt == PT_DOCK:
            new_point = PointDock(old_point.projection_coord, old_point.label, self._sprite_cfg, 0)
        else:
            print(f"unexpectedly got point type {pt} of type {type(pt)}")
            assert False
        
        self._points[i] = new_point
        self.points_listbox.delete(i)
        self.points_listbox.insert(i, str(new_point))
        self.set_current_point_controls()
        self.display_sprite()

    def _init_control_frame(self):
        def make_sv_callback(sv: StringVar, entry: Entry, validation_fn: Callable[[str], bool] = validate_null):
            def sv_callback(var_name, index, mode):
                s = sv.get()
                valid = validation_fn(s)
                if valid:
                    entry.configure(fg=BLACK)
                    self.update_point() #does a general validation check on all inputs, in event a bad input was left
                elif isinstance(entry, Entry) and not valid:
                    entry.configure(fg=RED)
            return sv_callback
        
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

        pos_x_label = Label(self.update_point_frame, text="Pos X")

        self.sv_pos_x = StringVar()
        self.pos_x_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_x, state=DISABLED)
        self.sv_pos_x.trace_add(SV_WRITE, make_sv_callback(self.sv_pos_x, self.pos_x_entry, validate_numeral))

        pos_y_label = Label(self.update_point_frame, text="Pos Y")

        self.sv_pos_y = StringVar()
        self.pos_y_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_y, state=DISABLED)
        self.sv_pos_y.trace_add(SV_WRITE, make_sv_callback(self.sv_pos_y, self.pos_y_entry, validate_numeral))

        pos_x_label.grid(row=r, column=0)
        self.pos_x_entry.grid(row=r, column=1)
        pos_y_label.grid(row=r, column=2)
        self.pos_y_entry.grid(row=r, column=3)

        r += 1

        pos_z_label = Label(self.update_point_frame, text="Pos Z")

        self.sv_pos_z = StringVar()
        self.pos_z_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_z, state=DISABLED)
        self.sv_pos_z.trace_add(SV_WRITE, make_sv_callback(self.sv_pos_z, self.pos_z_entry, validate_numeral))

        pos_z_label.grid(row=r, column=0)
        self.pos_z_entry.grid(row=r, column=1)

        r += 1

        pos_a_label = Label(self.update_point_frame, text="Angle")

        self.sv_pos_a = StringVar()
        self.pos_a_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_a, state=DISABLED)
        self.sv_pos_a.trace_add(SV_WRITE, make_sv_callback(self.sv_pos_a, self.pos_a_entry, validate_numeral))

        pos_r_label = Label(self.update_point_frame, text="Radius")

        self.sv_pos_r = StringVar()
        self.pos_r_entry = Entry(self.update_point_frame, textvariable=self.sv_pos_r, state=DISABLED)
        self.sv_pos_r.trace_add(SV_WRITE, make_sv_callback(self.sv_pos_r, self.pos_r_entry, validate_numeral))

        pos_a_label.grid(row=r, column=0)
        self.pos_a_entry.grid(row=r, column=1)
        pos_r_label.grid(row=r, column=2)
        self.pos_r_entry.grid(row=r, column=3)

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
        self.delete_button.grid(row=r, column=1, columnspan=2)

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

        self._image: ImageFile = PIL.Image.open(self._image_path)
        self._sprite_cfg.w = int(self._image.size[0] / 20)
        self._sprite_cfg.h = int(self._image.size[1] / 18)
        self._sprite_cfg.real = False

        path = self._image_path.replace("\\","/")
        file = path.split("/")[-1]
        self._root.title(f"Transcendence Effect Placer: {file}")

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
        i = self._selected_idx
        self._selected_idx = -1
        self.sv_point_type.set(PT_GENERIC)
        self.point_type_device.configure(state = DISABLED)
        self.point_type_thruster.configure(state = DISABLED)
        self.point_type_dock.configure(state = DISABLED)
        self.pos_x_entry.configure(fg=BLACK)
        self.pos_x_entry.delete(0, END)
        self.pos_x_entry.configure(state=DISABLED)
        self.pos_y_entry.configure(fg=BLACK)
        self.pos_y_entry.delete(0, END)
        self.pos_y_entry.configure(state=DISABLED)
        self.pos_z_entry.configure(fg=BLACK)
        self.pos_z_entry.delete(0, END)
        self.pos_z_entry.configure(state=DISABLED)
        self.pos_a_entry.configure(fg=BLACK)
        self.pos_a_entry.delete(0, END)
        self.pos_a_entry.configure(state=DISABLED)
        self.pos_r_entry.configure(fg=BLACK)
        self.pos_r_entry.delete(0, END)
        self.pos_r_entry.configure(state=DISABLED)
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
        self._selected_idx = i

    def get_cur_rot_frame(self) -> int:
        if self._mode == _MODE_STATION or self._rot_slider is None:
            return 0
        else:
            return int(self._rot_slider.get())

    def set_current_point_controls(self):
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            i = self._selected_idx
        else:
            #we can only edit one at a time, so we only take the first
            i = selected_index[0]
        if i < 0:
            print("no valid index selected")
            return

        point: Point = self._points[i]
        projected = point.projection_coord #point.get_projection_coord_at_direction(self.get_cur_rot_frame())
        x = projected.x
        y = projected.y
        polar = point.polar_coord
        a = polar.dir
        r = polar.rad
        z = polar.z

        pt = point.point_type

        print(i, type(point), pt, x, y, a, r, z)

        self.reset_point_controls()

        self.sv_point_type.set(pt)
        self.point_type_device.configure(state = NORMAL)
        self.point_type_thruster.configure(state = NORMAL)
        self.point_type_dock.configure(state = NORMAL)

        self.sv_pos_x.set(str(x))
        self.pos_x_entry.configure(state = NORMAL)
        self.sv_pos_y.set(str(y))
        self.pos_y_entry.configure(state = NORMAL)
        self.sv_pos_z.set(str(z))
        self.pos_z_entry.configure(state = NORMAL)
        self.sv_pos_a.set(str(a))
        self.sv_pos_r.set(str(r))

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

        print(point.mirror.x, point.mirror.y, point.mirror.z)
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

    def select_point(self, event: Event):
        #the index is actually a tuple of all selected items in the list
        selected_index = self.points_listbox.curselection()
        if not selected_index:
            return
        self._selected_idx = selected_index[0]

        self.reset_point_controls()
        self.set_current_point_controls()

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
        zs = self.pos_z_entry.get()

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
        point.update_from_projection(ICoord(x, y), z)
        self.points_listbox.delete(i)
        self.points_listbox.insert(i, str(point))

        self.display_sprite()

    def update_point_arcs(self, event: Event|None = None):
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
            new_arc = int(self.sv_pos_arc.get())
            new_start = int(self.sv_pos_arc_st.get())
            new_end = int(self.sv_pos_arc_en.get())

            if old_arc != new_arc:
                use_arc = True
            if old_start != new_start or old_end != new_end:
                use_range = True

            if use_range:
                point.arc_end = new_end
                point.arc_start = new_start
            elif use_arc:
                point.arc = new_arc

        self.display_sprite()

    def update_point_mirror(self, event: Event|None = None):
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
        
        m_x = bool(self.iv_mirror_x.get())
        m_y = bool(self.iv_mirror_y.get())
        m_z = bool(self.iv_mirror_z.get())

        point: Point = self._points[i]
        point.set_mirror_x(m_x)
        point.set_mirror_y(m_y)
        point.set_mirror_z(m_z)

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

        if self._selected_idx >= 0:
            self.set_current_point_controls()
        self.display_sprite()

    def add_point(self, event: Event[Label]):
        x = event.x - self._sprite_cfg.w // 2
        y = event.y - self._sprite_cfg.h // 2
        
        coord = ICoord(x, y)
        point = PointGeneric(coord, str(len(self._points)), self._sprite_cfg, self.get_cur_rot_frame())
        self._points.append(point)
        self.points_listbox.insert(END, str(point))
        self._selected_idx = len(self._points) - 1
        self.set_current_point_controls()
        self.display_sprite()

    def refresh_main_window(self):
        #reset collected points
        self._points = []
        self.points_listbox.delete(0, END)

        #reset sliders
        if self._anim_slider:
            self._anim_slider.set(0)
            self._anim_slider.configure(from_=0, to=self._sprite_cfg.anim_frames)
        if self._rot_slider:
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
        
        if self._image_display:
            self._image_display.config(image=self._sprite_image)
