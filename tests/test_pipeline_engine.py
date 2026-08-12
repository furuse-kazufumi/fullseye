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


def test_run_genome_is_deterministic():
    g = np.random.default_rng(2).random(ops.GENOME_LEN)
    img = _img()
    a = ops.run_genome(g, img.copy())
    b = ops.run_genome(g, img.copy())
    assert np.array_equal(np.asarray(a), np.asarray(b))


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
