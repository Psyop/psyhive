"""Stripped down version of mayapy psyq submission."""


class MayaPyTask(object):
    """Maya python task."""

    def __init__(self, py_, label=None):
        """Constructor.

        Args:
            py_ (str): python to execute
            label (str): task name
        """
        self.py_ = py_
        self.label = label

    def get_py(self, tmp_py):
        """Get python to execute.

        Args:
            tmp_py (str): path to tmp py file

        Returns:
            (str): python to execute for this task
        """
        return '\n'.join([
            'from psyhive.utils import dprint',
            'dprint("Starting task {label}")',
            'print " - [task] TMP PY {tmp_py}"',
            'print " - [task] EXECUTING TASK CODE"',
            '',
            self.py_,
            '',
            'dprint("Completed task {label}")',
            '',
        ]).format(label=self.label, tmp_py=tmp_py)
