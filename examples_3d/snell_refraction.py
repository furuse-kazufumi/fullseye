"""事例: 透明体(ガラス/水)を通る光線の曲がりと界面反射率を厳密に計算 (optics).

レンズ・水槽・ガラス越しの被写体は、光が界面で屈折して像がずれ、界面で一部が反射する。
この曲がり(Snell の法則)と反射率(Fresnel の式)を正しく計算できないと、屈折レンダ・
水中カメラの補正・透明体の外観検査が破綻する。ここでは match3d の光線光学 op
(snell_angle / refract / fresnel_reflectance / reflect)だけで屈折光線・反射率を求め、
すべて解析解(閉じた式)と突き合わせて検証する。合成データのみ・ネット不要・決定的。

検証(GT): 屈折は物理法則そのものが厳密な真値になる。
  (a) snell_angle が n1 sinθi = n2 sinθt を満たす(残差 < 1e-9)。
  (b) refract の返すベクトルが単位ベクトルで、法線となす角が snell_angle と一致(< 1e-6 度)。
  (c) fresnel_reflectance は [0,1]、垂直入射で ((n1-n2)/(n1+n2))²=0.04、grazing/全反射で 1 へ。
  beat-null: 「曲がらない」null(屈折方向=入射方向)は屈折角=入射角のままで Snell を破る。
  実 op は Snell の θt に 1e-6 度未満で一致する一方、no-bend null は平均 >5 度もずれる=判別的。
"""
import numpy as np
import match3d  # snell_angle / refract / fresnel_reflectance / reflect(光線光学 op)


def incident_dir(theta_i_deg):
    """入射角 θi(度)の入射光線方向を作る。法線 n=+z、x-z 面内で下向き(面へ向かう)。

    d=(sinθi, 0, -cosθi) は単位ベクトルで、外向き法線 n=+z に対し
    cosi = -d·n = cosθi。つまり d と -n のなす角がちょうど θi になる。
    """
    th = np.radians(theta_i_deg)
    return np.array([np.sin(th), 0.0, -np.cos(th)])


def angle_to_transmit_side(vec, n):
    """ベクトル vec が透過側の法線 -n となす角(度)。屈折光線の屈折角の実測に使う。"""
    v = np.asarray(vec, float); v = v / np.linalg.norm(v)
    n = np.asarray(n, float); n = n / np.linalg.norm(n)
    return float(np.degrees(np.arccos(np.clip(-float(v @ n), -1.0, 1.0))))


N = np.array([0.0, 0.0, 1.0])          # 界面の外向き法線(入射媒質側)
ETA1, ETA2 = 1.0, 1.5                  # 空気 → ガラス(密な媒質へ入射=全反射しない側)

# --- 1) 屈折側でテストする入射角(0=垂直 〜 85=grazing 手前)-------------------
angles = [0.0, 10.0, 25.0, 40.0, 55.0, 70.0, 85.0]

snell_resid = []      # (a) n1 sinθi = n2 sinθt の残差
refract_resid = []    # (b) refract の角度 vs snell_angle の差(度)
unit_resid = []       # (b) refract の単位性(|t|-1)
null_err = []         # beat-null: no-bend null(屈折=入射)の屈折角ずれ(度)

for thi in angles:
    tht = match3d.snell_angle(thi, ETA1, ETA2)                    # 屈折角(度)
    # (a) スネルの法則(閉じた式)の残差
    snell_resid.append(abs(ETA1 * np.sin(np.radians(thi)) - ETA2 * np.sin(np.radians(tht))))

    d = incident_dir(thi)                                        # 入射光線
    t = match3d.refract(d, N, ETA1, ETA2)                        # 屈折光線(ベクトル)
    assert t is not None, f"密媒質側なので全反射しないはず: θi={thi}"
    unit_resid.append(abs(np.linalg.norm(t) - 1.0))             # 単位ベクトルか
    # (b) 屈折光線が法線となす角 == snell_angle か
    refract_resid.append(abs(angle_to_transmit_side(t, N) - tht))

    # beat-null: 「曲がらない」null は屈折方向 = 入射方向。その屈折角は入射角 θi のまま。
    if thi > 0.0:
        null_dir = d                                           # 何も曲げない(誤ったモデル)
        null_angle = angle_to_transmit_side(null_dir, N)       # = θi
        null_err.append(abs(null_angle - tht))                 # 真の θt からのずれ

snell_resid = np.array(snell_resid)
refract_resid = np.array(refract_resid)
unit_resid = np.array(unit_resid)
null_err = np.array(null_err)

print(f"入射角                       : {angles}")
print(f"(a) Snell 残差 |n1 sinθi - n2 sinθt| max : {snell_resid.max():.2e}")
print(f"(b) 屈折角 vs snell_angle  max差(度)     : {refract_resid.max():.2e}")
print(f"(b) 屈折ベクトルの単位性 max|‖t‖-1|      : {unit_resid.max():.2e}")
print(f"beat-null: no-bend の屈折角ずれ 平均(度) : {null_err.mean():.3f}  (実 op は ~0)")

# --- 2) Fresnel 反射率: 範囲・垂直入射値・grazing での立ち上がり --------------
r_normal = match3d.fresnel_reflectance(1.0, ETA1, ETA2)          # 垂直入射(cos_i=1)
r0_analytic = ((ETA1 - ETA2) / (ETA1 + ETA2)) ** 2              # = 0.04 (air→glass)

graze_angles = [60.0, 70.0, 80.0, 85.0, 89.0]                   # grazing に向かう領域
r_graze = [match3d.fresnel_reflectance(np.cos(np.radians(a)), ETA1, ETA2) for a in graze_angles]
r_all = [match3d.fresnel_reflectance(np.cos(np.radians(a)), ETA1, ETA2)
         for a in np.linspace(0, 90, 46)]                       # [0,1] 範囲確認用

print(f"Fresnel 垂直入射             : {r_normal:.6f}  (解析 {r0_analytic:.6f})")
print(f"Fresnel grazing {graze_angles} : {[round(r, 4) for r in r_graze]}")
print(f"Fresnel 値域                 : [{min(r_all):.4f}, {max(r_all):.4f}]")

# --- 3) 全反射(TIR): ガラス → 空気で臨界角(~41.8度)を超えると全反射 ---------
crit = np.degrees(np.arcsin(ETA2 / ETA1))                       # ETA1=1.5,ETA2=1.0 の臨界角
thi_tir = 50.0                                                  # 臨界角超
tir_snell = match3d.snell_angle(thi_tir, 1.5, 1.0)             # NaN のはず
tir_refract = match3d.refract(incident_dir(thi_tir), N, 1.5, 1.0)  # None のはず
tir_fresnel = match3d.fresnel_reflectance(np.cos(np.radians(thi_tir)), 1.5, 1.0)  # 1.0
print(f"TIR (glass→air, θi=50>臨界{crit:.1f}度): snell={tir_snell}, "
      f"refract={'None' if tir_refract is None else 'vec'}, fresnel={tir_fresnel:.4f}")

# --- 4) 参考: reflect は鏡面反射(入射角=反射角)を満たす -----------------------
d40 = incident_dir(40.0)
r40 = match3d.reflect(d40, N)
refl_in = angle_to_transmit_side(d40, N)                        # 入射角 = 40
refl_out = float(np.degrees(np.arccos(np.clip(float(r40 @ N), -1.0, 1.0))))  # 反射角(法線 n 側)
print(f"reflect: 入射角 {refl_in:.3f} 度 = 反射角 {refl_out:.3f} 度")

# ═══ GT 検証(物理法則が厳密な真値。緩い assert ではなく tight tolerance)═══
# (a) スネルの法則を厳密に満たす
assert snell_resid.max() < 1e-9, f"Snell の法則を満たさない: {snell_resid.max():.2e}"
# (b) 屈折ベクトルは単位で、その屈折角が snell_angle と 1e-6 度未満で一致
assert unit_resid.max() < 1e-9, f"屈折ベクトルが単位でない: {unit_resid.max():.2e}"
assert refract_resid.max() < 1e-6, f"屈折角が snell_angle と不一致: {refract_resid.max():.2e}"
# beat-null: no-bend null は Snell の θt から平均 5 度以上ずれる(実 op は 1e-6 度未満)
assert null_err.mean() > 5.0, f"null が判別的でない: {null_err.mean():.3f} 度"
assert refract_resid.max() < 1e-6 < null_err.mean(), "実 op が null を上回っていない"
# (c) Fresnel: 値域 [0,1]、垂直入射で解析値 0.04、grazing で単調増加し 1 へ迫る
assert 0.0 <= min(r_all) and max(r_all) <= 1.0, "Fresnel が [0,1] を外れた"
assert abs(r_normal - r0_analytic) < 1e-9, f"垂直入射反射率が解析値と不一致: {r_normal}"
assert all(np.diff(r_graze) > 0), f"grazing で単調増加しない: {r_graze}"
assert r_graze[-1] > 0.6, f"grazing(89度)で 1 に迫らない: {r_graze[-1]:.3f}"
# 全反射: 臨界角超で snell=NaN, refract=None, fresnel=1.0(反射で全エネルギーが戻る)
assert np.isnan(tir_snell), f"臨界角超で NaN でない: {tir_snell}"
assert tir_refract is None, "臨界角超で全反射(None)にならない"
assert abs(tir_fresnel - 1.0) < 1e-12, f"全反射で反射率 1.0 でない: {tir_fresnel}"
# reflect: 入射角 = 反射角(鏡面反射)
assert abs(refl_in - refl_out) < 1e-9, f"鏡面反射で入射角≠反射角: {refl_in} vs {refl_out}"

print(f"PASS: Snell 残差 {snell_resid.max():.1e}・屈折角一致 {refract_resid.max():.1e}度 "
      f"(no-bend null は平均 {null_err.mean():.1f}度ずれ)、Fresnel 垂直 {r_normal:.3f}=0.04・"
      f"grazing {r_graze[-1]:.3f}→1・臨界角超で全反射")
