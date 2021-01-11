"""Tools for managing outsource vendor ingestion in maya."""

from .ming_remote import check_current_scene, read_scene_render_cam

try:
    from .ming_vendor_scene import VendorScene, ingest_current_scene
    from .ming_tools import ingest_vendor_anim
except ImportError:
    pass
