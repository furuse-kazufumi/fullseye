"""fast.py の parity ゲート — 「速いが違う」を作らないための自動化。

``tests/test_accel*.py`` が GPU twin に対してやっていることの CPU 版。``fast.FAST``
に載っている **すべての** twin について、registry の core op と 5 つの (a,b) ×
6 枚の画像で突き合わせ、interior の max-abs(二値出力は不一致率)が許容を超えたら
落ちる。落ちるべき twin は表に載せず ``fast.NOT_LISTED`` に実測値つきで残す。
"""
from __future__ import annotations

import numpy as np
import pytest

import fast
import ops

pytestmark = pytest.mark.skipif(not fast._HAS_CV2, reason="OpenCV not installed")

# 表が痩せていたら(cv2 が中途半端に居る等)テストが「全部 pass」で緑になってしまう。
MIN_TWINS = 30


def test_table_is_not_empty_and_names_are_real_ops():
    assert len(fast.FAST) >= MIN_TWINS, "fast.FAST が %d 件しかない" % len(fast.FAST)
    missing = sorted(n for n in fast.FAST if n not in ops.RT)
    assert not missing, "registry に無い名前が表に載っている: %s" % missing


@pytest.mark.parametrize("name", sorted(fast.FAST))
def test_twin_is_faithful(name):
    row = fast.parity(name)[0]
    assert "error" not in row, "%s: %s" % (name, row.get("error"))
    assert row["interior"] <= row["tol"], (
        "%s: interior=%.3e > tol=%.3e (full=%.3e, binary=%s) — "
        "faithful でない twin は FAST に載せず fast.NOT_LISTED に実測値を書くこと"
        % (name, row["interior"], row["tol"], row["full"], row["binary"]))


def test_gate_runs_for_every_entry_at_once():
    rows = fast.parity()
    assert len(rows) == len(fast.FAST)
    bad = [(r["name"], r["interior"], r["tol"]) for r in rows if not r["ok"]]
    assert not bad, "faithful でない twin: %s" % bad
    assert sum(1 for r in rows if r["ok"]) >= MIN_TWINS


def test_binary_twins_are_held_to_zero_mismatch():
    """二値(region)を返す twin は 5e-3 ではなく **不一致率 0** が条件。"""
    rows = {r["name"]: r for r in fast.parity()}
    for name in fast.FAST:
        op = ops._BY_NAME[name]
        if op.out_sort == "region" or name in fast._BINARY_OUT:
            assert rows[name]["tol"] == 0.0
            assert rows[name]["interior"] == 0.0


def test_declared_dtype_policy_matches_the_uint8_table():
    for name, twin in fast.FAST.items():
        has_u8 = name in fast._U8_KERNELS
        assert (twin.dtype_policy == "f64+u8") == has_u8, (
            "%s: dtype_policy=%r but uint8 kernel %s"
            % (name, twin.dtype_policy, "present" if has_u8 else "absent"))
        assert twin.note, "%s: note が空(なぜ載っているのかを書く)" % name


def test_twin_preserves_dtype_shape_and_range():
    img = fast.parity_images()[0]
    for name in sorted(fast.FAST):
        ref = np.asarray(ops.RT[name](img.copy(), 0.5, 0.4))
        got = np.asarray(fast.apply_fast(name, img.copy(), 0.5, 0.4))
        assert got.dtype == np.float64, name
        assert got.shape == ref.shape, name
        assert np.isfinite(got).all(), name
        assert got.min() >= -1e-12 and got.max() <= 1.0 + 1e-12, name


def test_unsupported_input_raises_fastunsupported_not_a_wrong_answer():
    """契約外の入力(uint8 / 3-D / 空)は「静かに違う答え」ではなく明示的な合図。"""
    for bad in (np.zeros((8, 8), np.uint8), np.zeros((8, 8, 3)), np.zeros((0, 0))):
        with pytest.raises(fast.FastUnsupported):
            fast.apply_fast("gaussian", bad, 0.5, 0.5)


def test_unknown_name_raises_keyerror():
    with pytest.raises(KeyError):
        fast.apply_fast("no_such_op_at_all", np.zeros((8, 8)), 0.5, 0.5)
    with pytest.raises(KeyError):
        fast.apply_uint8("sobel_mag", np.zeros((8, 8), np.uint8), 0.5, 0.5)


@pytest.mark.parametrize("name", sorted(fast._U8_KERNELS))
def test_uint8_kernel_matches_core_to_one_255th(name):
    """uint8 の整数カーネルは float64 の core と 1/255 まで一致する。

    median / モルフォロジは順序統計なので量子化後の入力に対して **厳密**、
    gaussian / box は整数丸めで最大 0.5/255。ここでは合わせて 1/255 を上限に取る。
    """
    core = ops.RT[name]
    for img in fast.parity_images():
        u8 = np.round(np.clip(img, 0, 1) * 255.0).astype(np.uint8)
        f64 = u8.astype(np.float64) / 255.0
        for a, b in fast.PARITY_AB:
            got = fast.apply_uint8(name, u8, a, b)
            assert got.dtype == np.uint8 and got.shape == u8.shape
            ref = np.clip(np.asarray(core(f64.copy(), a, b), np.float64), 0, 1)
            d = float(np.max(np.abs(ref - got.astype(np.float64) / 255.0)))
            assert d <= 1.0 / 255.0 + 1e-12, "%s a=%.2f b=%.2f: %.4f" % (name, a, b, d)


def test_not_listed_documents_the_rejects():
    """落とした候補は消さずに理由と実測値を残す(「速いが違う」を作らない規律)。"""
    for key in ("clahe", "bilateral", "rotate_img", "equalize", "otsu", "dyn_threshold",
                "edges_image"):
        assert key in fast.NOT_LISTED and fast.NOT_LISTED[key]
        assert key not in fast.FAST
