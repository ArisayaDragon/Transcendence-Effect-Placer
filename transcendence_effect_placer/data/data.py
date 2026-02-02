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
    
    def viewport_size(self):
        return max(1, self.w / (2.0 * self.viewport_ratio))

    def frame(self, rotation: int = 0, anim: int = 0) -> ICoord:
        rot_col = self.rot_x(rotation)
        rot_pos = self.rot_y(rotation)
        anim_x = anim * self.w * self.rot_cols
        rot_x = rot_col * self.w
        rot_y = rot_pos * self.h
        x = self.x + anim_x + rot_x
        y = self.y + rot_y
        return ICoord(x, y)

@dataclass
class CCoord:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __str__(self) -> str:
        return f"({self.x},{self.y},{self.z})"
    
    def as_icoord(self):
        return ICoord(int(self.x), int(self.y))

@dataclass
class ICoord:
    x: int = 0
    y: int = 0
    
    def __str__(self) -> str:
        return f"({self.x},{self.y})"
    
    def as_ccoord(self):
        return CCoord(float(self.x), float(self.y), 0)

@dataclass
class PCoord:
    a: float = 0.0
    r: float = 0.0
    z: float = 0.0
    
    def __str__(self) -> str:
        return f"({self.a} radians,{self.r},{self.z})"
    
    def dir_deg(self) -> float:
        return math.degrees(self.r)
    
    def dir_i360(self) -> float:
        return round(math.degrees(self.r)) % 360
    
    def dir_i180(self) -> float:
        dir = self.dir_i360()
        if dir <= 180:
            return dir
        return dir - 360
