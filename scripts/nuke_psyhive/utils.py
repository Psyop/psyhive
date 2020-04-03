"""General nuke utilities."""

import nuke


def open_scene(file_, force=False):
    """Open a scene in the current nuke.

    Args:
        file_ (str): path to file to open
        force (bool): lose unsaved changes with no confirmation
    """
    from psyhive import host

    if not force:
        host.handle_unsaved_changes()

    nuke.scriptClear()
    nuke.scriptOpen(file_)
