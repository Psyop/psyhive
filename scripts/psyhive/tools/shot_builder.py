"""Tools for building work files from a template (outside of any dcc)."""

import tempfile
import re
import six

from psyhive import tk, qt, farm
from psyhive.utils import File, get_single, abs_path


def submit_update_ma(template, shot):
    """Submit maya file update to farm.

    Args:
        template (TTWorkFileBase): template scene
        shot (TTShotRoot): shot to update to
    """
    _py = '\n'.join([
        'from maya_psyhive.tools import m_shot_builder',
        '_template = "{template.path}"',
        '_shot = "{shot.name}"',
        'm_shot_builder.build_shot_from_template(',
        '    template=_template, shot=_shot, force=True)',
    ]).format(template=template, shot=shot)
    _label = 'Build shot '+shot.name
    _task = farm.MayaPyTask(_py, label=_label)
    _job = farm.MayaPyJob(_label, tasks=[_task])
    _job.submit()

    print 'SUBMITTED UPDATE JOB TO FARM'


class _NkNode(object):
    """Represents a nuke node in an nk file."""

    def __init__(self, type_):
        """Constructor.

        Args:
            type_ (str): node type (eg. Write)
        """
        self.type_ = type_
        self.attrs = []

    def read_attr(self, attr):
        """Read value of the given attribute from this node.

        Args:
            attr (str): attribute name

        Returns:
            (any): attribute value
        """
        for _attr, _val in self.attrs:
            if _attr == attr:
                return _val
        raise ValueError(attr)

    def set_attr(self, attr, val):
        """Set value of the given attribute.

        Args:
            attr (str): attribute name
            val (any): attribute value
        """
        for _idx, (_attr, _) in enumerate(self.attrs):
            if _attr == attr:
                self.attrs[_idx] = (attr, val)
                return
        self.attrs.append((attr, val))

    @property
    def name(self):
        """Get name of this node.

        Returns:
            (str): node name
        """
        return self.read_attr('name')

    def __repr__(self):
        return '<{}:{}({})>'.format(
            type(self).__name__.strip('_'), self.type_, self.name)


class _NkFile(File):
    """Represents a nk text file."""

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to nk file
        """
        super(_NkFile, self).__init__(path)
        self.data = self._parse_data()

    def _parse_data(self):
        """Read nk data from file.

        Returns:
            (list): list of data items
        """
        _body = self.read()
        _header, _node_str = _body.split('\nRoot {')
        _node_str = 'Root {'+_node_str

        _data = []
        _data.append(_header)

        _node = _attr = _val = None
        for _line in _node_str.split('\n'):
            _tokens = _line.split()
            if not _line.startswith(' '):
                if _line.endswith('{'):  # New node
                    _node_type, _tail = _line.split()
                    assert _tail == '{'
                    _attr = _val = None
                    _node = _NkNode(_node_type)
                elif _line == '}':  # Finish node
                    _node.attrs.append((_attr, _val))
                    _data.append(_node)
                    _node = _attr = _val = None
                else:  # Single line node
                    _data.append(_line)
            elif len(_line) > 2 and not _line[1].isspace():
                if _attr:  # Finish attr
                    _node.attrs.append((_attr, _val))
                _attr = _tokens[0]
                _val = ' '.join(_tokens[1:])
            else:
                _val += '\n'+_line

        return _data

    def find_node(self, name=None, type_=None):
        """Find node within this nk file.

        Errors if search does not match exactly one node.

        Args:
            name (str): match node by name
            type_ (str): match by node type

        Returns:
            (_NkNode): matching node
        """
        return get_single(self.find_nodes(name=name, type_=type_))

    def find_nodes(self, type_=None, name=None):
        """Find nodes within this nk file.

        Args:
            type_ (str): match by node type
            name (str): match node by name

        Returns:
            (_NkNode list): matching nodes
        """
        _nodes = [_element for _element in self.data
                  if isinstance(_element, _NkNode)]
        if type_:
            _nodes = [_node for _node in _nodes if _node.type_ == type_]
        if name:
            _nodes = [_node for _node in _nodes if _node.name == name]
        return _nodes

    def write(self, path, force=False):
        """Write updated contents to disk.

        Args:
            path (str): path to write to
            force (bool): write without confirmation
        """
        _text = ''
        for _element in self.data:
            if isinstance(_element, six.string_types):
                _text += _element+'\n'
            elif isinstance(_element, _NkNode):
                _text += _element.type_+' {\n'
                for _attr, _val in _element.attrs:
                    _text += ' {} {}\n'.format(_attr, _val)
                _text += '}\n'
            else:
                raise ValueError(_element)

        File(path).write_text(_text.strip()+'\n', force=force)


def _update_nk_reads(nk_file, shot):
    """Update Read node in nk file.

    Args:
        nk_file (_NkFile): nk file to update
        shot (TTShotRoot): shot to update to
    """
    _start, _end = shot.get_frame_range()

    # Update read nodes
    for _node in nk_file.find_nodes(type_='Read'):
        _file = _node.read_attr('file')
        _orig_out = tk.get_output(_file)
        if not _orig_out:
            continue
        print 'ORIG OUT', _orig_out
        _new_out = _orig_out.map_to(Shot=shot.shot).find_latest(catch=True)
        print 'NEW OUT', _orig_out
        if not _new_out:
            _node.set_attr('disable', True)
        else:
            _node.set_attr('file', _new_out.path)
            _node.set_attr('first', _start)
            _node.set_attr('last', _end)
            _node.set_attr('origfirst', _start)
            _node.set_attr('origlast', _end)
        print 'UPDATED', _node
        print


def update_nk(template, shot, diff=True, force=True):
    """Update nk template to new shot.

    Args:
        template (TTWorkFileBase): template work file
        shot (TTShotRoot): shot to update to
        diff (bool): show diffs
        force (bool): save with no confirmation
    """
    _new_work = template.map_to(Shot=shot.shot).find_next()
    _start, _end = shot.get_frame_range()

    _nk = _NkFile(template.path)
    _update_nk_reads(nk_file=_nk, shot=shot)

    # Update write nodes
    for _node in _nk.find_nodes(type_='Write'):
        for _attr in ['file', 'proxy']:
            _file = _node.read_attr(_attr)
            _orig_out = tk.get_output(_file)
            if not _orig_out:
                continue
            print 'ORIG OUT', _orig_out
            _new_out = _orig_out.map_to(
                Shot=shot.shot, version=_new_work.version)
            print 'NEW OUT', _orig_out
            _node.set_attr(_attr, _new_out.path)
        print

    # Update root
    _root = _nk.find_node(type_='Root')
    _root.set_attr('name', _new_work.path)
    _root.set_attr('first_frame', _start)
    _root.set_attr('last_frame', _end)

    # Update header
    _header = _nk.data[0]
    assert isinstance(_header, six.string_types)
    _tokens = [_token for _token in re.split('[ "]', _header) if _token]
    for _token in _tokens:
        _orig_out = tk.get_output(_token)
        if not _orig_out:
            continue
        _new_out = _orig_out.map_to(
            Shot=shot.shot, version=_new_work.version)
        assert _header.count(_token) == 1
        _header = _header.replace(_token, _new_out.path)
        _nk.data[0] = _header

    if diff:
        _tmp_nk = File(abs_path('{}/test.nk'.format(tempfile.gettempdir())))
        _nk.write(_tmp_nk.path, force=True)
        _tmp_nk.diff(template.path)

    # Write new work
    if not force:
        qt.ok_cancel('Write new work file?\n\n{}'.format(_new_work.path))
    _nk.write(_new_work.path, force=True)
    _new_work.set_comment(comment='Scene built by shot_builder')
    print 'WROTE NK:', _new_work.path
