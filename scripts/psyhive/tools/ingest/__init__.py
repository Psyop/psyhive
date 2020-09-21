"""Tools for ingesting file from outsource vendors."""

from .ing_utils import parse_basename, vendor_from_path
from .ing_vendor_file import is_vendor_file, VendorFile
from .ing_psy_asset import is_psy_asset, PsyAsset

try:  # This will fail for outsource vendors
    from .ing_utils_psy import ICON
    from .ing_tools import ingest_seqs
except ImportError:
    pass
