"""Test generic maya tools."""

from maya import cmds

from psyhive import py_gui, icons, qt
from psyhive.utils import get_single, TMP, store_result
from hv_test import refresh

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_ns_cleaner, restore_sel

PYGUI_COL = 'navy'


def launch_gui():
    """Launch FK/IK switcher interface."""
    py_gui.MayaPyGui(__file__, title='FK/IK switcher')


@store_result
def _get_flex_icon(arrow, arrow_size=80, bicep_size=110, verbose=0):
    """Build flex icon using the given arrow.

    Args:
        arrow (str): name of arrow emoji
        arrow_size (int): size of arrow icon
        bicep_size (int): size of bicep icon
        verbose (int): print process data
    """
    _path = '{}/psyhive/icons/ik_fk_{}.png'.format(TMP, arrow)

    _bicep = icons.EMOJI.find('Flexed Biceps: Light Skin Tone')
    _arrow = icons.EMOJI.find(arrow)

    _px = qt.HPixmap(144, 144)
    _px.fill(qt.HColor(0, 0, 0, 0))

    _bicep_px = qt.HPixmap(_bicep).resize(bicep_size, bicep_size)
    _px.add_overlay(_bicep_px, (0, 0))

    _arrow_px = qt.HPixmap(_arrow).resize(arrow_size, arrow_size)
    _px.add_overlay(
        _arrow_px, (_px.width(), _px.height()), anchor='BR')

    _px.save_as(_path, verbose=verbose, force=True)

    return _path


class _FkIkSystem(object):
    """Represents an FK/IK system."""

    def __init__(self, rig, side):
        """Constructor.

        Args:
            rig (FileRef): rig
            side (str): which side (Lf/Rt)
        """
        if side not in ['Lf', 'Rt']:
            raise ValueError(side)

        self.rig = rig
        self.side = side

        self.fk_shoulder = rig.get_node(side+'_armFk_1_Ctrl')
        self.fk_elbow = rig.get_node(side+'_armFk_2_Ctrl')
        self.fk_hand = rig.get_node(side+'_armFk_3_Ctrl')

        self.ik_hand = rig.get_node(side+'_armIk_Ctrl')
        self.ik_pole = rig.get_node(side+'_armPole_Ctrl.rotatePivot')

        self.elbow_jnt = rig.get_node(side+'_armBnd_2_Jnt')
        self.gimbal = rig.get_node(side+'_wristGimbal_Ctrl')

    def apply_fk_to_ik(
            self, pole_vect_depth=10.0, build_tmp_geo=False, apply_=True):
        """Apply fk to ik.

        Args:
            pole_vect_depth (float): distance of pole vector from elbow
            build_tmp_geo (bool): build tmp geo
            apply_ (bool): apply the update to gimbal ctrl
        """
        print 'APPLYING FK -> IK'

        # Calculate pole pos
        _u_arm_v = hom.get_p(self.fk_elbow) - hom.get_p(self.fk_shoulder)
        _arm_v = hom.get_p(self.fk_hand) - hom.get_p(self.fk_shoulder)
        _ly = (_u_arm_v ^ _arm_v).normalized()
        _pole_dir = (_arm_v ^ _ly).normalized()
        _pole_pos = hom.get_p(self.fk_elbow) + _pole_dir*pole_vect_depth

        # Read hand mtx
        _hand_mtx = hom.get_m(self.fk_hand)

        if build_tmp_geo:
            _arm_v.build_crv(hom.get_p(self.fk_shoulder))
            _pole_dir.build_crv(hom.get_p(self.fk_elbow))
            _ly.build_crv(hom.get_p(self.fk_shoulder))
            _pole_pos.build_loc()
            _hand_mtx.build_geo()
            hom.get_m(self.ik_hand).build_geo(name='ik_hand')

        # Apply vals to ik ctrls
        _hand_mtx.apply_to(self.ik_hand)
        _pole_pos.apply_to(self.ik_pole)
        if self.side == 'Rt':
            cmds.rotate(
                180, 0, 0, self.ik_hand, relative=True, objectSpace=True,
                forceOrderXYZ=True)
        if apply_:
            cmds.setAttr(self.gimbal+'.FK_IK', 1)
            print 'SET', self.ik_hand, 'TO IK'

    def apply_ik_to_fk(self, build_tmp_geo=False, apply_=True):
        """Apply ik to fk.

        Args:
            build_tmp_geo (bool): build tmp geo
            apply_ (bool): apply update to gimbal ctrl
        """
        print 'APPLYING IK -> FK'

        # Position shoulder
        _u_arm_v = hom.get_p(self.elbow_jnt) - hom.get_p(self.fk_shoulder)
        _pole_v = hom.get_p(self.ik_pole) - hom.get_p(self.fk_shoulder)
        _lx = _u_arm_v.normalized()
        _ly = (_u_arm_v ^ _pole_v).normalized()
        if self.side == 'Rt':
            _lx = -_lx
        _shoulder_mtx = hom.axes_to_m(
            pos=hom.get_p(self.fk_shoulder), lx_=_lx, ly_=_ly)
        if build_tmp_geo:
            hom.get_m(self.fk_shoulder).build_geo(name='shoulder_old')
            _shoulder_mtx.build_geo(name='shoulder_new')
            _pole_v.build_crv(hom.get_p(self.fk_shoulder), name='to_pole')
            print hom.get_p(self.ik_pole).build_loc(name='pole')
        _shoulder_mtx.apply_to(self.fk_shoulder)
        del _lx, _ly, _pole_v, _u_arm_v

        # Position elbow
        _l_arm_v = hom.get_p(self.ik_hand) - hom.get_p(self.elbow_jnt)
        _pole_v = hom.get_p(self.ik_pole) - hom.get_p(self.elbow_jnt)
        _lx = _l_arm_v.normalized()
        _ly = (_lx ^ _pole_v).normalized()
        if self.side == 'Rt':
            _lx = -_lx
        _elbow_mtx = hom.axes_to_m(
            pos=hom.get_p(self.fk_elbow), lx_=_lx, ly_=_ly)
        if build_tmp_geo:
            _l_arm_v.build_crv(hom.get_p(self.fk_elbow))
            hom.get_m(self.fk_elbow).build_geo(name='elbow_old')
            _elbow_mtx.build_geo(name='elbow_new')
        _elbow_mtx.apply_to(self.fk_elbow)
        del _lx, _ly, _l_arm_v, _pole_v

        # Position hand
        hom.get_m(self.ik_hand).apply_to(self.fk_hand)
        if self.side == 'Rt':
            cmds.rotate(
                180, 0, 0, self.fk_hand, relative=True, objectSpace=True,
                forceOrderXYZ=True)
        if apply_:
            cmds.setAttr(self.gimbal+'.FK_IK', 0)
            print 'SET', self.ik_hand, 'TO FK'

    def toggle_ik_fk(self):
        """Toggle between ik/fk."""
        if not cmds.getAttr(self.gimbal+'.FK_IK'):
            self.apply_fk_to_ik()
        else:
            self.apply_ik_to_fk()


def _get_rig_and_side():
    """Get selected rig and side.

    Returns:
        (tuple): rig/side
    """
    _rig = ref.get_selected(catch=True) or ref.find_ref()
    _side = get_single(
        cmds.ls(selection=True),
        verb='selected', name='node').split(":")[1][:2]
    print 'RIG/SIDE', _rig, _side
    return _rig, _side


@restore_sel
@get_ns_cleaner(":tmp")
@py_gui.install_gui(
    label='FK -> IK', label_width=100,
    icon=_get_flex_icon('Right arrow'))
def fk_to_ik(pole_vect_depth=10.0, build_tmp_geo=True, apply_=True):
    """Switch FK to IK.

    Args:
        pole_vect_depth (float): distance of pole vector from elbow
        build_tmp_geo (bool): build tmp geo
        apply_ (bool): apply the change to gimbal ctrl
    """
    refresh.reload_libs()
    _rig, _side = _get_rig_and_side()
    _system = _FkIkSystem(rig=_rig, side=_side)
    _system.apply_fk_to_ik(
        pole_vect_depth=pole_vect_depth, build_tmp_geo=build_tmp_geo,
        apply_=apply_)


@restore_sel
@get_ns_cleaner(":tmp")
@py_gui.install_gui(
    label='IK -> FK', label_width=100,
    icon=_get_flex_icon('Left arrow'))
def ik_to_fk(build_tmp_geo=True, apply_=True):
    """Switch IK to FK.

    Args:
        build_tmp_geo (bool): build tmp geo
        apply_ (bool): apply the change to gimbal ctrl
    """
    refresh.reload_libs()
    _rig, _side = _get_rig_and_side()
    _system = _FkIkSystem(rig=_rig, side=_side)
    _system.apply_ik_to_fk(build_tmp_geo=build_tmp_geo, apply_=apply_)


@restore_sel
@get_ns_cleaner(":tmp")
@py_gui.install_gui(
    label='Toggle IK/FK', label_width=100,
    icon=_get_flex_icon('Left-Right Arrow'))
def toggle_ik_fk():
    """Toggle between IK/FK."""
    refresh.reload_libs()
    _rig, _side = _get_rig_and_side()
    _system = _FkIkSystem(rig=_rig, side=_side)
    _system.toggle_ik_fk()
