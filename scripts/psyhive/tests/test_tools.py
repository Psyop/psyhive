import operator
import os
import random
import shutil
import tempfile
import time
import unittest

from psyhive.tools.err_catcher import _Traceback
from psyhive.utils.py_file.docs import MissingDocs

_TRACEBACK_1 = r"""
Traceback (most recent call last):
  File "Z:/dev/global/code/pipeline/bootstrap/psyhive/scripts\psyhive\tools\err_catcher.py", line 213, in _catch_error_fn
    _result = func(*args, **kwargs)
  File "Z:/sync/global/code/pipeline/bootstrap/hv-test/python\hv_test\diary\y19\d0516\cache_scenes_test.py", line 368, in multi_select_test
    print _multi_select(range(10))
  File "Z:/sync/global/code/pipeline/bootstrap/hv-test/python\hv_test\diary\y19\d0516\cache_scenes_test.py", line 357, in _multi_select
    _MS_DIALOG = _MultiSelectDialog(items=items, multi=multi)
  File "Z:/sync/global/code/pipeline/bootstrap/hv-test/python\hv_test\diary\y19\d0516\cache_scenes_test.py", line 310, in __init__
    super(_MultiSelectDialog, self).__init__(ui_file=_ui_file)
  File "Z:/dev/global/code/pipeline/bootstrap/psyhive/scripts\psyhive\qt\interface.py", line 70, in __init__
    self.redraw_ui()
  File "Z:/dev/global/code/pipeline/bootstrap/psyhive/scripts\psyhive\qt\interface.py", line 234, in redraw_ui
    _redraw()
  File "Z:/dev/global/code/pipeline/bootstrap/psyhive/scripts\psyhive\qt\interface.py", line 316, in _redraw_method
    redraw(widget=widget)
  File "Z:/sync/global/code/pipeline/bootstrap/hv-test/python\hv_test\diary\y19\d0516\cache_scenes_test.py", line 28, in _redraw_list
    func(self, widget)
  File "Z:/sync/global/code/pipeline/bootstrap/hv-test/python\hv_test\diary\y19\d0516\cache_scenes_test.py", line 328, in _redraw__items
    _qt_item = qt.HListWidgetItem(_data_item)
TypeError: 'PySide2.QtWidgets.QListWidgetItem' called with wrong argument types:
  PySide2.QtWidgets.QListWidgetItem(int)
Supported signatures:
  PySide2.QtWidgets.QListWidgetItem(PySide2.QtWidgets.QListWidget = NULL, int = Type)
  PySide2.QtWidgets.QListWidgetItem(PySide2.QtGui.QIcon, unicode, PySide2.QtWidgets.QListWidget = NULL, int = Type)
  PySide2.QtWidgets.QListWidgetItem(PySide2.QtWidgets.QListWidgetItem)
  PySide2.QtWidgets.QListWidgetItem(unicode, PySide2.QtWidgets.QListWidget = NULL, int = Type)
""".strip()

_TRACEBACK_2 = r"""
Traceback (most recent call last):
  File "Z:/dev/global/code/pipeline/bootstrap/psyhive/scripts\psyhive\tools\err_catcher.py", line 213, in _catch_error_fn
    _result = func(*args, **kwargs)
  File "Z:/dev/global/code/pipeline/bootstrap/psyhive/scripts\psyhive\py_gui\install.py", line 56, in _install_gui_func
    return _func(*args, **kwargs)
  File "Z:/sync/global/code/pipeline/bootstrap/hv-test/python\hv_test\diary\y19\d0401\check_code.py", line 31, in check_code
    filter_=filter_, force=force, reverse=reverse, check_docs=check_docs)
  File "Z:/sync/global/code/pipeline/bootstrap/hv-test/python\hv_test\release\tools.py", line 73, in check_code
    _success = check_file(_py, check_docs=check_docs, force=force)
  File "Z:/sync/global/code/pipeline/bootstrap/hv-test/python\hv_test\release\tools.py", line 102, in check_file
    PyFile(file_).fix_docs()
  File "Z:/dev/global/code/pipeline/bootstrap/psyhive/scripts\psyhive\utils\py_file\file_.py", line 54, in fix_docs
    self.check_docs(recursive=False)
  File "Z:/dev/global/code/pipeline/bootstrap/psyhive/scripts\psyhive\utils\py_file\file_.py", line 39, in check_docs
    _docs = ast.get_docstring(self._get_ast())
  File "Z:/dev/global/code/pipeline/bootstrap/psyhive/scripts\psyhive\utils\cache.py", line 202, in _fn_wrapper
    _result = func(*args, **kwargs)
  File "Z:/dev/global/code/pipeline/bootstrap/psyhive/scripts\psyhive\utils\py_file\file_.py", line 78, in _get_ast
    raise _exc
  File "<unknown>", line 10
    os.environ['MANIM_SITE'] = 'local'
    ^
IndentationError: unexpected indent""".strip()


class TestErrCatcher(unittest.TestCase):

    def test(self):
        for _tb in [_TRACEBACK_1, _TRACEBACK_2]:
            _Traceback(_tb)


if __name__ == '__main__':
    unittest.main()
