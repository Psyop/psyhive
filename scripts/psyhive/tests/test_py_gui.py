import unittest

from psyhive import py_gui


class TestPyGui(unittest.TestCase):

    def test_browser_hook(self):

        _test = lambda: 'blah'
        assert _test() == 'blah'
        _hook = py_gui.BrowserLauncher(get_default_dir=_test)
        assert _hook.get_default_dir() == 'blah'


if __name__ == '__main__':
    unittest.main()
