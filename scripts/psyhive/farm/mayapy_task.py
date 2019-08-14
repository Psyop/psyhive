"""Stripped down version of mayapy psyq submission."""

import os


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
        _lines = []
        if os.environ.get('USERNAME') != 'render':
            _lines += [
                '# Set user to allow tank apps to work',
                'import os',
                'os.environ["USERNAME"] = "{user}"',
                '',
            ]
        _lines += [
            '# Print header',
            'from psyhive.utils import dprint',
            'dprint("Starting task {label}")',
            'print " - [task] TMP PY {tmp_py}"',
            'print " - [task] EXECUTING TASK CODE:"',
            'print """\n{py}\n"""',
            '',
            '# Execute task code',
            '{py}',
            '',
            'dprint("Completed task {label}")',
            '',
        ]

        return '\n'.join(_lines).format(
            label=self.label, tmp_py=tmp_py, py=self.py_,
            user=os.environ.get('USERNAME'))
