import math
import random
import tempfile
import unittest

from maya import cmds

from maya_psyhive import open_maya as hom
from maya_psyhive.utils import use_tmp_ns


def _rand_m():
    _vals = list(hom.HMatrix())
    for _idx in range(16):
        if _idx in [3, 7, 11, 15]:
            continue
        _vals[_idx] = random.random()
    return hom.HMatrix(_vals)


class TestOpenMaya(unittest.TestCase):

    @use_tmp_ns
    def test(self):

        _sphere1 = hom.CMDS.polySphere()
        _sphere2 = hom.CMDS.polySphere()
        _sphere3 = hom.CMDS.polySphere()

        # Test apply euler rotation to sphere
        _rot = hom.HEulerRotation(0, 0, math.pi)
        _rot.apply_to(_sphere1)
        assert cmds.getAttr(_sphere1.rotate) == [(0, 0, 180)]

        # Test apply euler rot as mtx to sphere
        hom.HMatrix().apply_to(_sphere1)
        _rot = hom.HEulerRotation(0, math.pi, 0)
        _mtx = _rot.as_mtx()
        cmds.xform(_sphere1, matrix=_mtx)
        assert cmds.getAttr(_sphere1.rotate) == [(0, 180, 0)]
        hom.HMatrix().apply_to(_sphere1)
        _mtx.apply_to(_sphere2)
        assert cmds.getAttr(_sphere2.rotate) == [(0, 180, 0)]

        # Test apply vector + rot as mtxs to sphere
        hom.HMatrix().apply_to(_sphere1)
        _mtx1 = hom.HVector(5, 10, 20).as_mtx()
        _mtx2 = hom.HEulerRotation(0, math.pi, 0).as_mtx()
        (_mtx2*_mtx1).apply_to(_sphere1)
        print cmds.getAttr(_sphere1.rotate)
        assert cmds.getAttr(_sphere1.rotate) == [(0, 180, 0)]
        assert cmds.getAttr(_sphere1.translate) == [(5, 10, 20)]
        (_mtx1*_mtx2).apply_to(_sphere1)
        assert cmds.getAttr(_sphere1.rotate) == [(0, 180, 0)]
        assert cmds.getAttr(_sphere1.translate) == [(
            -4.999999999999997, 10.0, -20.0)]
        (_mtx1*_mtx1).apply_to(_sphere1)
        assert cmds.getAttr(_sphere1.rotate) == [(0, 0, 0)]
        assert cmds.getAttr(_sphere1.translate) == [(10, 20, 40)]

        # Offset matrix cookbook
        _mtx_b = _rand_m()
        _mtx_a = _rand_m()
        _offs_a_to_b = _mtx_a.inverse() * _mtx_b
        assert _mtx_a * _offs_a_to_b == _mtx_b
        _mtx_b.apply_to(_sphere1)
        _mtx_a.apply_to(_sphere2)
        (_mtx_a * _offs_a_to_b).apply_to(_sphere3)
        assert hom.get_m(_sphere3) == _mtx_b

        # Test load/save preset
        _sphere2.tx.set_val(10)
        _tmp_preset = '{}/tmp.preset'.format(tempfile.gettempdir())
        assert (_sphere1.get_p() - _sphere2.get_p()).length()
        _sphere1.save_preset(_tmp_preset)
        print _tmp_preset
        _sphere2.load_preset(_tmp_preset)
        print (_sphere1.get_p() - _sphere2.get_p()).length()
        assert not round((_sphere1.get_p() - _sphere2.get_p()).length(), 5)

    def test_get_selected(self):
        cmds.select('persp')
        assert hom.get_selected() == 'persp'
        cmds.select('top', add=True)
        with self.assertRaises(ValueError):
            hom.get_selected()
        assert len(hom.get_selected(multi=True)) == 2
        cmds.select('time1', add=True)
        assert len(hom.get_selected(multi=True)) == 3
        assert len(hom.get_selected('transform', multi=True)) == 2
        assert len(hom.get_selected('camera', multi=True)) == 2

    @use_tmp_ns
    def test_read_connections(self):
        _sphere = hom.CMDS.polySphere()
        _sphere.tx.connect(_sphere.ty)
        _sphere.ty.connect(_sphere.tz)

        assert hom.read_incoming(_sphere.ty) == [(_sphere.tx, _sphere.ty)]
        assert hom.read_outgoing(_sphere.ty) == [(_sphere.ty, _sphere.tz)]

        assert (_sphere.tx, _sphere.ty) in _sphere.read_outgoing()
        assert (_sphere.ty, _sphere.tz) in _sphere.read_outgoing()
