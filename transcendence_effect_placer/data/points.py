
from abc import ABC, abstractmethod
import math
from PIL import ImageTk
import PIL
from PIL.ImageFile import ImageFile
from PIL.ImageDraw import ImageDraw
from PIL.Image import Image

from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
from transcendence_effect_placer.data.math import convert_polar_to_projection, convert_projection_to_polar
from transcendence_effect_placer.ui.load_file import SpriteOpener
from transcendence_effect_placer.ui.sprite_settings import SpriteSettingsDialogue

class PointType(str): pass

PT_DEVICE = PointType("Device")
PT_THRUSTER = PointType("Thruster")
PT_DOCK = PointType("Dock")
PT_GENERIC = PointType("Generic")

class Point(ABC):
    point_type: PointType = PT_GENERIC
    color = (0,255,0,255)

    def __init__(self, coord: ICoord, label: str, sprite_cfg: SpriteConfig, rot_frame: int):
        self.label = label
        self.projection_coord = coord
        print(self.projection_coord)
        self._cfg = sprite_cfg
        self.polar_coord = convert_projection_to_polar(self._cfg, coord, rot_frame)
        print(self.polar_coord)
        if rot_frame:
            self.projection_coord = convert_polar_to_projection(self._cfg, self.polar_coord)
            print('rotationally corrected pos:', self.projection_coord)
        self.mirror_x = False #mirrors left-right
        self.mirror_y = False #mirrors front-back

    def update_from_polar(self, coord: PCoord):
        self.polar_coord = coord
        self.projection_coord = convert_polar_to_projection(self._cfg, coord)

    def update_from_projection(self, coord: ICoord, rot_frame: int = 0):
        self.polar_coord = convert_projection_to_polar(self._cfg, coord, rot_frame)
        if rot_frame:
            self.projection_coord = convert_polar_to_projection(self._cfg, self.polar_coord)
        else:
            self.projection_coord = coord

    def pil_coord(self, coord: ICoord) -> ICoord:
        return ICoord(coord.x + round(self._cfg.w/2), coord.y + round(self._cfg.h/2))
    
    def __str__(self) -> str:
        return str(self.point_type) + ' ' + self.label + ': ' + repr(self.projection_coord)
    
    def set_mirror_x(self, mirror=True):
        self.mirror_x = mirror
    
    def set_mirror_y(self, mirror=True):
        self.mirror_y = mirror

    def set_z(self, z:int = 0):
        self.polar_coord.z = z
        self.update_from_polar(self.polar_coord)

    def set_radius(self, radius: float = 0.0):
        self.polar_coord.rad = radius
        self.update_from_polar(self.polar_coord)

    def set_pos_angle(self, pos_angle: float = 0.0):
        self.polar_coord.rad = pos_angle
        self.update_from_polar(self.polar_coord)

    def set_pos_angle_deg(self, pos_angle_degrees: float = 0.0):
        self.polar_coord.rad = math.radians(pos_angle_degrees)
        self.update_from_polar(self.polar_coord)

    def set_x(self, x:int = 0):
        self.projection_coord.x = x
        self.update_from_projection(self.projection_coord)

    def set_y(self, y:int = 0):
        self.projection_coord.y = y
        self.update_from_projection(self.projection_coord)

    def get_projection_coord_at_direction(self, direction: int = 0) -> ICoord:
        adjusted_direction = PCoord(self.polar_coord.dir + math.radians(direction), self.polar_coord.rad, self.polar_coord.z)
        return self.pil_coord(convert_polar_to_projection(self._cfg, adjusted_direction))
    
    @abstractmethod
    def to_xml(self) -> str:
        pass

    @abstractmethod
    def render_to_image(self, image: ImageDraw, rotation_dir: int):
        pass

    def _render_point(self, image:ImageDraw, direction: int = 0) -> ICoord:
        coord = self.get_projection_coord_at_direction(direction)
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
    
    def to_xml(self):
        ret = f'<Port x="{self.projection_coord.x}"\ty="{self.projection_coord.y}"/>'
        if self.mirror_x:
            ret += f'\n<Port x="{self.projection_coord.x * -1}"\ty="{self.projection_coord.y}"/>'
        if self.mirror_y:
            ret += f'\n<Port x="{self.projection_coord.x}"\ty="{self.projection_coord.y * -1}"/>'
        if self.mirror_x and self.mirror_y:
            ret += f'\n<Port x="{self.projection_coord.x * -1}"\ty="{self.projection_coord.y * -1}"/>'
        return ret
    
    def render_to_image(self, image, rotation_dir):
        '''
        Docstring for render_to_image
        
        :param self: Description
        :param image: Description
        :param rotation_dir: igmored for Docking points because they dont rotate
        '''
        self._render_point(image, 0)
    
class PointThuster(Point):
    point_type = PT_THRUSTER
    color = (255,255,0,255)

    def __init__(self, coord: ICoord, label: str, sprite_cfg: SpriteConfig, rot_frame: int, direction: int = 0):
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
        ret = f'<Effect type="thrustMain"\t\tposAngle="{self.polar_coord.dir_i360()}"\tposRadius="{round(self.polar_coord.rad)}"\tposZ="{round(self.polar_coord.z)}"\trotation="{self.direction}"\teffect="&efMainThrusterLarge;"{self.get_send_to_back()}{self.get_bring_to_front()}/>'
        if self.mirror_x:
            ret += f'<Effect type="thrustMain"\t\tposAngle="-{self.polar_coord.dir_i360()}"\tposRadius="{round(self.polar_coord.rad)}"\tposZ="{round(self.polar_coord.z)}"\trotation=-{self.direction}"\teffect="&efMainThrusterLarge;"{self.get_send_to_back()}{self.get_bring_to_front()}/>'
        #thrusters dont need y-mirroring
        return ret
    
    def _render_arc(self, image: ImageDraw, direction: int = 0):
        pos = self.get_projection_coord_at_direction(direction)
        pil_thrust_anngle = (self.direction + direction + 90) % 360
        c=3
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_anngle, pil_thrust_anngle, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_anngle, pil_thrust_anngle, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_anngle, pil_thrust_anngle, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_anngle, pil_thrust_anngle, fill=self.color)
        c+=1
        image.arc((pos.x-c, pos.y-c, pos.x+c, pos.y+c), pil_thrust_anngle, pil_thrust_anngle, fill=self.color)
    
    def render_to_image(self, image, rotation_dir):
        self._render_point(image, rotation_dir)
        self._render_arc(image, rotation_dir)
    
class PointDevice(Point):
    point_type = PT_DEVICE
    color = (255,0,255,255)
    color_arc = (255,0,0,255)

    def __init__(self, coord: ICoord, label: str, sprite_cfg: SpriteConfig, rot_frame: int, direction: int = 0, arc: int = -1, arc_start: int=-1, arc_end: int=-1):
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
    
    def _render_arc(self, image: ImageDraw, direction: int):
        pos = self.get_projection_coord_at_direction(direction)
        aim_dir, start, end = self.get_arc_at_dir(direction)
        image.arc((pos.x-5, pos.y-5, pos.x+5, pos.y+5), (90+start) % 360, (90+end) % 360, fill=self.color_arc)
        image.arc((pos.x-7, pos.y-7, pos.x+7, pos.y+7), (90+aim_dir) % 360, (90+aim_dir) % 360, fill=self.color)

    def get_arc_xml(self):
        return ""

    def to_xml(self):
        ret = f'<DeviceSlot id="{self.label}"\t\tposAngle="{self.polar_coord.dir_i360()}"\tposRadius="{round(self.polar_coord.rad)}"\tposZ="{round(self.polar_coord.z)}"\tfireAngle="{self.direction}"\t{self.get_arc_xml()}/>'
        if self.mirror_x:
            ret += f'<DeviceSlot id="{self.label}"\t\tposAngle="-{self.polar_coord.dir_i360()}"\tposRadius="{round(self.polar_coord.rad)}"\tposZ="{round(self.polar_coord.z)}"\tfireAngle=-{self.direction}"\t{self.get_arc_xml()}/>'
        #thrusters dont need y-mirroring
        return ret
    
    def render_to_image(self, image, rotation_dir):
        self._render_point(image, rotation_dir)
        self._render_arc(image, rotation_dir)
