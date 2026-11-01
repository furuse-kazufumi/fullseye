"""Runnable sample for named physical params and explicit template handles."""
from __future__ import annotations

import tempfile
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fullseye.mcp.catalog import Catalog
from fullseye.mcp.handles import HandleStore
from fullseye.mcp.server import call_tool


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        scene = np.zeros((48, 48), dtype=np.float64)
        template = np.array([[0, 1, 0], [1, 1, 0], [0, 0, 1]], dtype=np.float64)
        scene[20:23, 31:34] = template
        np.save(root / "scene.npy", scene)
        np.save(root / "template.npy", template)

        catalog = Catalog.load()
        store = HandleStore(roots=[str(root)])
        scene_handle = call_tool("fullseye_load_image", {
            "path": str(root / "scene.npy"), "vision": "none",
        }, catalog, store)["structuredContent"]["handle"]
        template_handle = call_tool("fullseye_load_template", {
            "path": str(root / "template.npy"), "vision": "none",
        }, catalog, store)["structuredContent"]["handle"]

        smoothed = call_tool("fullseye_pipeline", {
            "handle": scene_handle, "vision": "none",
            "stages": [{"op": "gaussian", "params": {"sigma_px": 1.2}}],
        }, catalog, store)["structuredContent"]
        matched = call_tool("fullseye_pipeline", {
            "handle": scene_handle, "template_handle": template_handle, "vision": "none",
            "stages": [{"op": "ncc_locate"}],
        }, catalog, store)["structuredContent"]
        proposal = call_tool("fullseye_suggest_pipeline", {
            "query": "gaussian", "start_sort": "image", "goal_sort": "image",
        }, catalog, store)["structuredContent"]

        assert smoothed["stages"][0]["named_params"]["sigma_px"]["value"] == 1.2
        assert matched["stages"][0]["value"][0] > 0.9
        assert proposal["unique"] and proposal["validation"]["valid"]
        print("PASS: named params, template handle, validated proposal")


if __name__ == "__main__":
    main()
