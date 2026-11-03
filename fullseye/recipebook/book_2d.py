"""2-D image recipes (registry ops; every one runs unchanged through MCP ``fullseye_pipeline``).

Organised by HALCON chapter: Filters, Segmentation, Regions / Morphology, Features, 1D Measuring,
XLD / Contours, Matching, Inspection, Texture, Color, Transformations, Restoration, Frequency.
"""
from __future__ import annotations

RECIPES = [
    {"name": "Measure — diameter of a bright round part", "family": "2d", "task": "measure",
     "task_class": "measurement", "halcon": "Regions", "input_sort": "image", "sample": "disk_image",
     "stages": [{"op": "gaussian", "a": 0.3, "b": 0.5}, {"op": "otsu", "a": 0.5, "b": 0.5},
                {"op": "fill_up", "a": 0.5, "b": 0.5}, {"op": "diameter_region", "a": 0.5, "b": 0.5}],
     "expect": [{"get": [], "approx": "diameter", "atol": 3.0}],
     "note": "smooth, Otsu, fill holes, then the region's maximal diameter in pixels "
             "(the disk's diameter 2r; the sample's disk has r = 18 + 6·variant)"},
    {"name": "Inspect — roundness of a punched disk (circularity)", "family": "2d", "task": "inspect",
     "task_class": "inspection", "halcon": "Regions", "input_sort": "image", "sample": "disk_image",
     "stages": [{"op": "otsu", "a": 0.5, "b": 0.5}, {"op": "fill_up", "a": 0.5, "b": 0.5},
                {"op": "circularity", "a": 0.5, "b": 0.5}],
     "expect": [{"get": [], "between": [0.9, 1.0]}],
     "note": "binarize, fill, circularity 4πA/P²-style score: near 1 for a good round part, lower when it is "
             "dented or oval"},
]

SAMPLES: dict = {}
MISSING_OPS: list = []
