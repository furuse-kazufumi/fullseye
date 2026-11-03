"""The typed-pipeline engine: decode / apply / clip semantics / genome plumbing."""
from __future__ import annotations

import numpy as np

import ops


def _img(n=32):
    return np.clip(np.random.default_rng(0).random((n, n)), 0, 1)


def test_decode_emits_one_stage_per_slot():
    g = np.random.default_rng(0).random(ops.GENOME_LEN)
    stages = ops.decode(g, ops.IMAGE)
    assert len(stages) == ops.N_SLOTS


def test_decode_threads_sort_through_stages():
    # every stage's declared sort must be a sort some op accepts as input
    g = np.random.default_rng(3).random(ops.GENOME_LEN)
    for st in ops.decode(g, ops.IMAGE):
        assert st.sort in {"image", "region", "feature", "contour", "color", "volume", "any", "match"}


def test_decode_is_deterministic():
    g = np.random.default_rng(1).random(ops.GENOME_LEN)
    assert [s.op for s in ops.decode(g)] == [s.op for s in ops.decode(g)]


def _same(a, b) -> bool:
    """入れ子(dict / list / tuple / ndarray / 数)まで含めて値が一致するか。

    ``run_genome`` は画像だけでなく特徴量や輪郭の dict(``{"shape", "cs"}``)も返す。
    ``np.array_equal(np.asarray(a), np.asarray(b))`` は dict を 0 次元の object 配列にし、
    中の配列の比較で「真偽値が曖昧」の ValueError を投げる(2026-11-04、master の py3.12/3.14。
    optional の backend が無い版では登録表が小さく、同じ seed でも輪郭を返す鎖が選ばれた)。
    """
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return isinstance(b, (list, tuple)) and len(a) == len(b) and all(map(_same, a, b))
    return np.array_equal(np.asarray(a), np.asarray(b), equal_nan=True)


def test_run_genome_is_deterministic():
    g = np.random.default_rng(2).random(ops.GENOME_LEN)
    img = _img()
    a = ops.run_genome(g, img.copy())
    b = ops.run_genome(g, img.copy())
    assert _same(a, b)


def test_run_genome_is_deterministic_for_every_kind_of_output():
    """出力の種類(画像・特徴量・輪郭の dict …)によらず決定的であること。

    seed 1 本だと、どの種類の出力を試すかが登録表の大きさ(= 入っている backend)で変わり、
    py3.11 では画像、py3.12 では輪郭の dict、と版ごとに別のものを検査していた。
    seed を 40 本回し、画像以外の出力も少なくとも 1 本は通ることを確かめる。
    """
    img = _img()
    kinds = set()
    for seed in range(40):
        g = np.random.default_rng(seed).random(ops.GENOME_LEN)
        a = ops.run_genome(g, img.copy())
        b = ops.run_genome(g, img.copy())
        assert _same(a, b), (seed, ops.pipeline_str(g))
        kinds.add("image" if isinstance(a, np.ndarray) and a.ndim == 2 else type(a).__name__)
    assert len(kinds) >= 2, kinds


def test_apply_genome_always_returns_2d_image():
    img = _img()
    for seed in range(20):
        g = np.random.default_rng(seed).random(ops.GENOME_LEN)
        out = ops.apply_genome(g, img)
        assert isinstance(out, np.ndarray) and out.ndim == 2


def test_apply_clips_image_results_to_unit_range():
    img = _img()
    for seed in range(30):
        g = np.random.default_rng(seed).random(ops.GENOME_LEN)
        out = ops.run_genome(g, img)
        if isinstance(out, np.ndarray) and out.ndim == 2:
            assert out.min() >= -1e-9 and out.max() <= 1 + 1e-9


def test_pipeline_str_roundtrips_op_names():
    g = np.random.default_rng(5).random(ops.GENOME_LEN)
    s = ops.pipeline_str(g)
    assert isinstance(s, str) and (s == "identity" or "->" in s or "(" in s)


def test_stage_builder_uses_declared_in_sort():
    st = ops.stage("otsu", 0.5, 0.0)
    assert st.op == "otsu" and st.sort == "image"
