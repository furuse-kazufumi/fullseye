"""事例: 向き付き点群(oriented point cloud)から水密(watertight)な表面を再構成する (reconstruction).

3D スキャナや depth センサが吐くのは「点の集まり + 各点の外向き法線」だけで、面(メッシュ)は無い。
CG・シミュレーション・3D 印刷はどれも閉じた面を要求するので、点群から面を起こす表面再構成が要る。
Poisson 系再構成の肝は **法線の向き(orientation)** で、内外を分ける符号を法線が与える。ここでは
「でこぼこした滑らかな閉曲面(bumpy blob)」を解析的に定義し(半径が方向で変わる星形曲面 r=R(d)·d)、
各点で **厳密な外向き法線** を勾配から計算した向き付き点群を作り、``recon3d.poisson_lite`` の winding
number モードで水密メッシュに戻す。

検証(GT): 再構成メッシュの表面から一様サンプルした点を、真の曲面の密な点群と突き合わせ、
metrics3d の chamfer / Hausdorff 距離(bbox 対角長で正規化)が小さいことを要求する。判別性
(beat-null)は二段構え: (1) 点群の外接球(bounding sphere)という自明な形は谷を全く再現できず
chamfer が桁違いに大きい (2) 法線を乱数化(向きを壊す)すると Poisson の内外判定が崩れ再構成が
悪化する。実 Poisson の chamfer がこれら null より十分小さいことを assert する。
"""
import sys
from pathlib import Path

# 重要: 同名の example ファイルがトップレベル module を隠さないよう、repo root を sys.path の先頭へ
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np                     # noqa: E402  (GT 計測にのみ使用。再構成の演算は fullseye op)
import recon3d                          # noqa: E402  (被験 op: poisson_lite)
import metrics3d                        # noqa: E402  (GT 計測: chamfer / hausdorff)


# ═══════════════════════════════════════════════════════════════════════════
# でこぼこ閉曲面: r = R(d)·d(星形曲面)。R は方向 d の滑らかな多項式なので
# 各方向にちょうど 1 点 → 常に閉じた滑らか曲面。外向き法線は F(x)=|x|-R(d) の勾配で厳密に出せる。
# ═══════════════════════════════════════════════════════════════════════════
R0 = 1.0
# 摂動係数(|Σ| < 1 に収まり R(d)>0・星形を保つ)。異方 2 次 + キラルな 3 次でこぶを作る。
_A = np.array([0.18, -0.12, 0.15, 0.10])


def _radius_and_grad(d):
    """方向 d(...,3, 単位ベクトル)→ 半径 R(d) と方向勾配 ∇_d R を解析的に返す。

    R(d)/R0 = 1 + a0*dx^2 + a1*dy^2 + a2*dx*dy*dz + a3*dz*(dx^2 - dy^2)
    ∇_d R は各成分で偏微分した閉形式。
    """
    dx, dy, dz = d[..., 0], d[..., 1], d[..., 2]
    a0, a1, a2, a3 = _A
    f = a0 * dx * dx + a1 * dy * dy + a2 * dx * dy * dz + a3 * dz * (dx * dx - dy * dy)
    R = R0 * (1.0 + f)
    gx = 2 * a0 * dx + a2 * dy * dz + a3 * dz * (2 * dx)
    gy = 2 * a1 * dy + a2 * dx * dz + a3 * dz * (-2 * dy)
    gz = a2 * dx * dy + a3 * (dx * dx - dy * dy)
    gradR = R0 * np.stack([gx, gy, gz], axis=-1)
    return R, gradR


def _fib_directions(n):
    """フィボナッチ螺旋で単位球面上の n 方向をほぼ一様に(決定論的、極を厳密には踏まない)。"""
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)                 # 極角
    gold = np.pi * (1.0 + 5.0 ** 0.5)
    theta = gold * i                                    # 方位角
    d = np.stack([np.sin(phi) * np.cos(theta),
                  np.sin(phi) * np.sin(theta),
                  np.cos(phi)], axis=1)
    return d / np.linalg.norm(d, axis=1, keepdims=True)


def sample_blob(n, offset):
    """でこぼこ閉曲面上の点と厳密な外向き単位法線を返す。offset で原点外へ平行移動(世界座標検証)。

    外向き法線 = ∇F/|∇F|(F=|x|-R(d))。∇F = d - (1/R)·(I - d dᵀ)∇_d R
    (半径関数 R(d) の接成分の寄与を引く)。F は外側で増加するので ∇F が外向き。
    """
    d = _fib_directions(n)
    R, gradR = _radius_and_grad(d)
    pts = R[:, None] * d + offset                       # 曲面上の点(世界座標)
    tang = gradR - (np.sum(gradR * d, axis=1, keepdims=True)) * d   # (I - d dᵀ)∇_d R
    grad = d - tang / R[:, None]                         # ∇F
    nrm = grad / np.linalg.norm(grad, axis=1, keepdims=True)
    return pts, nrm


def sample_mesh_surface(verts, faces, n, seed):
    """三角形メッシュの表面を面積重みで一様サンプル(n,3)。頂点ではなく面上の点を取る。"""
    rng = np.random.default_rng(seed)
    v0, v1, v2 = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
    prob = area / area.sum()
    tri = rng.choice(len(faces), size=n, p=prob)         # 面積に比例して三角形を選ぶ
    u = rng.random(n)
    w = rng.random(n)
    over = u + w > 1.0                                    # 三角形内の一様バリセントリック
    u[over], w[over] = 1.0 - u[over], 1.0 - w[over]
    a, b, c = v0[tri], v1[tri], v2[tri]
    return a + u[:, None] * (b - a) + w[:, None] * (c - a)


# --- 1) 合成データ: でこぼこ閉曲面の向き付き点群 + 真の曲面の密な点群(GT 参照) -----------
OFFSET = np.array([0.5, -0.3, 0.2])                      # 原点からずらす(世界座標の逆写像も検証)
pts, normals = sample_blob(6000, OFFSET)                 # 入力: 向き付き点群(6000 点)
gt_dense, _ = sample_blob(40000, OFFSET)                 # GT: 別サンプルの密な真曲面(40000 点)
scale = float(np.linalg.norm(gt_dense.max(0) - gt_dense.min(0)))   # bbox 対角長で正規化

# --- 2) 再構成: winding number モード(法線で内外を判定)で水密メッシュへ ------------------
verts, faces = recon3d.poisson_lite(pts, size=64, sigma=1.5, iso=0.5, normals=normals)
recon_pts = sample_mesh_surface(verts, faces, 20000, seed=7)      # 再構成面から一様サンプル

cham = metrics3d.chamfer_distance(recon_pts, gt_dense) / scale
haus = metrics3d.hausdorff_distance(recon_pts, gt_dense) / scale

# --- 3) null-A: 点群の外接球(自明な形)。谷を全く再現できず遠い ---------------------------
center = pts.mean(0)
radius_bs = float(np.linalg.norm(pts - center, axis=1).max())
null_pts = center + radius_bs * _fib_directions(20000)
cham_bs = metrics3d.chamfer_distance(null_pts, gt_dense) / scale

# --- 4) null-B: 法線を乱数化(向きを壊す)。Poisson は正しい向きが無いと内外を分けられない ---
rng = np.random.default_rng(123)
bad_normals = rng.normal(size=normals.shape)
bad_normals /= np.linalg.norm(bad_normals, axis=1, keepdims=True)
try:
    v_bad, f_bad = recon3d.poisson_lite(pts, size=64, sigma=1.5, iso=0.5, normals=bad_normals)
    bad_pts = sample_mesh_surface(v_bad, f_bad, 20000, seed=9)
    cham_bad = metrics3d.chamfer_distance(bad_pts, gt_dense) / scale
except ValueError:
    # 向きが壊れて内外指標場が縮退 → 等値面が抜けない = 再構成の完全な破綻(=無限に悪い)
    cham_bad = float("inf")

print(f"入力点群 / GT 密曲面        : {len(pts)} 点 / {len(gt_dense)} 点  (bbox 対角長 {scale:.3f})")
print(f"再構成メッシュ              : V{verts.shape} F{faces.shape}")
print(f"実 Poisson chamfer(正規化) : {cham:.5f}   Hausdorff(正規化): {haus:.4f}")
print(f"null-A 外接球 chamfer       : {cham_bs:.5f}  (実の {cham_bs / cham:.1f} 倍)")
print(f"null-B 乱数法線 chamfer     : {cham_bad:.5f}  (実の {cham_bad / cham:.1f} 倍)")

# GT: 実 Poisson は真曲面に密着(chamfer < 3% スケール ≈ voxel 分解能水準)。
# 判別: 外接球 null は谷を潰して桁違いに遠く(> 6% かつ実の 3 倍超)、乱数法線 null も実より悪い。
# 「実 << null」を固定閾値で要求するので、自明な形や向きの壊れた法線では PASS できない。
assert cham < 0.03, f"再構成が真曲面から離れている: chamfer(正規化) {cham:.5f}"
assert cham_bs > 0.06, f"null 外接球が悪くない=判別的でない: {cham_bs:.5f}"
assert cham < cham_bs / 3.0, f"実 Poisson が外接球 null に対し十分良くない: {cham:.5f} vs {cham_bs:.5f}"
assert cham < cham_bad / 2.0, f"実 Poisson が乱数法線 null に対し十分良くない: {cham:.5f} vs {cham_bad:.5f}"
print(f"PASS: 向き付き点群→水密メッシュ、chamfer(正規化) {cham:.5f} < 0.03 "
      f"(外接球 null {cham_bs:.5f} の 1/{cham_bs / cham:.0f}、乱数法線 null {cham_bad:.5f} の 1/{cham_bad / cham:.0f})")
