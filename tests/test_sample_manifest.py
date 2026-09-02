# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_assets/sample_images/manifest.json is written by TWO generators
(tools/gen_sample_images.py, tools/gen_synth_samples.py). Before 2026-09-02 the first
rewrote the whole file, so running it after the second silently dropped the three
synthesised entries. These tests pin the owner-aware merge: any order, idempotent,
other owners preserved, malformed manifest refused (fail-closed).
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, ROOT)

import gen_sample_images as GI   # noqa: E402
import gen_synth_samples as GS   # noqa: E402


def _names(mpath):
    with open(mpath, encoding="utf-8") as f:
        return [e["name"] for e in json.load(f)["images"]]


def _e(n, owner_hint=""):
    return {"name": n, "file": n + ".png", "source": owner_hint or "x", "licence": "own work"}


# --------------------------------------------------------------------------- #
# merge_manifest unit behaviour                                                 #
# --------------------------------------------------------------------------- #
def test_merge_any_order_keeps_both_owners(tmp_path):
    m = str(tmp_path / "manifest.json")
    a = [_e("gradient"), _e("blobs")]
    b = [_e("grain_synth"), _e("brick_quilt")]
    GI.merge_manifest(m, b, "gen_synth_samples")          # second script runs FIRST
    GI.merge_manifest(m, a, "gen_sample_images")          # then the first
    assert _names(m) == ["grain_synth", "brick_quilt", "gradient", "blobs"]
    GI.merge_manifest(m, a, "gen_sample_images")          # idempotent re-run
    GI.merge_manifest(m, b, "gen_synth_samples")
    assert _names(m) == ["grain_synth", "brick_quilt", "gradient", "blobs"]
    with open(m, encoding="utf-8") as f:
        owners = {e["name"]: e["owner"] for e in json.load(f)["images"]}
    assert owners == {"grain_synth": "gen_synth_samples", "brick_quilt": "gen_synth_samples",
                      "gradient": "gen_sample_images", "blobs": "gen_sample_images"}


def test_merge_drops_only_own_stale_entries_and_claims_legacy(tmp_path):
    m = str(tmp_path / "manifest.json")
    legacy = {"images": [_e("gradient"), _e("old_ours"), _e("grain_synth")]}   # no owner field
    with open(m, "w", encoding="utf-8") as f:
        json.dump(legacy, f)
    GI.merge_manifest(m, [_e("gradient", "new")], "gen_sample_images")
    # legacy entries are unowned -> preserved unless replaced by name
    assert _names(m) == ["gradient", "old_ours", "grain_synth"]
    with open(m, encoding="utf-8") as f:
        imgs = {e["name"]: e for e in json.load(f)["images"]}
    assert imgs["gradient"]["source"] == "new" and imgs["gradient"]["owner"] == "gen_sample_images"
    assert "owner" not in imgs["old_ours"]
    # now old_ours becomes ours, then vanishes from the generator -> dropped; others untouched
    GI.merge_manifest(m, [_e("gradient"), _e("old_ours")], "gen_sample_images")
    GI.merge_manifest(m, [_e("gradient")], "gen_sample_images")
    assert _names(m) == ["gradient", "grain_synth"]


def test_merge_refuses_malformed_manifest(tmp_path):
    m = str(tmp_path / "manifest.json")
    with open(m, "w", encoding="utf-8") as f:
        f.write("{not json")
    with pytest.raises(GI.ManifestError):
        GI.merge_manifest(m, [_e("gradient")], "gen_sample_images")
    with open(m, encoding="utf-8") as f:
        assert f.read() == "{not json"                    # untouched (fail-closed)
    with open(m, "w", encoding="utf-8") as f:
        json.dump({"images": [{"file": "no-name.png"}]}, f)
    with pytest.raises(GI.ManifestError):
        GI.merge_manifest(m, [_e("gradient")], "gen_sample_images")


# --------------------------------------------------------------------------- #
# the two real scripts against a temp OUT dir, both orders                      #
# --------------------------------------------------------------------------- #
def _run_both(tmp_path, monkeypatch, order):
    out = str(tmp_path / "sample_images")
    monkeypatch.setattr(GI, "OUT", out)
    monkeypatch.setattr(GS, "OUT", out)
    monkeypatch.setattr(sys, "argv", ["gen_synth_samples.py"])
    for mod in order:
        assert mod.main() == 0
    return out


@pytest.mark.parametrize("order", [(GI, GS), (GS, GI)], ids=["images-then-synth", "synth-then-images"])
def test_scripts_in_either_order_keep_all_entries(tmp_path, monkeypatch, order):
    out = _run_both(tmp_path, monkeypatch, order)
    names = _names(os.path.join(out, "manifest.json"))
    synth_names = set(GS._SAMPLES)
    base_names = set(GI._synthetic()) | set(GI._skimage())
    assert synth_names <= set(names), sorted(synth_names - set(names))     # the 3 that used to vanish
    assert base_names <= set(names), sorted(base_names - set(names))
    assert len(names) == len(set(names)) == len(synth_names | base_names)
    for n in names:                                                        # every entry has its PNG
        assert os.path.exists(os.path.join(out, n + ".png")), n
