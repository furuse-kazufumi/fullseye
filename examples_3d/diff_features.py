# -*- coding: utf-8 -*-
"""事例: 3-D スカラー場から微分特徴(勾配・Hessian・曲率・距離場・暗構造)を抽出する (features).

平たく言うと: ボリューム(3D CT/密度場)を「見る」には、まず各点の傾き(勾配 = sobel3d)と
曲がり方(Hessian = hessian3d)という微分量を計算する。この 2 つを組み合わせると等値面の
**曲面型**(お椀状の cap か・樋状の ridge か)が shape index として出る(curvature_maps)。
さらに種点からの**ユークリッド距離場**(edt_jfa)で「表面までどれだけ奥か」を測り、
モルフォロジの**black-hat**(morph_blackhat3d)で部品内部の**微小な空隙(欠陥)**を炙り出す。
本例はこの 5 つを 1 本の部品(球状ソリッド)の周りで噛み合わせ、各々を解析的な真値で裏取りする。

検証(GT):
  - sobel3d   : 既知の 2 次多項式場に当て、勾配 (gz,gy,gx)/32 が解析勾配を機械精度で復元
                (分離 conv の利得 = 2(中心差分)×4×4(平滑)= 32)。
  - hessian3d : 同じ場で 6 独立成分 (fzz,fyy,fxx,fzy,fzx,fyx) が解析 Hessian を機械精度で復元。
  - curvature_maps : sobel3d+hessian3d を内部に持つ。明るい球 blob の等値面は shape index
                S≈+1(cap)、円柱 blob は S≈+0.5(ridge)。curvedness は球半径に反比例(∝1/r)。
  - edt_jfa   : 球中心 1 点を種にした距離場が、球を定義する半径座標 r を厳密復元(scipy EDT 一致)。
  - morph_blackhat3d : ソリッド内部の暗い空隙(1 voxel)を black-hat が正確に mask 復元。

beat-the-null:
  - sobel/hessian は定数場で勾配≈0・線形場で Hessian≈0(微分が形に反応している裏取り)。
  - shape index は球(cap)と円柱(ridge)を判別的に分離(差 >0.3)。単なる強度/勾配の大小では
    「明るい凸」で一括りになり球と円柱を分けられない。
  - edt_jfa はユークリッド距離であり、箱型の Chebyshev(L∞)距離とは大きく食い違う(>5 voxel)。
  - black-hat は暗い空隙で立ち上がり(≈1)、空隙の無いソリッドや white top-hat では立たない(≈0)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import match3d as M

N = 48
zz, yy, xx = np.mgrid[0:N, 0:N, 0:N].astype(np.float64)
cz = cy = cx = (N - 1) / 2.0
r = np.sqrt((zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2)     # 部品の半径座標(全 op で共有)

# ══════════════════════════════════════════════════════════════════════════
# 1) sobel3d / hessian3d — 既知の 2 次多項式場で微分作用素を機械精度で裏取り
# ══════════════════════════════════════════════════════════════════════════
# f = a·z+b·y+c·x + 1/2(α z²+β y²+γ x²) + δ zy + ε zx + ζ yx
a, b, c = 0.70, -1.30, 0.40
al, be, ga = 0.11, -0.23, 0.17           # 対角 Hessian 成分の真値
de, ep, ze = 0.05, -0.09, 0.13           # 非対角 Hessian 成分の真値
f = (a * zz + b * yy + c * xx
     + 0.5 * (al * zz ** 2 + be * yy ** 2 + ga * xx ** 2)
     + de * zz * yy + ep * zz * xx + ze * yy * xx)

# 解析勾配(位置依存)
Az = a + al * zz + de * yy + ep * xx
Ay = b + be * yy + de * zz + ze * xx
Ax = c + ga * xx + ep * zz + ze * yy

gz, gy, gx = M.sobel3d(f)                 # 各 (1,1,D,H,W) の torch tensor
gz, gy, gx = gz[0, 0].numpy(), gy[0, 0].numpy(), gx[0, 0].numpy()
sl = slice(3, N - 3)                       # replicate 境界を避けた内部領域
GAIN = 32.0                                # 分離 conv の利得 2×4×4
e_gz = np.max(np.abs(gz[sl, sl, sl] / GAIN - Az[sl, sl, sl]))
e_gy = np.max(np.abs(gy[sl, sl, sl] / GAIN - Ay[sl, sl, sl]))
e_gx = np.max(np.abs(gx[sl, sl, sl] / GAIN - Ax[sl, sl, sl]))
print(f"sobel3d   : |grad/32 - 解析勾配| max = {max(e_gz, e_gy, e_gx):.2e}")
assert e_gz < 5e-4 and e_gy < 5e-4 and e_gx < 5e-4, "sobel3d が解析勾配を復元していない"

fzz, fyy, fxx, fzy, fzx, fyx = [h.numpy() for h in M.hessian3d(f)]   # 各 (D,H,W)
truth = {"fzz": al, "fyy": be, "fxx": ga, "fzy": de, "fzx": ep, "fyx": ze}
got = {"fzz": fzz, "fyy": fyy, "fxx": fxx, "fzy": fzy, "fzx": fzx, "fyx": fyx}
e_hess = max(np.max(np.abs(got[k][sl, sl, sl] - truth[k])) for k in truth)
print(f"hessian3d : |H成分 - 解析Hessian| max = {e_hess:.2e}  (6 独立成分)")
assert e_hess < 5e-4, "hessian3d が解析 Hessian を復元していない"

# beat-null: 定数場 → 勾配≈0 / 線形場 → Hessian≈0
gz0, gy0, gx0 = M.sobel3d(np.full((N, N, N), 3.14))
null_grad = max(float(g[0, 0].abs().max()) for g in (gz0, gy0, gx0))
lin = 2.0 * zz - 0.5 * yy + 1.3 * xx
null_hess = max(float(np.abs(h.numpy()[sl, sl, sl]).max()) for h in M.hessian3d(lin))
print(f"  null: 定数場の |grad| max = {null_grad:.2e} / 線形場の |Hessian| max = {null_hess:.2e}")
assert null_grad < 1e-5, "定数場で勾配が立ってしまっている"
assert null_hess < 1e-4, "線形場で Hessian が立ってしまっている"

# ══════════════════════════════════════════════════════════════════════════
# 2) curvature_maps — sobel3d+hessian3d を組み上げて等値面の曲面型を判別
# ══════════════════════════════════════════════════════════════════════════
sigma = 6.0
sphere = np.exp(-r ** 2 / (2 * sigma ** 2))                       # 明るい球 blob → cap
rho = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)                    # z 軸まわりの半径
cyl = np.exp(-rho ** 2 / (2 * sigma ** 2))                        # 明るい円柱 blob → ridge

mc = 1e-4 / 32  # sobel3d gain-corrected scale(2026-08 の /32 較正に追従) / scaled for the sobel3d gain-correction (2026-08 /32 calibration)
S_sph, C_sph, Msph, _ = [t.numpy() for t in M.curvature_maps(sphere, mc=mc)]
S_cyl, C_cyl, Mcyl, _ = [t.numpy() for t in M.curvature_maps(cyl, mc=mc)]

sh = (r > 4.5) & (r < 7.5) & (Msph > 0.5)                          # 勾配の強い球殻
cb = (rho > 4.5) & (rho < 7.5) & (np.abs(zz - cz) < 10) & (Mcyl > 0.5)  # 円柱の側面帯
s_sphere = float(np.median(S_sph[sh]))                            # 期待 cap ≈ +1
s_cyl = float(np.median(S_cyl[cb]))                               # 期待 ridge ≈ +0.5
print(f"curvature_maps : shape index  球={s_sphere:.3f}(cap≈+1) / 円柱={s_cyl:.3f}(ridge≈+0.5)")
assert s_sphere > 0.9, f"球の等値面を cap と判定できていない: {s_sphere:.3f}"
assert 0.4 < s_cyl < 0.6, f"円柱の等値面を ridge と判定できていない: {s_cyl:.3f}"
assert s_sphere - s_cyl > 0.3, "shape index が球(cap)と円柱(ridge)を判別的に分離できていない"

# curvedness は球殻で厳密に 1/r(2026-08-30 の利得補正後は絶対値で裏取りできる —
# それ以前は sobel3d 利得 32 が混入し 1/32 倍だったため比でしか確認できなかった)
def shell_curv(a0, b0):
    m = (r > a0) & (r < b0) & (Msph > 0.5)
    return float(np.median(C_sph[m])), float(np.median(r[m]))
c_in, r_in = shell_curv(3.0, 4.5)
c_out, r_out = shell_curv(7.5, 9.0)
abs_err_in = abs(c_in * r_in - 1.0)
abs_err_out = abs(c_out * r_out - 1.0)
print(f"  curvedness = 1/r : 内殻 c·r = {c_in * r_in:.3f} / 外殻 c·r = {c_out * r_out:.3f} "
      f"(どちらも 1 が真値)")
assert c_in > c_out, "小半径の殻で curvedness がより大きくなっていない(∝1/r に反する)"
assert abs_err_in < 0.1 and abs_err_out < 0.1, \
    f"curvedness が 1/r を絶対値で復元していない: c·r 内={c_in * r_in:.3f} 外={c_out * r_out:.3f}"

# ══════════════════════════════════════════════════════════════════════════
# 3) edt_jfa — 球中心 1 点を種にした距離場が半径座標 r を厳密復元
# ══════════════════════════════════════════════════════════════════════════
iz, iy, ix = int(round(cz)), int(round(cy)), int(round(cx))
seed = np.zeros((N, N, N), bool)
seed[iz, iy, ix] = True
edt = M.edt_jfa(seed).numpy()                                    # (D,H,W) 距離場
r_seed = np.sqrt((zz - iz) ** 2 + (yy - iy) ** 2 + (xx - ix) ** 2)  # 解析ユークリッド距離
edt_err = float(np.max(np.abs(edt - r_seed)))
cheb = np.maximum.reduce([np.abs(zz - iz), np.abs(yy - iy), np.abs(xx - ix)])
cheb_gap = float(np.max(np.abs(edt - cheb)))                     # L∞ null との乖離
print(f"edt_jfa   : |EDT - 解析ユークリッド距離| max = {edt_err:.2e} / Chebyshev(L∞)との最大差 = {cheb_gap:.2f}")
assert edt_err < 1e-3, "edt_jfa がユークリッド距離を厳密復元していない"
assert cheb_gap > 5.0, "EDT が箱型 L∞ 距離と区別できていない(ユークリッドでない)"

# ══════════════════════════════════════════════════════════════════════════
# 4) morph_blackhat3d — ソリッド部品内部の微小な暗い空隙(欠陥)を炙り出す
# ══════════════════════════════════════════════════════════════════════════
solid = np.ones((N, N, N), np.float32)                           # 均質な明ソリッド(部品内部)
vz, vy, vx = 14, 30, 20
void = np.zeros((N, N, N), bool)
void[vz, vy, vx] = True                                          # SE より小さい暗い空隙(1 voxel)
solid[void] = 0.0
bh = M.morph_blackhat3d(solid, r=1)                             # closing − vol(暗構造抽出)
th = M.morph_tophat3d(solid, r=1)                              # 対照: white top-hat(明構造抽出)
bh_void = float(bh[vz, vy, vx])
bh_other = float(bh[~void].max())
bh_clean = float(np.abs(M.morph_blackhat3d(np.ones((N, N, N), np.float32), r=1)).max())
th_max = float(np.abs(th).max())
print(f"morph_blackhat3d : 空隙で {bh_void:.3f} / 空隙以外 max {bh_other:.2e} / "
      f"空隙無しソリッド max {bh_clean:.2e} / white top-hat max {th_max:.2e}")
assert np.allclose(bh, void.astype(np.float32)), "black-hat が空隙 mask を厳密復元していない"
assert bh_void > 0.9 and bh_other < 1e-6, "black-hat が空隙だけを立てられていない"
assert bh_clean < 1e-6, "空隙の無いソリッドで black-hat が立ってしまっている(null 破れ)"
assert th_max < 1e-6, "white top-hat が暗い空隙に反応してしまっている(black-hat の差別化が崩れる)"

print(f"PASS: sobel3d/hessian3d が解析勾配・Hessian を機械精度({max(e_gz, e_gy, e_gx):.1e}/{e_hess:.1e})で復元。"
      f"curvature_maps が球=cap({s_sphere:.2f}) と円柱=ridge({s_cyl:.2f}) を判別分離し "
      f"curvedness=1/r を絶対値(c·r={c_in * r_in:.2f})で確認。"
      f"edt_jfa が半径 r を厳密復元(err {edt_err:.1e}, L∞ null と {cheb_gap:.0f} 差)。"
      f"morph_blackhat3d が内部空隙を厳密 mask 復元(top-hat/空隙無し null は不反応)")
