# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_ct_fidelity — 投影数を減らすと CT 再構成は**どこから壊れるか**を数字で出す。

    py -3.11 examples/poc_ct_fidelity.py

【この PoC が答える問題】
「投影を間引いても絵は出る」。出るが、**どこから信用できなくなるのか**。
Shepp-Logan ファントムを真値にして 180 / 90 / 45 / 24 / 12 本で撮り直し、
FBP の誤差を **2 つの零点**と並べて置く ——

    零点 A: 空白画像(全部ゼロ)   … 何もしない。RMSE は定義上 rms(真値) = 0.2420
    零点 B: フィルタ無し逆投影     … 撮ったデータは全部使う。ただしぼける

零点 A が要る理由は、零点 B だけだと「FBP が勝った」と言える範囲を測り
そこねるから。実測、**投影 12 本の FBP は零点 A(空白画像)より RMSE が悪い**。

    EXTEND: `filtered_backprojection(..., filter_name=...)` を差し替えると
    apodisation の効き方が変わる(§6 で ramp と hann を並べている)。角度
    スイープの本数は `VIEW_COUNTS` を書き換えるだけで増やせる。

【真値の作り方(自分で作る)】
`ellipse_phantom` でラスタライズした Shepp-Logan が真値。その総質量は
Σ rho_i π a_i b_i (size/2)^2 という**閉形式**があるので、ラスタライズ自体も
検算できる(実測 -3.2e-05)。

【独立な検算(真値との差分とは別経路)】
平行ビームの線積分は角度によらず総質量に等しい。実測、`radon_transform` の
各行の和はファントム総和に対し相対 **+1.3e-05**、角度間のばらつき **9.5e-05**。
この検算は再構成を一切見ない ―― 見るのはサイノグラムだけ。

★そしてこの検算は、真値との RMSE が見落とすものを 1 つ捕まえる:
**FBP は質量を保存しない**。180 本・検出器 363 bin で総質量は **-3.34 %**。
RMSE のほうは 0.02498 で、これは「ほぼ正解」に見える数字である。検出器を
727 bin に増やす(= フィルタの FFT パッド長が 1024 → 2048 になる)と質量欠損は
**-0.83 %** に 4 分の 1 になるのに、RMSE は 0.02498 → 0.02466 と 1.3 % しか
動かない。**画としては同じ、量としては 4 倍違う。**

【想定と違ったこと(消さずに残す)】
1. **零点 B は投影数にほとんど反応しない。** 最小二乗で真値にスケールを
   合わせたフィルタ無し逆投影の RMSE は 180 本で 0.1681、12 本で 0.1688 ——
   0.4 % しか動かない。1/|r| のぼけが支配的で、ストリークはその下に埋もれる。
   つまり**零点 B は「投影が足りない」という故障に対して盲目**。
2. **交差する。** FBP が零点 B を上回るのは 24 本まで(0.1512 対 0.1682)で、
   12 本では **FBP 0.2577 対 零点 B 0.1688 と負ける**。ランプフィルタは
   「測っていない高周波」を増幅するので、投影が足りないと零点より悪くなる。
   最初は「FBP は常に勝つ、差が縮むだけ」と思って書き始めた ―― 違った。
3. しかも 12 本の FBP は**零点 A(空白画像、0.2420)よりも悪い**。ところが
   相関は 0.611 あって、構造情報は確かに残っている。RMSE と相関がここで
   食い違う。**「空白のほうがマシ」は RMSE という物差しの言い分**であって、
   絵に情報が無いという意味ではない。両方書かないと嘘になる。

【私が間違えて直したこと】
- 最初、フィルタ無し逆投影を**そのまま** RMSE に掛けて「零点は 104 倍悪い」と
  書きかけた。実測 RMSE 104.2 ―― これは 1/|r| に有限の積分が無いせいで
  逆投影に**絶対スケールが存在しない**ことの反映で、手法の優劣ではない。
  自動ウィンドウ表示は黙ってこの再スケールをやる。だから零点 B は
  **最小二乗で真値に合わせてから**比べている(= 零点に最大限有利な条件)。
- 誤差の正規化を最初 rms(真値) で割っていたが、`filtered_backprojection` の
  docstring の表(180 本で 0.0250)と 4.13 倍ずれた。docstring 側は
  **RMSE / data_range**(= 1.0)、つまり密度そのままの RMSE だった。
  合わせた結果、解析サイノグラム経由の値は docstring と 4 桁一致する
  (180 本 0.02498 / 90 本 0.04537 / 45 本 0.10390)。この一致が
  「測定系が正しく組めている」ことの担保になっている。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import tomography as T                                           # noqa: E402

SIZE = 256                      # 再構成格子(真値と同じ)
VIEW_COUNTS = (180, 90, 45, 24, 12)
FLAT_RHO = 0.2                  # Shepp-Logan の「脳実質」= 一様領域の密度
DATA_RANGE = 1.0                # 真値の値域 [0, 1] —— RMSE の正規化に使う


def analytic_mass(size: int) -> float:
    """ファントムの総質量の**閉形式**(px 単位)。

    正規化座標での楕円 1 つの積分は rho * pi * a * b。格子は [-1,1] を
    size 画素に写すので、面積は (size/2)^2 倍になる。密度は足し合わせなので
    楕円の和もそのまま足せる(Shepp-Logan は負の rho を含むが同じ)。
    """
    total = sum(rho * np.pi * a * b for (_x, _y, a, b, _p, rho) in T.SHEPP_LOGAN)
    return total * (size / 2.0) ** 2


def flat_region_mask(truth: np.ndarray) -> np.ndarray:
    """真値が厳密に *FLAT_RHO* の領域を、縁を削って取り出す。

    ここでの真値の標準偏差は**厳密に 0** なので、再構成側で観測される
    標準偏差はまるごとストリーク(と補間ノイズ)である。縁を 2 px 削るのは
    アンチエイリアスされた境界画素を混ぜないため。
    """
    exact = np.abs(truth - FLAT_RHO) < 1e-12
    return ndi.binary_erosion(exact, np.ones((5, 5), dtype=bool))


def lsq_rescale(img: np.ndarray, truth: np.ndarray) -> tuple[np.ndarray, float, float]:
    """*img* を a*img + b の形で真値に最小二乗フィットする。

    フィルタ無し逆投影には絶対スケールが無いので、これをやらずに RMSE を
    取ると「手法の優劣」ではなく「単位の違い」を測ってしまう。零点に
    **最大限有利な**扱いであり、意図的にそうしている。
    """
    a_mat = np.stack([img.ravel(), np.ones(img.size)], axis=1)
    coef, *_ = np.linalg.lstsq(a_mat, truth.ravel(), rcond=None)
    return img * coef[0] + coef[1], float(coef[0]), float(coef[1])


def rmse(img: np.ndarray, truth: np.ndarray) -> float:
    """密度そのままの RMSE(= RMSE / data_range、data_range は 1.0)。"""
    return float(np.sqrt(((img - truth) ** 2).mean()))


def correlation(img: np.ndarray, truth: np.ndarray) -> float:
    """Pearson 相関。`fs.stat_correlation` は (N, D) 観測 -> (D, D) を返す。"""
    obs = np.stack([img.ravel(), truth.ravel()], axis=1)
    return float(fs.stat_correlation(obs)[0, 1])


def main() -> bool:
    truth = fs.ellipse_phantom(size=SIZE)
    flat = flat_region_mask(truth)
    blank_rmse = rmse(np.zeros_like(truth), truth)

    print("=" * 78)
    print("1) 真値 ―― 自分で作り、閉形式で検算する")
    print("=" * 78)
    m_an = analytic_mass(SIZE)
    print(f"   ファントム           = Shepp-Logan {len(T.SHEPP_LOGAN)} 楕円 / {SIZE}x{SIZE} 格子")
    print(f"   値域                 = [{truth.min():.3f}, {truth.max():.3f}] "
          f"(rms {np.sqrt((truth ** 2).mean()):.4f})")
    print(f"   総質量 閉形式        = {m_an:.3f} px 単位")
    print(f"   総質量 ラスタライズ  = {truth.sum():.3f}  "
          f"(相対 {truth.sum() / m_an - 1:+.2e} —— 真値そのものが正しく作れている)")
    print(f"   一様領域 (rho={FLAT_RHO}) = {int(flat.sum())} px、"
          f"ここでの真値の標準偏差 = {truth[flat].std():.1e}")

    print()
    print("=" * 78)
    print("2) 独立な検算 ―― 投影の質量保存(再構成を一切見ない)")
    print("=" * 78)
    print("   平行ビームの線積分は角度によらず総質量に等しい。")
    print("   views | 行和の平均 | 真値比      | 角度間ばらつき")
    print("   ------+------------+-------------+---------------")
    sinos = {}
    for n_views in VIEW_COUNTS:
        ang = fs.projection_angles(n_views)
        t0 = time.perf_counter()
        sino = fs.radon_transform(truth, ang)
        dt = time.perf_counter() - t0
        sinos[n_views] = (ang, sino, dt)
        rows = sino.sum(axis=1)
        print(f"   {n_views:5d} | {rows.mean():10.3f} | {rows.mean() / truth.sum() - 1:+11.2e} | "
              f"{rows.std() / rows.mean():.2e}")
    print("   ★ここが合わなければ以降は全部無意味。合っているので、")
    print("     以降に出る誤差は**再構成の誤差**であって投影の誤差ではない。")

    print()
    print("=" * 78)
    print("3) 投影数スイープ ―― FBP と 2 つの零点")
    print("=" * 78)
    print(f"   零点 A(空白画像)の RMSE = {blank_rmse:.4f}  ―― 何もしないと必ずこの値")
    print("   零点 B(フィルタ無し逆投影)は最小二乗で真値にスケールを合わせてから比べる")
    print()
    print("   views |  FBP RMSE | 零点B RMSE | FBP/零点B | FBP 相関 | 零点B 相関 | FBP SSIM")
    print("   ------+-----------+------------+-----------+----------+------------+---------")
    rows_out = []
    recon = {}                  # 図に使う再構成像(図を出すときだけ持つ)
    for n_views in VIEW_COUNTS:
        ang, sino, dt_proj = sinos[n_views]
        t0 = time.perf_counter()
        fbp = fs.filtered_backprojection(sino, ang, size=SIZE)
        dt_fbp = time.perf_counter() - t0
        t0 = time.perf_counter()
        bp_raw = fs.backproject_sinogram(sino, ang, size=SIZE)
        dt_bp = time.perf_counter() - t0
        bp, gain, _off = lsq_rescale(bp_raw, truth)
        if figs.enabled():
            recon[n_views] = (fbp, bp)
        r_fbp, r_bp = rmse(fbp, truth), rmse(bp, truth)
        rows_out.append({
            "views": n_views, "fbp": r_fbp, "bp": r_bp, "bp_raw": rmse(bp_raw, truth),
            "gain": gain, "corr_fbp": correlation(fbp, truth),
            "corr_bp": correlation(bp_raw, truth),
            "ssim": float(fs.ssim(fbp, truth, data_range=DATA_RANGE)),
            "ssim_bp": float(fs.ssim(bp, truth, data_range=DATA_RANGE)),
            "streak_fbp": float(fbp[flat].std()), "streak_bp": float(bp[flat].std()),
            "mass": float(fbp.sum() / truth.sum() - 1),
            "t_proj": dt_proj, "t_fbp": dt_fbp, "t_bp": dt_bp,
        })
        print(f"   {n_views:5d} | {r_fbp:9.4f} | {r_bp:10.4f} | {r_bp / r_fbp:8.2f}x | "
              f"{rows_out[-1]['corr_fbp']:8.4f} | {rows_out[-1]['corr_bp']:10.4f} | "
              f"{rows_out[-1]['ssim']:8.4f}")

    best, worst = rows_out[0], rows_out[-1]
    print()
    print("   ★零点との比較(正直に):")
    print(f"     180 本では FBP が零点 B を {best['bp'] / best['fbp']:.1f} 倍上回る。")
    crossed = [r for r in rows_out if r["fbp"] >= r["bp"]]
    if crossed:
        c = crossed[0]
        print(f"     しかし {c['views']} 本で**逆転する** —— FBP {c['fbp']:.4f} 対 "
              f"零点 B {c['bp']:.4f}。")
        print("     ランプフィルタは測っていない高周波を増幅するので、"
              "投影が足りないと")
        print("     ぼけただけの零点に負ける。「FBP は常に勝つ」は誤り。")
    else:
        print("     どの投影数でも FBP が零点 B を上回った(逆転は観測されなかった)。")
    below_blank = [r for r in rows_out if r["fbp"] > blank_rmse]
    if below_blank:
        b = below_blank[0]
        print(f"     さらに {b['views']} 本の FBP は**零点 A(空白画像 {blank_rmse:.4f})"
              f"よりも RMSE が悪い** ({b['fbp']:.4f})。")
        print(f"     ところが相関は {b['corr_fbp']:.3f} あり、構造情報は残っている。"
              "RMSE と相関がここで食い違う。")
        print("     『空白のほうがマシ』は RMSE という物差しの言い分であって、"
              "絵が無情報という意味ではない。")
    print(f"     零点 B は投影数にほとんど反応しない: "
          f"{best['views']} 本 {best['bp']:.4f} -> {worst['views']} 本 {worst['bp']:.4f} "
          f"({worst['bp'] / best['bp'] - 1:+.1%})。")
    print("     1/|r| のぼけが支配的で、ストリークはその下に埋もれる —— "
          "**零点 B は「投影が足りない」に盲目**。")
    print(f"     なお再スケール前の零点 B は RMSE {best['bp_raw']:.1f}"
          f"(ゲイン {best['gain']:.2e})。絶対スケールが無いので、")
    print("     生の数字で比べるのは手法ではなく単位を測ることになる。")

    # 「どこから壊れるか」は数字より絵のほうが速い。最後の 2 枚は**同じ 12 本**を
    # FBP と零点 B で並べたもの —— RMSE で負けているほうが構造は残っている。
    if recon:
        figs.save_grid(
            "recon_sweep",
            [truth, recon[180][0], recon[45][0], recon[12][0], recon[12][1],
             recon[12][0] - truth],
            ["真値(Shepp-Logan)", "FBP 180 本", "FBP 45 本", "FBP 12 本",
             "零点 B 12 本(最小二乗で合わせた)", "FBP 12 本 - 真値"],
            title="投影数を減らすと、どこから壊れるか",
            ncols=3, signed=[False] * 5 + [True],
            caption="12 本の FBP は RMSE では空白画像より悪いが、相関 0.61 で"
                    "構造は残っている。零点 B はぼけるだけでストリークが出ない。")

    print()
    print("=" * 78)
    print("4) ストリークの定量 ―― 真値が厳密に一定な領域の標準偏差")
    print("=" * 78)
    print(f"   {int(flat.sum())} px の一様領域(真値 rho={FLAT_RHO}、真値側の標準偏差は 0)")
    print("   views | FBP std | 零点B std | FBP 180本比")
    print("   ------+---------+-----------+------------")
    for r in rows_out:
        print(f"   {r['views']:5d} | {r['streak_fbp']:7.5f} | {r['streak_bp']:9.5f} | "
              f"{r['streak_fbp'] / best['streak_fbp']:10.1f}x")
    print(f"   ★FBP のストリークは {best['views']} -> {worst['views']} 本で "
          f"{worst['streak_fbp'] / best['streak_fbp']:.1f} 倍に増える。")
    print(f"     零点 B は {best['streak_bp']:.5f} -> {worst['streak_bp']:.5f} でほぼ動かない。")
    print("     この一様領域が、平均値では見えない故障を見せる唯一の場所。")

    print()
    print("=" * 78)
    print("5) 独立な検算その 2 ―― FBP は質量を保存しない")
    print("=" * 78)
    print("   §2 の検算は投影について合格した。同じ検算を**再構成**に掛けると落ちる。")
    print("   views | 再構成の総質量 / 真値")
    print("   ------+----------------------")
    for r in rows_out:
        print(f"   {r['views']:5d} | {r['mass']:+21.4%}")
    ang180 = fs.projection_angles(180)
    fine = fs.ellipse_sinogram(size=SIZE, angles_deg=ang180, n_detectors=727)
    rec_fine = fs.filtered_backprojection(fine, ang180, size=SIZE)
    coarse = fs.ellipse_sinogram(size=SIZE, angles_deg=ang180, n_detectors=363)
    rec_coarse = fs.filtered_backprojection(coarse, ang180, size=SIZE)
    m_c = rec_coarse.sum() / truth.sum() - 1
    m_f = rec_fine.sum() / truth.sum() - 1
    print(f"   検出器 363 bin (FFT pad 1024): 質量 {m_c:+.4%} / RMSE {rmse(rec_coarse, truth):.5f}")
    print(f"   検出器 727 bin (FFT pad 2048): 質量 {m_f:+.4%} / RMSE {rmse(rec_fine, truth):.5f}")
    print(f"   ★質量欠損は {abs(m_c / m_f):.1f} 倍改善するのに、RMSE は "
          f"{abs(rmse(rec_fine, truth) / rmse(rec_coarse, truth) - 1):.1%} しか動かない。")
    print("     ランプは DC ビンのゲインが厳密に 0、その近傍もほぼ 0 —— "
          "総質量が乗っている最低周波数が")
    print("     いちばん再構成できない帯域である。**画としては同じ、量としては 4 倍違う。**")
    print("     真値との RMSE だけを見ていると、この故障は一生見えない。")

    # 3〜5 節は同じ再構成を 3 つの物差しで測っている。並べないと
    # 「RMSE は 1.3 % しか動かないのに質量は 4 倍違う」が見えない。
    figs.save_table(
        "fidelity_table",
        ["投影数", "FBP RMSE", "零点B RMSE", "FBP 相関", "一様域 std", "総質量誤差"],
        [["%d" % r["views"], "%.4f" % r["fbp"], "%.4f" % r["bp"],
          "%.4f" % r["corr_fbp"], "%.5f" % r["streak_fbp"], "%+.2f %%" % (100 * r["mass"])]
         for r in rows_out],
        title="投影数スイープ —— 3 つの物差しは同じ順序に並ばない",
        caption="RMSE で見ると 12 本は空白画像 %.4f より悪い。相関とストリークは"
                "別のことを言う。" % blank_rmse)

    print()
    print("=" * 78)
    print("6) 疎な投影での処方箋 ―― ramp と hann")
    print("=" * 78)
    print("   views | ramp RMSE | hann RMSE | hann/ramp")
    print("   ------+-----------+-----------+----------")
    hann_rows = []
    for n_views in VIEW_COUNTS:
        ang, sino, _dt = sinos[n_views]
        h = fs.filtered_backprojection(sino, ang, size=SIZE, filter_name="hann")
        r_h = rmse(h, truth)
        r_r = next(x["fbp"] for x in rows_out if x["views"] == n_views)
        hann_rows.append((n_views, r_r, r_h))
        print(f"   {n_views:5d} | {r_r:9.4f} | {r_h:9.4f} | {r_h / r_r:8.2f}x")
    wins = [n for (n, r_r, r_h) in hann_rows if r_h < r_r]
    print(f"   ★hann が ramp を上回るのは {wins} 本。"
          "疎になるほど、増幅すべき高周波が最初から測られていない。")
    n12 = hann_rows[-1]
    print(f"     ただし {n12[0]} 本では hann ({n12[2]:.4f}) でも零点 B "
          f"({worst['bp']:.4f}) を上回れない。")
    print("     フィルタの選択は「投影が足りない」を救わない。足りないのは"
          "データであってアルゴリズムではない。")

    # ★この PoC の見出し。零点 A(水平線)と零点 B に FBP が**交差する**ところが
    #   目で見える。横軸は投影数(左が疎)。
    vs = np.array([r["views"] for r in rows_out], float)
    figs.save_plot(
        "rmse_vs_views",
        [("FBP (ramp)", vs, np.array([r["fbp"] for r in rows_out])),
         ("FBP (hann)", vs, np.array([r_h for (_n, _r, r_h) in hann_rows])),
         ("零点 B(無フィルタ BP)", vs, np.array([r["bp"] for r in rows_out])),
         ("零点 A(空白画像)", vs, np.full(vs.size, blank_rmse))],
        xlabel="投影数", ylabel="RMSE(密度そのまま)",
        title="FBP は零点と交差する",
        caption="24 本までは FBP の勝ち。12 本では零点 B にも零点 A にも負ける —— "
                "ランプは測っていない高周波を増幅するため。")

    print()
    print("=" * 78)
    print("7) 速さ(assert しない ―― 印字するだけ)")
    print("=" * 78)
    print("   views | radon [s] | FBP [s] | 無フィルタ BP [s]")
    print("   ------+-----------+---------+------------------")
    for r in rows_out:
        print(f"   {r['views']:5d} | {r['t_proj']:9.3f} | {r['t_fbp']:7.3f} | {r['t_bp']:17.3f}")
    print("   FBP と無フィルタ BP の差はランプの FFT 1 回ぶんで、"
          "コストはほぼ同じ ——")
    print("   つまり零点 B を選ぶ理由は速さではない(そして精度でもない)。")

    print()
    print("=" * 78)
    print("8) 自己検査 ―― 正しさだけを assert する")
    print("=" * 78)
    checks = []

    rows180 = sinos[180][1].sum(axis=1)
    conservation = abs(rows180.mean() / truth.sum() - 1)
    checks.append(("投影の質量保存が 1e-3 以内", conservation < 1e-3, f"{conservation:.2e}"))

    raster = abs(truth.sum() / m_an - 1)
    checks.append(("ラスタライズ質量が閉形式と 1e-3 以内", raster < 1e-3, f"{raster:.2e}"))

    checks.append(("真値の一様領域は厳密に一定", truth[flat].std() == 0.0,
                   f"{truth[flat].std():.1e}"))

    monotone = all(rows_out[i]["fbp"] < rows_out[i + 1]["fbp"] for i in range(len(rows_out) - 1))
    checks.append(("投影を減らすと FBP 誤差が単調に増える", monotone,
                   " < ".join(f"{r['fbp']:.4f}" for r in rows_out)))

    checks.append(("180 本では FBP が零点 B を 3 倍以上上回る",
                   best["bp"] / best["fbp"] > 3.0, f"{best['bp'] / best['fbp']:.2f}x"))

    checks.append(("12 本では FBP が零点 B に負ける(逆転が起きる)",
                   worst["fbp"] > worst["bp"], f"{worst['fbp']:.4f} > {worst['bp']:.4f}"))

    checks.append(("零点 B は投影数に 5 % 未満しか反応しない",
                   abs(worst["bp"] / best["bp"] - 1) < 0.05,
                   f"{worst['bp'] / best['bp'] - 1:+.2%}"))

    checks.append(("ストリークは投影を減らすと 5 倍以上に増える",
                   worst["streak_fbp"] / best["streak_fbp"] > 5.0,
                   f"{worst['streak_fbp'] / best['streak_fbp']:.1f}x"))

    checks.append(("検出器を倍にすると質量欠損が 2 倍以上改善する",
                   abs(m_c) > 2.0 * abs(m_f), f"{m_c:+.4%} -> {m_f:+.4%}"))

    ok = True
    for name, passed, detail in checks:
        print(f"   [{'ok ' if passed else 'NG '}] {name}: {detail}")
        ok = ok and passed
    if not ok:
        print("   1 つ以上の検査に落ちた。")
        return False
    for _name, passed, _detail in checks:
        assert passed

    print()
    print("PASS: tomography 6 op(projection_angles / ellipse_phantom / ellipse_sinogram / "
          "radon_transform / filtered_backprojection / backproject_sinogram)を実行。")
    print(f"      投影 180 -> 12 本で FBP の RMSE は {best['fbp']:.4f} -> {worst['fbp']:.4f}、"
          f"ストリークは {worst['streak_fbp'] / best['streak_fbp']:.0f} 倍。")
    print(f"      零点との比較の結論: 180 本では {best['bp'] / best['fbp']:.1f} 倍勝ち、"
          f"12 本では負ける。")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
