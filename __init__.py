import os
import sys

RELATIVE_VALUE = -1  # Directories to step up:  -1 = . (packages only), -2 = .. , -3 = ... , etc.
PATH_APPEND = ['scripts']  # After step up, append this sub path, example: ['foo', 'bar'] -> /foo/bar is appended

pth = os.path.sep.join(__file__.split(os.path.sep)[0:RELATIVE_VALUE] + PATH_APPEND)
if pth not in sys.path:
    sys.path.insert(0, pth)

del sys.modules[__name__] 
import psyhive

