# -*- coding: utf-8 -*-
"""事例: 曲座標展開で回転体の m 回対称を極/円筒/Zernike/LiDAR円筒投影から一貫復元 (metrology).

平たく言うと:
  回転体(円板・円筒・柱)の検査は、デカルト格子のままだと「ぐるり一周のパターン」を
  素直に読めない。中心を原点にした**曲座標(極 r-θ / 円筒 z-θ-r)へ展開**すると、周方向の
  特徴が 1 本の軸に並び、ふつうの 1D/2D 手法(FFT・直線探索)がそのまま効く。ここでは
  同じ「m=3 回対称(3 枚羽根)」を持つ回転体を、表現の異なる 4 つの op で作った 3 種の入力
  (2D 画像 / 3D voxel / 3D 点群)から取り出し、**どの曲座標展開でも同じ m が出る**ことを見る:
    - polar_unwrap       : 2D 画像の円板を (θ×r) 矩形へ → θ 軸の FFT で m を読む
    - cylinder_unwrap    : 3D voxel の円筒面を (z×θ×r) へ → 各高さ z で θ 軸 FFT が m
    - project_cylindrical: 3D 点群を円筒レンジ画像 (z×方位) へ → 方位軸 FFT が m
    - fit_zernike        : 円板上の曲面を極座標直交基底 (n,m) へ分解(波面計測の要)。
                           2θ の非点収差(astigmatism)= m=2 角モードが係数に立つことを確認。

検証(GT):
  * fit_zernike: 既知係数(piston/tilt/defocus/astigmatism)で合成した円板を入れ、
    lstsq が各係数を小数第 2 位まで復元、混入していないモードは ~0 であること。
  * polar_unwrap / cylinder_unwrap / project_cylindrical: 生成時に角周波数 m=3 を仕込む。
    展開後の周方向 FFT の最大ビンが厳密に m、しかも m での power が他ビンを桁で圧倒すること。
    円筒投影の画素は水平半径 ρ なので、平均 ρ が真の半径 R0、値域が R0±A に収まることも照合。

beat-the-null:
  * polar_unwrap: 回転対称(r のみに依存)な画像は θ 軸方向の分散がほぼ 0。羽根(角依存)画像は
    大きな分散。同じ op に通して分散が桁で違う=展開が角情報を確かに軸へ移している。
  * project_cylindrical: 半径を θ で変えず乱数にした「円筒でない」点群を零点とし、方位軸 FFT の
    m での power が羽根つき円筒の何倍も小さい(スペクトルが広帯域に散る)ことを assert する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import match3d as M  # noqa: E402  (polar_unwrap / cylinder_unwrap / fit_zernike)
from spherical_proj import project_cylindrical  # noqa: E402

M_FOLD = 3          # 仕込む回転対称の次数(3 枚羽根)。全 op で同じ m を復元できるかを見る。


def dominant_freq(signal_1d):
    """実 1D 信号の直流を抜いた rfft で、支配的な角周波数ビンと power スペクトルを返す。"""
    s = np.asarray(signal_1d, float)
    spec = np.abs(np.fft.rfft(s - s.mean()))
    return int(np.argmax(spec)), spec


# ═══════════════════════════════════════════════════════════════════════════
# 共通の合成: 中心対称の座標(正規化した極座標)を 256×256 画像上に用意する。
# ═══════════════════════════════════════════════════════════════════════════
N = 256
_cy = _cx = (N - 1) / 2.0
_rad = N / 2.0 - 1.0                       # fit_zernike/polar_unwrap と同じ内接円半径規約
_ii, _jj = np.mgrid[0:N, 0:N]
DX = (_jj - _cx) / _rad
DY = (_ii - _cy) / _rad
RHO = np.hypot(DX, DY)                     # 正規化半径(内接円で 1)
THETA = np.arctan2(DY, DX)                 # 方位角


def main():
    # ─────────────────────────────────────────────────────────────────────
    # 1) fit_zernike: 既知の波面係数を仕込んだ円板 → 極座標直交基底へ分解して復元
    #    基底(この実装の生 Zernike): (0,0)=piston, (1,±1)=tilt, (2,0)=defocus,
    #    (2,±2)=astigmatism(cos2θ/sin2θ の m=2 角モード)。
    # ─────────────────────────────────────────────────────────────────────
    c = {(0, 0): 0.30, (1, 1): 0.70, (2, 0): 1.20, (2, 2): -0.50}   # 真値
    disk = (c[(0, 0)] * np.ones_like(RHO)
            + c[(1, 1)] * RHO * np.cos(THETA)
            + c[(2, 0)] * (2.0 * RHO**2 - 1.0)
            + c[(2, 2)] * RHO**2 * np.cos(2.0 * THETA))
    coef = M.fit_zernike(disk, n_max=6)

    zern_err = max(abs(coef[k] - v) for k, v in c.items())          # 仕込んだモードの復元誤差
    injected_energy = sum(v * v for v in c.values())
    leak_energy = sum(v * v for k, v in coef.items() if k not in c)  # 混入していないモードの漏れ
    astig_mag = abs(coef[(2, 2)])                                    # m=2 角モード(非点収差)

    print("[fit_zernike] 円板の波面を極座標直交基底 (n,m) へ分解")
    print(f"  復元 (0,0)={coef[(0,0)]:+.4f} (1,1)={coef[(1,1)]:+.4f} "
          f"(2,0)={coef[(2,0)]:+.4f} (2,2)={coef[(2,2)]:+.4f}")
    print(f"  仕込みモード最大誤差={zern_err:.2e}  未仕込みモードの漏れエネルギー={leak_energy:.2e}")

    assert zern_err < 2e-2, f"Zernike 係数の復元誤差が大きい: {zern_err:.3e}"
    assert leak_energy < 1e-2 * injected_energy, \
        f"未仕込みモードへの漏れが大きい: {leak_energy:.3e} vs 仕込み {injected_energy:.3e}"
    assert astig_mag > 0.4, f"非点収差(m=2 角モード)が立っていない: {astig_mag:.3f}"

    # ─────────────────────────────────────────────────────────────────────
    # 2) polar_unwrap: 2D 画像の円板を (θ×r) へ展開。羽根 cos(mθ) 画像の θ 軸 FFT で m を読む。
    #    beat-null: 回転対称(r のみ依存)画像は θ 軸分散がほぼ 0。
    # ─────────────────────────────────────────────────────────────────────
    vane_img = np.cos(M_FOLD * THETA)                       # m 枚羽根(角依存)
    unwrapped = M.polar_unwrap(vane_img, ntheta=360, nr=64)  # (θ, r)
    assert unwrapped.shape == (360, 64), f"polar_unwrap 形状が想定外: {unwrapped.shape}"

    theta_line = unwrapped[:-1, 40]                          # 中半径の θ 断面(端の重複を除く)
    f_polar, sp_polar = dominant_freq(theta_line)
    peak_pw = sp_polar[M_FOLD]
    other_pw = np.max(np.delete(sp_polar[1:], M_FOLD - 1))   # m 以外の最大 power

    sym_img = (RHO <= 1.0) * np.sin(4.0 * RHO)              # 回転対称(角に依存しない同心リング)
    unwrapped_sym = M.polar_unwrap(sym_img, ntheta=360, nr=64)
    var_vane = float(unwrapped.var(axis=0).mean())           # θ 軸の分散(羽根)
    var_sym = float(unwrapped_sym.var(axis=0).mean())        # θ 軸の分散(対称)
    deterministic = np.array_equal(unwrapped, M.polar_unwrap(vane_img, ntheta=360, nr=64))

    print("[polar_unwrap] 円板 → (θ×r) 展開、θ 軸 FFT で羽根の次数を読む")
    print(f"  θ軸の支配周波数={f_polar}(期待 {M_FOLD})  power@m={peak_pw:.1f} / 他最大={other_pw:.2f}")
    print(f"  θ軸分散  羽根={var_vane:.4f}  回転対称={var_sym:.6f}(beat-null)  決定的={deterministic}")

    assert f_polar == M_FOLD, f"polar_unwrap の θ 軸に m={M_FOLD} が出ない: {f_polar}"
    assert peak_pw > 50.0 and peak_pw > 50.0 * (other_pw + 1e-9), \
        f"m の power が他ビンを圧倒していない: {peak_pw:.1f} vs {other_pw:.3f}"
    assert deterministic, "polar_unwrap が非決定的"
    assert var_sym < 1e-3 and var_vane > 100.0 * var_sym, \
        f"回転対称 null を分離できていない: 羽根 {var_vane:.4f} vs 対称 {var_sym:.6f}"

    # ─────────────────────────────────────────────────────────────────────
    # 3) cylinder_unwrap: 3D voxel の円筒殻を (z×θ×r) へ展開。z 一様・角に cos(mθ) を載せた殻。
    #    各高さ z の θ 軸 FFT が全て m、殻の半径 R_shell を径方向ビンから復元できるか。
    # ─────────────────────────────────────────────────────────────────────
    D, H, W = 24, 128, 128
    cyv = cxv = (H - 1) / 2.0
    yy, xx = np.mgrid[0:H, 0:W]
    r2 = np.hypot(yy - cyv, xx - cxv)
    th2 = np.arctan2(yy - cyv, xx - cxv)
    R_shell, sigma = 40.0, 4.0
    shell = np.exp(-((r2 - R_shell) / sigma) ** 2) * (1.0 + 0.5 * np.cos(M_FOLD * th2))
    vol = np.repeat(shell[None, :, :], D, axis=0)           # z 方向に一様な円筒殻
    cyl = M.cylinder_unwrap(vol, ntheta=180, nr=32)          # (z, θ, r)
    assert cyl.shape == (D, 180, 32), f"cylinder_unwrap 形状が想定外: {cyl.shape}"

    r_out = min(H, W) / 2.0 - 1.0
    bin_w = r_out / (32 - 1)
    peak_nr = int(np.argmax(cyl.mean(axis=(0, 1))))          # 径方向の輝度ピーク=殻の位置
    rec_R = peak_nr / (32 - 1) * r_out
    z_freqs = {dominant_freq(cyl[z, :-1, peak_nr])[0] for z in range(D)}  # 各高さの θ 周波数
    mid_pw = dominant_freq(cyl[D // 2, :-1, peak_nr])[1][M_FOLD]

    print("[cylinder_unwrap] 円筒殻 → (z×θ×r) 展開、殻半径と各 z の角次数を読む")
    print(f"  殻半径 復元={rec_R:.2f} / 真値={R_shell:.2f}(1 ビン幅={bin_w:.2f})")
    print(f"  各高さ z の θ 支配周波数 集合={sorted(z_freqs)}(期待 {{{M_FOLD}}})  power@m={mid_pw:.1f}")

    assert abs(rec_R - R_shell) < bin_w, f"殻半径の復元がビン幅超: {rec_R:.2f} vs {R_shell:.2f}"
    assert z_freqs == {M_FOLD}, f"全高さで m={M_FOLD} を復元できていない: {sorted(z_freqs)}"
    assert mid_pw > 10.0, f"円筒展開の m power が弱い: {mid_pw:.2f}"

    # ─────────────────────────────────────────────────────────────────────
    # 4) project_cylindrical: 3D 点群 → 円筒レンジ画像。半径を ρ(θ)=R0+A·cos(mθ) の溝付き柱に。
    #    方位軸 FFT が m、画素(=水平半径 ρ)の平均が R0、値域が R0±A。
    #    beat-null: 半径を θ で変えず乱数にした「円筒でない」点群は m power が桁で小さい。
    # ─────────────────────────────────────────────────────────────────────
    h_res, z_bins = 360, 48
    R0, A = 5.0, 0.8
    az = (np.arange(h_res) + 0.5) / h_res * 2.0 * np.pi - np.pi   # 方位ビン中心
    rho_theta = R0 + A * np.cos(M_FOLD * az)                      # 溝付き柱の半径 ρ(θ)
    zs = np.linspace(0.5, 9.5, 30)
    pts = np.array([[rho_theta[k] * np.cos(az[k]), rho_theta[k] * np.sin(az[k]), z]
                    for z in zs for k in range(h_res)])
    cyl_img = project_cylindrical(pts, h_res=h_res, z_bins=z_bins, z_range=(0.0, 10.0))
    assert cyl_img.shape == (z_bins, h_res), f"project_cylindrical 形状が想定外: {cyl_img.shape}"

    occ = cyl_img[cyl_img > 0.0]
    row = cyl_img[z_bins // 2]
    f_proj, sp_proj = dominant_freq(row)
    proj_pw = sp_proj[M_FOLD]

    rng = np.random.default_rng(0)
    pts_null = np.array([[r * np.cos(az[k]), r * np.sin(az[k]), z]
                         for z in zs for k, r in
                         ((k, rng.uniform(R0 - A, R0 + A)) for k in range(h_res))])
    null_img = project_cylindrical(pts_null, h_res=h_res, z_bins=z_bins, z_range=(0.0, 10.0))
    f_null, sp_null = dominant_freq(null_img[z_bins // 2])
    null_pw = sp_null[M_FOLD]

    print("[project_cylindrical] 溝付き柱の点群 → 円筒レンジ画像、方位軸 FFT で溝の次数を読む")
    print(f"  画素 ρ 平均={occ.mean():.3f}(真 R0={R0}) 値域[{occ.min():.2f},{occ.max():.2f}]"
          f"(真 R0±A=[{R0-A:.2f},{R0+A:.2f}])")
    print(f"  方位軸 支配周波数={f_proj}(期待 {M_FOLD})  power@m 柱={proj_pw:.1f} / 零点={null_pw:.1f}")

    assert abs(occ.mean() - R0) < 0.05, f"円筒レンジ画素の平均半径が R0 とずれる: {occ.mean():.3f}"
    assert occ.min() >= R0 - A - 0.05 and occ.max() <= R0 + A + 0.05, \
        f"画素 ρ の値域が R0±A を外れる: [{occ.min():.3f},{occ.max():.3f}]"
    assert f_proj == M_FOLD, f"方位軸に m={M_FOLD} が出ない: {f_proj}"
    assert f_null != M_FOLD, f"零点(乱数半径)が m={M_FOLD} を出してしまう: {f_null}"
    assert proj_pw > 5.0 * null_pw, \
        f"溝付き柱が零点を圧倒できていない: power@m 柱 {proj_pw:.1f} vs 零点 {null_pw:.1f}"

    # ─────────────────────────────────────────────────────────────────────
    # 5) 合成の締め: 3 種の曲座標展開が同一の m を復元(表現非依存)。
    # ─────────────────────────────────────────────────────────────────────
    assert f_polar == f_cyl_all(z_freqs) == f_proj == M_FOLD
    print(f"PASS: 曲座標展開 4 op を検証 — fit_zernike が波面係数を誤差 {zern_err:.1e} で復元"
          f"(非点収差=m2 角モード)、polar/cylinder/project の 3 展開が 2D画像・3Dvoxel・3D点群"
          f"から一致して m={M_FOLD} を復元(θ軸分散 羽根/対称={var_vane/var_sym:.0f}倍、"
          f"円筒投影 power@m 柱/零点={proj_pw/max(null_pw,1e-9):.0f}倍)。殻半径 {rec_R:.1f}≈{R_shell:.0f}")


def f_cyl_all(freq_set):
    """cylinder_unwrap の全高さで一致した唯一の角周波数を返す(集合が単一である前提)。"""
    assert len(freq_set) == 1
    return next(iter(freq_set))


if __name__ == "__main__":
    main()
