"""Test generic maya tools."""

import copy

from maya import cmds

from psyhive import qt
from psyhive.utils import get_single, str_to_ints

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
        self.ik_pole = rig.get_node('{side}_{limb}Pole_Ctrl'.format(**_names))
        self.ik_pole_rp = self.ik_pole+'.rotatePivot'

        self.fk2_jnt = rig.get_node('{side}_{limb}Bnd_2_Jnt'.format(**_names))
        self.gimbal = rig.get_node(
            '{side}_{gimbal}Gimbal_Ctrl'.format(**_names))

    def apply_fk_to_ik(
            self, pole_vect_depth=10.0, build_tmp_geo=False, apply_=True):
        """Apply fk to ik.

        First the pole vector is calculated by extending a line from the
        elbow joint in the direction of the cross product of the limb
        vector and the limb bend.

        Args:
            pole_vect_depth (float): distance of pole vector from fk2
            build_tmp_geo (bool): build tmp geo
            apply_ (bool): apply the update to gimbal ctrl
        """
        print 'APPLYING FK -> IK'

        # Calculate pole pos
        _limb_v = hom.get_p(self.fk3) - hom.get_p(self.fk1)
        if self.limb == 'arm':
            _limb_bend = -hom.get_m(self.fk2).ly_().normalized()
        elif self.limb == 'leg':
            _limb_bend = hom.get_m(self.fk2).lx_().normalized()
        else:
            raise ValueError(self.limb)
        _pole_dir = (_limb_v ^ _limb_bend).normalized()
        _pole_p = hom.get_p(self.fk2) + _pole_dir*pole_vect_depth

        # Read fk3 mtx
        _fk3_mtx = hom.get_m(self.fk3)

        if build_tmp_geo:
            _limb_v.build_crv(hom.get_p(self.fk1), name='limb_v')
            _limb_bend.build_crv(hom.get_p(self.fk2), name='limb_bend')
            _pole_dir.build_crv(hom.get_p(self.fk2), name='pole_dir')
            _pole_p.build_loc(name='pole')
            _fk3_mtx.build_geo(name='fk3')
            hom.get_m(self.ik_).build_geo(name='ik')

        # Apply vals to ik ctrls
        _fk3_mtx.apply_to(self.ik_)
        if self.side == 'Rt':
            cmds.rotate(
                180, 0, 0, self.ik_, relative=True, objectSpace=True,
                forceOrderXYZ=True)
        _pole_p.apply_to(self.ik_pole, use_constraint=True)
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
        _pole_v = hom.get_p(self.ik_pole_rp) - hom.get_p(self.fk1)
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
            _pole_v.build_crv(hom.get_p(self.fk1), name='fk1_to_pole')
            hom.get_p(self.ik_pole_rp).build_loc(name='pole')
        _fk1_mtx.apply_to(self.fk1)
        del _lx, _ly, _pole_v, _upper_v

        # Position fk2
        _lower_v = hom.get_p(self.ik_) - hom.get_p(self.fk2_jnt)
        _pole_v = hom.get_p(self.ik_pole_rp) - hom.get_p(self.fk2_jnt)
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
            _pole_v.build_crv(hom.get_p(self.fk2), name='fk2_to_pole')
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

    def exec_switch_and_key(
            self, switch_mode, key_mode, pole_vect_depth=10.0,
            build_tmp_geo=False, range_=None):
        """Execute fk/ik switch and key option.

        Args:
            switch_mode (str): fk/ik switch mode
            key_mode (str): key mode
            pole_vect_depth (float): pole vector depth
            build_tmp_geo (bool): build temp geo
            range_ (str): frame range for key over range option
        """
        _kwargs = copy.copy(locals())
        _kwargs.pop('self')
        _kwargs.pop('key_mode')

        # Read fn + trg ctrls
        if switch_mode == 'fk_to_ik':
            _trg_ctrls = self.get_ik_ctrls()
            _fn = self.apply_fk_to_ik
        elif switch_mode == 'ik_to_fk':
            _trg_ctrls = self.get_fk_ctrls()
            _kwargs.pop('pole_vect_depth')
            _fn = self.apply_ik_to_fk
        else:
            raise ValueError(switch_mode)

        # Apply pre frame option
        if key_mode in ['no', 'on_switch']:
            pass
        elif key_mode == 'over_range':
            _kwargs['key_mode'] = 'on_switch'
            _kwargs['switch_mode'] = switch_mode
            _frames = str_to_ints(range_)
            if not _frames:
                qt.notify_warning('No frame range found')
                return
            for _frame in _frames:
                cmds.currentTime(_frame)
                print 'UPDATING FRAME', _frame
                self.exec_switch_and_key(**_kwargs)
            return
        elif key_mode == 'prev':
            _frame = cmds.currentTime(query=True)
            cmds.setKeyframe(_trg_ctrls)
            cmds.currentTime(_frame-1)
            cmds.setKeyframe(_trg_ctrls)
            cmds.currentTime(_frame)
        else:
            raise ValueError(key_mode)

        # Execute the switch
        _kwargs.pop('switch_mode')
        _kwargs.pop('range_')
        _fn(**_kwargs)

        # Apply post frame option
        if key_mode in 'no':
            pass
        elif key_mode in ['on_switch', 'prev']:
            cmds.setKeyframe(_trg_ctrls)
        else:
            raise ValueError(key_mode)

    def get_fk_ctrls(self):
        """Get list of fk ctrls in this system.

        Returns:
            (str list): fk ctrls
        """
        return [self.fk1, self.fk2, self.fk3]

    def get_ik_ctrls(self):
        """Get list of ik ctrls in this system.

        Returns:
            (str list): ik ctrls
        """
        return [self.ik_, self.ik_pole]

    def toggle_ik_fk(self, build_tmp_geo=False, apply_=True):
        """Toggle between ik/fk.

        Args:
            build_tmp_geo (bool): build tmp geo
            apply_ (bool): apply the switch
        """
        if not cmds.getAttr(self.gimbal+'.FK_IK'):
            self.apply_fk_to_ik(
                build_tmp_geo=build_tmp_geo, apply_=apply_)
        else:
            self.apply_ik_to_fk(
                build_tmp_geo=build_tmp_geo, apply_=apply_)

    def __repr__(self):
        return '<{}:{}{}>'.format(
            type(self).__name__.strip("_"), self.side,
            self.limb.capitalize())


def get_selected_system():
    """Get selected fk/ik system.

    Returns:
        (_FkIkSystem): currently selected system
    """
    _rig = ref.get_selected(catch=True)
    if not _rig:
        return None
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
