# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""visionlab(マシンビジョン仮想環境)の契約テスト。

この層が出す数字は **部品を買う判断**に使われる。だから固定すべきは絵ではなく、
判断を誤らせない性質:

  1. **物理寸法が単一の換算点を通る** — 同じ 100 µm の欠陥が、系を変えれば
     別の画素数になること。ここが狂うと設計の比較が意味を失う。
  2. **光学の限界と実測の検出限界を別々に出す** — 前者は「原理的に情報があるか」、
     後者は「実際に見つかるか」。混ぜると、レンズを買うべきかアルゴリズムを
     直すべきかが分からなくなる。
  3. **落とした理由を混ぜない** — 「描けなかった」と「検査器が壊れた」を検出率
     0% に混ぜると、設計やアルゴリズムを不当に責める。
  4. **評価をハックできない** — 全画素を欠陥と答える検査器が高得点にならないこと。

以下の項目は敵対的検証で**実際に見つけたバグ**の回帰である:
  * ``VisionSystem(focal_mm="50")`` が通っていた(``float("50")`` が成功するため)
  * 形の違うマスクを返す検査器で掃引全体が ValueError で停止していた
"""
import numpy as np
import pytest

pytest.importorskip("scipy")

import visionlab as vl


def _sys(**kw):
    base = dict(focal_mm=50.0, working_distance_mm=300.0, pixel_pitch_um=3.45,
                width_px=512, height_px=512, f_number=5.6, depth_tolerance_mm=1.0)
    base.update(kw)
    return vl.VisionSystem(**base)


# --------------------------------------------------------------------------- #
# 1. 物理寸法の換算(設計と生成を繋ぐ唯一の点)                                  #
# --------------------------------------------------------------------------- #
def test_the_same_defect_is_different_pixels_on_different_systems():
    """同じ 100 µm が、系を変えれば別の画素数になる — これが比較の土台。"""
    near = _sys(working_distance_mm=150.0)
    far = _sys(working_distance_mm=900.0)
    assert near.px_for_um(100.0) > far.px_for_um(100.0)
    # 換算は um_per_pixel の逆数そのもの(二重定義を持たない)
    for s in (near, far):
        assert s.px_for_um(100.0) == pytest.approx(100.0 / s.um_per_pixel(), rel=1e-12)


def test_rendered_defect_measures_back_to_what_was_ordered():
    """注文した物理寸法が、生成後に測り返して概ね一致すること。"""
    s = _sys()
    _, mask, meta = vl.render_part(s, defect_um=400.0, kind="blob", seed=0)
    assert meta["defect_px"] == pytest.approx(400.0 / s.um_per_pixel(), rel=1e-12)
    # blob は直径を注文しているので、長軸が概ねその画素数
    assert meta["measured"]["major_axis_px"] == pytest.approx(meta["defect_px"], rel=0.5)
    assert meta["measured"]["major_axis_um"] == pytest.approx(
        meta["measured"]["major_axis_px"] * s.um_per_pixel(), rel=1e-9)


def test_sub_pixel_defect_is_refused_with_the_reason():
    """1 画素未満は描けない — それ自体が設計の答えなので、理由を告げて止める。"""
    s = _sys(working_distance_mm=2000.0)
    with pytest.raises(ValueError, match="below one pixel"):
        vl.render_part(s, defect_um=1.0)


def test_mask_is_independent_of_the_capture():
    """撮像でぼけても正解は動かない(検出率の基準として使えること)。"""
    s = _sys()
    _, m_sharp, _ = vl.render_part(s, defect_um=300.0, defocus_px=0.0, seed=1)
    _, m_blur, _ = vl.render_part(s, defect_um=300.0, defocus_px=4.0, seed=1)
    assert np.array_equal(m_sharp, m_blur)


# --------------------------------------------------------------------------- #
# 2. 光学の限界と実測の検出限界は別物                                            #
# --------------------------------------------------------------------------- #
def test_sweep_reports_both_limits_separately():
    s = _sys()
    sw = vl.inspection_sweep(s, [100.0, 200.0, 400.0], seeds=3)
    assert "optical_limit_um" in sw and "detection_limit_um" in sw
    assert sw["limited_by"] in ("diffraction", "sampling")
    for row in sw["table"]:
        assert row["optical_verdict"] in ("resolvable", "marginal", "not_resolvable")
    txt = vl.detection_report(sw)
    assert "optical limit" in txt and "detection limit" in txt


def test_detection_rate_is_monotone_in_defect_size():
    """大きい欠陥ほど見つかる — 崩れていたら評価か生成が壊れている。"""
    s = _sys()
    sw = vl.inspection_sweep(s, [100.0, 200.0, 400.0], seeds=3)
    rates = [r["detection_rate"] for r in sw["table"] if r["detection_rate"] is not None]
    assert rates == sorted(rates), rates


def test_sweep_is_deterministic():
    s = _sys()
    a = vl.inspection_sweep(s, [200.0], seeds=3)
    b = vl.inspection_sweep(s, [200.0], seeds=3)
    assert a["table"][0]["mean_iou"] == b["table"][0]["mean_iou"]
    assert a["detection_limit_um"] == b["detection_limit_um"]


# --------------------------------------------------------------------------- #
# 3. 落とした理由を混ぜない(敵対的検証で見つけた 2 件の回帰)                     #
# --------------------------------------------------------------------------- #
def test_unrenderable_and_detector_failure_are_counted_separately():
    """どちらも「検出率 0%」に混ぜない — 責任の所在が変わってしまう。"""
    s = _sys(working_distance_mm=2000.0)
    tiny = vl.inspection_sweep(s, [1.0], seeds=3)["table"][0]
    assert tiny["unrenderable"] == 3 and tiny["detector_failed"] == 0
    assert tiny["detection_rate"] is None, "描けなかったものを 0% にしている"

    s2 = _sys()
    broken = vl.inspection_sweep(s2, [200.0], seeds=3,
                                 detector=lambda img: np.zeros((3, 3), bool))["table"][0]
    assert broken["detector_failed"] == 3 and broken["unrenderable"] == 0
    assert broken["detection_rate"] is None, "検査器の失敗を設計のせいにしている"


def test_a_detector_that_raises_does_not_stop_the_sweep():
    """外から渡される任意の関数なので、落ちても掃引は続くこと。"""
    def boom(img):
        raise RuntimeError("boom")

    sw = vl.inspection_sweep(_sys(), [200.0], seeds=2, detector=boom)
    assert sw["table"][0]["detector_failed"] == 2
    assert "detector errors" in vl.detection_report(sw)


def test_string_arguments_are_refused_by_the_system_object_too():
    """float("50") が成功するので、器の側でも文字列を弾く必要がある。"""
    for kw in ({"focal_mm": "50"}, {"working_distance_mm": "300"},
               {"pixel_pitch_um": "3.45"}, {"f_number": "5.6"}):
        with pytest.raises(ValueError, match="must be a number"):
            _sys(**kw)
    with pytest.raises(ValueError, match="must be an integer"):
        _sys(width_px=10.5)


# --------------------------------------------------------------------------- #
# 4. 評価のハッキングに強いこと                                                  #
# --------------------------------------------------------------------------- #
def test_a_detector_that_flags_everything_scores_poorly():
    """全部欠陥と言えば必ず当たる — IoU ならそれが低得点になること。"""
    sw = vl.inspection_sweep(_sys(), [200.0], seeds=3,
                             detector=lambda img: np.ones(img.shape, bool))
    assert sw["table"][0]["mean_iou"] < 0.1


def test_a_detector_that_flags_nothing_scores_zero():
    sw = vl.inspection_sweep(_sys(), [200.0], seeds=3,
                             detector=lambda img: np.zeros(img.shape, bool))
    assert sw["table"][0]["mean_iou"] == 0.0
    assert sw["table"][0]["detection_rate"] == 0.0


# --------------------------------------------------------------------------- #
# 5. 入口の検証                                                                 #
# --------------------------------------------------------------------------- #
def test_bad_sweep_arguments_fail_closed():
    s = _sys()
    with pytest.raises(ValueError, match="non-empty"):
        vl.inspection_sweep(s, [])
    with pytest.raises(ValueError, match="positive and finite"):
        vl.inspection_sweep(s, [100.0, -1.0])
    with pytest.raises(ValueError, match="seeds"):
        vl.inspection_sweep(s, [100.0], seeds=0)
    with pytest.raises(ValueError, match="kind"):
        vl.render_part(s, kind="dent")


def test_all_defect_kinds_render_and_stay_in_range():
    s = _sys()
    for kind in ("scratch", "crack", "pits", "blob"):
        img, mask, meta = vl.render_part(s, defect_um=300.0, kind=kind, seed=0)
        assert img.shape == mask.shape and mask.any()
        assert 0.0 <= img.min() and img.max() <= 1.0
        assert meta["kind"] == kind
