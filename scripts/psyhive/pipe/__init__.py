"""Tools for managing and interacting with the pipeline."""

import os

from .misc import read_ver_n, TMP
from .project import (
    find_projects, find_project, Project, cur_project, get_project,
    PROJECTS_ROOT)
from .shot import Shot
from .work_file import WorkFile, WorkFileInc
from .asset import AssetFile

LOCATION = None
if 'PSYOP_ROOT' in os.environ:
    LOCATION = 'psy'
