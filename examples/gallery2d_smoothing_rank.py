# -*- coding: utf-8 -*-
"""gallery2d_smoothing_rank — 平滑化・ランク・復元・フィルタ・ノイズ系 2-D オペレータ一族を総ざらいで検証する (task: gallery2d)。

    py -3.11 examples/gallery2d_smoothing_rank.py

【平たく言うと(この一族は何のため?)】
画像を「均す/直す/汚す」ための道具箱。ぼかしてノイズを消す(smoothing)、
近傍の順位統計で外れ値を叩く(rank = median/min/max/percentile)、劣化した画像を
復元する(restoration = deconvolution/inpaint/TV)、一般の畳み込みフィルタ(filtering)、
逆にノイズやブレを人工的に加える(noise = 学習・ロバスト性評価用)。合わせて
撮像・計測前処理の中核。全部 image → image(2-D → 2-D)。

【検証(グラウンドトゥルース = GT)】
本ファイルは ops レジストリで category ∈ {smoothing, rank, restoration, filtering, noise}
に属する **全 86 op を 1 つ残らず呼び出し**、各 op について次の普遍契約を assert する:
  (1) 出力が有限(NaN/Inf を含まない)、
  (2) 宣言 out_sort と一致(image → 2-D の float ndarray、入力と同形状)、
  (3) 決定性(同じ入力 → ビット同一の出力。進化の holdout スコアリングが依存)。
これは repo の権威契約 tests/test_op_contracts.py と同じ判定基準。
  ※ image 出力を [0,1] に強制しないのは意図的。unsharp/deconv 等の先鋭化・逆畳み込みは
    設計上レンジを超過し得る(実測: unsharp が normal 画像で [-0.36, 1.37])。パイプライン
    境界で clip される側であり、test_op_honours_declared_sort も image に [0,1] を課さない。
加えて、効果が既知の代表 op には **より強い GT + beat-the-null** を課す(単に「動く」ではなく
挙動の正しさ): 平滑化は分散を下げる / median は salt-pepper を除去する / rank は min≤入力≤max /
gray モルフォロジは erosion≤入力≤dilation / noise op は定数画像に std>0 のばらつきを注入する /
unsharp は勾配エネルギーを増やす。すべて「何もしない(null)」を明確に上回ることを確認する。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402

# --------------------------------------------------------------------------- #
# 入力ファクトリ — tests/conftest.py の各バンク構成を複製(examples は tests/ を    #
# import してはならないため)。この一族は全て in_sort='image' だが、他 sort も      #
# 遭遇時に妥当な入力を返せるよう最小構成で用意する。                                 #
# --------------------------------------------------------------------------- #
def _rng():
    return np.random.default_rng(20260812)


def input_for(sort: str):
    """in_sort に対応する妥当な入力を返す(conftest の 'normal' 相当)。"""
    n = 48
    if sort in ("image", "any"):
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
        grad = xx / (n - 1)
        disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
        checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
        return np.clip(0.35 * grad + 0.45 * disk + checker
                       + 0.03 * _rng().standard_normal((n, n)), 0, 1)
    if sort == "region":
        yy, xx = np.mgrid[0:n, 0:n]
        return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)
    if sort == "color":
        g = input_for("image")
        return np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1)
    if sort == "volume":
        zz, vy, vx = np.mgrid[0:8, 0:24, 0:24]
        return np.clip(0.5 + 0.3 * np.sin(vx / 3.0) * np.cos(vy / 4.0) * (zz / 8.0), 0, 1)
    if sort == "contour":
        sq = np.array([[6.0, 6.0], [6.0, 20.0], [20.0, 20.0], [20.0, 6.0], [6.0, 6.0]])
        return {"shape": (32, 32), "cs": [sq]}
    raise ValueError(f"input_for: 未対応の sort {sort!r}")


# --------------------------------------------------------------------------- #
# TARGET 集合 — category ∈ {smoothing, rank, restoration, filtering, noise} の     #
# 全 op を明示的な文字列リテラルで列挙(op→example 逆引きインデックス用に、各 op 名  #
# がソース中に literal で出現する必要がある)。ops レジストリから機械抽出したもの。   #
# --------------------------------------------------------------------------- #
OPS = ["gaussian", "mean_box", "bilateral", "unsharp", "median", "min_filter",
       "max_filter", "percentile", "sk_tv", "sk_wavelet", "sk_median_disk",
       "sk_rolling_ball", "sk_nlm", "sk_tv_bregman", "cv_bilateral", "cv_median",
       "cv_box", "cv_gaussian", "cv_nlmeans", "cv_sharpen", "dl_aniso_diffusion",
       "dl_guided_filter", "gauss_filter", "gauss_image", "mean_image",
       "binomial_filter", "smooth_image", "mean_curvature_flow", "median_image",
       "median_rect", "median_separate", "gray_erosion_rect", "gray_dilation_rect",
       "gray_range_rect", "rank_image", "rank_rect", "sigma_image", "trimmed_mean",
       "anisotropic_diffusion", "isotropic_diffusion", "coherence_enhancing_diff",
       "bilateral_filter", "guided_filter", "simulate_motion", "add_noise_white",
       "eliminate_min_max", "median_weighted", "mean_sp", "eliminate_sp",
       "simulate_defocus", "add_noise_distribution", "dual_rank", "xsk_inpaint",
       "xsk_richardson_lucy", "xsk_unwrap_phase", "xcv_edge_preserving", "xcv_inpaint",
       "xpil_smooth_more", "xpil_mode_filter", "xpil_unsharp_mask", "xsp_wiener",
       "xsp_savgol", "xsp_dct_denoise", "xsp_cspline_smooth", "xsk2_rank_geomean",
       "xsk2_wiener", "xwt_visushrink", "xwt_firm_denoise", "xwt_lf_reconstruct",
       "xsk3_rank_mean_bilateral", "xcv3_denoise_tvl1", "xcv3_inpaint_ns",
       "xcv3_pyr_laplacian", "xkor_gaussian", "xkor_bilateral", "xkor_median",
       "xkor_unsharp", "xkor_motion_blur", "f2_gauss_pyramid", "iv_richardson_lucy",
       "iv_wiener_deconv_spatial", "iv_unsharp_deblur", "iv_motion_deblur",
       "iv_backproject_superres", "iv_gradient_inpaint", "tf_gradient_domain_reintegrate"]

# op 呼び出し時に振る knob(a, b)。conftest.KNOBS と同一。端点と中間で有限性・決定性を確認。
KNOBS = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85)]

# name -> Op のマップ(公開 REGISTRY から構築)。
BY = {o.name: o for o in ops.REGISTRY}


def _equal(x, y) -> bool:
    """決定性判定: 2 出力がビット同一か(NaN は上流で弾くので equal_nan 不要だが安全側で)。"""
    return (isinstance(x, np.ndarray) and isinstance(y, np.ndarray)
            and x.shape == y.shape and np.array_equal(x, y))


def check_universal_contracts() -> int:
    """全 TARGET op に (1)有限 (2)型=2-D float 同形状 (3)決定性 を課す。

    例外を投げた op は握り潰さず即 raise(loud failure)。返り値 = 検証した op 数。
    """
    for name in OPS:
        assert name in BY, f"op '{name}' が REGISTRY に存在しない(登録漏れ/改名)"
        op = BY[name]
        assert op.in_sort == "image" and op.out_sort == "image", (
            f"{name}: 期待した image->image でない ({op.in_sort}->{op.out_sort})")
        base = input_for(op.in_sort)
        for a, b in KNOBS:
            out = BY[name].fn(base.copy(), a, b)   # 例外はここで伝播 = FAIL loudly
            out = np.asarray(out)
            # (1) 有限
            assert np.all(np.isfinite(out)), f"{name}: 非有限値 (a={a}, b={b})"
            # (2) 宣言 out_sort=image と一致: 2-D の float ndarray、入力と同形状
            assert out.ndim == 2, f"{name}: image 出力が 2-D でない shape={out.shape} (a={a}, b={b})"
            assert np.issubdtype(out.dtype, np.floating), f"{name}: float dtype でない {out.dtype}"
            assert out.shape == base.shape, (
                f"{name}: 形状が保存されない {base.shape}->{out.shape} (a={a}, b={b})")
            # (3) 決定性: 同じ入力で 2 回目もビット同一
            out2 = np.asarray(BY[name].fn(base.copy(), a, b))
            assert _equal(out, out2), f"{name}: 非決定的 (a={a}, b={b})"
    return len(OPS)


def check_ground_truth() -> int:
    """効果が既知の代表 op に強い GT + beat-the-null を課す。返り値 = GT チェック数。"""
    n = 64
    rng = np.random.default_rng(7)
    # 段差エッジ(左 0.2 / 右 0.8)= 平滑化・先鋭化の GT 基準。
    yy, xx = np.mgrid[0:n, 0:n]
    clean = np.where(xx >= n // 2, 0.8, 0.2).astype(np.float64)
    # salt-pepper で汚した版。
    sp = clean.copy()
    m = rng.random((n, n))
    sp[m < 0.05] = 0.0
    sp[m > 0.95] = 1.0
    # ガウスノイズ場(分散低減の GT 基準)。
    noisy = np.clip(0.5 + 0.15 * rng.standard_normal((n, n)), 0, 1)

    def mae(a, c):
        return float(np.mean(np.abs(a - c)))

    def grad_energy(a):
        gx = np.diff(a, axis=1)
        gy = np.diff(a, axis=0)
        return float(np.sum(gx * gx) + np.sum(gy * gy))

    checks = 0

    # GT1: median は salt-pepper を除去 → clean への MAE が大幅に減少(null=何もしない を圧倒)。
    med = BY["median"].fn(sp.copy(), 0.5, 0.0)
    err_in, err_out = mae(sp, clean), mae(med, clean)
    assert err_out < 0.5 * err_in, f"GT median: 除去不足 in={err_in:.4f} out={err_out:.4f}"
    checks += 1

    # GT2: 平滑化(gaussian/mean_box/cv_gaussian)はノイズ場の分散を下げる(< 生分散)。
    v_in = float(np.var(noisy))
    for nm in ("gaussian", "mean_box", "cv_gaussian"):
        v_out = float(np.var(BY[nm].fn(noisy.copy(), 0.5, 0.0)))
        assert v_out < v_in, f"GT {nm}: 分散が下がらない in={v_in:.5f} out={v_out:.5f}"
        checks += 1

    # GT3: ランクフィルタの順序保存 — min_filter ≤ 入力 ≤ max_filter、かつ min ≤ max(各画素)。
    mn = BY["min_filter"].fn(noisy.copy(), 0.5, 0.0)
    mx = BY["max_filter"].fn(noisy.copy(), 0.5, 0.0)
    assert np.all(mn <= noisy + 1e-9) and np.all(mx >= noisy - 1e-9) and np.all(mn <= mx + 1e-9), \
        "GT rank: min<=in<=max の順序が壊れている"
    # min は実際に暗く、max は実際に明るい(null=恒等 を上回る非自明な変化)。
    assert mn.mean() < noisy.mean() - 1e-3 and mx.mean() > noisy.mean() + 1e-3, \
        "GT rank: min/max が入力から動いていない"
    checks += 1

    # GT4: グレースケール・モルフォロジ — erosion ≤ 入力 ≤ dilation(各画素)。
    er = BY["gray_erosion_rect"].fn(noisy.copy(), 0.5, 0.0)
    di = BY["gray_dilation_rect"].fn(noisy.copy(), 0.5, 0.0)
    assert np.all(er <= noisy + 1e-9) and np.all(di >= noisy - 1e-9), \
        "GT morph: erosion<=in<=dilation が壊れている"
    checks += 1

    # GT5: noise op は定数画像に非ゼロのばらつきを注入(入力 std=0 → 出力 std>0 = null を破る)。
    const = np.full((n, n), 0.5)
    assert float(np.std(const)) == 0.0
    for nm in ("add_noise_white", "add_noise_distribution"):
        s_out = float(np.std(BY[nm].fn(const.copy(), 0.5, 0.5)))
        assert s_out > 1e-3, f"GT {nm}: 定数画像にノイズが乗っていない std={s_out:.5f}"
        checks += 1

    # GT6: unsharp は勾配エネルギーを増やす(ぼけ画像を先鋭化 → エッジ応答が強まる)。
    blur = BY["gaussian"].fn(clean.copy(), 0.6, 0.0)
    sharp = BY["unsharp"].fn(blur.copy(), 0.6, 0.5)
    assert grad_energy(sharp) > grad_energy(blur) + 1e-6, \
        f"GT unsharp: 先鋭化していない blur={grad_energy(blur):.4f} sharp={grad_energy(sharp):.4f}"
    checks += 1

    return checks


def main() -> None:
    n_ops = check_universal_contracts()
    n_gt = check_ground_truth()
    assert n_ops == len(OPS)
    print(f"PASS: {n_ops} ops exercised, all finite/typed/deterministic; {n_gt} GT checks")


if __name__ == "__main__":
    main()
