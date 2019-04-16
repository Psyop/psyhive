"""Test generic maya tools."""

from maya import cmds

from psyhive.utils import get_single

from maya_psyhive import ref
from maya_psyhive import open_maya as hom


class _FkIkSystem(object):
    """Represents an FK/IK system."""

    def __init__(self, rig, side='Lf', limb='arm'):
        """Constructor.

        Args:
            rig (FileRef): rig
            side (str): which side (Lf/Rt)
            limb (str): which limb (arm/leg)
        """
        if side not in ['Lf', 'Rt']:
            raise ValueError(side)
        if limb not in ['arm', 'leg']:
            raise ValueError(side)

        self.rig = rig
        self.side = side
        self.limb = limb

        _names = {
            'side': side,
            'limb': limb,
            'gimbal': {'arm': 'wrist', 'leg': 'ankle'}[limb]}
        self.fk1 = rig.get_node('{side}_{limb}Fk_1_Ctrl'.format(**_names))
        self.fk2 = rig.get_node('{side}_{limb}Fk_2_Ctrl'.format(**_names))
        self.fk3 = rig.get_node('{side}_{limb}Fk_3_Ctrl'.format(**_names))

        self.ik_ = rig.get_node('{side}_{limb}Ik_Ctrl'.format(**_names))
        self.ik_pole = rig.get_attr(
            '{side}_{limb}Pole_Ctrl.rotatePivot'.format(**_names))

        self.fk2_jnt = rig.get_node('{side}_{limb}Bnd_2_Jnt'.format(**_names))
        self.gimbal = rig.get_node(
            '{side}_{gimbal}Gimbal_Ctrl'.format(**_names))

    def apply_fk_to_ik(
            self, pole_vect_depth=10.0, build_tmp_geo=False, apply_=True):
        """Apply fk to ik.

        Args:
            pole_vect_depth (float): distance of pole vector from fk2
            build_tmp_geo (bool): build tmp geo
            apply_ (bool): apply the update to gimbal ctrl
        """
        print 'APPLYING FK -> IK'

        # Calculate pole pos
        _upper_v = hom.get_p(self.fk2) - hom.get_p(self.fk1)
        _lower_v = hom.get_p(self.fk3) - hom.get_p(self.fk1)
        _ly = (_upper_v ^ _lower_v).normalized()
        _pole_dir = (_lower_v ^ _ly).normalized()
        _pole_pos = hom.get_p(self.fk2) + _pole_dir*pole_vect_depth

        # Read fk3 mtx
        _fk3_mtx = hom.get_m(self.fk3)

        if build_tmp_geo:
            _lower_v.build_crv(hom.get_p(self.fk1))
            _pole_dir.build_crv(hom.get_p(self.fk2))
            _ly.build_crv(hom.get_p(self.fk1))
            _pole_pos.build_loc()
            _fk3_mtx.build_geo()
            hom.get_m(self.ik_).build_geo(name='ik')

        # Apply vals to ik ctrls
        _fk3_mtx.apply_to(self.ik_)
        _pole_pos.apply_to(self.ik_pole)
        if self.side == 'Rt':
            cmds.rotate(
                180, 0, 0, self.ik_, relative=True, objectSpace=True,
                forceOrderXYZ=True)
        if apply_:
            cmds.setAttr(self.gimbal+'.FK_IK', 1)
            print 'SET', self.ik_, 'TO IK'

    def apply_ik_to_fk(self, build_tmp_geo=False, apply_=True):
        """Apply ik to fk.

        Args:
            build_tmp_geo (bool): build tmp geo
            apply_ (bool): apply update to gimbal ctrl
        """
        print 'APPLYING IK -> FK'

        # Position fk1
        _upper_v = hom.get_p(self.fk2_jnt) - hom.get_p(self.fk1)
        _pole_v = hom.get_p(self.ik_pole) - hom.get_p(self.fk1)
        if self.limb == 'arm':
            _lx = _upper_v.normalized()
            if self.side == 'Rt':
                _lx = -_lx
            _ly = (_upper_v ^ _pole_v).normalized()
        elif self.limb == 'leg':
            _ly = -_upper_v.normalized()
            if self.side == 'Rt':
                _ly = -_ly
            _lx = -(_upper_v ^ _pole_v).normalized()
        else:
            raise ValueError(self.limb)
        _fk1_mtx = hom.axes_to_m(
            pos=hom.get_p(self.fk1), lx_=_lx, ly_=_ly)
        if build_tmp_geo:
            hom.get_m(self.fk1).build_geo(name='fk1_old')
            _fk1_mtx.build_geo(name='fk1_new')
            _pole_v.build_crv(hom.get_p(self.fk1), name='to_pole')
            hom.get_p(self.ik_pole).build_loc(name='pole')
        _fk1_mtx.apply_to(self.fk1)
        del _lx, _ly, _pole_v, _upper_v

        # Position fk2
        _lower_v = hom.get_p(self.ik_) - hom.get_p(self.fk2_jnt)
        _pole_v = hom.get_p(self.ik_pole) - hom.get_p(self.fk2_jnt)
        if self.limb == 'arm':
            _lx = _lower_v.normalized()
            _ly = (_lx ^ _pole_v).normalized()
            if self.side == 'Rt':
                _lx = -_lx
        elif self.limb == 'leg':
            _ly = -_lower_v.normalized()
            if self.side == 'Rt':
                _ly = -_ly
            _lx = (_ly ^ _pole_v).normalized()
            if self.side == 'Rt':
                _lx = -_lx
        else:
            raise ValueError(self.limb)
        _fk2_mtx = hom.axes_to_m(
            pos=hom.get_p(self.fk2), lx_=_lx, ly_=_ly)
        if build_tmp_geo:
            _lower_v.build_crv(hom.get_p(self.fk2), name='lower')
            hom.get_m(self.fk2).build_geo(name='fk2_old')
            _fk2_mtx.build_geo(name='fk2_new')
        _fk2_mtx.apply_to(self.fk2)
        del _lx, _ly, _lower_v, _pole_v

        # Position fk3
        hom.get_m(self.ik_).apply_to(self.fk3)
        if self.side == 'Rt':
            cmds.rotate(
                180, 0, 0, self.fk3, relative=True, objectSpace=True,
                forceOrderXYZ=True)
        if apply_:
            cmds.setAttr(self.gimbal+'.FK_IK', 0)
            print 'SET', self.ik_, 'TO FK'

    def toggle_ik_fk(self, build_tmp_geo=False):
        """Toggle between ik/fk.

        Args:
            build_tmp_geo (bool): build tmp geo
        """
        if not cmds.getAttr(self.gimbal+'.FK_IK'):
            self.apply_fk_to_ik(build_tmp_geo=build_tmp_geo)
        else:
            self.apply_ik_to_fk(build_tmp_geo=build_tmp_geo)

    def __repr__(self):
        return '<{}:{}{}>'.format(
            type(self).__name__.strip("_"), self.side,
            self.limb.capitalize())


def get_selected_system():
    """Get selected fk/ik system.

    Returns:
        (_FkIkSystem): currently selected system
    """
    _rig = ref.get_selected()
    _node = get_single(
        cmds.ls(selection=True),
        verb='selected', name='node')

    _side = _node.split(":")[1][:2]
    if 'arm' in _node or 'wrist' in _node:
        _limb = 'arm'
    elif 'leg' in _node or 'ankle' in _node:
        _limb = 'leg'
    else:
        raise ValueError(_node)
    print 'RIG/SIDE/LIMB', _rig, _side, _limb
    return _FkIkSystem(rig=_rig, side=_side, limb=_limb)
