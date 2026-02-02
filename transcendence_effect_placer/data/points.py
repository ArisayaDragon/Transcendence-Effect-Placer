
from abc import ABC, abstractmethod
import math
from PIL.ImageDraw import ImageDraw
from dataclasses import dataclass

from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
from transcendence_effect_placer.data.math import convert_polar_to_projection, convert_projection_to_polar

@dataclass
class MirrorOptions:
    x: bool|int = False
    y: bool|int = False
    z: bool|int = False

MIRROR_NULL = MirrorOptions()

class PointType(str): pass

PT_DEVICE = PointType("Device")
PT_THRUSTER = PointType("Thruster")
PT_DOCK = PointType("Dock")
PT_GENERIC = PointType("Generic")

'''
Coordinate systems:
PIL: 0,0 is upper left, +x is right, +y is down <-- this is what PIL requires for drawing
Sprite: 0,0 is center of sprite, +x is right, +y is up <-- this is what the user interacts with
XMLPolar: *,0 is the center of the sprite, a=0 is forwards, and a+ moves counter clockwise
GeorgeScene: 0,0,0 is center of the sprite, +x is backwards (180 degrees from the bow), +y is PROBABLY to the port side (90 degrees from the bow), +z is above
GeorgeZ: the z position is weird and exists sort of outside most of these except the scene?
'''

class DefaultSpriteConfig(SpriteConfig):
    def viewport_size(self):
        return 256.0

DEFAULT_CFG = DefaultSpriteConfig(0,0,102,102,0,360,20,0.2,False)  #george uses a default viewport scale of 256

class PILCoord(ICoord):
    def to_sprite(self, cfg: SpriteConfig):
        return SpriteCoord(self.x - cfg.w//2, -(self.y - cfg.h//2))

class SpriteCoord(ICoord):
    def to_PIL(self, cfg: SpriteConfig):
        return PILCoord(self.x + cfg.w//2, -self.y + cfg.h//2)
    def to_gscene(self, z: float=0):
        return GSceneCoord(-self.y, -self.x, z)
    
class GSceneCoord(CCoord):
    def to_sprite(self):
        return SpriteCoord(-round(self.y), -round(self.x))
    def to_polar_XML(self, cfg: SpriteConfig = DEFAULT_CFG, facing: int = 0):
        pcoord = convert_projection_to_polar(cfg, self, facing)
        return PXMLCoord(pcoord.a, pcoord.r, pcoord.z)
    
class PXMLCoord(PCoord):
    def to_gscene(self, cfg: SpriteConfig = DEFAULT_CFG):
        icoord = convert_polar_to_projection(cfg, self)
        return GSceneCoord(icoord.x, icoord.y, self.z)

class Point(ABC):
    point_type: PointType = PT_GENERIC
    color = (0,255,0,255)
    mirror_support = MirrorOptions(0,0,0)

    def __init__(self, coord: PILCoord|SpriteCoord, label: str, sprite_cfg: SpriteConfig, rot_frame: int):
        self.label = label
        self.sprite_coord: SpriteCoord = coord.to_sprite(sprite_cfg) if isinstance(coord, PILCoord) else coord
        print(self.sprite_coord)
        self.scene_coord: GSceneCoord = self.sprite_coord.to_gscene()
        self._cfg = sprite_cfg
        self.polar_coord: PXMLCoord = self.scene_coord.to_polar_XML(self._cfg, rot_frame)
        print(self.polar_coord)
        self.scene_coord = self.polar_coord.to_gscene(self._cfg)
        print('rotationally corrected pos:', self.scene_coord)
        self.mirror = MirrorOptions()

    def _to_raw_coord(self, coord: ICoord) -> ICoord:
        return ICoord(coord.x, -coord.y)
    
    def _from_raw_coord(self, coord: ICoord) -> ICoord:
        return ICoord(coord.x, -coord.y)

    def update_from_polar(self, coord: PXMLCoord|PCoord):
        self.polar_coord = coord if isinstance(coord, PXMLCoord) else PXMLCoord(coord.a, coord.r, coord.z)
        self.scene_coord = self.polar_coord.to_gscene(self._cfg)
        self.sprite_coord = self.scene_coord.to_sprite()

    def update_from_projection(self, coord: SpriteCoord, rot_frame: int = 0):
        self.scene_coord = coord.to_gscene(self.scene_coord.z)
        self.polar_coord = self.scene_coord.to_polar_XML(self._cfg, rot_frame)
        self.scene_coord = self.polar_coord.to_gscene(self._cfg)
        self.sprite_coord = self.scene_coord.to_sprite()

    def pil_coord(self, coord: ICoord) -> ICoord:
        return ICoord(-1*coord.x + round(self._cfg.w/2), coord.y + round(self._cfg.h/2))
    
    def __str__(self) -> str:
        return str(self.point_type) + ' ' + self.label + ': ' + repr(self.sprite_coord)
    
    def set_mirror_x(self, mirror=True):
        self.mirror.x = mirror
    
    def set_mirror_y(self, mirror=True):
        self.mirror.y = mirror

    def set_mirror_z(self, mirror=True):
        self.mirror.z = mirror

    def set_z(self, z:int = 0):
        self.polar_coord.z = z
        self.update_from_polar(self.polar_coord)

    def set_radius(self, radius: float = 0.0):
        self.polar_coord.r = radius
        self.update_from_polar(self.polar_coord)

    def set_pos_angle(self, pos_angle: float = 0.0):
        self.polar_coord.r = pos_angle
        self.update_from_polar(self.polar_coord)

    def set_pos_angle_deg(self, pos_angle_degrees: float = 0.0):
        self.polar_coord.r = math.radians(pos_angle_degrees)
        self.update_from_polar(self.polar_coord)

    def set_x(self, x:int = 0):
        self.sprite_coord.x = x
        self.update_from_projection(self.sprite_coord)

    def set_y(self, y:int = 0):
        self.sprite_coord.y = y
        self.update_from_projection(self.sprite_coord)

    def _mirror_angle_degrees(self, degrees: float, mirror: MirrorOptions) -> float:
        #convert to transcendence ship angle, which is -90 degrees offset
        degrees -= 90
        degrees %= 360
        if degrees > 180:
            degrees -= 360
        if mirror.x:
            degrees *= -1
        if mirror.y:
            if degrees >= 0:
                degrees -= 180
            else:
                degrees += 180
            degrees *= -1
        #convert back to screenspace angle
        degrees += 90
        degrees %= 360
        return degrees

    def get_projection_coord_at_direction(self, direction: int = 0, mirror: MirrorOptions = MIRROR_NULL) -> ICoord:
        adj_dir_deg = math.degrees(self.polar_coord.a)
        adj_dir_deg = self._mirror_angle_degrees(adj_dir_deg, mirror) - direction % 360
        adj_dir = math.radians(adj_dir_deg)
        adj_rad = self.polar_coord.r
        adj_z = self.polar_coord.z * (-1 if mirror.z else 1)
        adjusted_direction = PCoord(adj_dir, adj_rad, adj_z)
        return self.pil_coord(convert_polar_to_projection(self._cfg, adjusted_direction))
    
    @abstractmethod
    def to_xml(self) -> str:
        pass

    @abstractmethod
    def render_to_image(self, image: ImageDraw, rotation_dir: int):
        pass

    def _get_mirror_options(self) -> list[MirrorOptions]:
        ret: list[MirrorOptions] = []
        ret.append(MIRROR_NULL) #always render self
        x = self.mirror.x and self.mirror_support.x
        y = self.mirror.y and self.mirror_support.y
        z = self.mirror.z and self.mirror_support.z
        if z:
            ret.append(MirrorOptions(0,0,1))
        if y:
            ret.append(MirrorOptions(0,1,0))
        if y and z:
            ret.append(MirrorOptions(0,1,1))
        if x:
            ret.append(MirrorOptions(1,0,0))
        if x and z:
            ret.append(MirrorOptions(1,0,1))
        if x and y:
            ret.append(MirrorOptions(1,1,0))
        if x and y and z:
            ret.append(MirrorOptions(1,1,1))
        return ret

    def _render_point(self, image:ImageDraw, direction: int = 0, mirror: MirrorOptions = MIRROR_NULL) -> ICoord:
        coord = self.get_projection_coord_at_direction(direction, mirror)
        image.circle((coord.x, coord.y), 2, self.color)
        return coord
        
class PointGeneric(Point):
    def to_xml(self):
        return ""
    def render_to_image(self, image, rotation_dir):
        self._render_point(image, rotation_dir)

class PointDock(Point):
    point_type = PT_DOCK
    color = (0,0,255,255)
    mirror_support = MirrorOptions(1,1,0)
    
    def to_xml(self):
        ret = f'<Port x="{self.sprite_coord.x}"\ty="{self.sprite_coord.y}"/>'
        if self.mirror.x:
            ret += f'\n<Port x="{self.sprite_coord.x * -1}"\ty="{self.sprite_coord.y}"/>'
        if self.mirror.y:
            ret += f'\n<Port x="{self.sprite_coord.x}"\ty="{self.sprite_coord.y * -1}"/>'
        if self.mirror.x and self.mirror.y:
            ret += f'\n<Port x="{self.sprite_coord.x * -1}"\ty="{self.sprite_coord.y * -1}"/>'
        return ret
    
    def render_to_image(self, image, rotation_dir):
        '''
        Docstring for render_to_image
        
        :param self: Description
        :param image: Description
        :param rotation_dir: igmored for Docking points because they dont rotate
        '''
        mirrors = self._get_mirror_options()
        for mirror in mirrors:
            self._render_point(image, 0, mirror)
    
class PointThuster(Point):
    point_type = PT_THRUSTER
    color = (255,255,0,255)
    mirror_support = MirrorOptions(1,0,1)

    def __init__(self, coord: PILCoord|SpriteCoord, label: str, sprite_cfg: SpriteConfig, rot_frame: int, direction: int = 0):
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
                    range_str += f",{i}"
            if range_start >= 0:
                if e != match:
                    if range_start == i-1:
                        pass
                    elif range_start == i-2:
                        range_str += f",{i-1}"
                    else:
                        range_str += f"-{i-1}"
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
        ret = f'<Effect type="thrustMain"\t\tposAngle="{self.polar_coord.dir_i360()}"\tposRadius="{round(self.polar_coord.r)}"\tposZ="{round(self.polar_coord.z)}"\trotation="{self.direction}"\teffect="&efMainThrusterLarge;"{self.get_send_to_back()}{self.get_bring_to_front()}/>'
        if self.mirror.x:
            ret += f'<Effect type="thrustMain"\t\tposAngle="-{self.polar_coord.dir_i360()}"\tposRadius="{round(self.polar_coord.r)}"\tposZ="{round(self.polar_coord.z)}"\trotation=-{self.direction}"\teffect="&efMainThrusterLarge;"{self.get_send_to_back()}{self.get_bring_to_front()}/>'
        #thrusters dont need y-mirroring
        return ret
    
    def _render_arc(self, image: ImageDraw, direction: int = 0, mirror: MirrorOptions = MIRROR_NULL):
        pos = self.get_projection_coord_at_direction(direction, mirror)
        pil_thrust_angle = (self.direction + direction + 90) % 360
        pil_thrust_angle = round(self._mirror_angle_degrees(pil_thrust_angle, mirror))
        c=3
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_angle-1, pil_thrust_angle+1, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_angle-1, pil_thrust_angle+1, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_angle-1, pil_thrust_angle+1, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_angle-1, pil_thrust_angle+1, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_angle-1, pil_thrust_angle+1, fill=self.color)
    
    def render_to_image(self, image, rotation_dir):
        mirrors = self._get_mirror_options()
        for mirror in mirrors:
            self._render_point(image, rotation_dir, mirror)
            self._render_arc(image, rotation_dir, mirror)
    
class PointDevice(Point):
    point_type = PT_DEVICE
    color = (255,0,255,255)
    color_arc = (255,0,0,255)
    mirror_support = MirrorOptions(1,1,1)

    def __init__(self, coord: PILCoord|SpriteCoord, label: str, sprite_cfg: SpriteConfig, rot_frame: int, direction: int = 0, arc: int = -1, arc_start: int=-1, arc_end: int=-1):
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
    
    def _render_arc(self, image: ImageDraw, direction: int, mirror: MirrorOptions = MIRROR_NULL):
        pos = self.get_projection_coord_at_direction(direction, mirror)
        aim_dir, start, end = self.get_arc_at_dir(direction)
        aim_dir = round(self._mirror_angle_degrees(aim_dir, mirror))
        start = round(self._mirror_angle_degrees(start, mirror))
        end = round(self._mirror_angle_degrees(end, mirror))
        image.arc((pos.x-5, pos.y-5, pos.x+5, pos.y+5), (90+start) % 360, (90+end) % 360, fill=self.color_arc)
        image.arc((pos.x-7, pos.y-7, pos.x+7, pos.y+7), (90+aim_dir) % 360, (90+aim_dir) % 360, fill=self.color)

    def get_arc_xml(self):
        return ""

    def to_xml(self):
        ret = f'<DeviceSlot id="{self.label}"\t\tposAngle="{self.polar_coord.dir_i360()}"\tposRadius="{round(self.polar_coord.r)}"\tposZ="{round(self.polar_coord.z)}"\tfireAngle="{self.direction}"\t{self.get_arc_xml()}/>'
        if self.mirror.x:
            ret += f'<DeviceSlot id="{self.label}"\t\tposAngle="-{self.polar_coord.dir_i360()}"\tposRadius="{round(self.polar_coord.r)}"\tposZ="{round(self.polar_coord.z)}"\tfireAngle=-{self.direction}"\t{self.get_arc_xml()}/>'
        #thrusters dont need y-mirroring
        return ret
    
    def render_to_image(self, image, rotation_dir):
        mirrors = self._get_mirror_options()
        for mirror in mirrors:
            self._render_point(image, rotation_dir, mirror)
            self._render_arc(image, rotation_dir, mirror)
