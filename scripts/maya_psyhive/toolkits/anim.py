"""Tools for animation."""

from psyhive import tk, qt, py_gui, icons
from psyhive.utils import lprint

from maya_psyhive import ref, m_pipe
from maya_psyhive.utils import reset_ns, set_namespace

PYGUI_TITLE = 'Anim Tools'
ICON = icons.EMOJI.find('Green Apple')


@reset_ns
@py_gui.install_gui(hide=['verbose'], label='Duplicate selected rig with anim')
def duplicate_sel_rig_with_anim(verbose=0):
    """Duplicate selected rig and apply the same animation.

    Args:
        verbose (int): print process data
    """
    _src_rig = m_pipe.get_selected_rig(catch=True)
    if not _src_rig:
        qt.notify_warning('No rigs selected.\n\nSelect a rig to duplicate.')
        return
    print "SRC RIG", _src_rig

    # Find anim
    _anim = []
    for _plug in _src_rig.find_plugs():
        _crv = _plug.find_anim()
        if not _crv:
            continue
        lprint(' -', _plug, verbose=verbose)
        _anim.append([_plug, _crv])

    # Bring in new rig
    set_namespace(':')
    _new_rig = ref.find_ref(tk.reference_publish(_src_rig.path).name)
    print "NEW RIG", _new_rig

    set_namespace(':'+_new_rig.namespace)
    for _src_plug, _src_crv in _anim:
        _new_plug = _new_rig.get_plug(_src_plug)
        _new_crv = _src_crv.duplicate()
        lprint(' -', _src_plug, _new_plug, _new_crv, verbose=verbose)
        _new_crv.connect(_new_plug)
