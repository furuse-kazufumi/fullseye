"""Access to the collected, license-clean Studio sample images.

Files live in ``studio_assets/sample_images/`` with a ``manifest.json`` recording
each image's source and licence (synthetic = own work; skimage.data = BSD / public
domain). Regenerate with ``py -3.11 tools/gen_sample_images.py``.
"""
from __future__ import annotations

import json
import os

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "studio_assets", "sample_images")


def _manifest():
    p = os.path.join(_DIR, "manifest.json")
    if not os.path.exists(p):
        return {"images": []}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def names() -> list:
    """Sample-image names, in manifest order (empty if not yet generated)."""
    return [it["name"] for it in _manifest().get("images", [])]


def entries() -> list:
    """``[{name, file, source, licence}, ...]`` — with provenance for disclosure."""
    return list(_manifest().get("images", []))


def path(name: str):
    """Absolute path to the sample image *name*, or ``None`` if absent."""
    p = os.path.join(_DIR, str(name) + ".png")
    return p if os.path.exists(p) else None


def load(name: str):
    """Load sample image *name* as a float [0,1] array (raises on unknown name)."""
    import imgio
    p = path(name)
    if p is None:
        raise KeyError("unknown sample image %r (have: %s)" % (name, ", ".join(names())))
    return imgio.load(p)
