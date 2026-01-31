from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass
class SpriteConfig:
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    anim_frames: int = 0
    rot_frames: int = 360
    rot_cols: int = 20
    viewport_ratio: float = 0.2
    real: bool = False

    def rot_col_size(self) -> int:
        return math.floor((self.rot_frames - 1) / self.rot_cols) + 1
    
    def rot_x(self, rotation: int = 0):
        return math.floor(rotation / self.rot_col_size())
    
    def rot_y(self, rotation: int = 0):
        return rotation % self.rot_col_size()

    def frame(self, rotation: int = 0, anim: int = 0) -> ICoord:
        rot_col = self.rot_x(rotation)
        rot_pos = self.rot_y(rotation)
        anim_x = anim * self.w
        rot_x = rot_col * self.w * (self.anim_frames + 1)
        rot_y = rot_pos * self.h
        x = self.x + anim_x + rot_x
        y = self.y + rot_y
        return ICoord(x, y)

@dataclass
class CCoord:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

@dataclass
class ICoord:
    x: int = 0
    y: int = 0

@dataclass
class PCoord:
    dir: float = 0.0
    rad: float = 0.0
    z: float = 0.0
