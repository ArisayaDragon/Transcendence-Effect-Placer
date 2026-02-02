from transcendence_effect_placer.data.data import SpriteConfig, CCoord, ICoord, PCoord
import math

#derived from TranscendeceDev -> TSE -> C3DConversion.cpp

_VIEW_ANGLE = 0.4636448
_K1 = math.sin(_VIEW_ANGLE)
_K2 = math.cos(_VIEW_ANGLE)
_MIN_ZG = 0.1
_D = 2.0
_MIN_DEN = 0.1
EPSILON = 1e-10

def convert_polar_to_projection(sprite_cfg: SpriteConfig, coord: PCoord) -> ICoord:
    scale = sprite_cfg.viewport_size()

    r = coord.r
    a = coord.a

    x = math.cos(a) * r / scale
    y = math.sin(a) * r / scale
    z = coord.z / scale

    #global coordinate conversion

    xg = x
    yg = y * _K2 - z * _K1
    zg = y * _K1 + z * _K2

    zg = max(_MIN_ZG, zg + 2.0)

    #convert to projection coords

    d = scale * _D
    den = zg / d

    return CCoord(xg / den, yg / den, coord.z) #z here would be coord.z, not zg or z, since we do this transform bidirectionally with user-supplied coord.z

def convert_projection_to_polar(sprite_cfg: SpriteConfig, coord: CCoord|ICoord, rotation_frame: int = 0) -> PCoord:
    return convert_projection_to_polar_original(sprite_cfg, coord, rotation_frame)

def convert_projection_to_polar_inverse(sprite_cfg: SpriteConfig, coord: CCoord|ICoord, rotation_frame: int = 0) -> PCoord:
    '''
    This version was an attempt to use algebra to reverse the values
    However it has issues from running up against limits that cause it to be distored
    '''
    #everything up here are the easily derived terms
    if isinstance(coord, ICoord):
        coord = CCoord(float(coord.x), float(coord.y), 0)
    scale = sprite_cfg.viewport_size()

    d = scale * _D

    px = coord.x
    py = coord.y
    pz = coord.z
    z = pz / scale
    
    r = (px ** 2 + py ** 2) ** 0.5

    rotation_offset = rotation_frame * (360 / sprite_cfg.rot_frames)

    #we need to undo xg/den=px and yg/den=px
    #to find xg, we need x, which needs the angle 
    '''
    This section is not real python
    this is me doing algebra to solve for a (angle)
    px = xg * d / zg

    xg / zg = d / px
    yg / zg = d / py
    xg * px = zg * d
    yg * py = zg * d
    xg * px = yg * py
    math.cos(a) * r / scale * px = math.sin(a) * r / scale * _K2 * py - z * _K1 * py
    kA = r / scale * px
    kB = r / scale * _K2 * py
    kC = z * _K1 * py
    math.cos(a) * kA = math.sin(a) * kB - kC
    math.sin(a) * kB - math.cos(a) * kA = kC
    '''
    kA = r / scale * px
    kB = r / scale * _K2 * py
    kC = z * _K1 * py
    #Applying the harmonic addition theorem
    #which states asin(x) - bcos(x) = Rsin(x-phi)
    #we know that kC = asin(x) - bcos(x) = Rsin(x-phi)
    #R = sqrt(a^2 + b^2)
    #phi = arctan2(b/a)
    transcendence_offset = math.radians(90)
    phi = math.atan2(kA,-kB) + transcendence_offset
    _r = (kA ** 2 + kB ** 2) ** 0.5
    #to avoid unsolvable cases we clip kC / _r
    s = min(max(kC / _r, -1),1)
    a = math.asin(s) + phi

    #now we apply our angle offset 
    a += math.radians(rotation_offset)
    ad = round(math.degrees(a))
    
    print("y", py, "\tz", pz, z, "\tx", px, "\tpolar", int(ad), round(r))

    return PCoord(a, r, coord.z)

def convert_projection_to_polar_original(sprite_cfg: SpriteConfig, coord: CCoord|ICoord, rotation_frame: int = 0) -> PCoord:
    '''
    This version was directly adapted from george's code
    It does weird things when ~pz > -2*py
    '''
    if isinstance(coord, ICoord):
        coord = CCoord(float(coord.x), float(coord.y), 0)
    scale = sprite_cfg.viewport_size()

    px = coord.x
    py = coord.y
    pz = coord.z

    z = min(pz, -2 * py) / scale
    d = _D * scale

    den = py * _K1 - d * _K2
    if den < _MIN_DEN:
        den = _MIN_DEN

    y = (-(z * _K1 * d) - (py * z * _K2) - (2.0 * py))/den
    yg = y * _K2 - z * _K1
    x = px * yg / py if abs(py) > EPSILON else -px / scale

    ox = x * scale
    oy = y * scale

    rotation_offset = rotation_frame * (360 / sprite_cfg.rot_frames)
    '''
    if abs(py) < EPSILON:
        if px < 0:
            rotation_offset += 270
        else:
            rotation_offset += 90
    elif py * px > 0 and pz > 0:
        rotation_offset += 180
    '''

    a = math.atan2(oy, ox) + math.radians(rotation_offset)
    r = (px*px + py*py) ** 0.5

    print("y", py, y, yg, "\tz", pz, z, "\tx", px, x, "\tpolar", int(math.degrees(a)), round(r))

    ad = round(math.degrees(a))
    return PCoord(a, r, coord.z) #we store the original z pos here to fix the case where pz is too high

    
def a_d(a) -> float:
    return math.degrees(a)

def d360(ad) -> float:
    return round(ad) % 360

def d180(ad) -> float:
    d = d360(ad)
    if d <= 180:
        return d
    return d - 360