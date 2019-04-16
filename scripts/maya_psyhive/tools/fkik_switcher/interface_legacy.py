"""Tools for managing the legacy (py_gui) interface for fk/ik switcher."""

from psyhive import py_gui, icons, qt
from psyhive.utils import TMP, store_result
from hv_test import refresh

from maya_psyhive.utils import get_ns_cleaner, restore_sel
from maya_psyhive.tools.fkik_switcher import system


PYGUI_COL = 'navy'


def launch_legacy_interface():
    """Launch FK/IK switcher interface."""
    return py_gui.MayaPyGui(__file__, title='FK/IK switcher')


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
    refresh.reload_libs(filter_='fkik')
    system.get_selected_system().apply_fk_to_ik(
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
    refresh.reload_libs(filter_='fkik')
    system.get_selected_system().apply_ik_to_fk(
        build_tmp_geo=build_tmp_geo, apply_=apply_)


@restore_sel
@get_ns_cleaner(":tmp")
@py_gui.install_gui(
    label='Toggle IK/FK', label_width=100,
    icon=_get_flex_icon('Left-Right Arrow'))
def toggle_ik_fk(build_tmp_geo=False):
    """Toggle between IK/FK.

    Args:
        build_tmp_geo (bool): build tmp geo
    """
    refresh.reload_libs(filter_='fkik')
    system.get_selected_system().toggle_ik_fk(build_tmp_geo=build_tmp_geo)
