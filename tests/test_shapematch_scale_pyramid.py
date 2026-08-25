"""スケール系のピラミッド化と、勾配の符号(HALCON metric)の回帰テスト。

この回で直したこと:

1. find_scaled_shape_model / find_aniso_shape_model / find_scaled_shape_models /
   find_aniso_shape_models が **点だけ伸縮した dict** を組んでいたため、
   ``template`` を持たず必ず平坦走査へ落ちていた。テンプレートを zoom して
   モデルを作り直す(= HALCON の作り方)ようにして、全部ピラミッドに乗せた
2. 異方 scale で **勾配の向きが元のまま** だった(座標を A で写すと法線は A^-T)
3. find_shape_models(複数インスタンス)も粗密探索にした
4. find_aniso_shape_models が **scale を一切見ずに** 素通ししていた
5. スコアが点ごとに |cos| を取っていた(= HALCON の ignore_local_polarity)。
   向きが乱数でも E[|cos|] = 2/pi = 0.637 の下駄が残り、雑音の強い画像では
   min_score が何も棄却できなかった。既定を符号つき(use_polarity)に戻し、
   反転許容は metric で選ぶ
"""
import numpy as np
import pytest
from scipy import ndimage

import shapematch as S


def _cross(n=40):
    t = np.zeros((n, n))
    t[n // 2 - 3:n // 2 + 3, 4:n - 4] = 1.0
    t[4:n - 4, n // 2 - 3:n // 2 + 3] = 1.0
    return ndimage.gaussian_filter(t, 1.0)


@pytest.fixture
def tpl():
    return _cross()


def _scene(positions, tpl, sd=0.02, seed=0, size=256, amp=1.0):
    rng = np.random.default_rng(seed)
    img = rng.normal(0.5, sd, (size, size))
    t = tpl * amp
    h, w = t.shape
    for (r, c) in positions:
        img[r - h // 2:r - h // 2 + h, c - w // 2:c - w // 2 + w] += t
    return img


# ── 1. zoom したモデルはピラミッドに乗る ──────────────────────────────────── #
@pytest.mark.parametrize("s", [0.8, 1.0, 1.25])
def test_zoom_model_keeps_a_template_so_it_can_be_pyramided(tpl, s):
    z = S.zoom_model(S.create_shape_model(tpl), s)
    assert z["template"].shape == z["shape"], "shape と template が食い違うと平坦走査へ落ちる"
    assert len(S.build_model_pyramid(z)) > 1


def test_zoom_model_drops_a_scale_that_is_too_small(tpl):
    assert S.zoom_model(S.create_shape_model(tpl), 0.05) is None


# ── 2. scale 系が実際にピラミッドを使い、真の scale を当てる ──────────────── #
@pytest.mark.parametrize("true_s", [0.8, 1.0, 1.25])
def test_find_scaled_shape_model_is_on_the_pyramid(tpl, true_s):
    img = _scene([(128, 128)], ndimage.zoom(tpl, true_s, order=1))
    r = S.find_scaled_shape_model(S.create_shape_model(tpl), img)
    assert r["levels"] > 1, "平坦走査へ落ちている"
    assert r["scale"] == true_s
    assert abs(r["row"] - 128) <= 2 and abs(r["col"] - 128) <= 2
    assert r["score"] > 0.85


def test_find_aniso_shape_model_picks_the_anisotropic_scale(tpl):
    img = _scene([(128, 128)], ndimage.zoom(tpl, (1.1, 0.9), order=1))
    r = S.find_aniso_shape_model(S.create_shape_model(tpl), img)
    assert (r["scale_row"], r["scale_col"]) == (1.1, 0.9)
    assert r["levels"] > 1
    assert abs(r["row"] - 128) <= 2 and abs(r["col"] - 128) <= 2


def test_find_aniso_shape_models_actually_varies_the_scale(tpl):
    # 以前は find_shape_models を素通ししており、scale の鍵すら返らなかった。
    img = _scene([(80, 80), (170, 170)], ndimage.zoom(tpl, (1.1, 0.9), order=1))
    r = S.find_aniso_shape_models(S.create_shape_model(tpl), img, max_matches=4)
    assert (r["scale_row"], r["scale_col"]) == (1.1, 0.9)
    assert r["num"] == 2


# ── 3. 複数インスタンスの粗密探索は平坦走査と同じ答えを出す ────────────────── #
@pytest.mark.parametrize("positions", [
    [(60, 60), (60, 190), (190, 60), (190, 190)],
    [(128, 128)],
    [(30, 128), (220, 128)],
])
def test_find_shape_models_pyramid_agrees_with_the_flat_scan(tpl, positions):
    m = S.create_shape_model(tpl)
    img = _scene(positions, tpl)
    a = S.find_shape_models(m, img, min_score=0.5, max_matches=6)
    b = S.find_shape_models(m, img, min_score=0.5, max_matches=6, num_levels=0)
    assert a["levels"] > 1
    assert a["num"] == b["num"] == len(positions)
    for got in (a, b):
        found = sorted((x["row"], x["col"]) for x in got["matches"])
        for (r, c), (gr, gc) in zip(sorted(positions), found):
            assert abs(gr - r) <= 3 and abs(gc - c) <= 3


# ── 4. 勾配の符号(metric) ────────────────────────────────────────────────── #
def test_default_metric_has_no_noise_floor(tpl):
    """**雑音だけの画像で下駄を履かない。** 点ごとに |cos| を取っていた頃は
    雑音 sd 0.15 で 0.57、sd 0.30 で 0.65 出ていた(min_score 0.5 が無力)。"""
    m = S.create_shape_model(tpl)
    for sd in (0.15, 0.30):
        r = S.find_shape_model(m, _scene([], tpl, sd=sd, seed=7))
        assert r["score"] < 0.3, f"雑音 sd={sd} で {r['score']:.3f} の下駄"
        assert not r["found"]


def test_local_polarity_metric_still_shows_the_floor(tpl):
    """緩い metric を選んだ時は下駄が戻る。**選べることを確かめる**テスト。"""
    m = S.create_shape_model(tpl, metric="ignore_local_polarity")
    r = S.find_shape_model(m, _scene([], tpl, sd=0.15, seed=7))
    assert r["score"] > 0.4


def test_object_beats_noise_by_a_wide_margin(tpl):
    m = S.create_shape_model(tpl)
    r = S.find_shape_model(m, _scene([(170, 170)], tpl, sd=0.30, seed=7))
    assert (r["row"], r["col"]) == (170, 170)
    assert r["score"] > 0.6      # 同じ雑音での下駄は 0.11

def test_polarity_inversion_is_a_choice_not_an_accident(tpl):
    """明暗が反転した物体: 既定(use_polarity)は一致させない = HALCON と同じ。
    反転を許したいなら ignore_global_polarity を選ぶ。"""
    img = _scene([(170, 170)], tpl, amp=-1.0)
    strict = S.find_shape_model(S.create_shape_model(tpl), img)
    loose = S.find_shape_model(
        S.create_shape_model(tpl, metric="ignore_global_polarity"), img)
    assert not strict["found"]
    assert loose["found"] and (loose["row"], loose["col"]) == (170, 170)


def test_metric_survives_zoom_and_the_pyramid(tpl):
    m = S.create_shape_model(tpl, metric="ignore_global_polarity")
    assert S.zoom_model(m, 0.8)["metric"] == "ignore_global_polarity"
    assert all(x["metric"] == "ignore_global_polarity"
               for x in S.build_model_pyramid(m))


def test_no_false_positives_on_pure_noise(tpl):
    """以前はこの画像で 10 件出ていた。"""
    r = S.find_shape_models(S.create_shape_model(tpl),
                            _scene([], tpl, sd=0.15, seed=3),
                            min_score=0.5, max_matches=8)
    assert r["num"] == 0


def test_all_instances_survive_in_a_noisy_scene(tpl):
    pos = [(60, 60), (60, 190), (190, 60), (190, 190)]
    r = S.find_shape_models(S.create_shape_model(tpl),
                            _scene(pos, tpl, sd=0.15, seed=3),
                            min_score=0.5, max_matches=8)
    assert r["num"] == 4
