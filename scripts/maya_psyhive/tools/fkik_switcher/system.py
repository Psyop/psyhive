"""Tools for switching between FK and IK.

The switch key option means:
    - in the case of a single frame switch: add a keyframe on the frame
      before switching
    - in the case of a range switch: add keyframes on the frames before
      and after the switch range

A range switch should key on the start and end frames, and then also any
of the frames between if they are already keyed.

If Elbow/Knee offset is applied on the IK ctrl, this is reset when
reverting to IK.
"""

import math

from maya import cmds, mel

from psyhive import host
from psyhive.utils import get_single, store_result, lprint, wrap_fn

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import single_undo, restore_sel


class Side(object):
    """Enum for side - left/right."""

    LEFT = 0
    RIGHT = 1


class Limb(object):
    """Enum for side - arm/leg."""

    ARM = 2
    LEG = 3


SIDES = (Side.LEFT, Side.RIGHT)
LIMBS = (Limb.ARM, Limb.LEG)


class FkIkSystem(object):
    """Represents an FK/IK system."""

    def __init__(self, rig, side='left', limb='arm'):
        """Constructor.

        Args:
            rig (FileRef): rig
            side (str): which side (left/right)
            limb (str): which limb (arm/leg)
        """
        if side not in SIDES:
            raise ValueError(side)
        if limb not in LIMBS:
            raise ValueError(limb)

        self.rig = rig
        self.side = side
        self.limb = limb

        self.setup_ctrls()

    def setup_ctrls(self):
        """Set up system controls."""

        _names = {
            'side': {Side.LEFT: 'Lf', Side.RIGHT: 'Rt'}[self.side],
            'limb': {Limb.ARM: 'arm', Limb.LEG: 'leg'}[self.limb],
            'gimbal': {Limb.ARM: 'wrist', Limb.LEG: 'ankle'}[self.limb],
            'offset': {Limb.ARM: 'Elbow', Limb.LEG: 'Knee'}[self.limb]}
        self.fk_ctrls = [
            self.rig.get_node('{side}_{limb}Fk_{idx}_Ctrl'.format(
                idx=_idx, **_names))
            for _idx in range(1, 4)]
        self.fk_jnts = [
            self.rig.get_node('{side}_{limb}Fk_{idx}_Jnt'.format(
                idx=_idx, **_names))
            for _idx in range(1, 4)]
        self.ik_jnts = [
            self.rig.get_node('{side}_{limb}Ik_{idx}_Jnt'.format(
                idx=_idx, **_names))
            for _idx in range(1, 4)]

        self.ik_ = self.rig.get_node(
            '{side}_{limb}Ik_Ctrl'.format(**_names))
        self.ik_pole = self.rig.get_node(
            '{side}_{limb}Pole_Ctrl'.format(**_names))
        self.ik_pole_rp = self.ik_pole.plug('rotatePivot')

        self.ik_offs = ['{}.{offset}_Offset'.format(self.ik_, **_names)]
        if self.limb == 'leg':
            self.ik_offs += [
                "{}.Heel_Roll".format(self.ik_),
                "{}.Heel_Pivot".format(self.ik_),
                "{}.Toe_Rotate".format(self.ik_),
                "{}.Foot_Rock".format(self.ik_),
            ]

        self.gimbal = self.rig.get_node(
            '{side}_{gimbal}Gimbal_Ctrl'.format(**_names))
        self.ik_fk_attr = self.gimbal.plug('FK_IK')
        self.set_to_ik = wrap_fn(self.ik_fk_attr.set_val, 1)
        self.set_to_fk = wrap_fn(self.ik_fk_attr.set_val, 0)

    def apply_fk_to_ik(self, pole_vect_depth=10.0, apply_=True,
                       build_tmp_geo=False, verbose=1):
        """Apply fk to ik.

        First the pole vector is calculated by extending a line from the
        elbow joint in the direction of the cross product of the limb
        vector (fk_ctrls[0] to fk3) and the limb bend.

        The ik joint is then moved to the position of the fk3 control.

        The arm/knee offset is reset on apply.

        Args:
            pole_vect_depth (float): distance of pole vector from fk_ctrls[1]
            apply_ (bool): apply the update to gimbal ctrl
            build_tmp_geo (bool): build tmp geo
            verbose (int): print process data
        """
        lprint('APPLYING FK -> IK', verbose=verbose)

        # Reset offset
        for _offs in self.ik_offs:
            cmds.setAttr(_offs, 0)

        # Calculate pole pos
        _limb_v = hom.get_p(self.fk_ctrls[2]) - hom.get_p(self.fk_ctrls[0])
        if self.limb is Limb.ARM:
            _limb_bend = -hom.get_m(self.fk_ctrls[1]).ly_().normalized()
        elif self.limb == Limb.LEG:
            _limb_bend = hom.get_m(self.fk_ctrls[1]).lx_().normalized()
        else:
            raise ValueError(self.limb)
        _pole_dir = (_limb_v ^ _limb_bend).normalized()
        _pole_p = hom.get_p(self.fk_ctrls[1]) + _pole_dir*pole_vect_depth
        _pole_p.apply_to(self.ik_pole, use_constraint=True)

        # Read fk3 mtx
        _ik_mtx = hom.get_m(self.fk_ctrls[2])
        _side_offs = hom.HMatrix()
        if self.side == Side.RIGHT:
            _side_offs = hom.HEulerRotation(math.pi, 0, 0).as_mtx()
        _ik_mtx = _side_offs * _ik_mtx
        _ik_mtx.apply_to(self.ik_)

        # Apply vals to ik ctrls
        if apply_:
            self.set_to_ik()
            lprint('SET', self.ik_, 'TO IK', verbose=verbose)

        if build_tmp_geo:
            _limb_v.build_crv(hom.get_p(self.fk_ctrls[0]), name='limb_v')
            _limb_bend.build_crv(hom.get_p(self.fk_ctrls[1]), name='limb_bend')
            _pole_dir.build_crv(hom.get_p(self.fk_ctrls[1]), name='pole_dir')
            _pole_p.build_loc(name='pole')
            _ik_mtx.build_geo(name='fk3')
            hom.get_m(self.ik_).build_geo(name='ik')

    def apply_ik_to_fk(self, apply_=True, build_tmp_geo=False, verbose=1):
        """Apply ik to fk.

        The fk ctrls are moved to match the ik joint positions.

        Args:
            apply_ (bool): apply update to gimbal ctrl
            build_tmp_geo (bool): build tmp geo
            verbose (int): print process data
        """
        lprint('APPLYING IK -> FK', verbose=verbose)

        for _idx in range(3):
            _mtx = hom.get_m(self.ik_jnts[_idx])
            _mtx.apply_to(self.fk_ctrls[_idx])

        if apply_:
            self.set_to_fk()
            lprint('SET', self.ik_, 'TO FK', verbose=verbose)

    @single_undo
    @restore_sel
    def exec_switch_and_key(
            self, switch_mode, key_mode, build_tmp_geo=False,
            switch_key=False, apply_=True, verbose=1):
        """Execute fk/ik switch and key option.

        Args:
            switch_mode (str): fk/ik switch mode
            key_mode (str): key mode
            build_tmp_geo (bool): build temp geo
            switch_key (bool): add key(s) on switch
            apply_ (bool): apply the switch
            verbose (int): print process data
        """

        # Read fn + trg ctrls
        if switch_mode == 'fk_to_ik':
            _fn = self.apply_fk_to_ik
        elif switch_mode == 'ik_to_fk':
            _fn = self.apply_ik_to_fk
        else:
            raise ValueError(switch_mode)

        # Apply pre frame option
        if key_mode in ['none']:
            pass
        elif key_mode == 'timeline':
            self.exec_switch_and_key_over_timeline(
                switch_mode=switch_mode, switch_key=switch_key)
            return
        elif key_mode == 'frame':
            if switch_key:
                _frame = cmds.currentTime(query=True)
                cmds.setKeyframe(self.get_key_attrs())
                cmds.currentTime(_frame-1)
                cmds.setKeyframe(self.get_key_attrs())
                cmds.currentTime(_frame)
        else:
            raise ValueError(key_mode)

        # Execute the switch
        _fn(build_tmp_geo=build_tmp_geo, apply_=apply_, verbose=verbose)

        # Apply post frame option
        if key_mode == 'none':
            pass
        elif key_mode == 'frame':
            cmds.setKeyframe(self.get_key_attrs())
        else:
            raise ValueError(key_mode)

    def exec_switch_and_key_over_timeline(self, switch_mode, switch_key=False, selection=True):
        """Exec switch and key over timeline selection.

        Args:
            switch_mode (str): fk/ik switch mode
            switch_key (bool): add keys on switch
        """

        # Read timeline range
        if selection:
            _timeline = mel.eval('$tmpVar=$gPlayBackSlider')
            _start, _end = [
                int(_val) for _val in cmds.timeControl(
                    _timeline, query=True, rangeArray=True)]
        else:
            _start, _end = host.t_range()
        print 'TIMELINE RANGE', _start, _end

        # Get list of keyed frames
        _frames = {_start, _end}
        for _attr in self.get_key_attrs():
            _crv = get_single(
                cmds.listConnections(_attr, type='animCurve'), catch=True)
            if not _crv:
                continue
            _ktvs = cmds.getAttr(_crv+'.ktv[*]') or []
            _frames = _frames.union([
                _frame for _frame, _ in _ktvs
                if _frame > _start and _frame < _end])
        _frames = sorted(_frames)
        print 'FRAMES', _frames

        # Key current state
        _orig_frames = _frames
        if switch_key:
            _orig_frames = [_start-1] + _frames + [_end+1]
        print 'KEYING CURRENT STATE', _orig_frames
        for _frame in _orig_frames:
            cmds.currentTime(_frame)
            cmds.setKeyframe(self.get_key_attrs())

        # Key switch
        print 'KEYING SWITCH', _frames
        for _frame in _frames:
            cmds.currentTime(_frame)
            cmds.refresh()
            self.exec_switch_and_key(
                switch_mode=switch_mode, key_mode='frame',
                switch_key=False, verbose=0)

    def get_ctrls(self):
        """Get all ctrls in this system.

        Returns:
            (str list): controls
        """
        return self.fk_ctrls + [self.ik_, self.ik_pole, self.gimbal]

    @store_result
    def get_key_attrs(self):
        """Get attrs to key for this system."""
        _attrs = []
        for _fk_ctrl in self.fk_ctrls:
            _attrs += [str(_fk_ctrl)+'.r'+_axis for _axis in 'xyz']
        _attrs += [self.ik_pole+'.t'+_axis for _axis in 'xyz']
        _attrs += [self.ik_+'.t'+_axis for _axis in 'xyz']
        _attrs += [self.ik_+'.r'+_axis for _axis in 'xyz']
        _attrs += [self.gimbal+'.FK_IK']
        _attrs += self.ik_offs

        return _attrs

    def toggle_ik_fk(self, build_tmp_geo=False, apply_=True):
        """Toggle between ik/fk.

        Args:
            build_tmp_geo (bool): build tmp geo
            apply_ (bool): apply the switch
        """
        if not self.ik_fk_attr.get_val():
            self.apply_fk_to_ik(
                build_tmp_geo=build_tmp_geo, apply_=apply_)
        else:
            self.apply_ik_to_fk(
                build_tmp_geo=build_tmp_geo, apply_=apply_)

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        return '<{}[{}]>'.format(
            type(self).__name__.strip("_"), self.ik_)


def get_selected_systems(class_=None):
    """Get selected FK/IK systems.

    Args:
        class_ (class): override FkIkSystem class

    Returns:
        (FkIkSystem list): selected systems
    """
    _class = class_ or FkIkSystem

    _rig = ref.get_selected(catch=True)
    if not _rig:
        return []

    _systems = set()
    for _node in cmds.ls(selection=True):
        for _side in SIDES:
            for _limb in LIMBS:
                _system = _class(rig=_rig, limb=_limb, side=_side)
                if _node in _system.get_ctrls():
                    _systems.add(_system)

    return sorted(_systems)


def get_selected_system(class_=None, error=None):
    """Get selected fk/ik system.

    Args:
        class_ (class): override FkIkSystem class
        error (Exception): override exception

    Returns:
        (FkIkSystem): currently selected system

    Raises:
        (ValueError): if no systems selected
    """
    _systems = get_selected_systems(class_=class_)
    return get_single(
        _systems, name='FK/IK system', verb='selected', error=error)
