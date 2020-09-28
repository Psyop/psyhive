"""Tools for managing outsource vendor ingestion in maya."""

from .ming_remote import check_current_scene

try:
    from .ming_vendor_scene import VendorScene
    from .ming_tools import ingest_vendor_anim
except ImportError:
    pass
