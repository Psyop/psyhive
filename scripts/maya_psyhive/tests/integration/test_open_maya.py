from maya import cmds

from maya_psyhive import open_maya as hom
import unittest


def _rand_m():
    _vals = list(hom.HMatrix())
    for _idx in range(16):
        if _idx in [3, 7, 11, 15]:
            continue
        _vals[_idx] = random.random()
    return hom.HMatrix(_vals)


class TestOpenMaya(unittest.TestCase):

    def test(self):

        _sphere1 = cmds.polySphere()[0]
        _sphere2 = cmds.polySphere()[0]
        _sphere3 = cmds.polySphere()[0]

        # Test apply euler rotation to sphere
        _rot = hom.HEulerRotation(0, 0, math.pi)
        _rot.apply_to(_sphere1)
        assert cmds.getAttr(_sphere1+'.rotate') == [0, 0, 180]

        # Test apply euler rot as mtx to sphere
        hom.HMatrix().apply_to(_sphere1)
        _rot = hom.HEulerRotation(0, math.pi, 0)
        _mtx = _rot.as_mtx()
        cmds.xform(_sphere1, matrix=_mtx)
        assert cmds.getAttr(_sphere1+'.rotate') == [0, 180, 0]
        hom.HMatrix().apply_to(_sphere1)
        _mtx.apply_to("pSphere2")
        assert cmds.getAttr(_sphere1+'.rotate') == [0, 180, 0]

        # Test apply vector + rot as mtxs to sphere
        hom.HMatrix().apply_to(_sphere1)
        _mtx1 = hom.HVector(5, 10, 20).as_mtx()
        _mtx2 = hom.HEulerRotation(0, math.pi, 0).as_mtx()
        (_mtx2*_mtx1).apply_to(_sphere1)
        assert cmds.getAttr(_sphere1+'.rotate') == [0, 180, 0]
        assert cmds.getAttr(_sphere1+'.translate') == [5, 10, 20]
        (_mtx1*_mtx2).apply_to(_sphere1)
        assert cmds.getAttr(_sphere1+'.rotate') == [0, 180, 0]
        assert cmds.getAttr(_sphere1+'.translate') == [-5, 10, -20]
        (_mtx1*_mtx1).apply_to(_sphere1)
        assert cmds.getAttr(_sphere1+'.rotate') == [0, 0, 0]
        assert cmds.getAttr(_sphere1+'.translate') == [10, 20, 40]

        # Offset matrix cookbook
        _mtx_b = _rand_m()
        _mtx_a = _rand_m()
        _offs_a_to_b = _mtx_a.inverse() * _mtx_b
        assert _mtx_a * _offs_a_to_b == _mtx_b
        _mtx_b.apply_to(_sphere1)
        _mtx_a.apply_to(_sphere2)
        (_mtx_a * _offs_a_to_b).apply_to(_sphere3)
        assert hom.get_m(_sphere3) == _mtx_b
