from __future__ import annotations
import tkinter as tk
from transcendence_effect_placer.ui.main_screen import SpriteViewer

def main():
    root = tk.Tk()
    sprite_viewer = SpriteViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()
    