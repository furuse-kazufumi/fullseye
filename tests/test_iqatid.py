# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""iqatid の門: 順位相関の閉形式(単調 1・反転 −1・同順位ありの手計算値・第 2 実装 graphinv._rank との一致)、limited-range Y′ の端点
16 / 235 と 1.321 dB、PSNR の +1 LSB = 48.13 dB、SSIM 恒等 1、公表表 14 本と PSNR 0.640、台帳の fail-closed(行数・名前・集合・MOS 範囲)、
評価器の fail-closed(nan を返す fn、未知の luma、空の subset)。実データ(TID2013)は環境変数 FULLSEYE_TID2013_DATA があるときだけ:
先頭 100 組の行ごと PSNR ≤ 0.0005 dB・SSIM ≤ 0.0001、3000 組の作者値から公表の順位相関を ≤ 0.001 で再現。
examples/poc_iqa_tid2013.py の門を単体テストにしたもの。画像と MOS は repo に入れない(教育・研究目的のみの配布条件)。"""
import math
import os
import sys
from pathlib import Path

import numpy as np
import pytest

import iqatid as IQ  # noqa: E402
import imgmetrics as IM  # noqa: E402

DATA = IQ.tid2013_root()
needs_data = pytest.mark.skipif(DATA is None, reason="FULLSEYE_TID2013_DATA (extracted TID2013) is not set")


# ── 順位相関 ───────────────────────────────────────────────────────────────────
def test_rank_data_average_ranks_known_example():
    r = IQ.rank_data([10, 20, 20, 30])
    assert r.tolist() == [1.0, 2.5, 2.5, 4.0]
    r2 = IQ.rank_data([3, 3, 3])
    assert r2.tolist() == [2.0, 2.0, 2.0]


def test_rank_correlations_closed_form_monotone_and_reversed():
    x = np.arange(50, dtype=float)
    assert abs(IQ.rank_spearman(x, np.exp(x / 10)) - 1.0) < 1e-12
    assert abs(IQ.rank_spearman(x, -x ** 3) + 1.0) < 1e-12
    assert abs(IQ.rank_kendall_b(x, np.exp(x / 10)) - 1.0) < 1e-12
    assert abs(IQ.rank_kendall_b(x, -x ** 3) + 1.0) < 1e-12


def test_rank_correlations_hand_computed_with_ties():
    # x = [1,2,3,4,5], y = [1,2,2,4,3]: 平均順位 y = [1, 2.5, 2.5, 5, 4]
    # Spearman = Pearson(順位): ρ = Σ(rx−3)(ry−3) / sqrt(Σ(rx−3)² Σ(ry−3)²) = (4+0.5·... ) 手計算:
    #   rx−3 = [−2,−1,0,1,2], ry−3 = [−2,−0.5,−0.5,2,1] → Σ積 = 4+0.5+0+2+2 = 8.5; Σ(rx−3)² = 10; Σ(ry−3)² = 4+0.25+0.25+4+1 = 9.5
    #   ρ = 8.5 / sqrt(95) = 0.87209...
    x = [1, 2, 3, 4, 5]
    y = [1, 2, 2, 4, 3]
    rho = IQ.rank_spearman(x, y)
    assert abs(rho - 8.5 / math.sqrt(95.0)) < 1e-12
    # Kendall τ_b: 対 10 本。y の同順位 1 本 (2,3)。不一致 1 本 (4,5)。一致 8 本。
    #   τ_b = (8 − 1) / sqrt((10 − 0)(10 − 1)) = 7 / sqrt(90) = 0.73786...
    tau = IQ.rank_kendall_b(x, y)
    assert abs(tau - 7.0 / math.sqrt(90.0)) < 1e-12
    # 分母が同順位で縮む向きの確認: τ_a = 7/10 < τ_b
    assert tau > 0.7


def test_rank_spearman_matches_second_implementation_graphinv():
    import graphinv as GI
    rng = np.random.default_rng(7)
    x = rng.integers(0, 40, 400).astype(float)        # 同順位を大量に含む
    y = x + rng.normal(0, 10, 400)
    y = np.round(y / 3) * 3
    assert np.allclose(IQ.rank_data(x), GI._rank(x))
    assert abs(IQ.rank_spearman(x, y) - GI._spearman(x, y)) < 1e-12


def test_rank_functions_treat_inf_as_largest_and_tied():
    # inf 同士は同順位、inf は有限の全てより上。順位だけ使うので有限の大きな値に置いた結果と一致する
    x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    y = [1.0, 2.0, float("inf"), 4.0, float("inf"), 3.0]
    y_fin = [1.0, 2.0, 100.0, 4.0, 100.0, 3.0]
    assert IQ.rank_data(y).tolist() == [1.0, 2.0, 5.5, 4.0, 5.5, 3.0]
    assert abs(IQ.rank_spearman(x, y) - IQ.rank_spearman(x, y_fin)) < 1e-15
    assert abs(IQ.rank_kendall_b(x, y) - IQ.rank_kendall_b(x, y_fin)) < 1e-15
    with pytest.raises(ValueError):
        IQ.rank_spearman(x, [1.0, 2.0, float("nan"), 4.0, 5.0, 6.0])


def test_rank_kendall_chunking_is_invariant_and_constant_input_is_nan():
    rng = np.random.default_rng(3)
    x = rng.integers(0, 9, 300).astype(float)
    y = rng.integers(0, 9, 300).astype(float)
    t1 = IQ.rank_kendall_b(x, y, chunk=7)
    t2 = IQ.rank_kendall_b(x, y, chunk=1000)
    assert abs(t1 - t2) < 1e-15
    assert math.isnan(IQ.rank_spearman(x, np.ones_like(x)))
    assert math.isnan(IQ.rank_kendall_b(np.ones_like(x), y))


def test_rank_functions_fail_closed():
    with pytest.raises(ValueError):
        IQ.rank_spearman([1, 2, 3], [1, 2])
    with pytest.raises(ValueError):
        IQ.rank_kendall_b([1.0, float("nan")], [1.0, 2.0])
    with pytest.raises(ValueError):
        IQ.rank_data([1.0])


# ── 輝度規約と Fullseye の指標 ───────────────────────────────────────────────────
def test_luma_limited_endpoints_and_offset_db():
    black = np.zeros((4, 6, 3), np.uint8)
    white = np.full((4, 6, 3), 255, np.uint8)
    yb, yw = IQ.luma_limited_u8(black), IQ.luma_limited_u8(white)
    assert yb.dtype == np.uint8 and yb.shape == (4, 6)
    assert int(yb[0, 0]) == 16 and int(yw[0, 0]) == 235
    # 灰 128 → 16 + 219·128/255 = 125.94 → 126
    assert int(IQ.luma_limited_u8(np.full((2, 2, 3), 128, np.uint8))[0, 0]) == 126
    # full range との差は 20 log10(255/219) = 1.321 dB(同じ雑音を limited に縮めた PSNR の差、丸め無しの理論値)
    assert abs(20 * math.log10(255 / 219) - 1.3213) < 1e-3
    with pytest.raises(ValueError):
        IQ.luma_limited_u8(np.zeros((4, 6), np.uint8))
    with pytest.raises(ValueError):
        IQ.luma_limited_u8(np.zeros((4, 6, 3), np.float64))


def test_psnr_one_lsb_is_48_13_db_and_ssim_identity_is_one():
    a = np.zeros((32, 32), np.uint8)
    b = np.ones((32, 32), np.uint8)
    assert abs(IM.psnr(a, b) - 20 * math.log10(255.0)) < 1e-9       # 48.1308 dB
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, (48, 64), dtype=np.uint8)
    assert abs(IM.ssim(img, img) - 1.0) < 1e-12
    assert math.isinf(IM.psnr(img, img))


# ── 公表値 ─────────────────────────────────────────────────────────────────────
def test_published_table_has_14_metrics_and_known_entries():
    pub = IQ.tid2013_published()
    assert len(pub) == 14
    assert pub["psnr"] == (0.640, 0.470) and pub["ssim"] == (0.637, 0.464) and pub["fsimc"] == (0.851, 0.667)
    s = sorted(pub.values(), key=lambda t: -t[0])
    assert s[0] == pub["fsimc"] and s[-1] == pub["wsnr"]            # 表の順位 1 位と 14 位
    assert len(IQ.TID2013_DISTORTIONS) == 24 and IQ.TID2013_DISTORTIONS[7] == "Gaussian blur"
    assert len(IQ.TID2013_SUBSETS["Full"]) == 24 and IQ.TID2013_SUBSETS["Simple"] == (1, 8, 10)


# ── 台帳の fail-closed(合成の配布物) ───────────────────────────────────────────
def _fake_root(tmp_path, n_ref=25, n_types=24, n_levels=5, break_name=False, drop_bmp=False, bad_mos=False):
    from PIL import Image
    rt = tmp_path / "tid"
    (rt / "distorted_images").mkdir(parents=True)
    (rt / "reference_images").mkdir()
    (rt / "metrics_values").mkdir()
    lines = []
    tiny = Image.fromarray(np.zeros((16, 16, 3), np.uint8))
    for r in range(1, n_ref + 1):
        tiny.save(rt / "reference_images" / ("I%02d.BMP" % r if r % 2 else "i%02d.bmp" % r))
        for t in range(1, n_types + 1):
            for lv in range(1, n_levels + 1):
                nm = "i%02d_%02d_%d.bmp" % (r, t, lv)
                if r == 1 and lv == 1:
                    nm = nm.upper()          # 配布物にある大文字の名前を再現
                lines.append("%.5f %s" % (9.0 - 0.001 * len(lines) if not bad_mos else 9.5, nm))
                if not (drop_bmp and r == 3 and t == 3 and lv == 3):
                    tiny.save(rt / "distorted_images" / nm)
    if break_name:
        assert "i01_02_2" in lines[6]                         # 置換対象の実在を確かめる(無言の no-op を防ぐ)
        lines[6] = lines[6].replace("i01_02_2", "x01_02_2")
    (rt / "mos_with_names.txt").write_text("\r\n".join(lines) + "\r\n")
    (rt / "metrics_values" / "PSNR.txt").write_text("\n".join("%.4f" % (30 + 0.001 * k) for k in range(len(lines))) + "\n")
    return rt


def test_index_reads_synthetic_distribution_case_insensitively(tmp_path):
    rt = _fake_root(tmp_path)
    ix = IQ.tid2013_index(rt)
    assert len(ix["names"]) == 3000 and ix["mos"].shape == (3000,)
    assert ix["ref"][0] == 1 and ix["dist_type"][5] == 2 and ix["level"][4] == 5
    assert ix["names"][0] == "I01_01_1.BMP" and ix["dist_files"][0].name == "I01_01_1.BMP"
    assert len(ix["ref_files"]) == 25
    v = IQ.tid2013_metric_values(rt, "psnr")                  # ファイルは PSNR.txt
    assert v.shape == (3000,) and abs(v[1] - 30.001) < 1e-9
    with pytest.raises(ValueError):
        IQ.tid2013_metric_values(rt, "ssim")                  # 無いファイル


def test_index_fails_closed_on_broken_input(tmp_path):
    with pytest.raises(ValueError):
        IQ.tid2013_index(_fake_root(tmp_path / "a", n_levels=4))              # 2400 行
    with pytest.raises(ValueError):
        IQ.tid2013_index(_fake_root(tmp_path / "b", break_name=True))         # 名前の形
    with pytest.raises(ValueError):
        IQ.tid2013_index(_fake_root(tmp_path / "c", drop_bmp=True))           # 集合の不一致
    with pytest.raises(ValueError):
        IQ.tid2013_index(_fake_root(tmp_path / "d", bad_mos=True))            # MOS 9.5
    with pytest.raises(ValueError):
        IQ.tid2013_index(tmp_path / "nowhere")
    assert IQ.tid2013_root(tmp_path / "nowhere") is None


def test_evaluate_on_synthetic_distribution_fails_closed(tmp_path):
    rt = _fake_root(tmp_path)
    ix = IQ.tid2013_index(rt)
    # 恒等の組ばかり → PSNR は inf。inf は正当(作者は 100000.0 と書く)で、数えて返す
    r_inf = IQ.tid2013_evaluate(rt, IM.psnr, subset=3, index=ix)
    assert r_inf["n_inf"] == 3 and np.all(np.isinf(r_inf["values"]))
    with pytest.raises(ValueError):
        IQ.tid2013_compare(r_inf["values"], [100000.0] * 3, [1.0, 2.0, 3.0])          # inf_as 無し → 黙って落とさない
    c = IQ.tid2013_compare(r_inf["values"], [100000.0] * 3, [1.0, 2.0, 3.0], inf_as=100000.0)
    assert c["n_inf"] == 3 and c["diff_max"] == 0.0
    with pytest.raises(ValueError):
        IQ.tid2013_evaluate(rt, lambda a, b: float("nan"), subset=3, index=ix)
    with pytest.raises(ValueError):
        IQ.tid2013_evaluate(rt, lambda a, b: 1.0, subset=3, luma="bt709", index=ix)
    with pytest.raises(ValueError):
        IQ.tid2013_evaluate(rt, lambda a, b: 1.0, subset=[], index=ix)
    with pytest.raises(ValueError):
        IQ.tid2013_evaluate(rt, lambda a, b: 1.0, subset=["i99_01_1"], index=ix)
    res = IQ.tid2013_evaluate(rt, lambda a, b: float(a.mean() + b.shape[0]), subset=["I01_01_1.BMP", "i02_03_4"], luma="rgb", index=ix)
    assert res["n"] == 2 and res["names"] == ["I01_01_1.BMP", "i02_03_4.bmp"] and res["luma"] == "rgb"
    assert res["values"].tolist() == [16.0, 16.0]
    with pytest.raises(ValueError):
        IQ.tid2013_compare([1, 2, 3], [1, 2], [1, 2, 3])
    rows = IQ.tid2013_by_distortion(np.arange(3000.0), ix)
    assert len(rows) == 24
    for rw in rows:
        assert rw["n"] == 125 and -1.0 <= rw["srocc"] <= 1.0


# ── 実データ(環境変数があるときだけ) ───────────────────────────────────────────
@pytest.fixture(scope="module")
def tid():
    if DATA is None:
        pytest.skip("no TID2013")
    return IQ.tid2013_index(DATA)


@needs_data
def test_real_first_100_pairs_match_author_psnr_and_ssim(tid):
    n = 100
    rp = IQ.tid2013_evaluate(DATA, lambda a, b: IM.psnr(a, b), subset=n, luma="limited_u8", index=tid)
    rc = IQ.tid2013_evaluate(DATA, lambda a, b: IM.psnr(a, b), subset=n, luma="rgb", index=tid)
    rs = IQ.tid2013_evaluate(DATA, lambda a, b: IM.ssim(a, b), subset=n, luma="limited_u8", index=tid)
    ap = IQ.tid2013_metric_values(DATA, "psnr")[:n]
    ac = IQ.tid2013_metric_values(DATA, "psnrc")[:n]
    asm = IQ.tid2013_metric_values(DATA, "ssim")[:n]
    assert len(rp["values"]) == n and len(rc["values"]) == n and len(rs["values"]) == n
    # 先頭 100 組には歪み 18(彩度変化)の i01_18_* が含まれ、Y′ が参照と同じ → PSNR inf、作者は 100000.0 と書く
    assert rp["n_inf"] == int(np.count_nonzero(ap == 100000.0)) == 5
    cp = IQ.tid2013_compare(rp["values"], ap, rp["mos"], inf_as=100000.0)
    assert cp["diff_max"] <= 0.0005                            # psnr.txt は 4 桁
    assert np.abs(rc["values"] - ac).max() <= 0.0005 and rc["n_inf"] == 0
    assert np.abs(rs["values"] - asm).max() <= 0.0001         # ssim.txt は 4 桁 → 丸め半分 0.00005 + 余裕


@needs_data
def test_real_author_values_reproduce_published_rank_correlations(tid):
    pub = IQ.tid2013_published()
    keys = sorted(pub)
    assert len(keys) == 14
    for k in keys:
        v = IQ.tid2013_metric_values(DATA, k)
        c = IQ.tid2013_compare(v, v, tid["mos"], published=pub[k])
        assert abs(c["d_srocc_published"]) <= 0.001, (k, c["srocc"])
        assert abs(c["d_krocc_published"]) <= 0.001, (k, c["krocc"])
