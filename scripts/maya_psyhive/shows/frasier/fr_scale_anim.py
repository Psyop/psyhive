"""Standalone script for scale face joint animation."""

from maya import cmds

_JNTS = [
    'LipUpper_03_R', 'LipUpper_02_L', 'LipUpper_02_R',
    'LipUpper_04_R', 'LipUpper_01_M', 'LipUpper_05_M',
    'LipCorner_01_R', 'LipLower_03_R', 'Depressor_01_R',
    'LipLower_02_R', 'LipCorner_01_L', 'LipLower_03_L',
    'LipUpper_04_L', 'LipUpper_03_L', 'Depressor_01_L',
    'LipLower_02_L', 'Mentalis_01_M', 'LipLower_01_M',
    'Buccinator_01_R', 'LevatorLower_R', 'LevatorUpper_R',
    'Nostril_01_R', 'Nose_01_M', 'Nostril_01_L', 'LevatorUpper_L',
    'LevatorLower_L', 'Buccinator_01_L', 'Depressor_02_R',
    'Mentalis_02_M', 'Depressor_02_L', 'ZygomaticMajor_01_R',
    'ZygomaticMajor_01_L', 'NasalisLower_R', 'NasalisLower_L']

_REST_POSES = {
    'Buccinator_01_L.tx': -2.8742,
    'Buccinator_01_L.ty': 10.3272,
    'Buccinator_01_L.tz': 4.5384,
    'Buccinator_01_R.tx': -2.8742,
    'Buccinator_01_R.ty': 10.3272,
    'Buccinator_01_R.tz': -4.5383,
    'Depressor_01_L.tx': 10.218,
    'Depressor_01_L.ty': -0.8355,
    'Depressor_01_L.tz': 2.2783,
    'Depressor_01_R.tx': 10.218,
    'Depressor_01_R.ty': -0.8355,
    'Depressor_01_R.tz': -2.2783,
    'Depressor_02_L.tx': 11.4379,
    'Depressor_02_L.ty': -0.2005,
    'Depressor_02_L.tz': 1.6216,
    'Depressor_02_R.tx': 11.4379,
    'Depressor_02_R.ty': -0.2005,
    'Depressor_02_R.tz': -1.6216,
    'LevatorLower_L.tx': -1.5475,
    'LevatorLower_L.ty': 11.3206,
    'LevatorLower_L.tz': 3.7592,
    'LevatorLower_R.tx': -1.5475,
    'LevatorLower_R.ty': 11.3206,
    'LevatorLower_R.tz': -3.7592,
    'LevatorUpper_L.tx': -0.3608,
    'LevatorUpper_L.ty': 12.0833,
    'LevatorUpper_L.tz': 2.3075,
    'LevatorUpper_R.tx': -0.3608,
    'LevatorUpper_R.ty': 12.0833,
    'LevatorUpper_R.tz': -2.3075,
    'LipCorner_01_L.tx': 8.8737,
    'LipCorner_01_L.ty': -1.7907,
    'LipCorner_01_L.tz': 2.8689,
    'LipCorner_01_R.tx': 8.8737,
    'LipCorner_01_R.ty': -1.7907,
    'LipCorner_01_R.tz': -2.8689,
    'LipLower_01_M.tx': 10.1488,
    'LipLower_01_M.ty': -2.5659,
    'LipLower_02_L.tx': 9.9316,
    'LipLower_02_L.ty': -2.4279,
    'LipLower_02_L.tz': 1.0465,
    'LipLower_02_R.tx': 9.9316,
    'LipLower_02_R.ty': -2.4279,
    'LipLower_02_R.tz': -1.0465,
    'LipLower_03_L.tx': 9.5264,
    'LipLower_03_L.ty': -2.008,
    'LipLower_03_L.tz': 1.8425,
    'LipLower_03_R.tx': 9.5264,
    'LipLower_03_R.ty': -2.008,
    'LipLower_03_R.tz': -1.8425,
    'LipUpper_01_M.tx': -2.8964,
    'LipUpper_01_M.ty': 12.9803,
    'LipUpper_02_L.tx': -2.8789,
    'LipUpper_02_L.ty': 12.6521,
    'LipUpper_02_L.tz': 1.016,
    'LipUpper_02_R.tx': -2.8789,
    'LipUpper_02_R.ty': 12.6521,
    'LipUpper_02_R.tz': -1.016,
    'LipUpper_03_L.tx': -3.0189,
    'LipUpper_03_L.ty': 12.1061,
    'LipUpper_03_L.tz': 2.0751,
    'LipUpper_03_R.tx': -3.0189,
    'LipUpper_03_R.ty': 12.1061,
    'LipUpper_03_R.tz': -2.0751,
    'LipUpper_04_L.tx': -1.8665,
    'LipUpper_04_L.ty': 12.5577,
    'LipUpper_04_L.tz': 1.9745,
    'LipUpper_04_R.tx': -1.8665,
    'LipUpper_04_R.ty': 12.5577,
    'LipUpper_04_R.tz': -1.9745,
    'LipUpper_05_M.tx': -1.7321,
    'LipUpper_05_M.ty': 13.3012,
    'Mentalis_01_M.tx': 10.9135,
    'Mentalis_01_M.ty': -1.2345,
    'Mentalis_02_M.tx': 11.9808,
    'Mentalis_02_M.ty': -0.2901,
    'NasalisLower_L.tx': 1.3134,
    'NasalisLower_L.ty': 12.9559,
    'NasalisLower_L.tz': 1.4358,
    'NasalisLower_R.tx': 1.3134,
    'NasalisLower_R.ty': 12.9559,
    'NasalisLower_R.tz': -1.4358,
    'Nose_01_M.tx': 0.4674,
    'Nose_01_M.ty': 15.2981,
    'Nostril_01_L.tx': 0.1181,
    'Nostril_01_L.ty': 13.1964,
    'Nostril_01_L.tz': 1.5742,
    'Nostril_01_R.tx': 0.1181,
    'Nostril_01_R.ty': 13.1964,
    'Nostril_01_R.tz': -1.5742,
    'ZygomaticMajor_01_L.tx': 0.4429,
    'ZygomaticMajor_01_L.ty': 10.6191,
    'ZygomaticMajor_01_L.tz': 4.9789,
    'ZygomaticMajor_01_R.tx': 0.4429,
    'ZygomaticMajor_01_R.ty': 10.6191,
    'ZygomaticMajor_01_R.tz': -4.9789}


def scale_face_joint_anim(namespace='Tier1_Male_01', scale=1.0):
    """Scale animation on face joints.

    Args:
        namespace (str): namespace of skeleton to read joints from
        scale (float): anim scale (1.0 has no effect)
    """

    # Get curves to scale
    _to_scale = []
    for _jnt in sorted(_JNTS):
        for _attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz']:
            _plug = '{}:{}.{}'.format(namespace, _jnt, _attr)
            _key = '{}.{}'.format(_jnt, _attr)
            _rest_val = _REST_POSES.get(_key, 0)
            _crvs = cmds.listConnections(
                _plug, destination=False, type='animCurve')
            if not _crvs:
                continue
            _crv = _crvs[0]
            _to_scale.append((_crv, _rest_val))
    print 'FOUND {:d} CURVES TO SCALE'.format(len(_to_scale))

    # Apply scaling
    for _crv, _rest_val in _to_scale:
        cmds.scaleKey(_crv, valueScale=scale, valuePivot=_rest_val)
    print 'SCALED {:d} CURVES - scale={:.03f}'.format(len(_to_scale), scale)
