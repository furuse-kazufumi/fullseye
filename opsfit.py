"""Typed registry for rotation-invariant and subpixel fitting operations."""
import filters_freq
import measure

_MOD = {"measure": measure, "filters_freq": filters_freq}

_CATALOG = {
    "fit": [
        ("fit_circle_geometric", "measure", ["keypoints"], "table"),
        ("fit_curve_principal_axis", "measure", ["keypoints"], "table"),
    ],
    "registration": [
        ("phase_correlation_shift", "filters_freq", ["image2d", "image2d"], "table"),
    ],
}


def _build():
    out = {}
    for category, rows in _CATALOG.items():
        for name, module, inputs, output in rows:
            out[name] = {"func": getattr(_MOD[module], name), "module": module,
                         "in": inputs, "out": output, "category": category,
                         "streamable": False}
    return out


OPSFIT = _build()
RESULT_ADAPTERS = {}


def list_ops(category=None):
    return sorted(n for n, m in OPSFIT.items()
                  if category is None or m["category"] == category)


def get(name):
    return OPSFIT[name]["func"]
