"""Guards for the 3-D example gallery (examples3d) — the discoverability layer.

An operator no one can find or run is invisible; the gallery is what makes the
3-D toolkit discoverable (Studio "3-D Examples", docs/EXAMPLES_3D.md). These guards
keep the gallery honest:

  * registry metadata and on-disk scripts stay in 1:1 sync (no dangling entry, no
    orphan file) — a broken index silently drops examples from the gallery;
  * every advertised script actually parses (compiles) — a syntax-broken example
    would be shown but fail when a user runs it;
  * a representative example per data provenance (synthetic / skeleton_ct / itokawa)
    actually runs to a passing ground-truth assertion.

The full 27-example run is `py -3.11 examples3d.py` (all subprocesses); here we run a
3-example smoke set so the suite stays fast while still proving the runner + real
sample data work end to end.
"""
from __future__ import annotations

import os
import py_compile

import pytest

import examples3d as E

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_metadata_and_files_are_in_sync():
    """Every registry id has a script and vice-versa (no dangling entry / orphan)."""
    meta = set(E.names())
    disk = set(E.discover())
    assert meta == disk, (
        f"registry/disk mismatch — only in metadata: {sorted(meta - disk)}; "
        f"only on disk: {sorted(disk - meta)}")
    assert len(meta) >= 20, f"gallery unexpectedly small: {len(meta)}"


def test_every_entry_has_required_metadata():
    """Each entry carries the fields the gallery renders."""
    for e in E.EXAMPLES:
        for field in ("id", "name", "task", "summary", "data"):
            assert e.get(field), f"{e.get('id')}: missing/empty {field}"
        assert e["data"] in ("synthetic", "skeleton_ct", "itokawa"), (e["id"], e["data"])


def test_every_example_script_compiles():
    """A gallery script that does not even parse would be advertised but broken."""
    for name in E.names():
        py_compile.compile(E.path(name), doraise=True)


def test_real_sample_data_is_present():
    """The shipped real-data samples the CT / Itokawa examples load must exist."""
    base = os.path.join(ROOT, "studio_assets", "sample_3d")
    for f in ("itokawa_points.npy", "skeleton_ct.npy", "ATTRIBUTION.md"):
        assert os.path.exists(os.path.join(base, f)), f"missing sample data: {f}"


@pytest.mark.parametrize("example_id", ["sdf_csg", "ct_bone_segmentation", "itokawa_self_register"])
def test_representative_example_runs_and_passes(example_id):
    """One example per data provenance runs to a passing GT assertion (real end-to-end)."""
    ok, note = E.run(example_id, timeout=240)
    assert ok, f"{example_id} failed: {note}"
