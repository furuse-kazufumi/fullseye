"""Point-cloud marker sizes follow the sampled surface spacing."""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import numpy as np

import pocviewer as pv


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_GLOBS = (
    "docs/view2026/viewers/*.html",
    "docs/view2026/anim3d/*.html",
    "docs/anim3d/*.html",
)

# Deliberately authored, non-surface particles may opt out.  Every entry needs
# a useful explanation; stale entries are rejected below.
POINT_SIZE_EXEMPTIONS: dict[str, str] = {
    **{
        ("docs/anim3d/gauss_bonnet.html:torus:cloud[%d]" % frame):
            "Authored topology samples are intentionally smaller so the torus remains readable."
        for frame in range(49)
    },
    **{
        ("docs/anim3d/itokawa_gravity.html:muses:cloud[%d]" % frame):
            "Authored spacecraft particles depict a trajectory event rather than a sampled surface."
        for frame in (0, 12, 24, 36, 48, 60, 72)
    },
    **{
        ("docs/anim3d/poc_lens_aberrations.html:%s:cloud[%d]" % (tab, frame)):
            "Authored optical-ray markers encode a ray bundle and are not surface samples."
        for tab in ("spherical", "coma", "astig", "chroma") for frame in range(56)
    },
    **{
        ("docs/view2026/anim3d/interactive_anim3d_viewer.html:arm:cloud[%d]" % frame):
            "Authored robot-arm markers show sparse targets rather than a sampled surface."
        for frame in (0, 137)
    },
    **{
        ("docs/view2026/anim3d/particle_dissolution_anim3d.html:size:cloud[%d]" % frame):
            "Authored dissolving grains preserve a physical grain radius instead of surface spacing."
        for frame in range(41)
    },
    **{
        ("docs/view2026/anim3d/salt_xrd_anim3d.html:powder:cloud[%d]" % frame):
            "Authored powder grains preserve particle size; late frames also have no measurable neighbour."
        for frame in range(84)
    },
    **{
        ("docs/view2026/viewers/poc_lidar_terrain_change.html:%s" % tab):
            "The explicit 1.8 m LiDAR marker is retained to compare three registered survey layers."
        for tab in ("plain", "flat", "full")
    },
}


def _data(path: Path) -> dict:
    html = path.read_text(encoding="utf-8")
    match = re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S)
    assert match, str(path)
    return json.loads(match.group(1))


def _array(data: dict, key: str) -> np.ndarray:
    rec = data["arrays"][key]
    dtype = {"q8": "u1", "q16": "<u2", "f32": "<f4"}[rec["t"]]
    raw = np.frombuffer(base64.b64decode(rec["b64"]), dtype=dtype).reshape(rec["shape"])
    if rec["t"].startswith("q"):
        top = 255.0 if rec["t"] == "q8" else 65535.0
        lo, hi = np.asarray(rec["lo"]), np.asarray(rec["hi"])
        return lo + raw.astype(np.float64) * (hi - lo) / top
    return raw.astype(np.float64)


def _records(path: Path):
    data = _data(path)
    page = path.relative_to(ROOT).as_posix()
    for tab in data["tabs"]:
        if tab["kind"] == "points":
            yield f"{page}:{tab['id']}", _array(data, tab["pos"]), tab.get("point_size")
        elif tab["kind"] == "anim3d":
            for cloud in tab.get("clouds", []):
                ident = f"{page}:{tab['id']}:cloud[{cloud['k']}]"
                yield ident, _array(data, cloud["pos"]), cloud.get("point_size")


def test_default_is_1_2_times_median_nearest_spacing_and_deterministic():
    rng = np.random.default_rng(8)
    pos = rng.normal(size=(20_100, 3))
    a = pv._default_point_size(pos)
    assert a == pv._default_point_size(pos)
    assert a == 1.2 * pv._median_nearest_spacing(pos)


def test_public_point_markers_match_surface_spacing():
    failures = []
    seen = set()
    paths = sorted({path for pattern in PUBLIC_GLOBS for path in ROOT.glob(pattern)})
    assert paths
    for path in paths:
        for ident, pos, size in _records(path):
            if ident in POINT_SIZE_EXEMPTIONS:
                seen.add(ident)
                continue
            spacing = pv._median_nearest_spacing(pos)
            if size is None or not 0.5 * spacing <= size <= 1.5 * spacing:
                failures.append((ident, size, spacing))
    assert not failures, "point-size gate violations: %r" % failures
    stale = set(POINT_SIZE_EXEMPTIONS) - seen
    assert not stale, "stale point-size exemptions: %r" % sorted(stale)


def test_default_point_markers_do_not_hit_28px_shader_cap():
    """At the documented 1280x1400 capture size the 3-D canvas is 560 px high."""
    capped = []
    for pattern in PUBLIC_GLOBS:
        for path in ROOT.glob(pattern):
            data = _data(path)
            page = path.relative_to(ROOT).as_posix()
            for tab in data["tabs"]:
                if tab["kind"] != "points":
                    continue
                ident = f"{page}:{tab['id']}"
                if ident in POINT_SIZE_EXEMPTIONS:
                    continue
                pos = _array(data, tab["pos"])
                lo, hi = pos.min(axis=0), pos.max(axis=0)
                centre = (lo + hi) / 2
                rad = 0.5 * np.linalg.norm(hi - lo) or 1.0
                view = tab.get("view") or {}
                az, el = view.get("az", -1.0), view.get("el", 0.5)
                direction = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
                distance = 2.0 * rad * view.get("dist", 1.0)
                depth = distance - (pos - centre) @ direction
                unclamped_px = tab["point_size"] * 560.0 / (2 * np.tan(0.9 / 2) * depth)
                if float(unclamped_px.max()) >= 28.0:
                    capped.append((ident, float(unclamped_px.max())))
    assert not capped, "default markers reach the 28 px shader cap: %r" % capped


def test_point_size_exemptions_have_specific_reasons():
    vague = {ident: reason for ident, reason in POINT_SIZE_EXEMPTIONS.items()
             if len(reason.strip()) < 12 or reason.strip().lower() in {"explicit", "legacy", "special"}}
    assert not vague, "point-size exemptions need specific reasons: %r" % vague


def test_slider_x1_matches_python_default_in_headless_chrome():
    """The browser's S.ps at slider ×1 is exactly the packed Python default."""
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import headless_chrome

    if not headless_chrome.find_chrome():
        import pytest
        pytest.skip("Chrome / Chromium is not installed")
    path = ROOT / "docs/view2026/viewers/poc_asteroid_curvature.html"
    data = _data(path)
    tab = next(t for t in data["tabs"] if t["kind"] == "points")
    with headless_chrome.HeadlessChrome() as chrome:
        chrome.open(path.as_uri() + "?tab=" + tab["id"], width=1280, height=1400)
        chrome.wait_for("window.__pocviewerPointSize && window.__pocviewerPointSize().tab === %s" % json.dumps(tab["id"]))
        actual = chrome.eval("window.__pocviewerPointSize()")
    assert actual["scale"] == 1
    assert actual["ps"] == tab["point_size"]
