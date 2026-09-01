# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""visiondesign の ground-truth 検証。

この層は「買う前に、そのカメラとレンズでその欠陥が見えるか」を閉形式で答える。
答えが間違っていると **買う判断を間違える**ので、教科書の式と手計算で照合する:

  * 倍率 m = f / (s - f)、視野 = センサ寸法 / m
  * Nyquist の物体側限界 = 2 * 画素ピッチ / m
  * Airy 径 = 2.44 * λ * N_eff、N_eff = N * (1 + |m|)(有限共役の作動 F 値)
  * 律速は 2 つの限界の大きい方 — **どちらが効いているかで対策が逆になる**
    (倍率を上げるのか、絞りを開けるのか)ので、名指しの正しさも固定する。

スケールを 2 通り以上で確認するのは、絶対誤差に隠れたスケールのバグを出すため
(このリポジトリの既存テストに倣う)。
"""
import numpy as np
import pytest

pytest.importorskip("scipy")

import optics
import visiondesign as vd


# --------------------------------------------------------------------------- #
# 1. 幾何 — 教科書の薄レンズ式との一致                                          #
# --------------------------------------------------------------------------- #
def test_geometry_matches_thin_lens_closed_form():
    for f_mm, wd_mm in ((50.0, 500.0), (25.0, 1000.0)):      # 2 スケール
        g = vd.system_geometry(focal_mm=f_mm, working_distance_mm=wd_mm,
                               pixel_pitch_um=3.45, width_px=2448, height_px=2048)
        # m = f / (s - f)
        assert g["magnification"] == pytest.approx(f_mm / (wd_mm - f_mm), rel=1e-9)
        # センサ寸法 = 画素数 * ピッチ
        assert g["sensor_w_mm"] == pytest.approx(2448 * 3.45e-3, rel=1e-12)
        # 視野 = センサ / 倍率、um/px = ピッチ / 倍率
        assert g["fov_w_mm"] == pytest.approx(g["sensor_w_mm"] / g["magnification"], rel=1e-12)
        assert g["um_per_pixel"] == pytest.approx(3.45 / g["magnification"], rel=1e-12)
        # optics.thin_lens と食い違わない(式を二重に持たない、の担保)
        conj = optics.thin_lens(focal_mm=f_mm, object_mm=wd_mm)
        assert g["image_distance_mm"] == pytest.approx(float(conj["image_mm"]), rel=1e-12)


def test_geometry_refuses_a_standoff_inside_the_focal_length():
    """焦点距離以内には実像ができない — 負の視野を返さず明示的に拒否する。"""
    with pytest.raises(ValueError, match="focal_mm"):
        vd.system_geometry(focal_mm=50.0, working_distance_mm=50.0)
    with pytest.raises(ValueError, match="focal_mm"):
        vd.system_geometry(focal_mm=50.0, working_distance_mm=30.0)


def test_geometry_rejects_text_and_bad_pixel_counts():
    """文字列が mm として通ると設計を丸ごと誤る(float('50') は成功してしまう)。"""
    with pytest.raises(ValueError, match="must be a number"):
        vd.system_geometry(focal_mm="50", working_distance_mm=500.0)
    with pytest.raises(ValueError, match="positive integer"):
        vd.system_geometry(width_px=0)
    with pytest.raises(ValueError, match="positive integer"):
        vd.system_geometry(height_px=10.5)


# --------------------------------------------------------------------------- #
# 2. 分解能 — 2 つの限界と「どちらが律速か」                                     #
# --------------------------------------------------------------------------- #
def test_resolving_power_matches_closed_form_both_limits():
    pitch, n, m, lam = 3.45, 8.0, 0.1, 0.55
    r = vd.resolving_power(pitch, n, m, lam)
    n_eff = n * (1.0 + m)
    assert r["working_f_number"] == pytest.approx(n_eff, rel=1e-12)
    assert r["airy_diameter_um"] == pytest.approx(2.44 * lam * n_eff, rel=1e-12)
    assert r["nyquist_object_um"] == pytest.approx(2.0 * pitch / m, rel=1e-12)
    assert r["diffraction_object_um"] == pytest.approx(2.44 * lam * n_eff / m, rel=1e-12)
    assert r["resolution_object_um"] == pytest.approx(
        max(r["nyquist_object_um"], r["diffraction_object_um"]), rel=1e-12)


def test_limiting_factor_is_named_correctly_on_both_sides():
    """律速の名指しが逆だと対策が逆になる(倍率を上げる vs 絞りを開ける)。"""
    # 絞り込むほど回折が効く
    stopped_down = vd.resolving_power(3.45, 22.0, 0.1)
    assert stopped_down["limited_by"] == "diffraction"
    # 開放かつ粗い画素ならサンプリングが効く
    wide_open = vd.resolving_power(10.0, 1.4, 0.1)
    assert wide_open["limited_by"] == "sampling"
    # Airy/画素 の比が判定と整合していること
    assert stopped_down["airy_over_pixel"] > wide_open["airy_over_pixel"]


def test_working_f_number_grows_with_magnification():
    """有限共役では作動 F 値 = N(1+m)。マクロで見落とされる典型。"""
    low = vd.resolving_power(3.45, 8.0, 0.05)
    high = vd.resolving_power(3.45, 8.0, 1.0)
    assert high["working_f_number"] == pytest.approx(16.0, rel=1e-12)
    assert high["working_f_number"] > low["working_f_number"]


# --------------------------------------------------------------------------- #
# 3. 実現可能性 — 判定と、判定の理由                                            #
# --------------------------------------------------------------------------- #
def test_feasibility_verdict_tracks_the_resolution_limit():
    base = dict(focal_mm=50.0, working_distance_mm=150.0, f_number=4.0,
                depth_tolerance_mm=0.05)
    r = vd.system_feasibility(defect_um=5.0, **base)
    assert r["verdict"] == "not_resolvable"
    big = vd.system_feasibility(defect_um=500.0, **base)
    assert big["verdict"] in ("resolvable", "marginal")
    assert big["pixels_across"] > r["pixels_across"]
    # 画素数 = 欠陥サイズ / (um/画素)
    assert big["pixels_across"] == pytest.approx(500.0 / big["um_per_pixel"], rel=1e-12)


def test_depth_tolerance_downgrades_a_resolvable_defect_to_marginal():
    """分解できても、部品が動く量が被写界深度を超えたら "marginal"。

    これが無いと机上では通るのにラインで落ちる — 実務で一番痛い外し方。
    """
    tight = vd.system_feasibility(defect_um=500.0, focal_mm=50.0,
                                  working_distance_mm=150.0, f_number=4.0,
                                  depth_tolerance_mm=0.01)
    loose = vd.system_feasibility(defect_um=500.0, focal_mm=50.0,
                                  working_distance_mm=150.0, f_number=4.0,
                                  depth_tolerance_mm=1000.0)
    assert tight["verdict"] == "resolvable" and tight["depth_of_field_ok"]
    assert loose["verdict"] == "marginal" and not loose["depth_of_field_ok"]
    assert tight["depth_of_field_mm"] == pytest.approx(loose["depth_of_field_mm"])


def test_corner_illumination_is_a_falloff_not_a_gain():
    r = vd.system_feasibility(defect_um=100.0)
    assert 0.0 < r["corner_illumination"] <= 1.0
    # 視野が広い(半画角が大きい)ほど角は暗い
    wide = vd.system_feasibility(defect_um=100.0, focal_mm=12.0,
                                 working_distance_mm=300.0)
    narrow = vd.system_feasibility(defect_um=100.0, focal_mm=100.0,
                                   working_distance_mm=300.0)
    assert wide["half_angle_deg"] > narrow["half_angle_deg"]
    assert wide["corner_illumination"] < narrow["corner_illumination"]


# --------------------------------------------------------------------------- #
# 4. 検出限界の掃引                                                             #
# --------------------------------------------------------------------------- #
def test_detectability_limit_is_monotone_and_reports_none_honestly():
    grid = [5.0, 10.0, 50.0, 100.0, 500.0, 2000.0]
    d = vd.detectability_limit(grid, focal_mm=50.0, working_distance_mm=150.0,
                               f_number=4.0, depth_tolerance_mm=0.05)
    assert [t["defect_um"] for t in d["table"]] == sorted(grid)   # 昇順で返す
    px = [t["pixels_across"] for t in d["table"]]
    assert px == sorted(px), "欠陥が大きいほど画素数が増えるはず"
    if d["limit_um"] is not None:
        # 限界より小さいものは 1 つも resolvable でない
        below = [t for t in d["table"] if t["defect_um"] < d["limit_um"]]
        assert all(t["verdict"] != "resolvable" for t in below)
    # どれも届かない設計では None を返す(例外ではない = それも答え)
    impossible = vd.detectability_limit([1.0, 2.0], focal_mm=50.0,
                                        working_distance_mm=5000.0, f_number=22.0)
    assert impossible["limit_um"] is None


def test_detectability_limit_rejects_a_degenerate_grid():
    with pytest.raises(ValueError, match="non-empty"):
        vd.detectability_limit([])
    with pytest.raises(ValueError, match="positive and finite"):
        vd.detectability_limit([10.0, -1.0])
    with pytest.raises(ValueError, match="positive and finite"):
        vd.detectability_limit([10.0, np.inf])


# --------------------------------------------------------------------------- #
# 5. 撮像シミュレーション                                                       #
# --------------------------------------------------------------------------- #
def test_image_formation_preserves_shape_range_and_only_blurs():
    rng = np.random.default_rng(0)
    img = np.zeros((64, 64))
    img[28:36, 20:44] = 1.0
    cap = vd.image_formation(img, f_number=8.0, pixel_pitch_um=3.45, vignetting=False)
    assert cap.shape == img.shape
    assert cap.dtype == np.float64
    assert 0.0 <= cap.min() and cap.max() <= 1.0
    # ぼけ = **勾配の最大値**が下がる。総量(総変動)ではない ―― 単調な段差を
    # ぼかしても総変動は保存されるので、総量で書くと「ぼけの検査」にならない。
    # 実際この行は総量で書かれていて、2026-09 まで通っていたのは周辺光量落ちが
    # 画像を暗くしていたから(その周辺光量落ち自体がバグだった)。vignetting を
    # 切ると 16.000000000000032 対 16.0 で、ぼけは総変動を 1 ミリも減らしていない。
    assert np.abs(np.diff(cap, axis=1)).max() < np.abs(np.diff(img, axis=1)).max()
    # 決定的(乱数を含まない)
    assert np.array_equal(cap, vd.image_formation(img, f_number=8.0,
                                                  pixel_pitch_um=3.45,
                                                  vignetting=False))
    _ = rng                                                # 乱数は使わない契約


def test_more_defocus_blurs_more_and_vignetting_darkens_the_corner():
    img = np.zeros((48, 48))
    img[20:28, 20:28] = 1.0
    sharp = vd.image_formation(img, defocus_px=0.0, vignetting=False)
    soft = vd.image_formation(img, defocus_px=3.0, vignetting=False)
    assert soft.max() < sharp.max(), "デフォーカスでピークが下がるはず"
    flat = np.ones((48, 48))
    vign = vd.image_formation(flat, vignetting=True, defocus_px=0.0,
                              image_distance_mm=2.0)     # わざと短い像距離 = 広い画角
    novign = vd.image_formation(flat, vignetting=False, defocus_px=0.0)
    assert vign[0, 0] < vign[24, 24], "角が中心より暗いこと"
    assert novign[0, 0] == pytest.approx(novign[24, 24], rel=0.05)


def test_vignetting_is_physical_not_normalised_to_the_array_corner():
    """cos^4 は**画角**で決まる ―― 配列の角ではない。

    2026-09 まではここが正規化半径で、配列の角が常に 45 度扱い(0.2500 固定)
    だった。レンズにも画素ピッチにも切り出しの大きさにも反応せず、例外も出ない。
    この検査は 2 つを縛る: (1) 全画面の角が ``system_feasibility`` の
    ``corner_illumination`` と一致すること(**唯一の真実源にする**)、
    (2) 同じ系の小さな切り出しは、ほとんど落ちないこと。
    """
    geo = vd.system_geometry(focal_mm=35.0, working_distance_mm=200.0,
                             pixel_pitch_um=3.45, width_px=2448, height_px=2048)
    feas = vd.system_feasibility(60.0, 35.0, 200.0, 3.45, 4.0, 2448, 2048)
    kw = dict(f_number=4.0, pixel_pitch_um=3.45, vignetting=True,
              image_distance_mm=geo["image_distance_mm"])

    full = vd.image_formation(np.ones((2048, 2448)), **kw)
    # 画素中心は感光面の端より半画素内側なので、厳密一致ではなく 1e-4 で縛る。
    assert full[0, 0] == pytest.approx(feas["corner_illumination"], abs=1e-4)
    assert full[0, 0] == pytest.approx(0.9671, abs=1e-3), "旧実装の 0.2500 に戻らないこと"

    tile = vd.image_formation(np.ones((232, 232)), **kw)
    assert tile[0, 0] > 0.999, "小さな切り出しはほとんど落ちない(旧実装は 0.2500)"

    # 像距離を変えれば答えが変わること = 物理量に反応している証拠。
    # 232x232 の角は光軸から 0.566 mm なので、像距離 2 mm では画角 15.8 度 →
    # cos^4 = 0.858。旧実装ならどちらも 0.2500 で、区別がつかなかった。
    near = vd.image_formation(np.ones((232, 232)), f_number=4.0, pixel_pitch_um=3.45,
                              vignetting=True, image_distance_mm=2.0)
    assert near[0, 0] == pytest.approx(0.858, abs=0.01)
    assert near[0, 0] < tile[0, 0] - 0.1, "像距離が短いほど強く落ちること"

    # 画素ピッチを変えても答えが変わる(旧実装はここにも反応しなかった)
    coarse = vd.image_formation(np.ones((232, 232)), f_number=4.0, pixel_pitch_um=13.8,
                                vignetting=True, image_distance_mm=geo["image_distance_mm"])
    assert coarse[0, 0] < tile[0, 0], "同じ画素数でもピッチが粗いほど広い画角"


def test_vignetting_without_image_distance_fails_closed():
    """既定値を置かない ―― 置けばまた「もっともらしい嘘」に戻るため。"""
    with pytest.raises(ValueError, match="image_distance_mm"):
        vd.image_formation(np.ones((8, 8)), vignetting=True)


def test_image_formation_fails_closed_on_bad_input():
    with pytest.raises(ValueError, match="2-D"):
        vd.image_formation(np.zeros((4, 4, 4)))
    with pytest.raises(ValueError, match="non-finite"):
        vd.image_formation(np.full((8, 8), np.nan))
    with pytest.raises(ValueError, match="empty"):
        vd.image_formation(np.zeros((0, 8)))
    with pytest.raises(ValueError, match="defocus_px"):
        vd.image_formation(np.zeros((8, 8)), defocus_px=-1.0)
    with pytest.raises(ValueError, match="must be a number"):
        vd.image_formation(np.zeros((8, 8)), f_number="8")
