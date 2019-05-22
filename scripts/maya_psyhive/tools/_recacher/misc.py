"""Misc utils for recacher tool."""

import tank

from psyhive import pipe, tk
from psyhive.utils import abs_path, store_result, dprint


class CacheDataShot(pipe.Shot):
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
                _data['asset'] = tk.TTAssetOutputVersion(_rig_path)
            except ValueError:
                del _cache_data[_name]
                continue

            # Ignore animcache of camera
            if (
                    _data['asset'].sg_asset_type == 'camera' and
                    _data['cache'].output_type == 'animcache'):
                del _cache_data[_name]
                continue

            _work_file = abs_path(_metadata.get('origin_scene'))
            _data['origin_scene'] = _work_file
            _data['work_file'] = tk.get_work(_work_file)

        return sorted(_cache_data.values())
