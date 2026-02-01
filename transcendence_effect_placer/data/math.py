from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
import math

#derived from TranscendeceDev -> TSE -> C3DConversion.cpp

_VIEW_ANGLE = 0.4636448
_K1 = math.sin(_VIEW_ANGLE)
_K2 = math.cos(_VIEW_ANGLE)
_MIN_ZG = 0.1
_D = 2.0
_MIN_DEN = 0.1

def convert_polar_to_projection(sprite_cfg: SpriteConfig, coord: PCoord) -> ICoord:
    scale = sprite_cfg.viewport_size()

    x = math.cos(coord.dir) * coord.rad / scale
    y = math.sin(coord.dir) * coord.rad / scale
    z = coord.z * -1 / scale

    #global coordinate conversion

    xg = x
    yg = y * _K2 - z * _K1
    zg = y * _K1 + z * _K2

    zg = max(_MIN_ZG, zg + 2.0)

    #convert to projection coords

    d = scale * _D
    den = zg / d

    return ICoord(int(xg / den), int(yg / den))

def convert_projection_to_polar(sprite_cfg: SpriteConfig, coord: CCoord|ICoord, rotation_frame: int = 0) -> PCoord:
    if isinstance(coord, ICoord):
        coord = CCoord(float(coord.x), float(coord.y), 0)
    scale = sprite_cfg.viewport_size()

    px = coord.x
    py = coord.y
    pz = coord.z

    z = pz * -1 / scale
    d = _D * scale

    den = py * _K1 - d * _K2
    if den < _MIN_DEN:
        den = _MIN_DEN

    y = (-(z * _K1 * d) - (py * z * _K2) - (2.0 * py))/den
    yg = y * _K2 - z * _K1
    x = px * yg / py if py else px / scale

    rotation_offset = rotation_frame * (360 / sprite_cfg.rot_frames)

    ox = x * scale
    oy = y * scale
    print("conversion:", py, y, oy, px, x, ox, scale)
    return PCoord(math.atan2(oy, ox) - math.radians(rotation_offset), (ox*ox + oy*oy) ** 0.5, 0)
