from __future__ import annotations
from tkinter import LEFT, RIGHT, TOP, BOTTOM, X, Y, VERTICAL, HORIZONTAL, BOTH, Toplevel, Tk
from tkinter import filedialog


class XMLSaver:
    def __init__(self, root: Tk):
        self._root = root
        self._path: str|None = None

    def save_path(self):
        new_path = filedialog.asksaveasfilename(filetypes=[("XML Files", ".xml"), ("Text Files", ".txt")], defaultextension=".xml", confirmoverwrite=True)
        if new_path:
            self._path = new_path
        return new_path

    def get_path(self):
        return self._path