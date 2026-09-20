# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""emproof(EM 校正のセカンドオピニオン)の門: 合成細胞で真値を持ち、台帳の登録面を全部通す。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import emproof as E  # noqa: E402

_OPS = ["seg_membrane_response", "seg_membrane_chord_score", "seg_boundary_membrane_gap",
        "seg_inject_merge", "seg_inject_split", "seg_label_changes", "holdout_threshold"]


def cells(size=160, n=16, rings=0, seed=0):
    """ボロノイ細胞のラベルと、境界に膜(暗い線)を持つ生画像。rings 個の閉じた輪を足せる。"""
    rng = np.random.default_rng(seed)
    s = rng.random((n, 2)) * size
    yy, xx = np.mgrid[0:size, 0:size]
    d = (yy[..., None] - s[:, 0]) ** 2 + (xx[..., None] - s[:, 1]) ** 2
    lab = (np.argmin(d, -1) + 1).astype(np.int64)
    edge = np.zeros((size, size), bool)
    edge[:, :-1] |= lab[:, :-1] != lab[:, 1:]
    edge[:-1, :] |= lab[:-1, :] != lab[1:, :]
    mem = ndi.gaussian_filter(edge.astype(float), 1.0)
    mem /= mem.max()
    # 閉じた輪(ミトコンドリア)は細胞の内側に置く(境界帯にかかると弧になり、弦と区別できない —— docstring の限界)
    deep = ndi.distance_transform_edt(~edge) > 6 + 3 + 3
    ys, xs = np.nonzero(deep)
    for i in rng.permutation(len(ys))[:rings]:
        ring = np.abs(np.hypot(yy - ys[i], xx - xs[i]) - 6) < 1.1
        mem = np.maximum(mem, ndi.gaussian_filter(ring.astype(float), 0.7) / 0.45)
    raw = 1.0 - 0.8 * np.clip(mem, 0, 1)
    return lab, raw


@pytest.fixture(scope="module")
def world():
    lab, raw = cells()
    return lab, raw, E.seg_membrane_response(raw, sigma=1.2)


# --------------------------------------------------------------------------- #
# 1. 膜応答                                                                     #
# --------------------------------------------------------------------------- #
def test_response_is_high_on_a_dark_line_and_low_in_a_dark_disk():
    img = np.ones((64, 64))
    img[:, 30:33] = 0.2                                     # 暗い線
    yy, xx = np.mgrid[0:64, 0:64]
    img[np.hypot(yy - 16, xx - 16) < 7] = 0.2               # 暗い塊
    M = E.seg_membrane_response(img, sigma=1.2, normalize=False)
    assert M[40, 31] > 5 * M[16, 16]
    assert M.min() >= 0.0
    Mn = E.seg_membrane_response(img, sigma=1.2)
    assert Mn.max() >= 1.0 and abs(float(np.percentile(Mn, 99.5)) - 1.0) < 1e-9
    with pytest.raises(ValueError, match="seg_membrane_response: sigma"):
        E.seg_membrane_response(img, sigma=0.0)
    with pytest.raises(ValueError, match="seg_membrane_response: image"):
        E.seg_membrane_response(np.full((8, 8), np.nan))


# --------------------------------------------------------------------------- #
# 2. 仕込む → 答え合わせ → 疑いが正解を指す                                     #
# --------------------------------------------------------------------------- #
def test_inject_and_label_changes_round_trip(world):
    lab, _raw, _M = world
    merged = E.seg_inject_merge(lab, n=2, seed=1, min_area=400)
    cut = E.seg_inject_split(merged, n=2, seed=1, min_area=800)
    ch = E.seg_label_changes(lab, cut)
    assert ch["n_merged"] == 2 and ch["n_split"] == 2
    assert len(np.unique(merged)) == len(np.unique(lab)) - 2
    assert int(cut.max()) == int(lab.max()) + 2
    # 吸った側の id 自身も before に並ぶ(対ごとに 1 行)
    for a in set(ch["merge_after"].tolist()):
        assert a in ch["merge_before"][ch["merge_after"] == a]
    assert E.seg_label_changes(lab, lab)["n_merged"] == 0
    with pytest.raises(ValueError, match="seg_inject_merge: only"):
        E.seg_inject_merge(lab, n=50, min_area=400)
    with pytest.raises(ValueError, match="seg_inject_split: axis"):
        E.seg_inject_split(lab, axis="diag")
    with pytest.raises(ValueError, match="seg_label_changes: before"):
        E.seg_label_changes(lab, lab[:-1])


def test_split_suspect_is_the_injected_boundary(world):
    lab, _raw, M = world
    cut = E.seg_inject_split(lab, n=1, seed=0, min_area=800, axis="col")
    ch = E.seg_label_changes(lab, cut)
    b, a = int(ch["split_before"][ch["split_before"] != ch["split_after"]][0]), int(ch["split_after"][ch["split_before"] != ch["split_after"]][0])
    gap = E.seg_boundary_membrane_gap(cut, M, tau=0.3, min_len=10)
    assert (int(gap["label_a"][0]), int(gap["label_b"][0])) == (min(a, b), max(a, b))
    assert gap["gap_fraction"][0] > 0.8 and gap["gap_fraction"][1] < 0.5
    assert np.all(np.diff(gap["gap_fraction"]) <= 0)
    assert len(E.seg_boundary_membrane_gap(lab, M, min_len=10 ** 6)["label_a"]) == 0


def test_merge_suspect_is_the_injected_chord_and_rings_are_ignored():
    lab, raw = cells(rings=4, seed=3)
    M = E.seg_membrane_response(raw, sigma=1.2)
    # 融合は「いちばん長く接する 2 細胞」で仕込む(短い接触の融合は弦が短く、設計上検出できない)
    g = E.seg_boundary_membrane_gap(lab, M, min_len=1)
    j = int(np.argmax(g["length"]))
    target, absorbed = int(g["label_a"][j]), int(g["label_b"][j])
    merged = lab.copy()
    merged[merged == absorbed] = target
    assert E.seg_label_changes(lab, merged)["n_merged"] == 1
    t = E.seg_membrane_chord_score(merged, M, tau=0.3, band=3, min_area=300, min_segment=8)
    assert int(t["label"][0]) == target and t["score"][0] > 0.8, list(zip(t["label"][:3], t["score"][:3]))
    # 他の細胞(輪だけ)は弦より下(穴で除かれる。輪の弧は残りうる = 実測 0.78 vs 弦 0.93、docstring の限界どおり)
    assert t["score"][1] < t["score"][0]
    assert set(t) == {"label", "component", "area", "score", "chord_px", "n_segments", "cy", "cx"}
    with pytest.raises(ValueError, match="seg_membrane_chord_score: membrane shape"):
        E.seg_membrane_chord_score(merged, M[:-1])
    with pytest.raises(ValueError, match="seg_membrane_chord_score: labels"):
        E.seg_membrane_chord_score(merged > 0, M)


# --------------------------------------------------------------------------- #
# 3. ホールドアウト                                                            #
# --------------------------------------------------------------------------- #
def test_holdout_threshold_chooses_on_train_and_reports_on_test():
    rng = np.random.default_rng(0)
    trn, tep = rng.random(200), rng.random(20) + 1.0        # 評価の正例は訓練の負例より必ず上
    r = E.holdout_threshold(np.array([0.95, 0.99]), trn, tep, rng.random(100), target_fpr=0.05)
    assert r["train_fpr"] <= 0.05 and r["test_fpr"] <= 0.1
    assert r["test_auc"] > 0.99 and r["test_tpr"] == 1.0
    assert r["tau"] > np.sort(trn)[-11]                         # 上位 10 個(5 %)だけを陽性に
    assert E.holdout_threshold([1, 2], [1, 2], [1], [1])["test_auc"] == 0.5          # 同点は 0.5
    assert E.holdout_threshold([1], [0], [1], [0], target_fpr=1.0)["train_fpr"] == 1.0
    with pytest.raises(ValueError, match="holdout_threshold: test_neg is empty"):
        E.holdout_threshold([1], [0], [1], [])
    with pytest.raises(ValueError, match="holdout_threshold: target_fpr"):
        E.holdout_threshold([1], [0], [1], [0], target_fpr=2.0)


# --------------------------------------------------------------------------- #
# 4. 台帳と公開経路                                                            #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opsemproof

    assert opsemproof.missing() == []
    assert set(opsemproof.OPSEMPROOF) == set(_OPS) == set(E.__all__) - {"MAX_LABEL_PIXELS", "SPLIT_AXES"}
    assert len(opsemproof.OPSEMPROOF) == 7 and len(opsemproof.categories()) == 4


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs
    import opsemproof

    for name in opsemproof.OPSEMPROOF:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "emproof"]
    assert {r[0] for r in rows} == set(_OPS)
    assert {r[3] for r in rows} == {"image2d", "table", "labels2d"}


def test_the_fuzzer_has_predicates_and_seeds_for_every_sort():
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opsemproof

    gens = cf.make_generators()
    for name, meta in opsemproof.OPSEMPROOF.items():
        assert meta["out"] in cf.TYPE_CHECKS, name
        for s in meta["in"]:
            assert s in cf.TYPE_CHECKS and s in gens, (name, s)
    lab = gens["labels2d"](np.random.default_rng(0)).astype(np.int64)
    img = gens["image2d"](np.random.default_rng(0))
    if img.shape == lab.shape:
        assert cf.TYPE_CHECKS["table"](E.seg_boundary_membrane_gap(lab, img, min_len=1))


def test_op_run_works_for_every_op(world):
    import fullseye as fs

    lab, raw, _M = world
    run = lambda *a, **k: fs.op_run(*a, **k)[0]     # noqa: E731
    M = run("seg_membrane_response", raw)
    assert M.shape == raw.shape
    merged = run("seg_inject_merge", lab, min_area=400)
    cut = run("seg_inject_split", merged, min_area=800)
    assert run("seg_label_changes", lab, cut)["n_merged"] == 1
    assert "score" in run("seg_membrane_chord_score", cut, M, min_area=300)
    assert "gap_fraction" in run("seg_boundary_membrane_gap", cut, M, min_len=10)
    assert run("holdout_threshold", [1.0], [0.0], [1.0], [0.0])["test_auc"] == 1.0


def test_the_family_guide_exists_and_names_its_ops():
    p = ROOT / "docs" / "ops" / "emproof" / "guides" / "emproof.md"
    assert p.exists()
    md = p.read_text(encoding="utf-8")
    assert "```mermaid" in md and "seg_membrane_chord_score" in md and "holdout_threshold" in md
    assert os.path.isdir(ROOT / "docs" / "ops" / "emproof")
