"""事例: トーラス(穴あきドーナツ)点群の表面再構成で「穴」を保つ (reconstruction).

3Dスキャンで得た点群からメッシュを起こすとき、対象がドーナツ状(genus 1=穴が1つ)なら
再構成も穴を保たねばならない。凸包(convex hull)で包むと穴が埋まって別物になる。
alpha shapes(Edelsbrunner+1983)は Delaunay 四面体分割の外接球半径が 1/alpha 未満の
四面体だけ残す(alpha-complex)ので、凸包を「削って」凹み・穴を復元できる。ここでは
中実トーラス(主半径 R=1.0, 管半径 r=0.35, z軸まわり)を体積サンプルし、
recon3d.estimate_alpha で推奨 alpha を出し、recon3d.alpha_shape_mesh で表面を張る。

検証(GT): トーラス中心の「穴」= z 軸(ρ=0)上のプローブ点が再構成に**内包されるか**を、
返ったメッシュ(頂点/三角形)へのレイキャスト奇偶判定で測る。真値は「穴は開いている」=
軸上プローブは管の外(内包されない)。判別子(discriminator)= 軸プローブが内包される割合:
alpha shape ≈ 0(穴を保つ)/ 同じ点群の凸包 ≈ 1(穴を埋める)。凸包の内包率は
Delaunay の厳密な内外判定でも裏取りし、レイキャスト測定自体の正しさも独立に確認する。
"""
import sys
from pathlib import Path

# リポジトリ root を最優先に(同名の example ファイルが top-level module を隠さないように)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy.spatial import ConvexHull, Delaunay

import recon3d  # fullseye: estimate_alpha / alpha_shape_mesh / alpha_shape_boundary


# --- 幾何ヘルパ -----------------------------------------------------------
def sample_solid_torus(n, R, r, seed):
    """中実トーラス(z軸まわり、主半径 R・管半径 r)を体積サンプル (n,3)。

    管断面(半径 r の円板)を一様に取り、主円(半径 R)に沿って回す。管の内部まで
    点を詰めることで alpha-complex が中実体を埋め、境界は 1 枚の閉じたトーラス面になる。
    """
    rng = np.random.default_rng(seed)
    theta = rng.uniform(0.0, 2.0 * np.pi, n)               # 主円まわりの角度
    rho = r * np.sqrt(rng.uniform(0.0, 1.0, n))            # 管断面内の半径(面積一様)
    psi = rng.uniform(0.0, 2.0 * np.pi, n)                 # 管断面内の角度
    u = rho * np.cos(psi)                                   # 半径方向オフセット
    w = rho * np.sin(psi)                                   # 鉛直方向オフセット
    x = (R + u) * np.cos(theta)
    y = (R + u) * np.sin(theta)
    z = w
    return np.stack([x, y, z], axis=1)


def _ray_hits(p, d, v0, e1, e2):
    """1本のレイ (p, 方向 d) と全三角形の交差数(Möller–Trumbore、ベクトル化)。

    v0,e1(=v1-v0),e2(=v2-v0) は前計算した三角形配列 (M,3)。t>eps かつ重心座標が
    範囲内の交差のみ数える。奇偶(parity)で内外を判定するため向き付けは不要。
    """
    pvec = np.cross(np.broadcast_to(d, e2.shape), e2)      # (M,3)
    det = np.einsum("ij,ij->i", e1, pvec)                  # (M,)
    eps = 1e-12
    ok = np.abs(det) > eps
    inv = np.zeros_like(det)
    inv[ok] = 1.0 / det[ok]
    tvec = p[None, :] - v0                                  # (M,3)
    uu = np.einsum("ij,ij->i", tvec, pvec) * inv
    qvec = np.cross(tvec, e1)                               # (M,3)
    vv = np.einsum("j,ij->i", d, qvec) * inv
    tt = np.einsum("ij,ij->i", e2, qvec) * inv
    tol = 1e-9
    hit = ok & (uu >= -tol) & (uu <= 1.0 + tol) \
        & (vv >= -tol) & (uu + vv <= 1.0 + tol) & (tt > 1e-9)
    return int(hit.sum())


def enclosed_fraction(probes, V, F, seed, n_rays=7):
    """プローブ点群がメッシュ (V,F) に内包される割合(レイキャスト奇偶の多数決)。

    各点から乱数方向へ n_rays 本レイを飛ばし、交差数が奇数=内側と判定、多数決で確定。
    多数決により非watertight な微小欠陥や退化交差に頑健(穴プローブは全方向で外側=頑健に0)。
    """
    if len(F) == 0:
        return 0.0
    v0 = V[F[:, 0]]
    e1 = V[F[:, 1]] - v0
    e2 = V[F[:, 2]] - v0
    rng = np.random.default_rng(seed)
    dirs = rng.normal(size=(n_rays, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    inside = np.zeros(len(probes), dtype=bool)
    for i, p in enumerate(probes):
        odd = sum(_ray_hits(p, d, v0, e1, e2) % 2 for d in dirs)
        inside[i] = odd * 2 > n_rays                        # 多数決(過半が奇数)
    return float(inside.mean())


def euler_characteristic(V, F):
    """閉曲面メッシュのオイラー標数 χ = V − E + F(トーラス=0, 球=2)。"""
    e = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]], axis=0)
    e = np.sort(e, axis=1)
    E = len(np.unique(e, axis=0))
    return len(V) - E + len(F)


# --- 1) 合成データ: 中実トーラス点群(穴あき, genus 1)---------------------
R_MAJOR, R_MINOR = 1.0, 0.35
pts = sample_solid_torus(n=9000, R=R_MAJOR, r=R_MINOR, seed=0)

# --- 2) alpha shape で表面再構成(推奨 alpha を推定して使用)---------------
# estimate_alpha は 1/alpha ≈ 2·(最近傍間隔中央値)。中実体を素直に埋めるよう *0.5 で
# 半径しきい値 1/alpha を約2倍広げる(test_recon3d と同じ流儀)。穴を跨ぐ四面体は
# 外接球半径 ~ (R−r)=0.65 と大きく、1/alpha より十分大きいので除外され、穴は保たれる。
alpha = recon3d.estimate_alpha(pts) * 0.5
Va, Fa = recon3d.alpha_shape_mesh(pts, alpha)

# --- 3) null: 同じ点群の凸包(穴を埋める)---------------------------------
# 面が参照する頂点だけに詰め直す(χ を凸包表面=球位相として正しく数えるため)。
hull = ConvexHull(pts)
used = np.unique(hull.simplices)
remap = -np.ones(len(pts), dtype=np.int64)
remap[used] = np.arange(len(used))
Vh = pts[used]
Fh = remap[hull.simplices].astype(np.int64)

# --- 4) 穴プローブ: z 軸(ρ=0)上、|z|<r で凸包内・穴の中の点列 -----------
zprobe = np.linspace(-0.25, 0.25, 41)
probes = np.stack([np.zeros_like(zprobe), np.zeros_like(zprobe), zprobe], axis=1)

# 判別子: 軸プローブが各再構成に内包される割合(同一のレイキャスト測定で公平比較)
alpha_frac = enclosed_fraction(probes, Va, Fa, seed=1)
hull_frac = enclosed_fraction(probes, Vh, Fh, seed=1)

# 独立検算: 凸包の内包は Delaunay の厳密な内外判定でも確認(レイキャスト自体の妥当性検証)
hull_frac_exact = float((Delaunay(pts).find_simplex(probes) >= 0).mean())

chi_a = euler_characteristic(Va, Fa)
chi_h = euler_characteristic(Vh, Fh)

print(f"トーラス点群              : N={len(pts)}  R={R_MAJOR} r={R_MINOR} (genus 1)")
print(f"推定 alpha                : {alpha:.4f}  (半径しきい値 1/alpha = {1.0/alpha:.4f})")
print(f"alpha メッシュ            : V{Va.shape} F{Fa.shape}  χ={chi_a} (トーラス χ=0)")
print(f"凸包メッシュ (null)       : V{Vh.shape} F{Fh.shape}  χ={chi_h} (球 χ=2)")
print(f"軸プローブ内包率 alpha    : {alpha_frac:.3f}  (穴が開いていれば ≈0)")
print(f"軸プローブ内包率 凸包null : {hull_frac:.3f}  (穴を埋めるので ≈1)")
print(f"凸包内包率(厳密Delaunay) : {hull_frac_exact:.3f}  (レイキャスト測定の裏取り)")

# --- GT/beat-null 検証 ----------------------------------------------------
# 再構成が非空であること。
assert len(Va) > 0 and len(Fa) > 0, f"alpha メッシュが空: V{Va.shape} F{Fa.shape}"
# レイキャスト測定の妥当性: 凸包の内包率が厳密判定と一致(測定手段が正しい)。
assert abs(hull_frac - hull_frac_exact) < 0.1, \
    f"レイキャストが厳密判定と乖離: {hull_frac:.3f} vs {hull_frac_exact:.3f}"
# null(凸包)は穴を埋める=軸プローブをほぼ全て内包する(零点ベースラインが本物)。
assert hull_frac > 0.9, f"凸包が穴を埋めていない(null 不成立): {hull_frac:.3f}"
# ★判別的アサート: alpha shape は穴を保つ=軸プローブをほぼ内包しない。
#   null 手法(凸包)は内包率 ≈1 でこの条件に FAIL する(=判別的)。
assert alpha_frac < 0.1, f"alpha shape が穴を埋めてしまった: {alpha_frac:.3f}"
# alpha は null より明確に穴を保つ(内包率が桁違いに小さい)。
assert alpha_frac < 0.2 * hull_frac, \
    f"alpha が null(凸包)を十分に上回らない: {alpha_frac:.3f} vs {hull_frac:.3f}"

print(f"PASS: alpha shape は穴を保持(軸プローブ内包率 {alpha_frac:.3f})、"
      f"凸包 null は穴を充填({hull_frac:.3f}, 厳密 {hull_frac_exact:.3f})で判別的。"
      f"χ_alpha={chi_a}(トーラス0) vs χ_hull={chi_h}(球2)")
