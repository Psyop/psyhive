"""Tools for vampire bloodline project."""

import math

from maya import cmds

from psyhive import icons, py_gui
from psyhive.utils import store_result, lprint, wrap_fn

from maya_psyhive import open_maya as hom
from maya_psyhive.utils import set_namespace

from maya_psyhive.tools import fkik_switcher
from maya_psyhive.tools.fkik_switcher import Side, Limb

ICON = icons.EMOJI.find("Vampire")
LABEL = "Vampire Bloodline"


class _VampireFkIkSystem(fkik_switcher.FkIkSystem):
    """Represents vapire rig FK/IK system."""

    def setup_ctrls(self):
        """Set up system controls."""

        _bones = {
            Limb.ARM: ('Shoulder', 'Elbow', 'Wrist'),
            Limb.LEG: ('Hip', 'Knee', 'Ankle')}
        _names = {
            'side': {Side.LEFT: 'L', Side.RIGHT: 'R'}[self.side],
            'limb': {Limb.ARM: 'Arm', Limb.LEG: 'Leg'}[self.limb],
            'gimbal': {Limb.ARM: 'wrist', Limb.LEG: 'ankle'}[self.limb],
            'offset': {Limb.ARM: 'Elbow', Limb.LEG: 'Knee'}[self.limb]}

        self.fk_ctrls = [
            self.rig.get_node('FK{bone}_{side}'.format(bone=_bone, **_names))
            for _bone in _bones[self.limb]]

        self.ik_jnts = [
            self.rig.get_node('IKX{bone}_{side}'.format(bone=_bone, **_names))
            for _bone in _bones[self.limb]]
        self.ik_ = self.rig.get_node('IK{limb}_{side}'.format(**_names))
        self.ik_pole = self.rig.get_node('Pole{limb}_{side}'.format(**_names))
        self.ik_pole_rp = self.ik_pole.plug('rotatePivot')
        self.ik_offs = []

        self.gimbal = self.rig.get_node('FKIK{limb}_{side}'.format(**_names))
        self.fk_ik_attr = self.gimbal.plug('FKIKBlend')
        self.set_to_ik = wrap_fn(self.fk_ik_attr.set_val, 10)
        self.set_to_fk = wrap_fn(self.fk_ik_attr.set_val, 0)

    def apply_fk_to_ik(self, pole_vect_depth=30.0, apply_=True,
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
            _limb_bend = -hom.get_m(self.fk_ctrls[1]).lz_().normalized()
        elif self.limb is Limb.LEG:
            _limb_bend = hom.get_m(self.fk_ctrls[1]).lz_().normalized()
        else:
            raise ValueError(self.limb)
        _pole_dir = -(_limb_v ^ _limb_bend).normalized()
        _pole_p = hom.get_p(self.fk_ctrls[1]) + _pole_dir*pole_vect_depth
        print 'APPLYING POLE', self.ik_pole

        # Read fk3 mtx
        _ik_mtx = hom.get_m(self.fk_ctrls[2])
        if self.side is Side.LEFT and self.limb is Limb.ARM:
            _offs = hom.HEulerRotation(math.pi/2, math.pi, 0)
        elif self.side is Side.LEFT and self.limb is Limb.LEG:
            _offs = hom.HEulerRotation(0, math.pi/2, -math.pi/2)
        elif self.side is Side.RIGHT and self.limb is Limb.ARM:
            _offs = hom.HEulerRotation(-math.pi/2, math.pi, 0)
        elif self.side is Side.RIGHT and self.limb is Limb.LEG:
            _offs = hom.HEulerRotation(0, math.pi/2, math.pi/2)
        else:
            raise ValueError(self.side, self.limb)
        _ik_mtx = _offs.as_mtx() * _ik_mtx

        # Apply vals to ik ctrls
        if apply_:
            _ik_mtx.apply_to(self.ik_)
            _pole_p.apply_to(self.ik_pole, use_constraint=True)
            self.set_to_ik()
            lprint('SET', self.ik_, 'TO IK', verbose=verbose)

        if build_tmp_geo:
            set_namespace(":tmp", clean=True)
            _limb_v.build_crv(hom.get_p(self.fk_ctrls[0]), name='limb_v')
            _limb_bend.build_crv(hom.get_p(self.fk_ctrls[1]), name='limb_bend')
            _pole_dir.build_crv(hom.get_p(self.fk_ctrls[1]), name='pole_dir')
            _pole_p.build_loc(name='pole')
            _ik_mtx.build_geo(name='trg_ik')
            hom.get_m(self.ik_).build_geo(name='cur_ik')
            set_namespace(":")

    @store_result
    def get_key_attrs(self):
        """Get attrs to key for this system."""
        _attrs = []
        for _fk_ctrl in self.fk_ctrls:
            _attrs += [str(_fk_ctrl)+'.r'+_axis for _axis in 'xyz']
        _attrs += [self.ik_pole+'.t'+_axis for _axis in 'xyz']
        _attrs += [self.ik_+'.t'+_axis for _axis in 'xyz']
        _attrs += [self.ik_+'.r'+_axis for _axis in 'xyz']
        _attrs += [self.fk_ik_attr]
        _attrs += self.ik_offs

        return _attrs


@py_gui.install_gui(label='Launch IK/FK switcher for vampire rig')
def launch_vampire_ikfk_switcher():
    """Launch IK/FK switcher for vampire rig.

    Returns:
        (FkIkSwitcherUi): dialog instance
    """
    return fkik_switcher.launch_interface(system_=_VampireFkIkSystem)
