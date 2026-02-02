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

    return ICoord(int(xg / den), int(yg / den))

def convert_projection_to_polar(sprite_cfg: SpriteConfig, coord: CCoord|ICoord, rotation_frame: int = 0) -> PCoord:
    if isinstance(coord, ICoord):
        coord = CCoord(float(coord.x), float(coord.y), 0)
    scale = sprite_cfg.viewport_size()

    px = coord.x
    py = coord.y
    pz = coord.z

    z = pz / scale
    d = _D * scale

    den = py * _K1 - d * _K2
    if den < _MIN_DEN:
        den = _MIN_DEN

    y = (-(z * _K1 * d) - (py * z * _K2) - (2.0 * py))/den
    yg = y * _K2 - z * _K1
    x = px * yg / py if py else -px / scale

    ox = x * scale
    oy = y * scale

    rotation_offset = rotation_frame * (360 / sprite_cfg.rot_frames)

    a = math.atan2(oy, ox) + math.radians(rotation_offset)
    r = (px*px + py*py) ** 0.5

    ad = round(math.degrees(a))
    return PCoord(a, r, coord.z)

'''
George loading code...

bool C3DObjectPos::InitFromXML (CXMLElement *pDesc, DWORD dwFlags, bool *retb3DPos)

//	InitFromXML
//
//	Initializes from an XML element. We accept the following forms:
//
//	posAngle="nnn"	posRadius="nnn"	posZ="nnn"
//
//	OR
//
//	x="nnn" y="nnn" z="nnn"		-> use the 3D transformation

	{
	//	Initialize based on which of the formats we've got. If we have posAngle
	//	then we have polar coordinates.

	int iAngle;
	if (pDesc->FindAttributeInteger(POS_ANGLE_ATTRIB, &iAngle))
		{
		m_iPosAngle = AngleMod(iAngle);
		m_iPosRadius = pDesc->GetAttributeIntegerBounded(POS_RADIUS_ATTRIB, 0, -1);
		InitPosZFromXML(pDesc, retb3DPos);
		}

	//	If we don't support x,y coords, then we're done

	else if (dwFlags & FLAG_NO_XY)
		{
		m_iPosAngle = 0;
		m_iPosRadius = 0;
		m_iPosZ = 0;
		if (retb3DPos) *retb3DPos = false;
		return false;
		}

	//	Otherwise, we expect Cartessian coordinates

	else
		{
		//	Get the position

		int x;
		if (!pDesc->FindAttributeInteger(POS_X_ATTRIB, &x) && !pDesc->FindAttributeInteger(X_ATTRIB, &x))
			{
			m_iPosAngle = 0;
			m_iPosRadius = 0;
			m_iPosZ = 0;
			if (retb3DPos) *retb3DPos = false;
			return false;
			}

		int y;
		if (!pDesc->FindAttributeInteger(POS_Y_ATTRIB, &y) && !pDesc->FindAttributeInteger(Y_ATTRIB, &y))
			y = 0;
		else
			y = -y;

		bool b3DPos;
		InitPosZFromXML(pDesc, &b3DPos);
		if (retb3DPos) *retb3DPos = b3DPos;

		//	Convert to polar coordinates

		if (b3DPos && (dwFlags & FLAG_CALC_POLAR))
			{
			CVector vPos(x * g_KlicksPerPixel, y * g_KlicksPerPixel);
			Metric rAngle;
			Metric rRadius;
			C3DConversion::CalcPolar(C3DConversion::DEFAULT_SCALE, vPos, m_iPosZ, &rAngle, &rRadius);

			m_iPosAngle = mathRound(mathRadiansToDegrees(rAngle));
			m_iPosRadius = mathRound(rRadius);
			}
		else
			{
			int iRadius;
			m_iPosAngle = IntVectorToPolar(x, y, &iRadius);
			m_iPosRadius = iRadius;
			}
		}

	//	If we have an origin, then adjust the position.

	int xOrigin, yOrigin;
	if (pDesc->FindAttributeInteger(ORIGIN_X_ATTRIB, &xOrigin))
		{
		yOrigin = pDesc->GetAttributeInteger(ORIGIN_Y_ATTRIB);
		CVector vOffset(xOrigin, yOrigin);
		CVector vPos = PolarToVector(m_iPosAngle, m_iPosRadius);
		CVector vResult = vPos + vOffset;

		Metric rRadius;
		m_iPosAngle = VectorToPolar(vResult, &rRadius);
		m_iPosRadius = mathRound(rRadius);
		}

	return true;
	}

void C3DObjectPos::InitPosZFromXML (CXMLElement *pDesc, bool *retb3DPos)

//	InitPosZFromXML
//
//	Helper to load a Z position

	{
	int iPosZ;
	if (pDesc->FindAttributeInteger(POS_Z_ATTRIB, &iPosZ) || pDesc->FindAttributeInteger(Z_ATTRIB, &iPosZ))
		{
		m_iPosZ = iPosZ;
		if (retb3DPos) *retb3DPos = true;
		}
	else
		{
		m_iPosZ = 0;
		if (retb3DPos) *retb3DPos = false;
		}
	}


'''