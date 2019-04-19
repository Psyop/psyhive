"""Tools for managing executing host across multiple host applications."""

NAME = None

try:
    import maya
except ImportError:
    pass
else:
    del maya
    NAME = 'maya'
