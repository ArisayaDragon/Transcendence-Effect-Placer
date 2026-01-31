from __future__ import annotations
from tkinter import LEFT, RIGHT, TOP, BOTTOM, X, Y, VERTICAL, HORIZONTAL, BOTH, Toplevel, Tk
from tkinter import filedialog


class SpriteOpener:
    def __init__(self, root: Tk):
        self._root = root
        self._path: str|None = None

    def load_image(self):
        new_path = filedialog.askopenfilename(filetypes=[("Image Files", ".png .jpg .jpeg .bmp")])
        if new_path:
            self._path = new_path
        return new_path

    def get_path(self):
        return self._path