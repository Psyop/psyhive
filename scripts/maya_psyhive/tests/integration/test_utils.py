from maya import cmds

from maya_psyhive.utils import set_namespace, add_attr, get_attr
import unittest


class TestUtils(unittest.TestCase):

    def test_add_attr(self):

        set_namespace(':tmp', clean=True)
        _cube = cmds.polyCube()[0]
        for _name, _val in [
                ('my_string', 'blah'),
                ('my_float', 1.0),
                ('my_int', 1),
        ]:
            _attr = _cube+'.'+_name
            add_attr(_attr, _val)
            assert get_attr(_attr) == _val
