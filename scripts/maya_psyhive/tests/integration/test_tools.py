import unittest

from maya_psyhive import ref
from maya_psyhive import open_maya as hom

from maya_psyhive.tools import fkik_switcher
from maya_psyhive.tools.frustrum_test_blast.blast import _rig_in_cam, _Rig
from maya_psyhive.tools.batch_cache.tmpl_cache import CTTShotRoot
from maya_psyhive.tools.frustrum_test_blast import remove_rigs


class TestTools(unittest.TestCase):

    def test_batch_cache(self):

        _path = 'P:/projects/hvanderbeek_0001P/sequences/dev/dev0000'
        _shot = CTTShotRoot(_path)
        _shot.read_work_files(force=True)

        from maya_psyhive.tools import batch_cache
        _dialog = batch_cache.launch()
        _dialog.close()

    def test_fkik_switcher(self):

        _dialog = fkik_switcher.launch_interface()
        _dialog.ui.close()

    def test_frustrum_test_blast(self):

        # Test frustrum test
        _path = (
            'P:/projects/hvanderbeek_0001P/assets/3D/character/archer/rig/'
            'output/rig/rig_main/v016/maya/archer_rig_main_v016.mb')
        _ref = ref.obtain_ref(namespace='archer', file_=_path, class_=_Rig)
        assert isinstance(_ref, _Rig)
        _cam = hom.HFnCamera('persp')
        _pos = hom.HMatrix([
            0.95, 0.00, 0.31, 0.00, 0.08, 0.96, -0.26, 0.00, -0.29, 0.27,
            0.92, 0.00, -19.37, 25.40, 54.23, 1.00])
        _pos.apply_to(_cam)
        assert _rig_in_cam(rig=_ref, cam=_cam)
        _pos = hom.HMatrix([
            0.80, -0.00, -0.60, 0.00, -0.10, 0.98, -0.13, 0.00, 0.60, 0.16,
            0.79, 0.00, -16.33, 37.34, 109.80, 1.00])
        _pos.apply_to(_cam)
        assert not _rig_in_cam(rig=_ref, cam=_cam)

        # Test remove rigs ui
        _dialog = remove_rigs.launch([_ref], exec_=False)
        _dialog.close()


if __name__ == '__main__':
    unittest.main()
