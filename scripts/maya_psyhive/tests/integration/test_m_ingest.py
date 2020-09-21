import unittest
import pprint

from maya import cmds

from psyhive import pipe, host
from psyhive.utils import File

from maya_psyhive import ref, open_maya as hom
from maya_psyhive.tools import m_ingest


class TestMIngest(unittest.TestCase):

    EXEC_SORT = 0.5

    def test_check_current_scene(self):

        _build_bad_scene()
        _issues = m_ingest.check_current_scene(show_dialog=False)
        pprint.pprint(_issues)
        assert 'File extension for animation should be ma' in _issues
        assert 'Scene has display layers: test_LYR' in _issues
        assert len(_issues) == 7


def _build_bad_scene(force=True):

    _root = pipe.TMP+'/psyhive/remote_scene_check'

    # Built test refs
    _cube_mb = File('{}/cube.mb'.format(_root))
    if not _cube_mb.exists():
        print 'CREATING', _cube_mb
        cmds.polyCube()
        host.save_as(_cube_mb, export_selection=True)
    _deep_cube_mb = File('{}/dir/deep_cube.mb'.format(_root))
    if not _deep_cube_mb.exists():
        print 'CREATING', _deep_cube_mb
        cmds.polyCube()
        host.save_as(_deep_cube_mb, export_selection=True)
    _2_cube_mb = File('{}/2cube.mb'.format(_root))
    if not _2_cube_mb.exists():
        print 'CREATING', _cube_mb
        cmds.select([cmds.polyCube()[0] for _ in range(2)])
        host.save_as(_2_cube_mb, export_selection=True)
    _asset_cube_mb = File('{}/dir/cube_rig_v001.mb'.format(_root))
    if not _asset_cube_mb.exists():
        print 'CREATING', _asset_cube_mb
        cmds.polyCube()
        host.save_as(_asset_cube_mb, export_selection=True)
    _psy_asset_cube_mb = File('{}/dir/cube_rig_main_v001.mb'.format(_root))
    if not _psy_asset_cube_mb.exists():
        print 'CREATING', _psy_asset_cube_mb
        cmds.polyCube()
        host.save_as(_psy_asset_cube_mb, export_selection=True)

    # Build scene
    host.new_scene(force=force)

    _ref = ref.create_ref(_cube_mb, namespace='bad_namespace')
    _ref.find_top_node().add_to_grp('CHAR')

    # Good ref
    _ref = ref.create_ref(_cube_mb, namespace='cube_1')
    _ref.find_top_node().add_to_grp('CHAR')

    # Good asset ref
    _ref = ref.create_ref(_asset_cube_mb, namespace='cube_2')
    _ref.find_top_node().add_to_grp('CHAR')

    # Good psy asset ref
    _ref = ref.create_ref(_psy_asset_cube_mb, namespace='cube_3')
    _ref.find_top_node().add_to_grp('CHAR')

    # Missing ref
    _ref = ref.create_ref(_deep_cube_mb, namespace='deepRef_7')
    _ref.find_top_node().add_to_grp('CHAR')

    # Multi top node
    _ref = ref.create_ref(_2_cube_mb, namespace='multiTop')
    assert not _ref.find_top_node(catch=True)

    # Without namespace
    hom.CMDS.polyCube().add_to_dlayer('test_LYR')

    # In bad group
    _ref = ref.create_ref(_cube_mb, namespace='badParent')
    _ref.find_top_node().add_to_grp('RANDOM')

    # In junk
    _ref = ref.create_ref(_cube_mb, namespace='junkRef_1')
    _ref.find_top_node().add_to_grp('JUNK')

    # No namespace
    cmds.file(_cube_mb.path, reference=True, renamingPrefix='blah')

    host.save_scene('{}/test2009_animation_v003.mb'.format(_root), force=True)
