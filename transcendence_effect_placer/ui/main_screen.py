from __future__ import annotations
import tkinter as tk
from tkinter import LEFT, RIGHT, TOP, BOTTOM, X, Y, VERTICAL, HORIZONTAL, BOTH, Toplevel, Tk, Scale, Label
from tkinter import filedialog, messagebox
from abc import ABC, abstractmethod
from PIL import ImageTk
import PIL
from PIL.ImageFile import ImageFile
from PIL.ImageDraw import ImageDraw
from PIL.Image import Image
import numpy as np
from time import sleep
import math

from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
from transcendence_effect_placer.data.math import convert_polar_to_projection, convert_projection_to_polar
from transcendence_effect_placer.ui.load_file import SpriteOpener
from transcendence_effect_placer.ui.sprite_settings import SpriteSettingsDialogue

#set PIL max pixels
Image.MAX_IMAGE_PIXELS = 2 ** 34 #this is 2**36, which is 64GB - should be plenty big for current transcendence ships

class SpriteMode(str): pass

_MODE_SHIP = SpriteMode("Ship")
_MODE_STATION = SpriteMode("Station")

class PointType(str): pass

_PT_DEVICE = PointType("Device")
_PT_THRUSTER = PointType("Thruster")
_PT_DOCK = PointType("Dock")
_PT_GENERIC = PointType("Generic")

class Point(ABC):
    point_type: PointType = _PT_GENERIC
    color = (0,255,0,255)

    def __init__(self, coord: ICoord, label: str, sprite_cfg: SpriteConfig, rot_frame: int):
        self.label = label
        self.projection_coord = coord
        print(self.projection_coord)
        self._cfg = sprite_cfg
        self.polar_coord = convert_projection_to_polar(self._cfg, coord, rot_frame)
        print(self.polar_coord)
        if rot_frame:
            self.projection_coord = convert_polar_to_projection(self._cfg, self.polar_coord)
            print('rotationally corrected pos:', self.projection_coord)
        self.mirror_x = False #mirrors left-right
        self.mirror_y = False #mirrors front-back

    def update_from_polar(self, coord: PCoord):
        self.polar_coord = coord
        self.projection_coord = convert_polar_to_projection(self._cfg, coord)

    def update_from_projection(self, coord: ICoord, rot_frame: int):
        self.polar_coord = convert_projection_to_polar(self._cfg, coord, rot_frame)
        if rot_frame:
            self.projection_coord = convert_polar_to_projection(self._cfg, self.polar_coord, rot_frame)
        else:
            self.projection_coord = coord

    def pil_coord(self, coord: ICoord) -> ICoord:
        return ICoord(coord.x + round(self._cfg.w/2), coord.y + round(self._cfg.h/2))
    
    def __str__(self) -> str:
        return str(self.point_type) + ' ' + self.label + ': ' + repr(self.projection_coord)
    
    def set_mirror_x(self, mirror=True):
        self.mirror_x = mirror
    
    def set_mirror_y(self, mirror=True):
        self.mirror_y = mirror

    def set_z(self, z:int = 0):
        self.polar_coord.z = z
        self.update_from_polar(self.polar_coord)

    def set_radius(self, radius: float = 0.0):
        self.polar_coord.rad = radius
        self.update_from_polar(self.polar_coord)

    def set_pos_angle(self, pos_angle: float = 0.0):
        self.polar_coord.rad = pos_angle
        self.update_from_polar(self.polar_coord)

    def set_pos_angle_deg(self, pos_angle_degrees: float = 0.0):
        self.polar_coord.rad = math.radians(pos_angle_degrees)
        self.update_from_polar(self.polar_coord)

    def set_x(self, x:int = 0):
        self.projection_coord.x = x
        self.update_from_projection(self.projection_coord)

    def set_y(self, y:int = 0):
        self.projection_coord.y = y
        self.update_from_projection(self.projection_coord)

    def get_projection_coord_at_direction(self, direction: int = 0) -> ICoord:
        adjusted_direction = PCoord(self.polar_coord.dir + math.radians(direction), self.polar_coord.rad, self.polar_coord.z)
        return self.pil_coord(convert_polar_to_projection(self._cfg, adjusted_direction))
    
    @abstractmethod
    def to_xml(self) -> str:
        pass

    def draw(self, image: Image, rotation_dir: int):
        draw = ImageDraw.Draw(image, rotation_dir)

    @abstractmethod
    def render_to_image(self, image: ImageDraw, rotation_dir: int):
        pass

    def _render_point(self, image:ImageDraw, direction: int = 0) -> ICoord:
        coord = self.get_projection_coord_at_direction(direction)
        image.circle((coord.x, coord.y), 2, self.color)
        return coord
        
class PointGeneric(Point):
    def to_xml(self):
        return ""
    def render_to_image(self, image, rotation_dir):
        self._render_point(image, rotation_dir)

class PointDock(Point):
    point_type = _PT_DOCK
    color = (0,0,255,255)
    
    def to_xml(self):
        ret = f'<Port x="{self.projection_coord.x}"\ty="{self.projection_coord.y}"\>'
        if self.mirror_x:
            ret += f'\n<Port x="{self.projection_coord.x * -1}"\ty="{self.projection_coord.y}"\>'
        if self.mirror_y:
            ret += f'\n<Port x="{self.projection_coord.x}"\ty="{self.projection_coord.y * -1}"\>'
        if self.mirror_x and self.mirror_y:
            ret += f'\n<Port x="{self.projection_coord.x * -1}"\ty="{self.projection_coord.y * -1}"\>'
        return ret
    
    def render_to_image(self, image, rotation_dir):
        '''
        Docstring for render_to_image
        
        :param self: Description
        :param image: Description
        :param rotation_dir: igmored for Docking points because they dont rotate
        '''
        self._render_point(image, 0)
    
class PointThuster(Point):
    point_type = _PT_THRUSTER
    color = (255,255,0,255)

    def __init__(self, coord: ICoord, label: str, sprite_cfg: SpriteConfig, rot_frame: int, direction: int = 0):
        '''
        Docstring for __init__
        
        :param coord: pos on image
        :type coord: ICoord
        :param label: name of point
        :type label: str
        :param sprite_cfg: sprite configuration
        :type sprite_cfg: SpriteConfig
        :param direction: direction thruster is facing (in degrees)
        :type direction: int
        '''
        super().__init__(coord, label, sprite_cfg, rot_frame)
        self.direction = direction
        self.under_over = [0 for i in range(sprite_cfg.rot_frames)]

    def set_direction(self, direction: int):
        self.direction = direction

    def send_to_back(self, frame: int):
        self.under_over[frame] = -1

    def bring_to_front(self, frame: int):
        self.under_over[frame] = 1

    def accumulate_range_str(self, match: int):
        range_str = ""
        range_start = -1
        for i in range(len(self.under_over)):
            e = self.under_over[i]
            # if we are not already in a range
            if range_start < 0:
                if e == match:
                    range_start = i
                    range_str.append(f",{i}")
            if range_start >= 0:
                if e != match:
                    if range_start == i-1:
                        pass
                    elif range_start == i-2:
                        range_str.append(f",{i-1}")
                    else:
                        range_str.append(f"-{i-1}")
                    range_start = -1
        range_str = range_str.strip(',')
        return range_str

    def get_send_to_back(self):
        if all([e == -1 for e in self.under_over]):
            return '\tsendToBack="*"'
        range_str = self.accumulate_range_str(-1)
        if not range_str:
            return ""
        else:
            return f'\tsendToBack="{range_str}"'
        
    def get_bring_to_front(self):
        if all([e == 1 for e in self.under_over]):
            return '\tbringToFront="*"'
        range_str = self.accumulate_range_str(1)
        if not range_str:
            return ""
        else:
            return f'\tbringToFront="{range_str}"'

    def to_xml(self):
        ret = f'<Effect type="thrustMain"\t\tposAngle="{round(self.polar_coord.dir_degrees()) % 360}"\tposRadius="{round(self.polar_coord.rad)}"\tposZ="{round(self.polar_coord.z)}"\trotation="{self.direction}"\teffect="&efMainThrusterLarge;"{self.get_send_to_back()}{self.get_bring_to_front()}\>'
        if self.mirror_x:
            ret += f'<Effect type="thrustMain"\t\tposAngle="-{round(self.polar_coord.dir_degrees()) % 360}"\tposRadius="{round(self.polar_coord.rad)}"\tposZ="{round(self.polar_coord.z)}"\trotation=-{self.direction}"\teffect="&efMainThrusterLarge;"{self.get_send_to_back()}{self.get_bring_to_front()}\>'
        #thrusters dont need y-mirroring
        return ret
    
    def _render_arc(self, image: ImageDraw, direction: int = 0):
        pos = self.get_projection_coord_at_direction(direction)
        pil_thrust_anngle = (self.direction + direction + 90) % 360
        c=3
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_anngle, pil_thrust_anngle, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_anngle, pil_thrust_anngle, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_anngle, pil_thrust_anngle, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_anngle, pil_thrust_anngle, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_anngle, pil_thrust_anngle, fill=self.color)
    
    def render_to_image(self, image, rotation_dir):
        self._render_point(image, rotation_dir)
        self._render_arc(image, rotation_dir)
    
class PointDevice(Point):
    point_type = _PT_DEVICE
    color = (255,0,255,255)
    color_arc = (255,0,0,255)

    def __init__(self, coord: ICoord, label: str, sprite_cfg: SpriteConfig, rot_frame: int, direction: int = 0, arc: int = -1, arc_start: int=-1, arc_end: int=-1):
        super().__init__(coord, label, sprite_cfg, rot_frame)
        self.direction = direction
        self.arc_start = arc_start
        self.arc_end = arc_end
        self.arc = arc

    def set_direction(self, direction: int):
        self.direction = direction

    def set_arc(self, arc: int):
        self.arc = arc

    def set_arc_start(self, arc_start: int):
        self.arc_start = arc_start

    def set_arc_end(self, arc_end: int):
        self.arc_end = arc_end

    def get_arc_at_dir(self, dir: int) -> tuple[int, int, int]:
        '''
        Docstring for get_arc_at_dir
        
        :param self: Description
        :param dir: Description
        :type dir: int
        :return: default fire direction, arc start angle, arc end angle
        :rtype: tuple[int, int, int]
        '''
        direction = (self.direction + dir) % 360
        #if we have an arc, that overrides start and end
        if (self.arc >= 0):
            start = round(direction - self.arc / 2) % 360
            end = round(direction + self.arc / 2) % 360
        elif (self.arc_start >= 0 and self.arc_end >= 0):
            start = (self.arc_start + dir) % 360
            end = (self.arc_end + dir) % 360
        else:
            start = -1
            end = -1
        return (direction, start, end)
    
    def _render_arc(self, image: ImageDraw, direction: int):
        pos = self.get_projection_coord_at_direction(direction)
        aim_dir, start, end = self.get_arc_at_dir(direction)
        image.arc((pos.x-5, pos.y-5, pos.x+5, pos.y+5), (90+start) % 360, (90+end) % 360, fill=self.color_arc)
        image.arc((pos.x-7, pos.y-7, pos.x+7, pos.y+7), (90+aim_dir) % 360, (90+aim_dir) % 360, fill=self.color)

    def to_xml(self):
        ret = f'<Effect type="thrustMain"\t\tposAngle="{round(self.polar_coord.dir_degrees()) % 360}"\tposRadius="{round(self.polar_coord.rad)}"\tposZ="{round(self.polar_coord.z)}"\trotation="{self.direction}"\teffect="&efMainThrusterLarge;"{self.get_send_to_back()}{self.get_bring_to_front()}\>'
        if self.mirror_x:
            ret += f'<Effect type="thrustMain"\t\tposAngle="-{round(self.polar_coord.dir_degrees()) % 360}"\tposRadius="{round(self.polar_coord.rad)}"\tposZ="{round(self.polar_coord.z)}"\trotation=-{self.direction}"\teffect="&efMainThrusterLarge;"{self.get_send_to_back()}{self.get_bring_to_front()}\>'
        #thrusters dont need y-mirroring
        return ret
    
    def render_to_image(self, image, rotation_dir):
        self._render_point(image, rotation_dir)
        self._render_arc(image, rotation_dir)



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
        self.load_image()

    def load_sprite_cfg(self):
        self._wnd_sprite_settings.open_dialogue(self._sprite_cfg)

        if self._wnd_sprite_settings._sprite_cfg.real:
            self._sprite_cfg = self._wnd_sprite_settings._sprite_cfg
            self.create_main_window()
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

    def display_sprite(self):
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
            if pt.point_type == _PT_DEVICE:
                export_str_devices += '\n' +pt.to_xml()
            elif pt.point_type == _PT_DOCK:
                export_str_docking += '\n' +pt.to_xml()
            elif pt.point_type == _PT_THRUSTER:
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

    def create_main_window(self):
        menubar = tk.Menu(self._root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Load", command=self.load_image)
        file_menu.add_command(label="Change Sprite Parameters", command=self.load_sprite_cfg)
        file_menu.add_command(label="Export")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        self._root.config(menu=menubar)

        control_container = tk.Frame(self._root, width=int(self._root.winfo_screenwidth() * 0.2))
        control_container.pack(side=LEFT, fill=Y)

        control_canvas = tk.Canvas(control_container)
        control_canvas.pack(side=LEFT, fill="both", expand=True)
        
        control_frame_scroll_y = tk.Scrollbar(control_container, orient=VERTICAL, command=control_canvas.yview)
        control_frame_scroll_y.pack(side=RIGHT, fill=Y)

        control_canvas.configure(yscrollcommand=control_frame_scroll_y.set)

        control_frame = tk.Frame(control_container, width=int(self._root.winfo_screenwidth() * 0.2))
        control_frame.pack(side=LEFT, fill=Y)

        display_frame = tk.Frame(self._root, width=int(self._root.winfo_screenwidth() * 0.8))
        display_frame.pack(side=RIGHT, fill=BOTH, expand=True)

        self._image_display = tk.Label(display_frame)
        self._image_display.pack()

        self.display_sprite()
        if self._sprite_image is None:
            #error
            print('Err: sprite_image was none')
            self._root.quit()
            return
        self._image_display.config(image=self._sprite_image)

        slider_frame = tk.Frame(display_frame)
        slider_frame.pack(fill=X)

        def update_sprite(value):
            self.display_sprite()

        self._anim_slider = tk.Scale(slider_frame, from_=0, to=self._sprite_cfg.anim_frames, orient=tk.HORIZONTAL, length=200, command=update_sprite)
        self._anim_slider.set(0)
        self._anim_slider.pack(side=LEFT)

        self._rot_slider = tk.Scale(slider_frame, from_=0, to=self._sprite_cfg.rot_frames - 1, orient=tk.HORIZONTAL, length=200, command=update_sprite)
        self._rot_slider.set(0)
        self._rot_slider.pack(side=RIGHT)

        coordinates_listbox = tk.Listbox(control_frame)
        coordinates_listbox.pack(fill=BOTH, expand=True)

        entry_frame = tk.Frame(control_frame)
        entry_frame.pack()

        pos_x_label = tk.Label(entry_frame, text="Pos X")
        pos_x_label.pack(side=LEFT)

        self.pos_x_entry = tk.Entry(entry_frame)
        self.pos_x_entry.pack(side=LEFT)

        pos_y_label = tk.Label(entry_frame, text="Pos Y")
        pos_y_label.pack(side=LEFT)

        self.pos_y_entry = tk.Entry(entry_frame)
        self.pos_y_entry.pack(side=LEFT)

        def update_coordinates():
            selected_index = coordinates_listbox.curselection()
            if not selected_index:
                return

            x = int(self.pos_x_entry.get())
            y = int(self.pos_y_entry.get())

            self._points[selected_index[0]].update_from_projection(ICoord(x, y), 0)
            coordinates_listbox.delete(selected_index)
            coordinates_listbox.insert(tk.END, f"({x}, {y})")

        update_button = tk.Button(entry_frame, text="Update", command=update_coordinates)
        update_button.pack(side=LEFT)

        def add_coordinate(event):
            x = event.x - self._sprite_cfg.w // 2
            y = event.y - self._sprite_cfg.h // 2
            
            coord = ICoord(x, y)
            point = PointGeneric(coord, str(len(self._points)), self._sprite_cfg, self._rot_slider.get())
            self._points.append(point)
            coordinates_listbox.insert(tk.END, str(coord))
            self.display_sprite()

        self._image_display.bind("<Button-1>", add_coordinate)
