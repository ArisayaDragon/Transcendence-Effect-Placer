# Transcendence Effect Placer

This is a small utility for accelerating the implementation of ships into the game [Transcendence](https://github.com/kronosaur/TranscendenceDev)

It provides an easy way to interactively place effects and devices onto a pre-rendered sprite.
This placement data can then be exported to XML, the contents of which can then be pasted into a Transcendence `<ShipClass>`.

## Quickstart

### Installation

As this is a python program, is is possible to run it directly out of the repo by running `python transcendence_effect_placer.py`

However, prepackaged executables are provided in the release section of this repo for your convenience: https://github.com/ArisayaDragon/Transcendence-Effect-Placer/releases

### Usage

Upon starting the program, you will be immediately prompted to load a sprite.
Once you have selected a sprite sheet, you will need to enter some basic information about the sprite.

* Sprite Pos X: This is the left most pixel column of the ship's first frame (relative to the upper left of the sprite sheet)
* Sprite Pos Y: This is the top most pixel row of the ship's first frame (relative to the upper left of the sprite sheet)
* Sprite Width: This is the width of an individual frame of the ship's rotation
* Sprite Height: This is the height of an indivudal frame of the ship's rotation
* Animation Frames: This is the number of additional frames per rotation that are used for animation
* Rotation Frames: This is the total number of rotation frames for this ship. Transcendence currently supports up to 360.
* Rotation Columns: This is the number of columns that the rotation frames are split up between.
* Viewport Ratio: This is the distance across the viewable area of the 3d camera relative to the z-height of the camera. If you are using Arisaya's default blender scene, just leave this as the default (0.2)

Accepting these settings will then prompt the program to load up the image file and display the first rotation frame of the ship on the right side of the screen.

Two sliders are present underneath the ship, allowing you to rotate it around or play through its animation frames (if any are present)

You can click on the ship to add a point. The point may not be exactly where you clicked, but dont worry about that, you can finetune it later (and probably will need to anyways)

The point will show up in a list to the left, and its data will automatically populate the sliders beneath that list.

To make this point exportable to Transcendence, you will need to pick one of 3 types for it:
* Device - these are typically used for weapon firing points. They rotate with the ship, and have additional direction and optional fire arc parameters. Only arc OR arc start + arc end needs to be defined. If both are defined, arc will override arc start/arc end. They are specified in polar coordinates, with a z-offset.
* Effect - these are typically used for engine/thruster effects. They rotate with the ship, and have an additional direction. They are specified in polar coordinates, with a z-offset.
* Dock - these are docking ports. They do not rotate with the ship, and are specified in terms of X and Y. They also do not use Z position.

You can then adjust the sliders to move the point around. The ability to move the ship through its rotation facings will let you verify that the effect or device position remains in a sensible location as the ship moves - in some extreme cases (large and/or tall ships), not setting the z-pos correctly may cause an effect or weapon to completely 'fall off' of the ship as it rotates, or end up in nonsensical locations.

Once you are satisfied with the position of this point, you can then mirror it as necessary - the mirrored points do not show up in the list, and are attached to the parent point.

You may also clone a point, creating a fully editable separate point.

You can also click on the sprite to add more points. Generic points aren't exportable though so make sure to change them to a valid point type.

Once you are satisified with the placement of the points, you can then go to File->Export and save a file with XML that you can paste into your `<ShipClass>`. Note that you will probably want to change some of the text fields, such as the ids of device slots.

## Building Packaged Executables From Source

Requirements:
* Python 3.10+
    * Needs to have [pip](https://packaging.python.org/en/latest/tutorials/installing-packages/#ensure-you-can-run-pip-from-the-command-line) installed

1. Clone this repo
2. run __venv_init.bat
3. run _venv_start.bat
4. run install_requirements.bat
5. run build.bat
6. your executable will be available in the `build` directory!
