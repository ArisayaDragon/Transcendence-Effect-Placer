from __future__ import annotations
import tkinter as tk
from tkinter import LEFT, RIGHT, TOP, BOTTOM, X, Y, VERTICAL, HORIZONTAL, BOTH, Toplevel, Tk
from tkinter import filedialog, messagebox
from PIL import ImageTk, Image
import numpy as np

from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
from transcendence_effect_placer.ui.load_file import SpriteOpener
from transcendence_effect_placer.ui.sprite_settings import SpriteSettingsDialogue
from transcendence_effect_placer.ui.main_screen import SpriteViewer

def main():
    root = tk.Tk()
    print(type(root))
    sprite_viewer = SpriteViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
    