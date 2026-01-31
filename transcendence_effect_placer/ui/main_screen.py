from __future__ import annotations
import tkinter as tk
from tkinter import LEFT, RIGHT, TOP, BOTTOM, X, Y, VERTICAL, HORIZONTAL, BOTH, Toplevel, Tk, Scale, Label
from tkinter import filedialog, messagebox
from PIL import ImageTk, Image
from PIL.ImageFile import ImageFile
import numpy as np
from time import sleep

from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
from transcendence_effect_placer.data.math import convert_polar_to_projection, convert_projection_to_polar
from transcendence_effect_placer.ui.load_file import SpriteOpener
from transcendence_effect_placer.ui.sprite_settings import SpriteSettingsDialogue

#set PIL max pixels
Image.MAX_IMAGE_PIXELS = 2 ** 34

class SpriteViewer:
    def __init__(self, root: Tk):
        self._root = root
        self._image_path: str|None = None
        self._image: ImageFile|None = None
        self._sprite_image: ImageTk.PhotoImage|None = None
        self._image_display: Label|None = None
        self._sprite_cfg = SpriteConfig()
        self.coordinates = []
        self._wnd_image_loader = SpriteOpener(root)
        self._wnd_sprite_settings = SpriteSettingsDialogue(root)
        self._anim_slider: Scale|None = None
        self._rot_slider: Scale|None = None
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

        self._image = Image.open(self._image_path)
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
        
        self._sprite_image = ImageTk.PhotoImage(self._image.crop(crop_rect))
        if self._image_display is None:
            print('Err: Label storing image was not initialized')
            return
        self._image_display.config(image=self._sprite_image)

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

            self.coordinates[selected_index[0]] = (x, y)
            coordinates_listbox.delete(selected_index)
            coordinates_listbox.insert(tk.END, f"({x}, {y})")

        update_button = tk.Button(entry_frame, text="Update", command=update_coordinates)
        update_button.pack(side=LEFT)

        def add_coordinate(event):
            x = event.x - self._sprite_cfg.w // 2
            y = event.y - self._sprite_cfg.h // 2
            
            coord = ICoord(x, y)
            self.coordinates.append(coord)
            coordinates_listbox.insert(tk.END, str(coord))

        self._image_display.bind("<Button-1>", add_coordinate)
