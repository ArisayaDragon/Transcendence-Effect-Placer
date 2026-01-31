from __future__ import annotations
import tkinter as tk
from tkinter import LEFT, RIGHT, TOP, BOTTOM, X, Y, VERTICAL, HORIZONTAL, BOTH, Toplevel, Tk
from tkinter import filedialog, messagebox
from PIL import ImageTk, Image
import numpy as np

from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
from transcendence_effect_placer.ui.load_file import SpriteOpener
from transcendence_effect_placer.ui.sprite_settings import SpriteSettingsDialogue


class SpriteViewer:
    def __init__(self, root: Tk):
        self._root = root
        self._image_path: str|None = None
        self._image: None = None
        self._sprite_cfg = SpriteConfig()
        self.coordinates = []
        self._wnd_image_loader = SpriteOpener(root)
        self._wnd_sprite_settings = SpriteSettingsDialogue(root)
        self.load_image()

    def load_sprite_cfg(self):
        self._wnd_sprite_settings.open_dialogue()
        

    def load_image(self):
        can_continue = False

        self._wnd_image_loader.load_image()
        self._image_path = self._wnd_image_loader.get_path()

        if not self._image_path:
            return

        image = Image.open(self.image_path)
        self._sprite_cfg.w = int(image.size[0] / 20)
        self._sprite_cfg.h = int(image.size[1] / 18)
        
        self._wnd_sprite_settings.open_dialogue()
        #hopefully we cant get here until that dialogue box is closed?

    def create_main_window(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Load", command=self.load_image)
        file_menu.add_command(label="Change Sprite Parameters", command=self.change_settings)
        file_menu.add_command(label="Export")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        self.root.config(menu=menubar)

        control_container = tk.Frame(self.root, width=int(self.root.winfo_screenwidth() * 0.2))
        control_container.pack(side=LEFT, fill=Y)

        control_canvas = tk.Canvas(control_frame)
        control_canvas.pack(side=LEFT, fill="both", expand=True)
        
        control_frame_scroll_y = tk.Scrollbar(control_frame, orient=VERTICAL, command=control_canvas.yview)
        control_frame_scroll_y.pack(side=RIGHT, fill=Y)

        control_canvas.configure(yscrollcommand=control_frame_scroll_y.set)

        control_frame = tk.Frame(self.root, width=int(self.root.winfo_screenwidth() * 0.2))
        control_frame.pack(side=LEFT, fill=Y)

        display_frame = tk.Frame(self.root, width=int(self.root.winfo_screenwidth() * 0.8))
        display_frame.pack(side=RIGHT, fill=BOTH, expand=True)

        image_label = tk.Label(display_frame)
        image_label.pack()

        self.image_tk = ImageTk.PhotoImage(Image.open(self.image_path))
        image_label.config(image=self.image_tk)

        slider_frame = tk.Frame(display_frame)
        slider_frame.pack(fill=X)

        animation_slider = tk.Scale(slider_frame, from_=0, to=self.sprite_settings["animation_frames"], orient=tk.HORIZONTAL, length=200)
        animation_slider.set(0)
        animation_slider.pack(side=LEFT)

        rotation_slider = tk.Scale(slider_frame, from_=0, to=self.sprite_settings["rotation_frames"] - 1, orient=tk.HORIZONTAL, length=200)
        rotation_slider.set(0)
        rotation_slider.pack(side=RIGHT)

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
            x = event.x - self.sprite_settings["sprite_width"] // 2
            y = event.y - self.sprite_settings["sprite_height"] // 2

            self.coordinates.append((x, y))
            coordinates_listbox.insert(tk.END, f"({x}, {y})")

        image_label.bind("<Button-1>", add_coordinate)

    def change_settings(self):
        settings_window = tk.Toplevel()
        settings_window.title("Change Sprite Parameters")
