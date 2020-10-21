"""Tools for managing base class for psyhive.qt dialogs."""

import ctypes
import os
import time


class BaseDialog(object):
    """Base class for psyhive.qt dialogs."""

    def set_icon(self, icon):
        """Set icon for this interface.

        Args:
            icon (str|QPixmap): icon to apply
        """
        from psyhive import qt, host

        _icon = qt.get_icon(icon)
        self.setWindowIcon(_icon)

        if not host.NAME:
            _uid = time.strftime('%y%m%d_%H%M%S_'+type(self).__name__)
            _app = qt.get_application()
            if os.name == 'nt':
                _shell32 = ctypes.windll.shell32
                _shell32.SetCurrentProcessExplicitAppUserModelID(_uid)
            _app.setWindowIcon(_icon)
            print 'SET WINDOW ICON', icon, _app
