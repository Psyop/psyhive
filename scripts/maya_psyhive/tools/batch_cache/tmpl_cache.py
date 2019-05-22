import copy
import operator
import os
import pprint

from maya import cmds

import tank

from psyhive import tk, refresh, qt, icons, pipe, py_gui
from psyhive.utils import (
    get_result_to_file_storer, Cacheable, check_heart, lprint,
    store_result_on_obj, store_result, dprint, abs_path,
    get_result_storer)
from maya_psyhive import ref


class CTTShotRoot(tk.TTShotRoot):
    """Used to stored cache shotgun request data for a shot."""

    @store_result
    def read_cache_data(self, force=False):
        """Read cache data for this shot and store the result.

        Args:
            force (bool): force reread data

        Returns:
            (dict): shotgun response
        """
        dprint('Finding latest caches', self)

        _shotgun = tank.platform.current_engine().shotgun
        _project = pipe.cur_project()

        # Request data from shotgun
        _sg_data = _shotgun.find(
            "PublishedFile", filters=[
                ["project", "is", [tk.get_project_data(_project)]],
                ["sg_format", "is", 'alembic'],
                ["entity", "is", [tk.get_shot_data(self)]],
            ],
            fields=["code", "name", "sg_status_list", "sg_metadata", "path"])

        # Remove omitted and non-latest versions
        _cache_data = {}
        for _data in _sg_data:
            _cache = tk.TTShotOutputVersion(
                _data['path']['local_path'])
            _data['cache'] = _cache

            # Store only latest
            if _cache.vers_dir not in _cache_data:
                _cache_data[_cache.vers_dir] = _data
            elif _cache > _cache_data[_cache.vers_dir]['cache']:
                _cache_data[_cache.vers_dir] = _data

        # Read asset for latest versions
        for _name, _data in _cache_data.items():

            # Read asset
            _metadata = eval(
                _data['sg_metadata'].
                replace('true', 'True').
                replace('null', 'None').
                replace('false', 'False')) or {}
            _data['metadata'] = _metadata
            _rig_path = _metadata.get('rig_path')
            if not _rig_path:
                del _cache_data[_name]
                continue
            try:
                _data['asset_ver'] = CTTAssetOutputVersion(_rig_path)
            except ValueError:
                del _cache_data[_name]
                continue

            # Ignore animcache of camera
            if (
                    _data['asset_ver'].sg_asset_type == 'camera' and
                    _data['cache'].output_type == 'animcache'):
                del _cache_data[_name]
                continue

            _work_file = abs_path(_metadata.get('origin_scene'))
            _data['origin_scene'] = _work_file
            _data['work_file'] = tk.get_work(_work_file)
            _data['shot'] = self

        return sorted(_cache_data.values())


class CTTAssetOutputVersion(tk.TTAssetOutputVersion, Cacheable):
    """Asset with built in caching."""

    @store_result_on_obj
    def is_latest(self):
        """Test if this is the latest version.

        Returns:
            (bool): whether latest"""
        return super(CTTAssetOutputVersion, self).is_latest()


class CTTMayaShotWork(tk.TTMayaShotWork, Cacheable):
    """Work file with built in caching."""

    @property
    def cache_fmt(self):
        """Get cache format.

        Returns:
            (str): format for cache files
        """
        return '{}/cache/psyhive/{}_{{}}.cache'.format(
            self.get_work_area().path, self.basename)

    @store_result_on_obj
    def get_cacheable_assets(self):
        """Get list of cacheable assets.

        Returns:
            (CTTAssetOutputVersion list): list of assets
        """
        return sorted(set(self.get_cacheable_refs().values()))

    def get_dependencies(self):
        return self.read_dependencies()[0]

    @store_result_on_obj
    def get_cacheable_refs(self, show_unhandled=False):
        """Get dict of cacheable refs.

        Args:
            show_unhandled (bool): print out unhandled references

        Returns:
            (dict): namespace/asset
        """
        _refs = {}
        for _ns, _path in self.get_dependencies()['refs'].items():
            try:
                _asset = tk.TTAssetOutputName(_path)
            except ValueError:
                if show_unhandled:
                    print 'UNHANDLED:', _path
                continue
            if _asset.step in ['shade']:
                continue
            _refs[_ns] = _asset

        return _refs

    @get_result_to_file_storer(
        get_depend_path=operator.attrgetter('path'), min_mtime=1558543997)
    def read_dependencies(
            self, force=False, confirm=True, new_scene=True, verbose=0):
        """Read dependencies of this workfile.

        Args:
            force (bool): force reread
            confirm (bool): confirm before replace current scene
            new_scene (bool): new scene after read
            verbose (int): print process data

        Returns:
            (dict): namespace/path dependencies dict
        """

        # Make sure scene is loaded
        _replaced_scene = False
        if not cmds.file(query=True, location=True) == self.path:
            if confirm:
                qt.ok_cancel(
                    'Open scene to read contents?\n\n{}\n\n'
                    'Current scene will be lost.'.format(self.path))
            cmds.file(
                self.path, open=True, prompt=False, force=True,
                loadReferenceDepth='none')
            _replaced_scene = True

        _deps = {'refs': {}, 'abcs': {}}

        # Read refs
        for _ref in ref.find_refs():
            if not _ref.path:
                continue
            _deps['refs'][_ref.namespace] = _ref.path

        # Read abcs
        for _abc in cmds.ls(type='ExocortexAlembicFile'):
            if ':' not in _abc:
                continue
            _ns = str(_abc.split(':')[0])
            _path = str(cmds.getAttr(_abc+'.fileName', asString=True))
            _deps['abcs'][_ns] = _path

        if verbose:
            pprint.pprint(_deps)
        if new_scene:
            cmds.file(new=True, force=True)

        return _deps, _replaced_scene


