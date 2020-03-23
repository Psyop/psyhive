"""Forces scripts/ directory into sys.path.

This allows access to psyhive and maya_psyhive modules.
"""

import os
import sys

# Directories to step up:  -1 = . (packages only), -2 = .. , -3 = ... , etc.
_RELATIVE_VALUE = -1

# After step up, append this sub path
# example: ['foo', 'bar'] -> /foo/bar is appended
_PATH_APPEND = ['scripts']

_PATH = os.path.sep.join(
    __file__.split(os.path.sep)[0:_RELATIVE_VALUE] + _PATH_APPEND)
if _PATH not in sys.path:
    sys.path.insert(0, _PATH)

del sys.modules[__name__]
import psyhive
