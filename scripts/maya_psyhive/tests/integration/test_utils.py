import unittest

from maya import cmds

from psyhive.utils import get_single
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import (
    set_namespace, create_attr, get_val, use_tmp_ns, is_visible)


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
            create_attr(_attr, _val)
            assert get_val(_attr) == _val

    @use_tmp_ns
    def test_is_visible(self):

        _sphere = hom.CMDS.polySphere()
        _grp1 = hom.CMDS.group()
        _grp2 = _grp1.duplicate()
        _sphere1 = hom.HFnMesh(get_single(_grp1.list_relatives(
            allDescendents=True, path=True, type='transform')))
        _sphere2 = hom.HFnMesh(get_single(_grp2.list_relatives(
            allDescendents=True, path=True, type='transform')))
        _sphere2.hide()
        assert is_visible(_sphere1.shp)
        assert not is_visible(_sphere2.shp)
