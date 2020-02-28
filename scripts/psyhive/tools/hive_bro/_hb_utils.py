"""General utils for HiveBro."""

from psyhive import host


def cur_dcc():
    """Get current dcc name (using tank template naming).

    Returns:
        (str): dcc name
    """
    return {'hou': 'houdini'}.get(host.NAME, host.NAME)
