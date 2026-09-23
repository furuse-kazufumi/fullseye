# 極小曲面と管メッシュ — render3d.minimal_surface / minimal_surface_bend /
#                        gyroid_isosurface / gyroid_solid_mask / curve3d_tube_mesh
# 実問題: 膜構造・TPMS の足場・軽量格子を設計したい。石鹸膜が張る形(極小曲面)は
# 与えられた境界で面積が最小になる曲面で、膜張力が一様になるため構造材として良い。
#
# ★この例の要点は絵ではなく**定義そのもの**: 極小曲面とは「平均曲率 H が至るところ
#   0」の曲面である。既存の `vertex_curvature` がまさにその H を測るので、
#   「これは極小曲面だ」という主張を、**作り方を知らない op が採点する**。
#   対照群として単位球(H = 1)と半径 1 の円柱(H = 0.5)を同じ手続きにかけ、
#   門が素通しでないことを示す。
#
# ★カテノイドとヘリコイドは等長なのでガウス曲率 K が一致するが、それは
#   **必要条件にすぎない** —— K が一致しても極小とは限らないので、門は H に置く。
#
# repo をそのまま clone した状態でも動くように、リポジトリ直下を import パスへ入れる。
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

import numpy as np

import fullseye as fs
import render3d


def mean_curvature(V, F, trim=0.1):
    """既存 op で |H| を測る。端は評価が甘いので上側を落とす。"""
    h = np.asarray(fs.ledger.vertex_curvature((V, F)), dtype=np.float64)
    h = np.abs(h[np.isfinite(h)])
    if trim > 0 and h.size > 20:
        cut = int(h.size * trim)
        h = np.sort(h)[:-cut] if cut else h
    return h


print("== 1. 極小曲面は H = 0 —— 既存 vertex_curvature が採点する ==")
print("曲面          V      F     |H| 中央値   |H| p90     面積")
for kind in ("catenoid", "helicoid", "enneper", "scherk"):
    V, F = render3d.minimal_surface(kind, nu=90, nv=140, extent=1.2)
    h = mean_curvature(V, F)
    area = float(fs.ledger.mesh_area((V, F)))
    print("%-12s %5d %6d   %9.5f  %9.5f  %8.4f"
          % (kind, V.shape[0], F.shape[0], np.median(h), np.percentile(h, 90), area))
    assert np.median(h) < 0.01, (kind, np.median(h))
    assert np.percentile(h, 90) < 0.05, (kind, np.percentile(h, 90))

print("\n   対照群(極小ではない曲面) —— 門が素通しでないことの証拠:")
nu, nv = 90, 140
th = np.linspace(0.01, np.pi - 0.01, nu)[:, None]
ph = np.linspace(0.0, 2.0 * np.pi, nv, endpoint=False)[None, :]
Vs = np.stack([(np.sin(th) * np.cos(ph)).ravel(),
               (np.sin(th) * np.sin(ph)).ravel(),
               np.broadcast_to(np.cos(th), (nu, nv)).ravel()], axis=1)
zz = np.linspace(-1.0, 1.0, nu)[:, None]
Vc = np.stack([np.broadcast_to(np.cos(ph), (nu, nv)).ravel(),
               np.broadcast_to(np.sin(ph), (nu, nv)).ravel(),
               np.broadcast_to(zz, (nu, nv)).ravel()], axis=1)
Fg = render3d._surf_grid_faces(nu, nv, wrap_v=True)
for name, V, want in (("単位球(H = 1)", Vs, 1.0), ("円柱 r=1(H = 0.5)", Vc, 0.5)):
    h = mean_curvature(V, Fg)
    print("   %-18s |H| 中央値 %.5f   理論 %.1f" % (name, np.median(h), want))
    assert abs(np.median(h) - want) < 0.05, (name, np.median(h))

print("\n== 2. 曲げの族は等長 —— t を振っても H は 0 のまま・面積も変わらない ==")
print("t (× π/2)   |H| 中央値      面積")
areas = []
for t in (0.0, 0.25, 0.5, 0.75, 1.0):
    V, F = render3d.minimal_surface_bend(t * np.pi / 2.0, nu=80, nv=120, extent=1.0)
    h = mean_curvature(V, F)
    a = float(fs.ledger.mesh_area((V, F)))
    areas.append(a)
    print("  %.2f      %9.5f    %9.4f" % (t, np.median(h), a))
    assert np.median(h) < 0.02, (t, np.median(h))
assert max(areas) / min(areas) - 1.0 < 0.02, areas
print("   面積の振れ幅 %.4f 〜 %.4f(等長変形なので変わらない)"
      % (min(areas), max(areas)))

print("\n== 3. ★ガウス曲率の一致は**必要条件にすぎない** ==")
Vc1, _ = render3d.minimal_surface("catenoid", 80, 120, 1.0)
Vh1, _ = render3d.minimal_surface("helicoid", 80, 120, 1.0)
k1c, k2c = fs.ledger.principal_curvatures(Vc1)
k1h, k2h = fs.ledger.principal_curvatures(Vh1)
Kc = np.asarray(k1c) * np.asarray(k2c)
Kh = np.asarray(k1h) * np.asarray(k2h)
mc = float(np.median(Kc[np.isfinite(Kc)]))
mh = float(np.median(Kh[np.isfinite(Kh)]))
print("   カテノイド K 中央値 %.5f / ヘリコイド %.5f(等長なので近い)" % (mc, mh))
print("   だが K が一致しても極小とは限らない —— 門にするのは H のほう")
assert mc < 0 and mh < 0 and abs(mc - mh) < 0.5 * abs(mc), (mc, mh)

print("\n== 4. ジャイロイド —— 対称性で体積比 1/2、ただし**節面近似** ==")
print("格子      場 > 0 の体積比   理論との差")
for n in (48, 64, 96):
    frac = float((render3d._gyroid_field("example", (n, n, n), 1.0) > 0).mean())
    print("  %2d^3       %.6f        %.2e" % (n, frac, abs(frac - 0.5)))
    assert abs(frac - 0.5) < 0.02, (n, frac)
print("   (level = 0 で場は体心反転に対し奇 —— 格子の細かさに依らない対称性)")

print("\n   印刷できる固体(numpy だけで動く。メッシュ形は scikit-image が要る):")
for t in (0.1, 0.2, 0.4):
    m = np.asarray(render3d.gyroid_solid_mask((64, 64, 64), 0.0, 1.0, t))
    print("   厚さ %.1f  体積分率 %.4f" % (t, m.mean()))
try:
    Vg, Fg2 = render3d.gyroid_isosurface((64, 64, 64), 0.0, 1.0)
    hg = mean_curvature(Vg, Fg2)
    k1, k2 = fs.ledger.principal_curvatures(Vg)
    kk = np.abs(np.concatenate([np.asarray(k1), np.asarray(k2)]))
    kk = kk[np.isfinite(kk)]
    print("   節面メッシュ %d 頂点 / %d 面、|H| / 主曲率スケール = %.4f"
          % (Vg.shape[0], Fg2.shape[0], np.median(hg) / max(np.median(kk), 1e-12)))
    print("   ★Schoen のジャイロイドは H = 0 だが、これは**節面近似**なので残差が残る"
          " —— 隠さず出す")
except ValueError as exc:
    print("   メッシュ形は使えない:", exc)

print("\n== 5. 管メッシュ —— 円の管はトーラス(体積・表面積が解析解) ==")
R, r, m, k = 2.0, 0.3, 720, 48
ang = np.linspace(0.0, 2.0 * np.pi, m, endpoint=False)
centre = np.stack([R * np.cos(ang), R * np.sin(ang), np.zeros(m)], axis=1)
V, F = render3d.curve3d_tube_mesh(centre, radius=r, segments=k, closed=True)
vol = abs(float(fs.ledger.mesh_volume((V, F))))
area = float(fs.ledger.mesh_area((V, F)))
v_want, a_want = 2.0 * np.pi ** 2 * R * r ** 2, 4.0 * np.pi ** 2 * R * r
print("   V=%d F=%d" % (V.shape[0], F.shape[0]))
print("   体積 %.5f  解析解 2π²Rr² = %.5f  比 %.5f" % (vol, v_want, vol / v_want))
print("   面積 %.5f  解析解 4π²Rr  = %.5f  比 %.5f" % (area, a_want, area / a_want))
assert abs(vol / v_want - 1.0) < 0.01, vol
assert abs(area / a_want - 1.0) < 0.01, area

# ★平行移動フレームの効き目: まっすぐな区間を含む曲線でも半径が崩れない
z = np.linspace(0.0, 4.0, 200)
x = np.where(z < 2.0, 0.0, (z - 2.0) ** 2 * 0.3)
bent = np.stack([x, np.zeros_like(z), z], axis=1)
Vb, _ = render3d.curve3d_tube_mesh(bent, radius=0.15, segments=16)
rad = np.linalg.norm(Vb.reshape(bent.shape[0], 16, 3) - bent[:, None, :], axis=2)
print("   まっすぐな区間を含む曲線でも半径 %.12f 〜 %.12f" % (rad.min(), rad.max()))
print("   ★フレネ枠は直線部で法線が定義できず、変曲点で従法線が反転して管がねじれる"
      " —— だから平行移動フレームで掃く")
assert abs(rad.min() - 0.15) < 1e-9 and abs(rad.max() - 0.15) < 1e-9

print("\nOK — 極小性は既存 vertex_curvature が、管の体積と面積は既存 mesh_volume /")
print("     mesh_area が採点した。どれもこの族の作り方を知らない op である。")
