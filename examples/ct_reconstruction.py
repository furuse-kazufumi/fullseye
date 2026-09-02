# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ct_reconstruction — 1 本の試料を CT でスキャンし、**寸法 mm と欠陥の数**まで出す。

    py -3.11 examples/ct_reconstruction.py

【この例が解く問題】
アルミの丸棒(外径 30.00 mm)を X 線 CT で 1 本スキャンする。中には偏心した
空洞(直径 6.00 mm、中心 x=+6.00 / y=-3.00 mm)が 1 つある。答えるべきことは
2 つだけ ——「**外径は何 mm か**」と「**欠陥は何個あるか**」。

    ellipse_phantom / ellipse_sinogram   閉形式の真値(離散化誤差ゼロ)
      → radon_transform                  数値投影(保存則で真値と突き合わせる)
      → backproject_sinogram             フィルタ無しの下限
      → filtered_backprojection          標準の再構成
      → sart_reconstruct                 反復解法
      → sinogram_center_of_rotation      回転中心のずれを測る
      → sinogram_center_shift            そのずれを直す
      → beam_hardening_apply / _correct   カッピング(空洞が太って見える)
      → ring_artifact_apply / _remove     リング(偽の空洞が増える)
      → metal_trace_interpolate           金属ストリーク(偽の欠陥 35 個)

`examples/tomography_reconstruct.py` は同じ族の 3-D 側(投影 → ボクセル →
体積 mm³)を通す。こちらは **2-D スライス 1 枚と、そこに乗る 5 種の故障**を
担当する ―― 重なりは `ellipse_phantom` / `projection_angles` の 2 つだけで、
再構成 3 種と偽像 5 種と回転中心 2 種は**ここでしか実行されない**。

【グラウンドトゥルース(数値で嘘を弾く)】
1. **保存則**: 平行ビームの線積分は角度によらず総質量に等しい。実測、
   `radon_transform` の各行の和はファントムの総和に対し相対 **-6.2e-06**、
   角度間のばらつき **2.5e-04**。ここが合わなければ以降は全部無意味。
2. **閉形式**: `ellipse_sinogram` は離散化誤差ゼロの真値。`radon_transform`
   との差は peak の **0.412 %** RMS(差の正体は部分体積の縁)。
3. **寸法**: 外径 30.00 mm / 空洞 6.00 mm が閉形式の真値。格子で二値化した
   真ファントム自身が既に 29.989 / 5.981 mm なので、**そこが天井**。
4. **可逆性**: `beam_hardening_correct` はモデル逆なので往復が peak の
   **1.7e-08**。`sinogram_center_shift` は**整数シフトなら往復が厳密に 0**、
   半画素なら peak の **4.5e-02**(補間は低域通過であって可逆ではない)。
5. **偏りの定数性**: 回転中心の推定誤差は入れたずれの大小によらず
   **+3.3e-04 px 一定** ―― これは推定器の性能ではなくファントムと検出器
   標本化の性質だから、定数であることそのものが検算になる。

【この例が出す正直な結論】
**外径は壊れても壊れたと言わない。** 5 種の故障すべてを通して外径は
29.94-30.17 mm(振れ幅 0.8 %)に収まる。一方**欠陥の数**は 1 → 5(リング)
→ 36(金属)→ 0(フィルタ無し)と桁で壊れる。寸法だけを見ている検査は、
サイノグラムが壊れていることに気付けない。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tomography as T                                            # noqa: E402

# ---- 撮像の幾何(すべて mm) --------------------------------------------- #
SIZE = 256                      # ファントムの面内格子
PIX_MM = 0.25                   # 画素ピッチ
HALF_MM = SIZE * PIX_MM / 2.0   # 正規化座標 [-1,1] が覆う半幅 = 32 mm
N_VIEWS = 180

# ---- 試料: アルミ丸棒 + 偏心した空洞 ------------------------------------- #
R_OUT_MM = 15.0                 # 外半径  -> 外径 30.00 mm
R_VOID_MM = 3.0                 # 空洞半径 -> 直径 6.00 mm
VOID_X_MM, VOID_Y_MM = 6.0, -3.0
RHO = 1.0 / 60.0                # 画素あたり減弱(最大線積分がちょうど 2.0)

# ---- 金属インサート(6 節でだけ足す) ------------------------------------- #
METAL_X_MM, METAL_Y_MM, METAL_R_MM = -8.0, 6.0, 1.2
METAL_DENSITY = 30.0            # アルミの 30 倍


def nm(mm):
    """mm → ellipse_phantom の正規化座標([-1, 1] が視野全体)。"""
    return mm / HALF_MM


#: (x0, y0, a, b, phi_deg, rho) —— 空洞は「減弱を打ち消す負の楕円」で作る。
SAMPLE = [(0.0, 0.0, nm(R_OUT_MM), nm(R_OUT_MM), 0.0, RHO),
          (nm(VOID_X_MM), nm(VOID_Y_MM), nm(R_VOID_MM), nm(R_VOID_MM), 0.0, -RHO)]
SAMPLE_METAL = SAMPLE + [(nm(METAL_X_MM), nm(METAL_Y_MM),
                          nm(METAL_R_MM), nm(METAL_R_MM), 0.0, RHO * METAL_DENSITY)]


def _rule(title):
    print(f"\n{'=' * 76}\n{title}\n{'=' * 76}")


# --------------------------------------------------------------------------- #
class Gauge:
    """再構成像 1 枚から「外径 mm / 欠陥の数 / 最大空洞の直径 mm」を読む検査。

    しきい値は材料(RHO)と空気(0)の中点。外形は穴埋めした最大連結成分、
    欠陥はその内側で材料に届かなかった画素。**現場の手順そのもの**で、
    tomography 側の op は 1 つも使わない ―― 使うと「再構成が壊れていることを
    再構成の道具で測る」ことになるため。
    """

    def __init__(self, size, pix_mm):
        self.n = size
        self.pix_mm = pix_mm

    def __call__(self, image, threshold=0.5 * RHO):
        solid = image > threshold
        body = ndimage.binary_fill_holes(solid)
        lbl, k = ndimage.label(body)
        if k == 0:
            return {"outer_mm": 0.0, "n_defect": 0, "void_mm": float("nan"),
                    "void_x_mm": float("nan"), "void_y_mm": float("nan")}
        sizes = ndimage.sum(np.ones_like(lbl), lbl, range(1, k + 1))
        body = lbl == (int(np.argmax(sizes)) + 1)
        holes = body & ~solid
        hl, hk = ndimage.label(holes)
        out = {"outer_mm": self._equiv_mm(int(body.sum())), "n_defect": int(hk),
               "void_mm": float("nan"), "void_x_mm": float("nan"),
               "void_y_mm": float("nan")}
        if hk:
            hs = ndimage.sum(np.ones_like(hl), hl, range(1, hk + 1))
            big = hl == (int(np.argmax(hs)) + 1)
            out["void_mm"] = self._equiv_mm(int(big.sum()))
            cy, cx = ndimage.center_of_mass(big)
            out["void_x_mm"] = (cx - (self.n - 1) / 2.0) * self.pix_mm
            out["void_y_mm"] = (cy - (self.n - 1) / 2.0) * self.pix_mm
        return out

    def _equiv_mm(self, n_px):
        """面積等価直径。円なので面積 → 直径が厳密に決まる。"""
        return 2.0 * np.sqrt(n_px / np.pi) * self.pix_mm


def report(tag, m, extra=""):
    void = "  --- (空洞が消えた)" if not np.isfinite(m["void_mm"]) else (
        f"  空洞 {m['void_mm']:6.3f} mm @ "
        f"({m['void_x_mm']:+.3f}, {m['void_y_mm']:+.3f}) mm")
    print(f"   {tag:26s} 外径 {m['outer_mm']:7.3f} mm  欠陥 {m['n_defect']:3d} 個"
          f"{void}{extra}")


# --------------------------------------------------------------------------- #
def main():
    ok = True
    angles = T.projection_angles(N_VIEWS, 180.0, "uniform")

    # ------------------------------------------------------------------ #
    _rule("1) 撮る前に決まる限界 と、閉形式の真値")
    # ------------------------------------------------------------------ #
    d = T.sinogram_design(n_angles=N_VIEWS, size=SIZE, detector_pitch_mm=PIX_MM)
    print(f"   視野                 = {d['field_of_view_mm']:.1f} mm "
          f"({d['n_detectors']} 検出器 x {PIX_MM} mm)")
    print(f"   分解できる最小構造   = {d['resolvable_feature_mm']:.2f} mm (Nyquist)")
    print(f"   完全標本化に要る視点 = {d['views_for_full_sampling']} 本 "
          f"(実際 {N_VIEWS} 本 -> {d['undersampling_factor']:.2f}x, {d['verdict']})")

    phantom = T.ellipse_phantom(SIZE, SAMPLE, supersample=4)
    mass_closed = np.pi * (R_OUT_MM ** 2 - R_VOID_MM ** 2) / PIX_MM ** 2 * RHO
    print(f"\n   試料: 外径 {2 * R_OUT_MM:.2f} mm の丸棒 + 空洞 "
          f"{2 * R_VOID_MM:.2f} mm @ ({VOID_X_MM:+.2f}, {VOID_Y_MM:+.2f}) mm")
    print(f"   総質量(画素単位)   閉形式 {mass_closed:.4f} / "
          f"ellipse_phantom {phantom.sum():.4f}  "
          f"(相対 {phantom.sum() / mass_closed - 1:+.2e})")
    assert abs(phantom.sum() / mass_closed - 1.0) < 1e-4

    # ------------------------------------------------------------------ #
    _rule("2) 投影 ―― 保存則で「投影器が正しい」を先に確かめる")
    # ------------------------------------------------------------------ #
    sino_exact = T.ellipse_sinogram(SIZE, SAMPLE, angles)      # 離散化誤差ゼロ
    sino_num = T.radon_transform(phantom, angles)              # 数値投影
    print(f"   ellipse_sinogram -> {sino_exact.shape}  peak {sino_exact.max():.6f}")
    print(f"   radon_transform  -> {sino_num.shape}  peak {sino_num.max():.6f}")

    # 保存則: 平行ビームでは、どの角度でも投影の和 = 物体の総質量
    rows = sino_num.sum(axis=1)
    rel = rows.mean() / phantom.sum() - 1.0
    spread = (rows.max() - rows.min()) / rows.mean()
    print(f"\n   ★保存則(角度によらず総和が等しい)")
    print(f"     投影 1 本の和(平均) = {rows.mean():.6f} / "
          f"ファントム総和 = {phantom.sum():.6f}  相対 {rel:+.2e}")
    print(f"     角度間のばらつき      = {spread:.2e} "
          f"(0 でないのは光線の標本化。0 から離れたら投影器が壊れている)")
    assert abs(rel) < 1e-4 and spread < 1e-3

    diff = float(np.sqrt(((sino_num - sino_exact) ** 2).mean()) / sino_exact.max())
    print(f"\n   数値投影 vs 閉形式    RMS = {diff:.4%} of peak "
          f"(差の正体はファントム自身の反エイリアス縁)")
    assert diff < 0.01

    # ------------------------------------------------------------------ #
    _rule("3) 再構成 3 種 ―― 寸法はどれで測れて、どれで測れないか")
    # ------------------------------------------------------------------ #
    t0 = time.perf_counter()
    rec_fbp = T.filtered_backprojection(sino_exact, angles)
    t_fbp = time.perf_counter() - t0
    n = rec_fbp.shape[0]
    pix_eff = SIZE * PIX_MM / n
    gauge = Gauge(n, pix_eff)
    truth = T.ellipse_phantom(n, SAMPLE, supersample=4)

    def nrms(img, ref=None):
        ref = truth if ref is None else ref
        return float(np.sqrt(((img - ref) ** 2).mean()) / (ref.max() - ref.min()))

    t0 = time.perf_counter()
    rec_bp = T.backproject_sinogram(sino_exact, angles)
    t_bp = time.perf_counter() - t0
    t0 = time.perf_counter()
    rec_sart = T.sart_reconstruct(sino_exact, angles, n_iter=10)
    t_sart = time.perf_counter() - t0

    # フィルタ無し BP は絶対スケールを持たない(1/|r| に有限積分が無い)。
    # 表示器の自動窓がやるのと同じ最小二乗の載せ替えをして初めて比較できる。
    design = np.stack([rec_bp.ravel(), np.ones(rec_bp.size)], 1)
    coef, *_ = np.linalg.lstsq(design, truth.ravel(), rcond=None)
    rec_bp_scaled = coef[0] * rec_bp + coef[1]

    print(f"   再構成格子 {rec_fbp.shape}  実効画素 {pix_eff:.5f} mm")
    print(f"   真値(閉形式)                外径 {2 * R_OUT_MM:7.3f} mm  欠陥   1 個"
          f"  空洞  {2 * R_VOID_MM:.3f} mm @ ({VOID_X_MM:+.3f}, {VOID_Y_MM:+.3f}) mm")
    m_truth = gauge(truth)
    report("この格子で二値化した真値", m_truth, "   <- 測定の天井")
    report("backproject_sinogram", gauge(rec_bp_scaled),
           f"   nRMS {nrms(rec_bp_scaled):.4f}  {t_bp:6.2f} s")
    report("filtered_backprojection", gauge(rec_fbp),
           f"   nRMS {nrms(rec_fbp):.4f}  {t_fbp:6.2f} s")
    report("sart_reconstruct(10)", gauge(rec_sart),
           f"   nRMS {nrms(rec_sart):.4f}  {t_sart:6.2f} s")
    print(f"   ★SART は nRMS を {nrms(rec_fbp) / nrms(rec_sart):.2f} 倍良くする代わりに "
          f"{t_sart / max(t_fbp, 1e-9):.0f} 倍の時間を買う "
          f"({t_fbp:.2f} s -> {t_sart:.1f} s、この機械での実測)。")
    print(f"     10 sweep x {N_VIEWS} 視点 = 順投影も逆投影も "
          f"{10 * N_VIEWS} 回で、FBP の逆投影 {N_VIEWS} 回に対する比そのもの。")
    print(f"     production の走査機が FBP を回しているのはこの一列のためである。")

    print(f"\n   フィルタ無し BP の生の値域 = "
          f"[{rec_bp.min():.4f}, {rec_bp.max():.4f}] "
          f"(真値は [{truth.min():.4f}, {truth.max():.5f}])")
    print(f"     -> 生の nRMS は {nrms(rec_bp):.1f}。1/|r| に有限積分が無いので "
          f"**絶対スケールが存在しない**。")
    print(f"     載せ替えて初めて {nrms(rec_bp_scaled):.4f} = FBP の "
          f"{nrms(rec_bp_scaled) / nrms(rec_fbp):.1f} 倍。これが ramp フィルタの寄与。")
    print(f"   ★それでも外径は {gauge(rec_bp_scaled)['outer_mm']:.3f} mm と "
          f"{gauge(rec_bp_scaled)['outer_mm'] / (2 * R_OUT_MM) - 1:+.2%} しか外さない。")
    print(f"     **壊れているのは寸法ではなく空洞**: 1/|r| のボケが埋めてしまい、"
          f"欠陥は {gauge(rec_bp_scaled)['n_defect']} 個になる。")

    m_fbp, m_sart = gauge(rec_fbp), gauge(rec_sart)
    assert gauge(rec_bp_scaled)["n_defect"] == 0        # BP では空洞が消える
    assert m_fbp["n_defect"] == 1 and m_sart["n_defect"] == 1
    assert abs(m_fbp["outer_mm"] - 2 * R_OUT_MM) < 0.05
    assert abs(m_fbp["void_mm"] - 2 * R_VOID_MM) < 0.10
    assert abs(m_fbp["void_x_mm"] - VOID_X_MM) < 0.05
    assert abs(m_fbp["void_y_mm"] - VOID_Y_MM) < 0.05
    assert nrms(rec_sart) < nrms(rec_fbp) < nrms(rec_bp_scaled)

    # ------------------------------------------------------------------ #
    _rule("4) 回転中心 ―― 測って直す。整数は厳密、半画素は戻らない")
    # ------------------------------------------------------------------ #
    print("   `sinogram_center_shift(s, shift_px=d)` は検出器軸に **-d** だけ動かす。")
    print("   つまり d を入れた結果の軸オフセットは -d。それを測り直せるか:")
    print("\n     入れた d | 測った軸オフセット | 誤差 px |  修正前 nRMS -> 修正後 |"
          " 修正後 外径 mm")
    print("     ---------+--------------------+---------+------------------------+"
          "---------------")
    biases = []
    for shift in (0.0, 0.5, 1.0, 2.0):
        moved = T.sinogram_center_shift(sino_exact, shift_px=shift, angles_deg=angles)
        est = T.sinogram_center_of_rotation(moved, angles)
        fixed = T.sinogram_center_shift(moved, angles_deg=angles)   # None -> 自動計測
        r_bad, r_fix = (T.filtered_backprojection(moved, angles),
                        T.filtered_backprojection(fixed, angles))
        biases.append(est + shift)
        print(f"     {shift:+8.2f} | {est:+18.6f} | {abs(est + shift):.1e} |"
              f"     {nrms(r_bad):.4f} -> {nrms(r_fix):.4f}     |"
              f"    {gauge(r_fix)['outer_mm']:.3f}")
    print(f"\n   ★推定誤差は入れたずれの大小によらず {np.mean(biases):+.2e} px で**一定**。")
    print("     推定器の性能ではなく、ファントムと検出器標本化の性質だから "
          "―― 定数であること")
    print("     そのものが「推定器が仕事をしている」ことの検算になる。")
    assert max(abs(b) for b in biases) < 1e-3
    assert np.std(biases) < 1e-6                      # 一定の偏り

    print("\n   往復(d 動かして -d 戻す)で何が落ちるか:")
    for shift in (1.0, 0.5, 0.25):
        there = T.sinogram_center_shift(sino_exact, shift_px=shift, angles_deg=angles)
        back = T.sinogram_center_shift(there, shift_px=-shift, angles_deg=angles)
        err = float(np.abs(back - sino_exact).max())
        note = "  <- 整数シフトは配列の付け替えなので厳密" if shift == 1.0 else ""
        print(f"     d = {shift:4.2f} px  max|Δ| = {err:.3e}  "
              f"(peak の {err / sino_exact.max():.2e}){note}")
        if shift == 1.0:
            assert err == 0.0
        else:
            assert err > 1e-3      # 補間は低域通過。戻らないことを固定する

    # ------------------------------------------------------------------ #
    _rule("5) ビームハードニング ―― 空洞が太って見える")
    # ------------------------------------------------------------------ #
    yy, xx = np.mgrid[0:n, 0:n] - (n - 1) / 2.0
    rr = np.hypot(yy, xx)
    r_px = nm(R_OUT_MM) * n / 2.0
    v_rr = np.hypot(yy - nm(VOID_Y_MM) * n / 2.0, xx - nm(VOID_X_MM) * n / 2.0)
    core = (rr < 0.22 * r_px) & (v_rr > 2.0 * nm(R_VOID_MM) * n / 2.0)
    rim = (rr > 0.80 * r_px) & (rr < 0.93 * r_px)

    def cupping(img):
        """中心/縁の平均比。1.0 なら平ら、1 未満がカッピング。"""
        return float(img[core].mean() / img[rim].mean())

    hard = T.beam_hardening_apply(sino_exact, high_energy_fraction=0.5,
                                  attenuation_ratio=0.4)
    rec_hard = T.filtered_backprojection(hard, angles)
    exact_inv = T.beam_hardening_correct(hard, 0.5, 0.4)
    rec_exact = T.filtered_backprojection(exact_inv, angles)

    print(f"   2 スペクトルモデル w=0.5, k=0.4 (I/I0 = (1-w)e^-p + w e^-kp)")
    print(f"   カッピング(中心/縁)  清浄 {cupping(rec_fbp):.4f}  "
          f"-> 硬化 {cupping(rec_hard):.4f}  -> モデル逆 {cupping(rec_exact):.4f}")
    report("清浄", m_fbp, f"   nRMS {nrms(rec_fbp):.4f}")
    report("硬化(未補正)", gauge(rec_hard), f"   nRMS {nrms(rec_hard):.4f}")
    report("モデル逆で補正", gauge(rec_exact), f"   nRMS {nrms(rec_exact):.4f}")
    m_hard = gauge(rec_hard)
    print(f"   ★空洞が {m_fbp['void_mm']:.3f} -> {m_hard['void_mm']:.3f} mm と "
          f"{m_hard['void_mm'] / m_fbp['void_mm'] - 1:+.1%} 太って見える "
          f"―― 中心が暗くなるので")
    print("     しきい値が空洞側へ食い込む。**欠陥は 1 個のまま**なので、"
          "数を見ていても気付けない。")

    rt = float(np.abs(exact_inv - sino_exact).max())
    print(f"\n   往復(apply -> correct)  max|Δ| = {rt:.3e} "
          f"= peak の {rt / sino_exact.max():.2e}  (逆表の刻みそのもの)")
    assert rt / sino_exact.max() < 1e-6
    assert cupping(rec_hard) < 0.94 < cupping(rec_exact)
    assert abs(cupping(rec_exact) - cupping(rec_fbp)) < 1e-6

    # 実データ側の経路: 同じ材料の一様棒を撮って多項式を較正する
    water = [(0.0, 0.0, nm(12.0), nm(12.0), 0.0, RHO)]
    cal_clean = T.ellipse_sinogram(SIZE, water, angles)
    cal_hard = T.beam_hardening_apply(cal_clean, 0.5, 0.4)
    m = cal_clean > 1e-6
    design = np.stack([cal_hard[m], cal_hard[m] ** 2], 1)
    c, *_ = np.linalg.lstsq(design, cal_clean[m], rcond=None)
    rec_poly = T.filtered_backprojection(
        T.beam_hardening_correct(hard, poly_coeffs=tuple(c)), angles)
    rec_naive = T.filtered_backprojection(
        T.beam_hardening_correct(hard, poly_coeffs=(1.0, 0.18)), angles)
    print(f"\n   多項式経路(実データで使えるのはこちら。w, k は誰も知らない)")
    print(f"     一様棒 φ24 mm を撮って較正 -> c = "
          f"({c[0]:.4f}, {c[1]:.4f})   (小 p 展開の 1/(1-w+wk) = "
          f"{1 / (1 - 0.5 + 0.5 * 0.4):.4f} が c1 の予言値)")
    print(f"     較正あり (c1={c[0]:.3f}, c2={c[1]:.3f}) : "
          f"カッピング {cupping(rec_poly):.4f}  nRMS {nrms(rec_poly):.4f}")
    print(f"     較正なし (c1=1.000, c2=0.180) : "
          f"カッピング {cupping(rec_naive):.4f}  nRMS {nrms(rec_naive):.4f}")
    print("   ★★正直な結論 ―― **カッピングを平らにすることと、密度が合うことは別**。")
    print(f"     較正なしの多項式はカッピングを {cupping(rec_naive):.4f} まで"
          f"(むしろ行き過ぎて)平らにするのに、")
    print(f"     nRMS は {nrms(rec_naive):.4f} と硬化したまま "
          f"({nrms(rec_hard):.4f}) からほとんど改善しない。c1 が 1 では")
    print(f"     全体の倍率が {c[0]:.3f} 倍ずれたままだからで、"
          f"**画が平らになったことは補正の証拠にならない**。")
    assert abs(c[0] - 1 / 0.7) < 0.02              # 小 p 展開の予言と一致
    assert abs(cupping(rec_poly) - 1.0) < 0.02 and nrms(rec_poly) < 1.05 * nrms(rec_fbp)
    assert cupping(rec_naive) > 1.0 and nrms(rec_naive) > 3.0 * nrms(rec_fbp)

    # ------------------------------------------------------------------ #
    _rule("6) リング ―― 検出器 1 画素の利得誤差が、偽の空洞を生む")
    # ------------------------------------------------------------------ #
    n_det = sino_exact.shape[1]
    one_off = np.zeros(n_det)
    one_off[n_det // 2 + 40] = 0.15
    rec_one = T.filtered_backprojection(
        T.ring_artifact_apply(sino_exact, offsets=one_off), angles)
    print(f"   検出器 {n_det} bin のうち 1 本だけ利得誤差 0.15 -> "
          f"nRMS {nrms(rec_fbp):.4f} -> {nrms(rec_one):.4f}")
    print("     角度によらない一定オフセットを逆投影すると、その bin の光線が"
          "接する半径に円が 1 本立つ。")

    ringed = T.ring_artifact_apply(sino_exact, gain_sigma=0.02, seed=0)
    rec_ring = T.filtered_backprojection(ringed, angles)
    m_ring = gauge(rec_ring)
    print(f"\n   全 bin に N(0, 0.02) の利得誤差:")
    report("清浄", m_fbp, f"   nRMS {nrms(rec_fbp):.4f}")
    report("リングあり", m_ring, f"   nRMS {nrms(rec_ring):.4f}")
    print(f"   ★外径は {m_ring['outer_mm']:.3f} mm と "
          f"{m_ring['outer_mm'] / m_fbp['outer_mm'] - 1:+.3%} しか動かないのに、"
          f"欠陥が 1 -> {m_ring['n_defect']} 個。")
    print(f"     増えた {m_ring['n_defect'] - 1} 個は**リングがしきい値を割った"
          f"だけの偽の空洞**である。")

    print("\n   窓を振る(除去率 = 元に戻った割合 / 副作用 = 清浄なサイノグラムを"
          "同じ設定で処理した悪化):")
    print("     窓  mode     除去後 nRMS   除去率   清浄への副作用")
    print("     --------------------------------------------------")
    removals = {}
    for window, mode in ((3, "median"), (5, "median"), (7, "median"),
                         (11, "median"), (5, "mean")):
        fixed = T.ring_artifact_remove(ringed, window=window, mode=mode)
        r = T.filtered_backprojection(fixed, angles)
        collateral = nrms(T.filtered_backprojection(
            T.ring_artifact_remove(sino_exact, window=window, mode=mode),
            angles)) - nrms(rec_fbp)
        undone = (nrms(rec_ring) - nrms(r)) / (nrms(rec_ring) - nrms(rec_fbp))
        removals[(window, mode)] = (nrms(r), undone, collateral)
        print(f"     {window:2d}  {mode:6s}    {nrms(r):.4f}     {undone:5.1%}"
              f"   {collateral:+.5f}")
    rec_deringed = T.filtered_backprojection(
        T.ring_artifact_remove(ringed, window=5, mode="median"), angles)
    report("既定 (5, median) で除去", gauge(rec_deringed),
           f"   nRMS {nrms(rec_deringed):.4f}")
    print("   既定が (5, median) なのは、**除去率が最大だからではなく**、"
          "清浄なサイノグラムに")
    print(f"     ほとんど何もしないから(副作用 "
          f"{removals[(5, 'median')][2]:+.5f} に対し (5, mean) は "
          f"{removals[(5, 'mean')][2]:+.5f})。")
    assert m_ring["n_defect"] > m_fbp["n_defect"]
    assert gauge(rec_deringed)["n_defect"] == 1
    assert removals[(5, "median")][1] > 0.5
    assert abs(removals[(5, "median")][2]) < 1e-4 < removals[(5, "mean")][2]

    # ------------------------------------------------------------------ #
    _rule("7) 金属 ―― ストリークは偽の欠陥を 35 個作る")
    # ------------------------------------------------------------------ #
    sino_metal = T.ellipse_sinogram(SIZE, SAMPLE_METAL, angles)
    rec_metal = T.filtered_backprojection(sino_metal, angles)
    rec_limar = T.filtered_backprojection(
        T.metal_trace_interpolate(sino_metal, angles), angles)

    # インサートの足跡の外だけで評価する(中は「金属を消した」ので当然合わない)
    m_cy = nm(METAL_Y_MM) * n / 2.0 + (n - 1) / 2.0
    m_cx = nm(METAL_X_MM) * n / 2.0 + (n - 1) / 2.0
    gy, gx = np.mgrid[0:n, 0:n]
    outside = np.hypot(gy - m_cy, gx - m_cx) > 2.5 * nm(METAL_R_MM) * n / 2.0

    def nrms_out(img):
        return float(np.sqrt(((img - truth)[outside] ** 2).mean())
                     / (truth.max() - truth.min()))

    print(f"   φ{2 * METAL_R_MM:.1f} mm、アルミの {METAL_DENSITY:.0f} 倍の"
          f"インサートを ({METAL_X_MM:+.1f}, {METAL_Y_MM:+.1f}) mm に置く")
    print(f"   足跡の外での nRMS   清浄 {nrms_out(rec_fbp):.4f}  -> "
          f"金属あり {nrms_out(rec_metal):.4f}  -> LI-MAR {nrms_out(rec_limar):.4f}")
    m_metal, m_limar = gauge(rec_metal), gauge(rec_limar)
    report("清浄", m_fbp)
    report("金属あり", m_metal, f"   ピーク {rec_metal.max() / RHO:.1f} x RHO")
    report("metal_trace_interpolate", m_limar,
           f"   ピーク {rec_limar.max() / RHO:.2f} x RHO")
    print(f"   ★外径は {m_metal['outer_mm']:.3f} mm(清浄 {m_fbp['outer_mm']:.3f})"
          f"とほぼ変わらないのに、欠陥は 1 -> {m_metal['n_defect']} 個。")
    print(f"     LI-MAR は像側でしきい値を切り、その二値マスクを再投影した bin を"
          f"「欠測」として")
    print(f"     検出器軸に線形補間する。結果、偽欠陥は "
          f"{m_metal['n_defect']} -> {m_limar['n_defect']} 個に戻り、"
          f"nRMS も {nrms_out(rec_metal):.4f} -> {nrms_out(rec_limar):.4f}。")
    print(f"     代償は正直に: **足跡の中の金属は消えている**(ピークが "
          f"{rec_metal.max() / RHO:.1f} -> {rec_limar.max() / RHO:.2f} x RHO)。")
    print("     臨床では閾値像から金属を描き戻すが、その段は実装されていない。")
    assert m_metal["n_defect"] > 10 and m_limar["n_defect"] == 1
    assert nrms_out(rec_limar) < 0.25 * nrms_out(rec_metal)
    assert rec_limar.max() < 0.1 * rec_metal.max()

    # ------------------------------------------------------------------ #
    _rule("8) 正直な結論 ―― 外径は壊れても壊れたと言わない")
    # ------------------------------------------------------------------ #
    table = [("閉形式の真値", 2 * R_OUT_MM, 1),
             ("この格子の天井", m_truth["outer_mm"], m_truth["n_defect"]),
             ("FBP(清浄)", m_fbp["outer_mm"], m_fbp["n_defect"]),
             ("SART(清浄)", m_sart["outer_mm"], m_sart["n_defect"]),
             ("フィルタ無し BP", gauge(rec_bp_scaled)["outer_mm"],
              gauge(rec_bp_scaled)["n_defect"]),
             ("ビームハードニング", m_hard["outer_mm"], m_hard["n_defect"]),
             ("リング", m_ring["outer_mm"], m_ring["n_defect"]),
             ("金属", m_metal["outer_mm"], m_metal["n_defect"])]
    print("   条件                   外径 mm    真値比    欠陥の数")
    print("   ----------------------------------------------------")
    for tag, outer, nd in table:
        print(f"   {tag:22s} {outer:7.3f}   {outer / (2 * R_OUT_MM) - 1:+7.2%}"
              f"     {nd:3d}")
    outers = [o for _, o, _ in table]
    counts = [c for _, _, c in table]
    span = (max(outers) - min(outers)) / (2 * R_OUT_MM)
    print(f"\n   外径の振れ幅   = {span:.2%}(5 種の故障すべてを含めて)")
    print(f"   欠陥の数の範囲 = {min(counts)} - {max(counts)} 個 "
          f"({max(counts) / max(min(counts), 1):.0f} 倍)")
    print("   ★寸法だけを見ている検査は、サイノグラムが壊れていることに"
          "気付けない。壊れたことを")
    print("     教えるのは**積分量(外径・面積)ではなく、位相のある量"
          "(欠陥の数・位置)**である。")
    assert span < 0.01                                # 外径はどの故障でも 1% 未満
    assert max(counts) > 10 * max(min(counts), 1)     # 欠陥数は桁で壊れる

    # ------------------------------------------------------------------ #
    _rule("9) fail-closed ―― 黙って通さない")
    # ------------------------------------------------------------------ #
    cases = [
        ("角度数がサイノグラムの行数と不一致",
         lambda: T.filtered_backprojection(sino_exact, angles[:10])),
        ("知らないフィルタ名",
         lambda: T.filtered_backprojection(sino_exact, angles, filter_name="brick")),
        ("cutoff が 0",
         lambda: T.filtered_backprojection(sino_exact, angles, cutoff=0.0)),
        ("SART の緩和係数 2.5(発散する)",
         lambda: T.sart_reconstruct(sino_exact, angles, n_iter=1, relaxation=2.5)),
        ("負の線積分を硬化させる",
         lambda: T.beam_hardening_apply(sino_exact - 1.0)),
        ("リング除去の窓が偶数",
         lambda: T.ring_artifact_remove(sino_exact, window=4)),
        ("視野の外まで中心をずらす",
         lambda: T.sinogram_center_shift(sino_exact, shift_px=n_det)),
        ("視点 3 本未満で回転中心を測る",
         lambda: T.sinogram_center_of_rotation(sino_exact[:2], angles[:2])),
        ("10 度の楔で回転中心を測る(有限で符号まで間違う)",
         lambda: T.sinogram_center_of_rotation(
             T.ellipse_sinogram(SIZE, SAMPLE, np.linspace(0.0, 10.0, 40)),
             np.linspace(0.0, 10.0, 40))),
        ("金属マスクの形が合わない",
         lambda: T.metal_trace_interpolate(sino_exact, angles,
                                           mask=np.zeros((3, 3), bool))),
        ("非有限のサイノグラム",
         lambda: T.filtered_backprojection(sino_exact * np.nan, angles)),
    ]
    passed = 0
    for tag, fn in cases:
        try:
            fn()
        except ValueError as exc:
            print(f"   拒否 {tag:40s}: {str(exc).split('.')[0][:56]}")
        else:
            passed += 1
            print(f"   ★通過 {tag:40s}: 拒否されなかった")
    print(f"\n   {len(cases) - passed}/{len(cases)} が文書化された ValueError で拒否")
    if passed:
        ok = False

    print(f"\nPASS: 投影 -> 再構成 -> 外径 {m_fbp['outer_mm']:.3f} mm "
          f"(真値 {2 * R_OUT_MM:.2f} mm, {m_fbp['outer_mm'] / (2 * R_OUT_MM) - 1:+.2%}) "
          f"/ 空洞 {m_fbp['void_mm']:.3f} mm (真値 {2 * R_VOID_MM:.2f} mm) まで閉じた。")
    print(f"      tomography 17 op のうち 15 op を実行 "
          f"(残る 2 op = radon_volume / fbp_volume は 3-D 側で、"
          f"examples/tomography_reconstruct.py が通す)。")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
