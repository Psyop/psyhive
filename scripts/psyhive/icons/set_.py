"""Tools for managing sets of icons."""

import copy
import operator
import pprint

from HTMLParser import HTMLParser

from psyhive.utils import (
    Seq, store_result_on_obj, lprint, read_file,
    File, apply_filter, get_single, store_result)

_FOUND_EMOJIS = set()


class _Emoji(File):
    """Represents an emoji image file."""

    def __init__(self, name, path_, url):
        """Constructor.

        Args:
            name (str): emoji name
            path_ (str): path to file
            url (str): url of image file
        """
        super(_Emoji, self).__init__(path_)
        self.name = name
        self.url = url
        self.index = int(self.path.split('.')[-2])

    def __repr__(self):
        return '<{}[{:d}]:{}>'.format(
            type(self).__name__.strip('_'), self.index, self.name)


class _EmojiIndexParser(HTMLParser):
    """Parser for emoji set's index.html file."""

    _count = 0
    names = {}
    urls = {}

    def handle_starttag(self, tag, attrs):
        """Handle html tag.

        Args:
            tag (str): name of tag
            attrs (list): tag attrs
        """
        if not tag == 'img':
            return
        _title = _url = None
        for _key, _val in attrs:
            if _key == 'title':
                _title = _val
            elif _key == 'data-src':
                _url = _val
        if not _title:
            return
        for _find, _replace in [
                (u'\u201c', '"'),
                (u'\u201d', '"'),
                (u'\u2019', "'"),
                (u'\xc5', ''),
        ]:
            _title = _title.replace(_find, _replace)
        self.names[_title] = self._count
        self.urls[_title] = _url
        self._count += 1


class EmojiSet(Seq):
    """Represents an image sequence containing an emoji image set.

    The set should also have an index.hmtl file in the dir.
    """

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super(EmojiSet, self).__init__(*args, **kwargs)
        self.index = '{}/index.html'.format(self.dir)

    @store_result
    def find(self, match, catch=False, verbose=0):
        """Find an emoji matching the given name.

        Args:
            match (str): name/filter to match
            catch (bool): no error if unable to find icon
                (to facilitate missing icons)
            verbose (int): print process data

        Returns:
            (str): path to emoji image file
        """
        global _FOUND_EMOJIS
        _match = self.find_emoji(match, catch=catch, verbose=verbose)
        if not _match:
            return None
        _FOUND_EMOJIS.add(_match.name)
        lprint('EMOJI', _match, verbose=verbose)
        return _match.path

    def find_emoji(self, match, catch=False, verbose=0):
        """Find an emoji object matching the given name.

        Args:
            match (str): name/filter to match
            catch (bool): no error if unable to find icon
                (to facilitate missing icons)
            verbose (int): print process data

        Returns:
            (_Emoji): emoji object
        """

        # Try index match
        try:
            _idx_matches = self.find_emojis(index=match)
        except OSError as _exc:
            if catch:
                return None
            raise _exc
        lprint(
            'FOUND {:d} INDEX MATCHES'.format(len(_idx_matches)),
            verbose=verbose)
        _idx_match = get_single(_idx_matches, catch=True)
        if _idx_match:
            return _idx_match

        # Try exact match
        _exact_matches = self.find_emojis(name=match)
        lprint(
            'FOUND {:d} EXACT MATCHES'.format(len(_exact_matches)),
            verbose=verbose)
        _exact_match = get_single(_exact_matches, catch=True)
        if _exact_match:
            return _exact_match

        # Try filter match
        _filter_matches = self.find_emojis(filter_=match)
        _names = sorted([_emoji.name for _emoji in _filter_matches])
        lprint(
            'FOUND {:d} FILTER MATCHES: {}'.format(
                len(_filter_matches), _names),
            verbose=verbose)
        _filter_match = get_single(_filter_matches, catch=True)
        if _filter_match:
            return _filter_match

        pprint.pprint(sorted([
            str(_emoji.name.replace(u'\u2019', "'"))
            for _emoji in _filter_matches]))
        raise ValueError('Filter {} matched {:d} emojis'.format(
            match, len(_filter_matches)))

    def find_emojis(self, filter_=None, name=None, index=None):
        """Search for emojis in this set.

        Args:
            filter_ (str): apply filter to emoji names
            name (str): match an exact name
            index (int): match an index
        """
        _emojis = copy.copy(self._read_emojis())
        if index is not None:
            _emojis = [
                _emoji for _emoji in _emojis
                if _emoji.index == index]
        if name:
            _emojis = [
                _emoji for _emoji in _emojis
                if _emoji.name.lower() == name.lower()]
        if filter_:
            _emojis = apply_filter(
                _emojis, filter_, key=operator.attrgetter('name'))

        return _emojis

    @store_result_on_obj
    def _read_emojis(self):
        """Read the list of emojis and cache the result."""
        _emojis = []
        _parser = self._read_html()
        for _name, _idx in _parser.names.items():
            _url = _parser.urls[_name]
            _emoji = _Emoji(path_=self[_idx], name=_name, url=_url)
            _emojis.append(_emoji)

        return _emojis

    @store_result_on_obj
    def _read_html(self, verbose=0):
        """Parse data from the index.html file.

        Args:
            verbose (int): print process data
        """
        lprint('READING {}'.format(self.index), verbose=verbose)
        _body = read_file(self.index)
        if hasattr(_body, 'decode'):  # py2 requires this
            _body = _body.decode('utf8')
        _parser = _EmojiIndexParser()
        _parser.feed(_body)

        return _parser
