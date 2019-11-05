"""General tools relating to tank."""

from psyhive.utils import lprint


def reference_publish(file_, verbose=0):
    """Reference a publish into the current scene.

    Args:
        file_ (str): path to reference
        verbose (int): print process data
    """
    from psyhive import tk

    # Find ref util module
    _mgr = tk.find_tank_app('assetmanager')
    _ref_util = tk.find_tank_mod(
        'tk_multi_assetmanager.reference_util', catch=True)
    if not _ref_util:
        _mgr.init_app()
        _ref_util = tk.find_tank_mod(
            'tk_multi_assetmanager.reference_util')
    lprint('REF UTIL', _ref_util, verbose=verbose)

    _ref_list = _mgr.reference_list
    _pub_dir = _ref_list.asset_manager.publish_directory
    _publish = _pub_dir.publish_from_path(file_)
    lprint('PUBLISH', _publish, verbose=verbose)

    _ref = _ref_util.reference_publish(_publish)
    lprint('REF', _ref, verbose=verbose)

    return _ref[0]
