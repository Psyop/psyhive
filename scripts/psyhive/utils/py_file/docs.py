"""Tools for managing python docstrings.

The docstring has the format:

    '''Header (required) - one line summary.

    Description (optional) - more detailed description. Together with the
    header this is called the body.

    Args: (optional)
        arg name (arg type): arg description

    Returns: (optional)
        (result type): result description

    Raises: (optional)
        (exception type): exception cause
    '''
"""


class MissingDocs(RuntimeError):
    """Raised when docstrings are missing."""


class PyArgDocs(object):
    """Represents arg docstring."""

    def __init__(self, name, type_, desc):
        """Constructor.

        Args:
            name (str): arg name
            type_ (str): arg type name
            desc (str): arg desc
        """
        self.name = name
        self.type_ = type_
        self.desc = desc


class PyDefDocs(object):
    """Represents docstrings on a python def."""

    def __init__(self, text):
        """Constructor.

        Args:
            text (str): docstrings text
        """
        self.text = text or ''
        self.lines = self.text.split('\n')

        # Read header/desc/body
        self.header = self.text.split('\n')[0]
        _desc = '\n'.join(self.text.split('\n')[2:])
        for _split in ['Args:', 'Result:', 'Raises:']:
            _desc = _desc.split(_split)[0]
        self.desc = _desc.strip()
        self.desc_full = '{}\n\n{}'.format(self.header, self.desc)

        self.exc_type, self.exc_desc = self._read_exc()
        self.result_type, self.result_desc = self._read_result()
        self.args = self._read_args()

    def _read_args(self):
        """Read arg docstrings."""
        if 'Args:' not in self.text:
            return []

        _text = self.text.split('Args:')[-1]
        for _split in ['Raises:', 'Returns:']:
            _text = _text.split(_split)[0]

        # Separate into args
        _args = []
        for _line in _text.split('\n'):
            _line = _line.strip()
            if '): ' in _line:
                _name = _line.split()[0]
                _type = _line.split()[1].strip('():')
                _desc = _line.split("): ")[-1]
                _arg = PyArgDocs(name=_name, type_=_type, desc=_desc)
                _args.append(_arg)
            elif _line and _args:
                _args[-1].desc += ' '+_line.strip()

        return _args

    def _read_exc(self):
        """Read exception/raises section."""
        _type, _desc = None, None

        if 'Raises:' in self.lines:
            _text = self.text.split('Raises:')[-1].strip()
            _type = _text.split('): ')[0].strip('(')
            _desc = ' '.join(_text.split('): ')[-1].strip().split())

        return _type, _desc

    def _read_result(self):
        """Read result section."""
        _type, _desc = None, None

        if 'Returns:' in self.lines:
            _text = self.text.split('Returns:')[-1].split('Raises:')[0].strip()
            _type = _text.split('): ')[0].strip('(')
            _desc = ' '.join(_text.split('): ')[-1].strip().split())

        return _type, _desc
