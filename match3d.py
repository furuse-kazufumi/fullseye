"""match3d — 3D マッチング・マトリクス(データ構造 × 2D 手法 × データ変換)。docs/MATCH_3D_MATRIX.md。

核心: 多くの 3D 手法は「3D データを既知の 2D 手法が効く表現へ変換」して作れる。ここに変換
(splat / 投影 / FFT / 勾配場)と、それらに載る手法(NCC は accel_match、shape-based / phase
correlation はここ)を集約する。GPU=torch cu128 / RTX5090。cv2/HALCON が手薄な 3D voxel
マッチングの差別化領域。
"""
from __future__ import annotations

import numpy as np

# torch は import 時ではなく初回使用時に読み込む(実測 ~700 ms を起動から外す)。
# torch_lazy が旧 _TorchMissing の役割も兼ねる: 不在なら使用時に明確な ImportError、
# is_tensor は torch 未ロードなら import せず False(tensor は torch なしに作れない)。
# Lazy torch; is_tensor stays free, missing torch still fails clearly on use.
from torch_lazy import F, torch  # noqa: F401
from torch_lazy import HAS_TORCH as _HAS_TORCH

import accel_match as M   # 3D NCC / pyramid / sub-voxel


def _f32_finite(arr, name):
    """torch 経路の float32 キャスト安全版。

    float64 では有限でも |x|>~3.4e38 は float32 で inf に化け、grid_sample/lstsq
    の下流が NaN を**無言で**返す(連鎖ファザー第 3〜5 波で fit_zernike として
    実測、同クラス=polar_unwrap/cylinder_unwrap/scene_flow_lk)。キャスト後の
    有限性で契約を検証し fail-closed にする。"""
    a = np.asarray(arr, np.float32)
    if not np.isfinite(a).all():
        raise ValueError(
            "%s has non-finite value(s) after float32 cast — the input "
            "contains NaN/Inf or exceeds the float32 range (~3.4e38); "
            "rescale it first" % (name,))
    return a


# ═══════════════════════════════════════════════════════════════════════════
# データ変換(構造 → 共通の voxel / 勾配 表現)
# ═══════════════════════════════════════════════════════════════════════════
def _lo_hi(bounds):
    """``bounds=(lo, hi)``(3 次元ベクトル 2 本)を検証して返す。fail-closed。

    このライブラリには ``bounds`` の流儀が 3 つある(2026-09-02 実測):

    * ここ(match3d)      … ``(lo, hi)`` = 3 次元ベクトル 2 本
    * tsdf_fusion / occupancy(3-D) … ``((xmin,xmax),(ymin,ymax),(zmin,zmax))``
    * occupancy(2-D)     … ``(xmin, xmax, ymin, ymax)`` の平坦 4 要素

    取り違えても黙って別の体積が出ることは無い(確認済み)が、これまでは
    ``operands could not be broadcast together with shapes (200,3) (2,)`` という
    **素の numpy エラー**が漏れていた。それだと「op の契約の穴」なのか
    「引数の流儀違い」なのかが呼び手に分からない。何が来たかを名指しする。
    """
    try:
        lo = np.asarray(bounds[0], np.float64).reshape(-1)
        hi = np.asarray(bounds[1], np.float64).reshape(-1)
    except (TypeError, IndexError, KeyError) as exc:
        raise ValueError(
            "bounds must be (lo, hi) with two length-3 vectors; got %r" % (bounds,)
        ) from exc
    if lo.size != 3 or hi.size != 3:
        raise ValueError(
            "bounds must be (lo, hi) with two length-3 vectors, got lengths "
            "%d and %d — note tsdf_fusion / occupancy use the other convention "
            "((xmin,xmax),(ymin,ymax),(zmin,zmax)), which lands here as length 2"
            % (lo.size, hi.size))
    if not (np.all(np.isfinite(lo)) and np.all(np.isfinite(hi))):
        raise ValueError("bounds contain non-finite values: lo=%r hi=%r"
                         % (lo.tolist(), hi.tolist()))
    if not np.all(hi > lo):
        raise ValueError("bounds must satisfy hi > lo on every axis; got lo=%r hi=%r"
                         % (lo.tolist(), hi.tolist()))
    return lo, hi


def points_to_voxel(points, size, bounds=None, device="cpu", smooth=0.0):
    """点群 (N,3) → 密度 voxel (size³)。scatter_add で splat、任意で gaussian 平滑。

    bounds=(lo,hi) を与えれば複数雲を同一格子に載せられる(=マッチング前提)。

    手順: 各点を ``idx = floor((p − lo)/(hi − lo)·(size − 1))`` で整数格子に落とし、その voxel に
    1 を加算する(値 = その voxel に落ちた点の個数)。``smooth > 0`` なら σ=``smooth``(voxel 単位)
    の gaussian を 3 軸分離 conv で掛ける(半径 ``max(1, int(4σ + 0.5))``、端は replicate)。
    出力の軸順は **点の列の順そのまま**(``points[:, 0]`` → 軸 0)で、(depth,row,col) への
    並べ替えはしない。

    - ``bounds``: ``(lo, hi)`` の 3 次元ベクトル 2 本。None なら点群自身の min/max(雲ごとに
    格子が変わるので、2 つの雲を比べるときは必ず同じ bounds を渡す)。長さ 3 でない・非有限・
    ``hi <= lo`` の軸があると ValueError(tsdf 系の ``((xmin,xmax),...)`` 流儀は長さ 2 として拒否)。
    - 範囲外の点は捨てずに **端の voxel へ clip される**(端に偽の密度が溜まる)。切り落としたい
    なら事前に点群側で除く。
    - ``size``: 一辺の voxel 数。``hi − lo`` が 0 の軸は 1e-9 に置換されるだけで警告しない。
    - 空の点群で bounds=None は numpy の min が例外を出す。
    - 返り値: ``(size, size, size)`` float64 numpy(device で計算しても CPU に戻す)。値は個数
    (平滑後は個数の重み分布)で正規化はしない。

    後段: ``match_points_ncc`` / ``signed_distance_field`` / ``voxel_to_mesh`` の入力に。
    """
    P = np.asarray(points, np.float64)
    if bounds is None:
        lo, hi = P.min(0), P.max(0)
    else:
        lo, hi = _lo_hi(bounds)
    span = np.maximum(hi - lo, 1e-9)
    idx = np.clip(np.floor((P - lo) / span * (size - 1)).astype(np.int64), 0, size - 1)
    flat = (idx[:, 0] * size + idx[:, 1]) * size + idx[:, 2]
    g = torch.zeros(size ** 3, dtype=torch.float32, device=device)
    g.scatter_add_(0, torch.as_tensor(flat, device=device),
                   torch.ones(len(P), dtype=torch.float32, device=device))
    vol = g.view(size, size, size)
    if smooth > 0:
        vol = _gauss3d(vol[None, None], smooth)[0, 0]
    return vol.detach().cpu().numpy().astype(np.float64)


def gaussians_to_voxel(means, scales, opacities, size, bounds, device="cpu"):
    """3DGS(異方性ガウス)→ 密度 voxel。各ガウスを means に opacity で置き、平均 scale で平滑。

    近似(等方 splat + 平滑): 厳密な異方共分散ラスタライズは重いので、まず means を opacity 重み
    で splat → scale 平均ぶん gaussian 平滑。マッチングの coarse alignment には十分。

    引数: ``means`` (N,3) 中心、``opacities`` は長さ N に reshape されて splat の重みになる
    (``points_to_voxel`` が 1 を足すところに opacity を足す)。``scales`` は形を問わず
    **平均値 1 つ**にまとめ、``σ = mean(scales)/mean(hi − lo)·size``(world 長 → voxel 長)を
    平滑幅にする(下限 0.5 voxel。``scales`` が空なら σ=1)。異方性・回転は無視される。
    ``bounds=(lo, hi)`` は必須(None 不可。``_lo_hi`` で検証し不正なら ValueError)。範囲外の
    中心は端 voxel に clip される。返り値 ``(size, size, size)`` float64、軸順は ``means`` の列順。
    opacity の総和はほぼ保存されるが正規化はしない。点群に落とすなら ``gaussians_to_points``。
    """
    P = np.asarray(means, np.float64)
    op = np.asarray(opacities, np.float64).reshape(-1)
    lo, hi = _lo_hi(bounds)
    span = np.maximum(hi - lo, 1e-9)
    idx = np.clip(np.floor((P - lo) / span * (size - 1)).astype(np.int64), 0, size - 1)
    flat = (idx[:, 0] * size + idx[:, 1]) * size + idx[:, 2]
    g = torch.zeros(size ** 3, dtype=torch.float32, device=device)
    g.scatter_add_(0, torch.as_tensor(flat, device=device),
                   torch.as_tensor(op, dtype=torch.float32, device=device))
    vol = g.view(size, size, size)
    sig = float(np.mean(scales)) / span.mean() * size if np.size(scales) else 1.0
    vol = _gauss3d(vol[None, None], max(0.5, sig))[0, 0]
    return vol.detach().cpu().numpy().astype(np.float64)


def mesh_to_voxel(vertices, faces, size, bounds=None, samples=40000,
                  device="cpu", smooth=0.8):
    """mesh(頂点+面)→ 密度 voxel。面上を一様サンプリング → splat(mesh 行を全手法へ接続)。

    三角形上の一様点は barycentric(sqrt トリック)。占有 voxel が要るなら閾値化する。

    手順: 各三角形の面積に比例して ``samples`` 個の面を選び(``default_rng(0)`` の固定 seed
    → 毎回同じ点)、面内一様な barycentric 点を作って ``points_to_voxel`` に渡す(``smooth``
    既定 0.8 voxel)。``faces`` は (F,3) の頂点 index、``vertices`` は (V,3)。
    退化面(面積 0)しか無い mesh は確率が NaN になり ``rng.choice`` が ValueError を出す。
    ``bounds=None`` ならサンプル点の min/max(mesh の bbox とほぼ一致するが、サンプル次第で
    僅かに内側)。``bounds`` の検証・範囲外 clip は ``points_to_voxel`` と同じ。
    返り値 ``(size, size, size)`` float64 の点密度(占有ではない。占有が要るなら閾値で
    2 値化)。軸順は頂点座標の列順。seed を変えたい・点群も欲しいときは ``mesh_to_points`` で
    点群を作ってから ``points_to_voxel`` へ。
    """
    V = np.asarray(vertices, np.float64)
    Fc = np.asarray(faces, np.int64)
    tri = V[Fc]                                          # (F,3,3)
    areas = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0],
                                          tri[:, 2] - tri[:, 0]), axis=1)
    p = areas / areas.sum()
    rng = np.random.default_rng(0)
    pick = rng.choice(len(Fc), size=samples, p=p)
    u = rng.random(samples); v = rng.random(samples)
    over = u + v > 1
    u[over] = 1 - u[over]; v[over] = 1 - v[over]
    t = tri[pick]
    pts = t[:, 0] + u[:, None] * (t[:, 1] - t[:, 0]) + v[:, None] * (t[:, 2] - t[:, 0])
    return points_to_voxel(pts, size, bounds, device, smooth)


def depth_to_points(depth, fx, fy, cx, cy, stride=1):
    """深度マップ(2.5D)→ point cloud(ピンホール逆投影)。depth 行を全手法へ接続。

    画素 (行 v, 列 u) の深度 z から ``X = (u − cx)·z/fx``、``Y = (v − cy)·z/fy``、``Z = z`` を作る。
    返り値は ``(N,3)`` float64、列は **(X, Y, Z) のカメラ座標**(深度と同じ単位)。z が 0 以下の
    画素は捨てるので N は画素数以下(無効深度は 0 で表す規約)。

    - ``fx, fy, cx, cy``: 画素単位の焦点距離と主点。``project_points`` の K と同じ規約。
    - ``stride``: 行・列とも ``stride`` 画素おきに間引く。u, v は間引き後の index に ``stride``
    を掛けた **元画像の画素座標**で計算するので、間引いても幾何は変わらない。
    - 入力検証は無い(2-D でなければ添字で失敗)。NaN 深度は ``z > 0`` が偽で捨てられる。
    - 点は行優先の順に並ぶが、行・列の情報は残らない。格子構造を保ちたいなら
    ``depth_to_organized_points``。
    後段: ``points_to_voxel`` / ``estimate_point_normals`` / ``icp_point2plane``。
    逆写像は ``project_points``、TSDF 化は ``tsdf_from_depth``。
    """
    d = np.asarray(depth, np.float64)[::stride, ::stride]
    vv, uu = np.mgrid[0:d.shape[0], 0:d.shape[1]]
    z = d.reshape(-1)
    ok = z > 0
    u = (uu.reshape(-1)[ok] * stride - cx) * z[ok] / fx
    v = (vv.reshape(-1)[ok] * stride - cy) * z[ok] / fy
    return np.stack([u, v, z[ok]], axis=1)


def voxel_to_mips(vol):
    """3D → 直交 3 方向の最大値投影(MIP)。2D 手法(accel の 2D NCC 等)を適用する入口。

    入力 ``(D,H,W)`` に対し ``[max(axis=0), max(axis=1), max(axis=2)]`` の list を返す。形は
    それぞれ ``(H,W)``(軸 0=D を潰す)、``(D,W)``(軸 1=H を潰す)、``(D,H)``(軸 2=W を潰す)、
    dtype float64。値は入力の最大値そのまま(正規化しない)。負の値も max なので通り、
    密度 0 の背景は 0 のまま。
    形の検証は無い(2-D は ``axis=2`` で失敗し、4-D 以上は動いてしまう)ので、呼び手で次元を確かめる。
    ``match_mip_2d`` はこの 3 枚に 2D NCC を掛けて 3D 位置を冗長推定する。任意視点の投影は
    ``render_volume_projection``(mode="mip")。
    """
    v = np.asarray(vol, np.float64)
    return [v.max(axis=0), v.max(axis=1), v.max(axis=2)]


def _gauss1d(sigma, device):
    r = max(1, int(4.0 * sigma + 0.5))
    x = torch.arange(-r, r + 1, dtype=torch.float32, device=device)
    k = torch.exp(-(x * x) / (2 * sigma * sigma))
    return k / k.sum()


def _gauss3d(t, sigma):
    k = _gauss1d(sigma, t.device)
    r = (k.numel() - 1) // 2
    for ax in range(3):
        dim = 2 + ax
        shp = [1, 1, 1, 1, 1]; shp[dim] = k.numel()
        pad = [0, 0, 0, 0, 0, 0]; pad[(2 - ax) * 2] = r; pad[(2 - ax) * 2 + 1] = r
        t = F.conv3d(F.pad(t, tuple(pad), mode="replicate"), k.view(*shp))
    return t


def sobel3d(vol, device="cpu"):
    """3D 勾配 (gz,gy,gx)。導関数[-1,0,1]×平滑[1,2,1] の分離 conv3d。

    vol は numpy でも torch tensor(GPU 上でも可)でも受ける(scene_flow 等の device 常駐用)。

    返り値は **torch tensor 3 本**(numpy ではない)、各 ``(1,1,D,H,W)`` float32、``device`` 上。
    ``gz`` は軸 0 方向、``gy`` は軸 1、``gx`` は軸 2 の微分(入力が (D,H,W) なら (depth,row,col)
    順)。numpy に戻すなら ``g[0, 0].cpu().numpy()``。
    利得: 微分 [-1,0,1](傾き 1 で 2)× 他 2 軸の平滑 [1,2,1](各 4)で **真の勾配の 32 倍**が出る
    (正規化しない)。真の値が要るなら 32 で割る(``curvature_maps`` / ``scene_flow_lk`` は内部で
    割っている。``hessian3d`` は利得 1 なので混ぜるときに注意)。
    端は replicate padding(境界で偽のエッジを作らない)。tensor 入力が 3-D なら batch 次元を
    足し、5-D ならそのまま使う。dtype は float32 に落とす。
    後段: ``curvature_maps`` / ``match_shape_3d`` の単位勾配、``hough_plane_3d`` の法線。
    方向の要らないエッジ強度なら ``morph_gradient3d`` も代替。
    """
    if torch.is_tensor(vol):
        t = vol.to(device=device, dtype=torch.float32)
        if t.ndim == 3:
            t = t[None, None]
    else:
        t = torch.as_tensor(np.asarray(vol, np.float32)[None, None], device=device)
    deriv = torch.tensor([-1.0, 0.0, 1.0], device=device)
    smooth = torch.tensor([1.0, 2.0, 1.0], device=device)
    grads = []
    for d in range(3):
        out = t
        for ax in range(3):
            k = deriv if ax == d else smooth
            r = 1
            shp = [1, 1, 1, 1, 1]; shp[2 + ax] = 3
            pad = [0, 0, 0, 0, 0, 0]; pad[(2 - ax) * 2] = r; pad[(2 - ax) * 2 + 1] = r
            out = F.conv3d(F.pad(out, tuple(pad), mode="replicate"), k.view(*shp))
        grads.append(out)
    return grads[0], grads[1], grads[2]      # (gz,gy,gx) 各 (1,1,D,H,W)


# ═══════════════════════════════════════════════════════════════════════════
# 手法(2D → 3D)
# ═══════════════════════════════════════════════════════════════════════════
def match_phase_3d(a, b, device="cpu"):
    """3D 位相相関(FFT)。b を a に合わせる整数シフト (dz,dy,dx) を返す。

    Reddy & Chatterji の 3D 版。相互パワースペクトルの逆 FFT のピーク = 平行移動。テンプレート
    不要・全 volume・O(N log N)。回転/スケールは別途(PCA / log-polar)。

    引数: ``a``, ``b`` は同形の 3-D 配列(違えば ValueError)。float32 に落として FFT する。
    返り値: int の tuple ``(dz, dy, dx)``、各軸 ``(−N/2, N/2]`` に折り返し済み。意味は
    ``np.roll(b, (dz,dy,dx), axis=(0,1,2)) ≈ a``(b をこれだけ動かすと a に重なる)。
    - 循環相関なので、はみ出した部分は反対側から回り込む(窓掛けはしない)。シフトが volume の
    半分を超えると符号が反転して見える。
    - 位相のみ(``R/|R|``)なので振幅・コントラスト差に不変だが、ノイズが白色化されてピークが
    埋もれることがある。全 0 の volume は 0 になり index 0 を返す。
    - 整数精度。サブボクセルは ``refine_translation_lk`` / ``refine_peak_newton`` へ。
    - 回転・スケールがあると効かない(``match_logpolar_z`` → 回転補正 → 本 op の順)。
    """
    _va, _vb = np.asarray(a), np.asarray(b)
    if _va.shape != _vb.shape:
        raise ValueError("match_phase_3d: both volumes must share one shape "
                         "(got %r vs %r) — this operator correlates them "
                         "voxel-for-voxel" % (_va.shape, _vb.shape))
    # ★2026-09-07: numpy の FFT に置き換えた。式は同じ(float32 の fftn → 位相のみ →
    # ifftn の実部 → argmax)で、torch でやる必要がどこにも無かった。torch を入れない
    # CI(py3.10 / 3.12)ではこの op が ImportError になり PoC が落ちていた。
    if str(device) not in ("cpu", "None") and not _HAS_TORCH:
        raise ValueError(
            "match_phase_3d: device=%r needs the optional 'torch' backend "
            "(the numpy path runs on the CPU only)" % (device,))
    A = np.fft.fftn(np.asarray(a, np.float32))
    B = np.fft.fftn(np.asarray(b, np.float32))
    R = A * B.conj()
    R = R / (np.abs(R) + 1e-9)
    r = np.fft.ifftn(R).real
    pk = np.unravel_index(int(np.argmax(r)), r.shape)
    shp = r.shape
    return tuple(int(p - s if p > s // 2 else p) for p, s in zip(pk, shp))   # 折り返し補正


def _unit_grad3d(vol, device, mc=0.0):
    gz, gy, gx = sobel3d(vol, device)
    mag = torch.sqrt(gz * gz + gy * gy + gx * gx)
    m = (mag > mc).float()
    inv = m / mag.clamp_min(1e-8)
    return gz * inv, gy * inv, gx * inv, m


def match_shape_3d(vol, template, device="cpu", mc=0.05, subvoxel=True):
    """3D 形状ベース(勾配方向)マッチング = 2D shapematch_gpu の voxel 版(「輪郭マッチング」)。

    テンプレとシーンの **単位勾配ベクトルの内積和**(Steger 流)。強度/コントラストに不変で、
    エッジ/形状で一致を測る。score(pos)=Σ<û_scene(pos+dt), û_model(dt)>/n を 3 成分の conv3d で。

    手順: 両 volume に ``sobel3d`` → 大きさ ``mc`` 超の voxel だけ単位ベクトル化(以下は 0)。
    テンプレの単位勾配 3 成分をカーネルに、シーンの単位勾配と成分ごとに conv3d して和を取り、
    テンプレの有効 voxel 数 ``n`` で割る。score は **[−1, 1]**、1 で完全一致(勾配の向きが全て
    揃う)、コントラスト反転で −1。
    - ``mc``: ``sobel3d`` の **生出力(真の勾配の 32 倍)** に対する閾値。小さいほど平坦部の
    ノイズ勾配が投票に入る。
    - 位置: 返り値 ``[score, z, y, x]``(float64 配列)の座標は **テンプレ中心 voxel(index T//2)**
    が scene のどこに載るか。テンプレが完全に収まる位置以外は 0 に落とすので、テンプレが scene
    より大きいと全 0 のまま index (0,0,0) が返る(例外は出ない)。
    - ``subvoxel=True`` で argmax の ±2 近傍の正スコア重心に精緻化(``accel_match._subvoxel_com``)。
    後段: ``refine_translation_lk``(corner 規約なので T//2 を引く)/ ``refine_lm``。回転には
    不変でない(``match_logpolar_z`` で先に回転を合わせる)。
    """
    sz, sy, sx, _ = _unit_grad3d(vol, device, mc)           # 単位勾配(シーン)
    tz, ty, tx, tm = _unit_grad3d(np.asarray(template, np.float64), device, mc)
    n = float(tm.sum().clamp_min(1.0))
    Td, Th, Tw = np.asarray(template).shape
    pd, ph, pw = Td // 2, Th // 2, Tw // 2

    def corr(scene, ker):
        return F.conv3d(F.pad(scene, (pw, pw, ph, ph, pd, pd)), ker)

    score = (corr(sz, tz) + corr(sy, ty) + corr(sx, tx)) / n
    D, H, W = np.asarray(vol).shape
    lo = (pd, ph, pw); hi = (D - (Td - 1 - pd), H - (Th - 1 - ph), W - (Tw - 1 - pw))
    mask = torch.zeros_like(score)
    if all(h > l for l, h in zip(lo, hi)):
        mask[:, :, lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = 1.0
    score = (score * mask)[0, 0].detach().cpu().numpy().astype(np.float64)
    idx = np.unravel_index(int(np.argmax(score)), score.shape)
    pos = M._subvoxel_com(score, idx, 2) if subvoxel else [float(i) for i in idx]
    return np.array([float(score[idx])] + pos)


def moment_axes(points, weights=None):
    """点群/重み付き点の **重心 + 主軸**(慣性テンソルの固有ベクトル)。姿勢推定の基礎。

    返り値 (centroid(3,), axes(3,3) 列=主軸, eigvals(3,))。固有値降順。回転の正準化に使う。

    定義: ``w`` を総和 1 に正規化し、重心 ``c = Σ w p``、散布行列 ``C = Σ w (p−c)(p−c)ᵀ``
    (共分散。慣性テンソル ``tr(C)I − C`` と固有ベクトルは共通で固有値の順序が逆)を ``eigh`` で
    分解する。``axes[:, i]`` が i 番目に大きい固有値の主軸(降順)。固有値は分散(長さ²)。
    - 固有ベクトルの符号は任意で、``axes`` は左手系(det=−1)になり得る(``match_pca`` は第 3 軸を
    反転して右手系にしている)。
    - ``weights`` は長さ N。総和 0 は 0 除算で NaN(例外は出ない)。点数 0 は失敗する(検証は無い)。
    - 主軸が縮退(球など)なら軸の向きは不定。
    後段: ``match_pca``、``obb``(有向 bbox)、正準姿勢への回転。
    """
    P = np.asarray(points, np.float64)
    w = np.ones(len(P)) if weights is None else np.asarray(weights, np.float64)
    w = w / w.sum()
    c = (P * w[:, None]).sum(0)
    Q = P - c
    cov = (Q * w[:, None]).T @ Q
    vals, vecs = np.linalg.eigh(cov)
    order = np.argsort(vals)[::-1]
    return c, vecs[:, order], vals[order]


def match_pca(pts_scene, pts_model):
    """PCA 姿勢マッチング(構造=point cloud × 手法=主軸整列)。

    両雲の主軸を合わせる粗い剛体変換(回転 R + 並進 t)を返す。NCC/位相相関が扱えない
    **回転**をここで担う(符号の 4 通り曖昧性は最小二乗で解消。この残差は両雲の点が
    同じ並び順で対応している前提の粗い基準 — 無対応の実測雲では ICP 等で後段精密化を)。
    返り値 (R(3,3), t(3,))。

    返り値の意味: ``pts_scene ≈ (R @ pts_model.T).T + t``(``t = c_scene − R·c_model``)。R は
    必ず ``det=+1`` の回転(反射は出さない)。残差は点を index 順に対応させて測るので、無対応の
    雲では 4 候補の選択が当てにならない(その場合は ``icp_point2point_3d`` に ``init_R/init_t``
    として渡して精緻化する)。主軸が縮退している(球・円柱など固有値が等しい)雲では軸が不定で
    結果は安定しない。点数は両雲で違ってよい。入力は (N,3)(検証は ``moment_axes`` 任せで無い)。
    """
    cs, As, _ = moment_axes(pts_scene)
    cm, Am, _ = moment_axes(pts_model)
    # eigh の固有ベクトル枠は掌性(det ±1)が不定。S=diag(sx,sy,sx·sy) は常に det=+1 なので
    # det(R)=det(As)·det(Am) が 4 候補すべてで同符号になり、左手系ペアだと全候補が
    # 下の det<0 ガードで棄却され恒等回転に落ちていた(46%/ランダム試行で実測)。
    # 両枠を先に右手系へ正準化して、4 候補が常に真の回転になるようにする。
    As = As.copy(); Am = Am.copy()
    if np.linalg.det(As) < 0:
        As[:, 2] *= -1.0
    if np.linalg.det(Am) < 0:
        Am[:, 2] *= -1.0
    best = None
    Qs = np.asarray(pts_scene, np.float64) - cs
    Qm = np.asarray(pts_model, np.float64) - cm
    # 主軸の符号 4 通り(det=+1 の回転のみ)を試し、残差最小を選ぶ
    for sx in (1, -1):
        for sy in (1, -1):
            S = np.diag([sx, sy, sx * sy])
            R = As @ S @ Am.T
            if np.linalg.det(R) < 0:
                continue
            resid = float(np.mean(np.linalg.norm(
                Qs[:min(len(Qs), len(Qm))] - (R @ Qm[:min(len(Qs), len(Qm))].T).T, axis=1)))
            if best is None or resid < best[0]:
                best = (resid, R)
    R = best[1] if best else np.eye(3)
    t = cs - R @ cm
    return R, t


def match_mip_2d(scene_vol, model_vol, device="cpu"):
    """MIP 投影 → 2D NCC(構造=voxel → 2D × 手法=NCC、変換=直交 MIP)。

    3 直交方向の最大値投影で 3 枚の 2D 問題に落とし、既存の 2D NCC で定位 → 3 枚から 3D 座標を
    冗長推定。全 3D NCC より安く coarse alignment に。回転が無い平行移動探索向き。

    手順: ``voxel_to_mips`` で scene・model とも 3 枚の MIP を作り、各投影で model MIP の
    ``> 5%·max`` の bbox を切り出してテンプレにし、``accel_match.ncc_locate_batch``(2D NCC、
    テンプレ中心規約)で位置を取る。軸 0 を潰した投影は (y,x)、軸 1 は (z,x)、軸 2 は (z,y) を
    与えるので各座標は 2 枚から得られ、その平均を返す。
    返り値 ``(3,)`` float64 の ``[z, y, x]``(整数 NCC 位置の平均なので .5 刻み)。score は返さない。
    - 位置は **切り出した bbox テンプレの中心**が scene MIP のどこに載るか。model volume の
    中心ではない。
    - model MIP が全 0 の投影は飛ばし、ある座標が 1 枚からも得られなければ 0.0 になる(例外は
    出ない)。
    - MIP は重なりで奥行き情報を失うので、複数物体・クラッタには弱い。
    後段: この粗位置を ``refine_translation_lk`` / ``refine_lm`` に渡す。
    """
    sm = voxel_to_mips(scene_vol)
    mm = voxel_to_mips(model_vol)
    # 各投影で model MIP の bbox を切り出しテンプレ化 → 2D NCC
    axis_coords = {0: (1, 2), 1: (0, 2), 2: (0, 1)}   # 投影 ax が捨てる軸→残る 2 軸
    acc = {0: [], 1: [], 2: []}
    for ax in (0, 1, 2):
        s2, m2 = sm[ax], mm[ax]
        nz = np.argwhere(m2 > m2.max() * 0.05)
        if len(nz) == 0:
            continue
        lo = nz.min(0); hi = nz.max(0) + 1
        tmpl = m2[lo[0]:hi[0], lo[1]:hi[1]]
        r = M.ncc_locate_batch([s2], tmpl, device)[0]     # [score,row,col]=残る 2 軸の座標
        a0, a1 = axis_coords[ax]
        acc[a0].append(r[1]); acc[a1].append(r[2])
    pos = [float(np.mean(acc[k])) if acc[k] else 0.0 for k in (0, 1, 2)]
    return np.array(pos)


def _edges3d(vol, device, thr_ratio=0.3):
    gz, gy, gx = sobel3d(vol, device)
    mag = torch.sqrt(gz * gz + gy * gy + gx * gx)[0, 0]
    return (mag > thr_ratio * float(mag.max())).float()


def match_chamfer_3d(scene, template, device="cpu", thr=0.3, edt="scipy"):
    """chamfer / 距離場マッチング(部分・遮蔽に頑健)。voxel × chamfer 列。

    シーンのエッジの EDT(各 voxel から最近エッジまでの距離)に、テンプレのエッジ点を載せて
    距離和を最小化。score(pos)=Σ_{template edge} DT_scene(pos+edge)/n。**低いほど良い一致**。
    エッジ点の一部が欠けても効く(NCC より遮蔽に強い)。相関(conv3d)は常に GPU。距離場は
    edt="scipy"(CPU、既定)か edt="jfa"(`edt_jfa`、全 GPU で CPU 往復なし。scipy と厳密一致)。
    返り値 [chamfer 距離, d, h, w]。

    手順: 両 volume で ``|∇| > thr·max|∇|`` の voxel をエッジにする(``thr`` は各 volume の最大
    勾配に対する **相対比**、勾配は ``sobel3d``)。scene エッジの距離変換 DT を作り、テンプレの
    エッジ 2 値 volume をカーネルに conv3d した値をエッジ数 ``n`` で割る。
    返り値 ``[距離, z, y, x]`` の距離は「テンプレのエッジ 1 voxel あたり、最寄り scene エッジまでの
    平均距離(voxel 単位)」で 0 が完全一致。位置は **テンプレ中心 (T//2)** の scene 座標で
    **整数**(subvoxel 精緻化は無い。要るなら ``refine_translation_lk`` へ。corner 規約なので
    T//2 を引く)。テンプレが完全に収まらない位置は最大値+1 で埋めて除外する。
    テンプレにエッジが無い(``thr`` が高すぎる等)と score が全 0 になり index (0,0,0) が返る。
    scene にエッジが無い場合の距離場は意味を持たない(``thr`` を下げる)。
    ``edt="jfa"`` は ``edt_jfa`` を使い ``device`` 上で完結、それ以外は scipy(CPU)。
    """
    se = _edges3d(scene, device, thr).detach().cpu().numpy() > 0.5
    te = _edges3d(template, device, thr).detach().cpu().numpy() > 0.5
    if edt == "jfa":
        dtt = edt_jfa(se, device)[None, None].to(torch.float32)   # 全 GPU 距離場
    else:
        from scipy import ndimage
        dt = ndimage.distance_transform_edt(~se)            # scene エッジまでの距離場
        dtt = torch.as_tensor(dt[None, None], dtype=torch.float32, device=device)
    n = max(1.0, float(te.sum()))
    Td, Th, Tw = te.shape
    pd, ph, pw = Td // 2, Th // 2, Tw // 2
    ker = torch.as_tensor(te[None, None].astype(np.float32), device=device)
    score = F.conv3d(F.pad(dtt, (pw, pw, ph, ph, pd, pd)), ker)[0, 0] / n
    D, H, W = np.asarray(scene).shape
    big = float(score.max()) + 1.0
    lo = (pd, ph, pw); hi = (D - (Td - 1 - pd), H - (Th - 1 - ph), W - (Tw - 1 - pw))
    mask = torch.full_like(score, big)
    if all(h > l for l, h in zip(lo, hi)):
        mask[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = 0.0
    s = (score + mask).detach().cpu().numpy()                # 無効位置は大 → argmin で除外
    idx = np.unravel_index(int(np.argmin(s)), s.shape)
    return np.array([float(s[idx]), float(idx[0]), float(idx[1]), float(idx[2])])


def match_points_ncc(pts_scene, pts_model, size, bounds, device="cpu", smooth=0.8):
    """点群同士マッチング(構造=point cloud × 手法=NCC、変換=splat)。model を scene 内で定位。

    手順: ``pts_scene`` と ``pts_model`` を **同じ** ``bounds=(lo,hi)`` と ``size`` で
    ``points_to_voxel``(σ=``smooth`` voxel の平滑つき)に通し、model 側は ``> 5%·max`` の bbox を
    切り出してテンプレにし、``accel_match.ncc_locate_3d`` で NCC 定位する。
    返り値 ``[NCC, z, y, x]`` float64(NCC ∈ [−1,1]、位置は voxel index、±2 近傍重心で
    サブボクセル)。
    - 位置は **切り出した bbox テンプレの中心**が scene voxel のどこに載るか。world 座標に戻すには
    ``lo + idx/(size−1)·(hi−lo)``(``points_to_voxel`` の格子)。
    - ``bounds`` は必須(``_lo_hi`` で検証、不正は ValueError)。両雲を含む範囲にしないと範囲外の
    点が端 voxel に clip される。
    - model の voxel が全 0 なら ``[0,0,0,0]``。
    - 並進のみ。回転・スケールは ``match_pca`` / ``match_logpolar_z`` で先に合わせる。
    後段: ``icp_point2point_3d`` の ``init_t``、``refine_translation_lk``。
    """
    vs = points_to_voxel(pts_scene, size, bounds, device, smooth)
    vm_full = points_to_voxel(pts_model, size, bounds, device, smooth)
    nz = np.argwhere(vm_full > vm_full.max() * 0.05)
    if len(nz) == 0:
        return np.array([0.0, 0.0, 0.0, 0.0])
    lo = nz.min(0); hi = nz.max(0) + 1
    tmpl = vm_full[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]      # model の bbox を切り出しテンプレ化
    return M.ncc_locate_3d([vs], tmpl, device, subvoxel=True)[0]


# ═══════════════════════════════════════════════════════════════════════════
# 回転 + スケール(log-polar × 位相相関 = Fourier-Mellin、z 軸部分群)
# ═══════════════════════════════════════════════════════════════════════════
def _hp_emphasis(H, W, device):
    """Reddy-Chatterji 高域強調 H=(1-X)(2-X), X=cos(pi fy)cos(pi fx)。DC 支配を抑える。"""
    fy = torch.linspace(-0.5, 0.5, H, device=device)[:, None]
    fx = torch.linspace(-0.5, 0.5, W, device=device)[None, :]
    X = torch.cos(np.pi * fy) * torch.cos(np.pi * fx)
    return (1 - X) * (2 - X)


def _fmt_spectrum(img2d, device):
    """2D → Hann 窓 → |FFT| → fftshift → 高域強調。平行移動不変な回転/スケール表現。"""
    H, W = img2d.shape
    wy = torch.hann_window(H, periodic=False, device=device)[:, None]
    wx = torch.hann_window(W, periodic=False, device=device)[None, :]
    t = torch.as_tensor(np.asarray(img2d, np.float32), device=device) * wy * wx
    Fv = torch.fft.fftshift(torch.fft.fft2(t)).abs()
    return Fv * _hp_emphasis(H, W, device)


def _logpolar(img2d, nt, nr, device, rmin=2.0):
    """2D → log-polar(theta∈[0,π): |FFT| は 180° 対称、rho は対数)。grid_sample で GPU。"""
    H, W = img2d.shape
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
    rmax = min(H, W) / 2.0 - 1
    theta = torch.linspace(0, float(np.pi), nt, device=device)
    rho = torch.exp(torch.linspace(float(np.log(rmin)), float(np.log(rmax)), nr, device=device))
    ys = cy + rho[None, :] * torch.sin(theta[:, None])
    xs = cx + rho[None, :] * torch.cos(theta[:, None])
    grid = torch.stack([xs / (W - 1) * 2 - 1, ys / (H - 1) * 2 - 1], dim=-1)[None]
    out = F.grid_sample(img2d[None, None], grid, align_corners=True, mode="bilinear")
    return out[0, 0], float(np.log(rmax) - np.log(rmin))


def _parab(r, i, axis, fix):
    """周期対応の放物線サブピクセル。axis 方向 i、他軸 fix の近傍 3 点で頂点を補間。"""
    n = r.shape[axis]

    def g(k):
        k = k % n
        return float(r[k, fix] if axis == 0 else r[fix, k])

    a, b, c = g(i - 1), g(i), g(i + 1)
    d = a - 2 * b + c
    return i + (0.5 * (a - c) / d if abs(d) > 1e-9 else 0.0)


def match_logpolar_z(a, b, device="cpu", project="mip", nt=360, nr=192):
    """log-polar × 位相相関(Fourier-Mellin)で **z 軸回転 + 等方スケール**を復元。

    構造=voxel × 手法=Fourier-Mellin。PCA が点対応を要すのに対し、これはテンプレ/対応不要で
    回転(z 軸)とスケールを同時推定する唯一の列。核心: z 投影(MIP)を取ると z 軸回転=面内回転・
    等方スケール=面内スケールに落ち、確立された 2D Fourier-Mellin(|FFT|→高域強調→log-polar→
    位相相関)が使える。返り値 (angle_deg, scale)。

    honest な限界(**coarse 推定器**、下流で NCC/ICP 精緻化前提): |回転|≲40° で誤差 ~2-5°。
    |FFT| の 180° 対称により ±45°/±90° 近傍は別名化して外し得る。スケールは中央ローブ偏りで
    ~10% 過小に出る。full-whitening はこの投影の非シフト DC プラトーでゼロロックするため、
    plain 相関 + rho-Hann 窓 + 放物線サブピクセルを用いる。

    引数: ``a``, ``b`` は 3-D volume(同形でなくてもよいが、投影の縦横比が違うと log-polar の
    対応が崩れる)。``project="mip"`` で軸 0 の最大値投影、それ以外は軸 0 の総和投影。``nt``/``nr``
    は log-polar の角度・半径サンプル数(角度分解能 180°/nt)。
    返り値 ``(angle_deg, scale)``: ``b`` が ``a`` を軸 0 まわりに ``angle_deg`` 回して ``scale``
    倍したものと推定する(``b ≈ zoom(rotate(a, angle_deg, axes=(1,2)), scale)``、回転の向きは
    ``scipy.ndimage.rotate`` と同じ)。角度は ±90° の範囲で別名化する。
    後段: ``refine_rotation_z(scene=b, template=a, init_angle_deg=angle_deg)`` で追い込み →
    ``match_phase_3d`` で並進。
    """
    v_a = np.asarray(a, np.float64)
    v_b = np.asarray(b, np.float64)
    pa = v_a.max(0) if project == "mip" else v_a.sum(0)
    pb = v_b.max(0) if project == "mip" else v_b.sum(0)
    ma = _fmt_spectrum(pa, device)
    mb = _fmt_spectrum(pb, device)
    la, span = _logpolar(ma, nt, nr, device)
    lb, _ = _logpolar(mb, nt, nr, device)
    wr = torch.hann_window(nr, periodic=False, device=device)[None, :]   # rho は非周期→窓
    laz = (la - la.mean()) * wr
    lbz = (lb - lb.mean()) * wr
    A = torch.fft.fft2(lbz)
    B = torch.fft.fft2(laz)
    r = torch.fft.ifft2(A * B.conj()).real                              # theta 周期・plain 相関
    pk = np.unravel_index(int(torch.argmax(r)), tuple(r.shape))
    fi = _parab(r, pk[0], 0, pk[1])
    fj = _parab(r, pk[1], 1, pk[0])
    dth = fi - (nt if fi > nt / 2 else 0)
    dlr = fj - (nr if fj > nr / 2 else 0)
    angle = -float(dth) / nt * 180.0
    scale = float(np.exp(-float(dlr) / (nr - 1) * span))
    return angle, scale


# ═══════════════════════════════════════════════════════════════════════════
# GPU 厳密 EDT(jump flooding)→ chamfer を全 GPU 化
# ═══════════════════════════════════════════════════════════════════════════
def _shift3(t, dz, dy, dx, fill):
    """(3,D,H,W) を整数シフト、露出領域は fill。オーバーラップ無しは全 fill。"""
    out = torch.full_like(t, fill)
    D, H, W = t.shape[1:]
    if abs(dz) >= D or abs(dy) >= H or abs(dx) >= W:
        return out                                          # 重なり無し
    zsr = slice(max(0, -dz), D - max(0, dz)); zds = slice(max(0, dz), D - max(0, -dz))
    ysr = slice(max(0, -dy), H - max(0, dy)); yds = slice(max(0, dy), H - max(0, -dy))
    xsr = slice(max(0, -dx), W - max(0, dx)); xds = slice(max(0, dx), W - max(0, -dx))
    out[:, zds, yds, xds] = t[:, zsr, ysr, xsr]
    return out


def edt_jfa(seed_bool, device="cpu"):
    """3D ユークリッド距離変換 = Jump Flooding Algorithm(GPU)。各 voxel → 最近 seed 距離。

    実測で scipy EDT と厳密一致(max|err|=0、N≤160・JFA+2)。scipy(C 実装)は小さい N では
    速いが、GPU-JFA は N≥96 で追い抜く(RTX5090 実測 96→2.6× / 128→4.7×)。全 voxel 並列で
    GPU 常駐でき、chamfer を CPU 往復なしの全 GPU パイプラインにするのが本質。末尾の step=1 を
    2 パス(JFA+2)にして大 N の近似誤差も消す。返り値 距離場 (D,H,W) の torch tensor。

    引数 ``seed_bool`` は ``(D,H,W)`` の bool(True=seed、距離 0)。返り値は **torch float32
    tensor** ``(D,H,W)``(``device`` 上、numpy ではない。台帳経由 ``fs.ledger.edt_jfa`` では
    numpy に変換される)。距離は voxel 中心間のユークリッド距離(voxel 単位)。
    seed が 1 つも無いと全 voxel が 1e6 に飽和する(例外は出ない)。26 方向 × log2(max(D,H,W))
    段のジャンプなので、メモリは ``(3,D,H,W)`` float32 が数枚分。
    用途: ``signed_distance_field``(両側)、``match_chamfer_3d(edt="jfa")``。CPU 版は
    ``scipy.ndimage.distance_transform_edt(~seed)`` と同じ値。
    """
    _INF = 1e9
    s = torch.as_tensor(np.asarray(seed_bool, bool), device=device)
    D, H, W = s.shape
    zz, yy, xx = torch.meshgrid(
        torch.arange(D, device=device, dtype=torch.float32),
        torch.arange(H, device=device, dtype=torch.float32),
        torch.arange(W, device=device, dtype=torch.float32), indexing="ij")
    pos = torch.stack([zz, yy, xx], 0)
    coord = torch.where(s[None].expand(3, -1, -1, -1), pos, torch.full_like(pos, -_INF))
    offs = [(dz, dy, dx) for dz in (-1, 0, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
            if (dz, dy, dx) != (0, 0, 0)]
    step = 1
    while step < max(D, H, W):
        step *= 2
    steps = []
    while step >= 1:
        steps.append(step); step //= 2
    steps += [1, 1]                                          # JFA+2(N≤160 で厳密 max|err|=0)
    for st in steps:
        base = coord
        best = coord.clone()
        best_d2 = ((best - pos) ** 2).sum(0)
        for (dz, dy, dx) in offs:
            cand = _shift3(base, dz * st, dy * st, dx * st, -_INF)
            d2 = ((cand - pos) ** 2).sum(0)
            upd = d2 < best_d2
            best_d2 = torch.where(upd, d2, best_d2)
            best = torch.where(upd[None].expand(3, -1, -1, -1), cand, best)
        coord = best
    return torch.sqrt(((coord - pos) ** 2).sum(0)).clamp_max(1e6)


# ═══════════════════════════════════════════════════════════════════════════
# generalized Hough 3D(勾配方向 R-table 投票)= 向きビンごとの相関の総和
# ═══════════════════════════════════════════════════════════════════════════
def _sphere_dirs(ndir, device):
    """ndir 個の参照単位方向。ndir≤26 は正規化 26 近傍、超えたら fibonacci 球。"""
    if ndir <= 26:
        d = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)
             if (a, b, c) != (0, 0, 0)]
        v = torch.tensor(d[:ndir], dtype=torch.float32, device=device)
    else:
        i = torch.arange(ndir, dtype=torch.float32, device=device)
        ga = float(np.pi * (3 - np.sqrt(5.0)))
        z = 1 - 2 * (i + 0.5) / ndir
        rr = torch.sqrt(torch.clamp(1 - z * z, min=0.0))
        th = ga * i
        v = torch.stack([z, rr * torch.sin(th), rr * torch.cos(th)], 1)
    return v / v.norm(dim=1, keepdim=True)


def match_hough_3d(scene, template, device="cpu", ndir=26, mc=0.05,
                   topk=1, nms=3, subvoxel=True):
    """generalized Hough 3D(Ballard R-table 投票)。voxel × Hough 列。

    GHT を **向きビンごとの相関の総和** として GPU ネイティブに定式化:
    accumulator A(t) = Σ_bin ( scene_bin ⋆ template_bin )。各エッジが勾配方向に応じて投票し、
    欠けたエッジはピークを下げるだけ(**遮蔽・クラッタに頑健**)。shape-based(連続内積の単一解)
    と違い **投票 accumulator を返し、NMS で複数ピーク = 複数インスタンス** を取れるのが差別化。
    返り値 (topk,4) の [votes, d, h, w](votes 降順)。

    手順: 両 volume の単位勾配(``mc`` は ``sobel3d`` の生出力への閾値)を ``ndir`` 本の参照方向の
    うち最も近いものに量子化し、方向ビンごとに「scene のそのビンの 2 値場 ⋆ テンプレのそのビンの
    2 値場」を conv3d で足し合わせる。テンプレの有効エッジ数で割るので votes は **[0, 1]**、1 で
    全エッジが一致。
    - ``ndir``: 26 以下は 26 近傍方向のリストの先頭 ``ndir`` 本(26 未満は方向が偏る)、27 以上は
    fibonacci 球で一様。方向が粗いほど回転に寛容だが偽ピークも増える。
    - 返り値 ``(topk, 4)`` の各行 ``[votes, z, y, x]``、votes 降順。座標は **テンプレ中心 (T//2)**
    の scene 座標、``subvoxel=True`` なら ±2 近傍重心。
    - ``nms``: ピークを取るたびに ``±nms`` voxel の立方体を −1 で潰してから次を探す。近接する
    複数インスタンスは ``nms`` を小さく。
    - テンプレにエッジが無ければ全 0 の ``(topk,4)``。テンプレが完全に収まらない位置は 0。
    後段: 各ピークを ``refine_translation_lk`` / ``refine_peak_newton`` で精緻化。
    """
    sz, sy, sx, sm = _unit_grad3d(scene, device, mc)
    tz, ty, tx, tm = _unit_grad3d(np.asarray(template, np.float64), device, mc)
    dirs = _sphere_dirs(ndir, device)                       # (ndir,3)
    sg = torch.stack([sz[0, 0], sy[0, 0], sx[0, 0]], 0)     # (3,D,H,W)
    tg = torch.stack([tz[0, 0], ty[0, 0], tx[0, 0]], 0)
    sbin = torch.argmax(torch.einsum("kd,dzyx->kzyx", dirs, sg), 0)   # (D,H,W)
    tbin = torch.argmax(torch.einsum("kd,dzyx->kzyx", dirs, tg), 0)
    smask = sm[0, 0] > 0.5
    tmask = tm[0, 0] > 0.5
    Td, Th, Tw = np.asarray(template).shape
    pd, ph, pw = Td // 2, Th // 2, Tw // 2
    acc = None
    ntempl = 0.0
    for i in range(ndir):
        tind = ((tbin == i) & tmask).float()
        c = float(tind.sum())
        if c < 0.5:
            continue
        ntempl += c
        sind = ((sbin == i) & smask).float()[None, None]
        corr = F.conv3d(F.pad(sind, (pw, pw, ph, ph, pd, pd)), tind[None, None])
        acc = corr if acc is None else acc + corr
    if acc is None:
        return np.zeros((topk, 4))
    acc = (acc / max(1.0, ntempl))[0, 0]
    D, H, W = np.asarray(scene).shape
    lo = (pd, ph, pw); hi = (D - (Td - 1 - pd), H - (Th - 1 - ph), W - (Tw - 1 - pw))
    mask = torch.zeros_like(acc)
    if all(h > l for l, h in zip(lo, hi)):
        mask[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] = 1.0
    a = (acc * mask).detach().cpu().numpy()
    peaks = []
    for _ in range(topk):
        idx = np.unravel_index(int(np.argmax(a)), a.shape)
        pos = M._subvoxel_com(a, idx, 2) if subvoxel else [float(i) for i in idx]
        peaks.append([float(a[idx])] + list(pos))
        z0, z1 = max(0, idx[0] - nms), idx[0] + nms + 1
        y0, y1 = max(0, idx[1] - nms), idx[1] + nms + 1
        x0, x1 = max(0, idx[2] - nms), idx[2] + nms + 1
        a[z0:z1, y0:y1, x0:x1] = -1.0
    return np.array(peaks)


# ═══════════════════════════════════════════════════════════════════════════
# 線→面リフト: 曲面曲率(主曲率 κ1,κ2 / shape index)= 2 次の曲面固有量
# ═══════════════════════════════════════════════════════════════════════════
def hessian3d(vol, device="cpu"):
    """3D Hessian の 6 独立成分 (fzz,fyy,fxx,fzy,fzx,fyx)。分離 conv3d(2 階/1 階×平滑)。

    カーネル: 2 階 [1,−2,1](利得 1)、1 階 [−0.5,0,0.5](利得 1)、残りの軸は [1,2,1]/4 の平滑
    (利得 1)。対角成分は「その軸の 2 階 × 他 2 軸の平滑」、交差成分は「2 軸の 1 階 × 残り軸の
    平滑」。**単位は 1/voxel² の真の値**(``sobel3d`` の 32 倍利得とは違う)。端は replicate。
    返り値は **list の torch tensor 6 本**、各 ``(D,H,W)`` float32、``device`` 上、順は
    (zz, yy, xx, zy, zx, yx)(軸 0=z, 1=y, 2=x)。numpy が要れば ``.cpu().numpy()``。入力は
    numpy 相当(float32 に変換)。
    用途: ``curvature_maps`` の主曲率(``sobel3d`` と組で使う)、blob/管状構造の検出。
    """
    t = torch.as_tensor(np.asarray(vol, np.float32)[None, None], device=device)
    d2 = torch.tensor([1.0, -2.0, 1.0], device=device)
    d1 = torch.tensor([-0.5, 0.0, 0.5], device=device)
    sm = torch.tensor([1.0, 2.0, 1.0], device=device) / 4.0

    def sep(k0, k1, k2):
        out = t
        for ax, k in enumerate((k0, k1, k2)):
            shp = [1, 1, 1, 1, 1]; shp[2 + ax] = 3
            pad = [0, 0, 0, 0, 0, 0]; pad[(2 - ax) * 2] = 1; pad[(2 - ax) * 2 + 1] = 1
            out = F.conv3d(F.pad(out, tuple(pad), mode="replicate"), k.view(*shp))
        return out

    fzz = sep(d2, sm, sm); fyy = sep(sm, d2, sm); fxx = sep(sm, sm, d2)
    fzy = sep(d1, d1, sm); fzx = sep(d1, sm, d1); fyx = sep(sm, d1, d1)
    return [x[0, 0] for x in (fzz, fyy, fxx, fzy, fzx, fyx)]


def curvature_maps(vol, device="cpu", mc=6.25e-4):
    """level-set の主曲率 → shape index S(Koenderink)と curvedness。閉形式(Kindlmann 2003)。

    2D 輪郭の曲率(スカラー 1 個)の **線→面リフト**: 曲面は主曲率 κ1,κ2 の 2 個を持つ。
    mean = (κ1+κ2)/2 = (|g|²trH − gᵀHg)/|g|³、Gauss K = κ1κ2 = gᵀadj(H)g/|g|⁴(g=∇, H=Hessian)。
    S=(2/π)atan2(κ1+κ2, κ1−κ2) ∈[-1,1] は **強度・回転に不変な局所曲面型**(cup−1/rut/saddle0/
    ridge+.5/cap+1)。外向き法線規約で明凸 blob=cap(+1)。返り値 (S, curvedness, mask, |g|)、全 torch。

    単位系: sobel3d の分離 conv 利得 32(deriv[-1,0,1]×平滑[1,2,1]²)をここで割り戻すので、
    κ1,κ2/curvedness は **真の 1/voxel 単位**(半径 R の球殻で curvedness=1/R)、|g| と
    mask 閾値 mc は **voxel あたりの真の勾配単位**。旧版(〜2026-08-29)は割り戻しを忘れ
    curvedness が 1/32 倍・mc が生 sobel3d 単位だった(shape index S は比なので影響なし)。
    旧 mc 値を使っていた場合は 1/32 して渡すこと(既定値 0.02→6.25e-4 も等価変換済み)。
    """
    gz, gy, gx = sobel3d(vol, device)
    # sobel3d は利得 32 の規約(refine_translation_lk 等は grad_scale=32 で補正) — ここでも割り戻す
    gz, gy, gx = gz[0, 0] / 32.0, gy[0, 0] / 32.0, gx[0, 0] / 32.0
    a, b, c, d, e, f = hessian3d(vol, device)               # a=Hzz b=Hyy c=Hxx d=Hzy e=Hzx f=Hyx
    g2 = gz * gz + gy * gy + gx * gx
    gmag = torch.sqrt(g2.clamp_min(1e-12))
    trH = a + b + c
    gHg = (gz * gz * a + gy * gy * b + gx * gx * c
           + 2 * gz * gy * d + 2 * gz * gx * e + 2 * gy * gx * f)
    ksum = -(g2 * trH - gHg) / (g2 * gmag).clamp_min(1e-12)  # κ1+κ2(外向き法線)
    A11 = b * c - f * f; A22 = a * c - e * e; A33 = a * b - d * d
    A12 = e * f - d * c; A13 = d * f - b * e; A23 = d * e - a * f
    gAg = (gz * gz * A11 + gy * gy * A22 + gx * gx * A33
           + 2 * gz * gy * A12 + 2 * gz * gx * A13 + 2 * gy * gx * A23)
    K = gAg / (g2 * g2).clamp_min(1e-12)                    # Gauss 曲率 κ1κ2
    Hm = ksum * 0.5
    disc = torch.sqrt((Hm * Hm - K).clamp_min(0.0))
    k1 = Hm + disc; k2 = Hm - disc
    S = (2 / float(np.pi)) * torch.atan2(k1 + k2, (k1 - k2).clamp_min(1e-9))
    curv = torch.sqrt(((k1 * k1 + k2 * k2) * 0.5).clamp_min(0.0))
    mask = (gmag > mc).float()
    return S, curv, mask, gmag


def match_curvature_3d(scene, template, device="cpu", mc=6.25e-4, subvoxel=True):
    """曲率(shape index)マッチング。voxel × 曲率列(線→面リフトの本丸)。

    scene/template を **curvedness で重み付けした shape-index 場**へ変換 → 既存 3D NCC で定位。
    強度でなく **局所曲面形状**で一致を測るため、同じ強度でも形が違う対象(球 vs 円柱/鞍点)を
    区別できる。S は回転不変なので回転にもある程度頑健。返り値 [score, d, h, w]。

    手順: 両 volume で ``curvature_maps`` → ``S × curvedness × mask`` の重み付き shape-index 場
    ``w`` を作り、テンプレ側は ``|w| > 0.1·max|w|`` の bbox を切り出して
    ``accel_match.ncc_locate_3d`` に渡す。返り値 ``[NCC, z, y, x]`` float64、NCC ∈ [−1, 1]。
    - **位置は切り出した bbox テンプレの中心**が scene に載る座標。元テンプレ volume の中心とは
    bbox のオフセット分ずれる(元テンプレ座標に戻すには bbox の lo を足し直す)。
    - ``mc``: ``curvature_maps`` の勾配マスク閾値(真の勾配単位、voxel あたり)。平坦部を除いて
    曲率ノイズを抑える。
    - テンプレの曲率場が全 0(平坦・``mc`` が高すぎ)なら ``[0,0,0,0]`` を返す。
    - 曲率は 2 階微分なのでノイズに敏感。ノイズが多い volume は先に ``points_to_voxel`` の
    ``smooth`` 等で滑らかにする。
    ``subvoxel=True`` で NCC ピークの ±2 近傍重心に精緻化。
    """
    Ss, Cs, Ms, _ = curvature_maps(scene, device, mc)
    St, Ct, Mt, _ = curvature_maps(template, device, mc)
    ws = (Ss * Cs * Ms).detach().cpu().numpy()
    wt = (St * Ct * Mt).detach().cpu().numpy()
    nz = np.argwhere(np.abs(wt) > np.abs(wt).max() * 0.1)
    if len(nz) == 0:
        return np.array([0.0, 0.0, 0.0, 0.0])
    lo = nz.min(0); hi = nz.max(0) + 1
    tmpl = wt[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]         # 曲率テンプレの bbox
    return M.ncc_locate_3d([ws], tmpl, device, subvoxel=subvoxel)[0]


# ═══════════════════════════════════════════════════════════════════════════
# パラメトリック Hough(2D 直線/円 → 3D 平面/球)= テンプレ不要の原始形状検出
# ═══════════════════════════════════════════════════════════════════════════
def _thin_surface(vol, device, iso=0.5):
    """薄い境界面(1 voxel)= (vol>iso) と、その erosion の差。厚い勾配帯を排除。"""
    t = torch.as_tensor(np.asarray(vol, np.float32), device=device)
    b = (t > iso).float()[None, None]
    er = -F.max_pool3d(-b, 3, stride=1, padding=1)       # min-pool = erosion
    return ((b > 0.5) & (er < 0.5))[0, 0]


def hough_plane_3d(vol, device="cpu", ndir=200, nd=128, mc=0.0, iso=0.5, tol=1.0):
    """平面検出(2D Hough 直線の 3D リフト)。勾配=法線を使い (法線 n, 距離 d) 空間へ投票。

    薄い境界面の各 voxel が自分の法線方向ビンと d=n·p に投票 → ピーク=支配平面。法線は勝ちビン内
    の実法線平均で精緻化、d は投影のモード。点群/voxel の地面・壁の抽出に。返り値 (n(3,), d, inliers, total)。

    手順: ``(vol > iso)`` の 1 voxel 厚の境界面(占有 voxel のうち 3³ erosion で消えるもの)を取り、
    その voxel の単位勾配(``sobel3d``、``mc`` は生出力への閾値)を法線 ``n`` にする。``n`` は軸 0
    成分が非負になるよう半球へ畳み、``d = n·p``(``p`` は整数 voxel index ``(z,y,x)``)。``ndir``
    本の参照方向(26 以下は 26 近傍、それ以上は fibonacci 球)と ``nd`` 個の d ビンに投票し、
    最多ビンの実法線平均で n を、その n への射影ヒストグラムのモード近傍の中央値で d を精緻化する。
    返り値 ``(n(3,), d, inliers, total)``: ``n`` は **(z,y,x) 順**の単位法線(numpy float32)、
    平面は ``n·(z,y,x) = d``(voxel 単位)。``inliers`` は ``|n·p − d| < tol`` の境界 voxel 数、
    ``total`` は境界 voxel の総数(inliers/total が支配平面の占める割合)。
    - 境界 voxel が 10 未満なら **None を返す**(例外ではない)。
    - 密度 voxel は ``iso`` で 2 値化される(個数密度なら 0.5 で「1 点以上」)。
    - 1 枚しか返さない。複数平面はインライアを除いて再実行するか、点群なら ``plane_segmentation``
    / ``ransac_plane``。
    後段: ``distance_point_plane`` / ``angle_between_planes`` で計測。
    """
    gz, gy, gx, _ = _unit_grad3d(vol, device, mc)
    gz, gy, gx = gz[0, 0], gy[0, 0], gx[0, 0]
    surf = _thin_surface(vol, device, iso)
    idx = torch.nonzero(surf, as_tuple=False).float()
    if len(idx) < 10:
        return None
    P = idx
    n = torch.stack([gz[surf], gy[surf], gx[surf]], 1)
    flip = n[:, 0] < 0
    n[flip] *= -1                                        # 半球に畳む(n と -n は同一平面)
    d = (n * P).sum(1)
    dirs = _sphere_dirs(ndir, device)
    dirs = dirs * torch.sign(dirs[:, 0:1] + 1e-9)
    bins = torch.argmax(n @ dirs.T, 1)
    dmin, dmax = float(d.min()), float(d.max())
    dbin = torch.clamp(((d - dmin) / (dmax - dmin + 1e-9) * (nd - 1)).long(), 0, nd - 1)
    acc = torch.zeros(ndir * nd, device=device)
    acc.scatter_add_(0, bins * nd + dbin, torch.ones(len(bins), device=device))
    pk = int(torch.argmax(acc)); bi = pk // nd
    ncoarse = dirs[bi]
    inbin = (n @ ncoarse) > 0.98
    nrm = n[inbin].mean(0) if int(inbin.sum()) >= 5 else ncoarse
    nrm = nrm / nrm.norm().clamp_min(1e-9)
    proj = P @ nrm
    hist = torch.histc(proj, bins=nd, min=dmin, max=dmax)
    hb = int(torch.argmax(hist))
    dc = dmin + (hb + 0.5) / nd * (dmax - dmin)
    near = proj[(proj - dc).abs() < (dmax - dmin) / nd * 2]
    dval = float(near.median()) if len(near) > 0 else float(dc)
    inl = int(((P @ nrm) - dval).abs().lt(tol).sum())
    return nrm.detach().cpu().numpy(), dval, inl, int(len(idx))


def hough_sphere_3d(vol, device="cpu", radii=None, mc=0.0, iso=0.5, subvoxel=True):
    """球検出(2D Hough 円の 3D リフト)。中心 = p + sgn·r·n を半径 r ごとに投票。

    薄い境界面の各 voxel が法線 n に沿って中心へ投票(符号は明/暗どちらの球でも拾えるよう両方試す)。
    半径ごとの中心ピーク投票の最大 = 検出球。votes-vs-radius を放物線補間で sub-voxel 半径。
    産業: ボール・球状部品・点群中の球面。返り値 (votes, radius, center(3,))。

    手順: ``(vol > iso)`` の 1 voxel 厚の境界面 voxel ``p`` とその単位法線 ``n``(``sobel3d``、
    ``mc`` は生出力への閾値)から、半径 ``r`` ごとに ``c = round(p ± r·n)`` へ投票し(± は明球・
    暗球の両方を試し、多い方を採る)、volume 内に落ちた票の最大値をその r のスコアにする。全 r で
    最大のものが検出球。
    - ``radii``: 試す半径(voxel 単位)の列。None なら ``range(4, 16)``(4〜15)。``subvoxel=True``
    は最良 r の **両隣 r±1 が radii に含まれるとき**だけ votes の放物線補間で半径を ±1 以内に
    精緻化する(端の r や飛び飛びの radii では整数のまま)。
    - 返り値 ``(votes, radius, center)``: votes は票数(境界 voxel 数が上限)、radius は float、
    center は **整数 (z,y,x) の tuple**(中心は精緻化しない)。
    - 境界 voxel が 10 未満なら **None**。``radii`` が空だと TypeError で落ちる。
    - 1 個しか返さない。複数球は検出した球の voxel を消して再実行するか、点群なら
    ``ransac_sphere`` / ``fit_sphere_3d``。
    """
    gz, gy, gx, _ = _unit_grad3d(vol, device, mc)
    gz, gy, gx = gz[0, 0], gy[0, 0], gx[0, 0]
    surf = _thin_surface(vol, device, iso)
    idx = torch.nonzero(surf, as_tuple=False).float()
    if len(idx) < 10:
        return None
    n = torch.stack([gz[surf], gy[surf], gx[surf]], 1)
    D, H, W = surf.shape
    dims = torch.tensor([D, H, W], device=device)
    radii = list(radii) if radii is not None else list(range(4, 16))
    vote_r = {}
    best = None
    for r in radii:
        rbest = 0.0; rcenter = (0, 0, 0)
        for sgn in (1.0, -1.0):
            ci = torch.round(idx + sgn * r * n).long()
            ok = ((ci >= 0) & (ci < dims)).all(1)
            cj = ci[ok]
            if len(cj) < 5:
                continue
            acc = torch.zeros(D * H * W, device=device)
            acc.scatter_add_(0, (cj[:, 0] * H + cj[:, 1]) * W + cj[:, 2],
                             torch.ones(len(cj), device=device))
            v, pk = torch.max(acc, 0)
            if float(v) > rbest:
                rbest = float(v); rcenter = np.unravel_index(int(pk), (D, H, W))
        vote_r[r] = rbest
        if best is None or rbest > best[0]:
            best = (rbest, r, rcenter)
    rr = best[1]                                         # 放物線で sub-voxel 半径
    if subvoxel and (rr - 1) in vote_r and (rr + 1) in vote_r:
        a, b, c = vote_r[rr - 1], vote_r[rr], vote_r[rr + 1]
        den = a - 2 * b + c
        off = 0.5 * (a - c) / den if abs(den) > 1e-9 else 0.0
        rr = rr + float(np.clip(off, -1, 1))
    return best[0], rr, tuple(int(x) for x in best[2])


# ═══════════════════════════════════════════════════════════════════════════
# 線→面リフト: 球面調和記述子(2D 輪郭 Fourier 記述子 → 3D 曲面 SH、回転不変)
# ═══════════════════════════════════════════════════════════════════════════
def _sh_basis(L, ntheta, nphi):
    """実装用 SH 基底 Y_lm(θ,φ) 行列と帯域ラベル・面積重み。scipy 版差を吸収。"""
    from scipy import special
    th = np.linspace(0, np.pi, ntheta)
    ph = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    TH, PH = np.meshgrid(th, ph, indexing="ij")
    if hasattr(special, "sph_harm_y"):
        def Y(l, m):
            return special.sph_harm_y(l, m, TH, PH)      # 新 API: (l,m,theta,phi)
    else:
        def Y(l, m):
            return special.sph_harm(m, l, PH, TH)        # 旧 API: (m,l,phi,theta)
    rows, bands = [], []
    for l in range(L + 1):
        for m in range(-l, l + 1):
            rows.append(Y(l, m).reshape(-1)); bands.append(l)
    return np.stack(rows, 0), np.array(bands), np.sin(TH).reshape(-1), TH, PH


def sh_descriptor(vol, L=8, nradii=12, ntheta=32, nphi=64, device="cpu"):
    """球面調和記述子。同心球 shell の SH 帯域エネルギー ‖f_l(r)‖ を (半径 × 周波数) で返す。

    2D 閉輪郭を 1D Fourier 記述子で表す **線→面リフト**: 3D 閉曲面は SH で表し、帯域エネルギーは
    回転で m を帯域内に混ぜるだけ=**回転不変**(Kazhdan 2003)。全 shell を grid_sample で取り、
    固定 SH 基底との内積 → 帯域二乗和。retrieval/verification 用の大域シグネチャ。返り値 (nradii,L+1)。

    honest 開示(2026-08-30 レビュー実測): 球面求積は一様 θ×φ グリッド和(Gauss-Legendre
    でない)ため、値は**厳密な SH 帯域エネルギーの近似**(既定 32×64 で l=4 自己内積が
    理論値の ~0.62 倍、解像度↑で 1 に収束)。match_sh_descriptor は L2 正規化+コサイン
    類似度なので**同一 ntheta/nphi 同士の比較には影響しない**が、絶対値を物理量として
    使う・異なる解像度設定間で比較するのは不可。

    引数: ``vol`` は **立方体**(N,N,N)前提。中心 ``c = (N−1)/2`` と座標の正規化に軸 0 の長さ N
    だけを使うので、非立方体だと軸 1,2 のサンプル位置が歪む(検証は無い)。shell 半径は
    ``0.2·rmax`` 〜 ``rmax = N/2 − 1`` を ``nradii`` 等分(voxel 単位)、各 shell を
    ``ntheta × nphi`` の (θ,φ) 格子で trilinear サンプルする。``L`` は最大次数。
    返り値 ``(nradii, L+1)`` float32 numpy、``[i, l]`` が i 番目の shell の次数 l のエネルギー
    (非負)。物体は volume の中心に置く(中心がずれると回転不変性が崩れる。``moment_axes`` の
    重心で先に中心合わせを)。scipy の ``sph_harm_y``/``sph_harm`` を呼び出し時 import。
    """
    v = np.asarray(vol, np.float64)
    N = v.shape[0]
    c = (N - 1) / 2.0
    B, bands, w, TH, PH = _sh_basis(L, ntheta, nphi)
    Bt = torch.as_tensor(B, dtype=torch.complex64, device=device)
    wt = torch.as_tensor(w, dtype=torch.float32, device=device)
    t = torch.as_tensor(v, dtype=torch.float32, device=device)[None, None]
    rmax = N / 2.0 - 1
    radii = np.linspace(rmax * 0.2, rmax, nradii)
    dirz = torch.as_tensor(np.cos(TH).reshape(-1), dtype=torch.float32, device=device)
    diry = torch.as_tensor((np.sin(TH) * np.sin(PH)).reshape(-1), dtype=torch.float32, device=device)
    dirx = torch.as_tensor((np.sin(TH) * np.cos(PH)).reshape(-1), dtype=torch.float32, device=device)
    band_masks = [torch.as_tensor(bands == l, device=device) for l in range(L + 1)]
    desc = torch.zeros(nradii, L + 1, device=device)
    for ri, r in enumerate(radii):
        zz = c + r * dirz; yy = c + r * diry; xx = c + r * dirx
        grid = torch.stack([xx / (N - 1) * 2 - 1, yy / (N - 1) * 2 - 1,
                            zz / (N - 1) * 2 - 1], dim=-1)[None, None, None]
        shell = F.grid_sample(t, grid, align_corners=True, mode="bilinear")[0, 0, 0, 0]
        coeff = Bt @ (shell * wt).to(torch.complex64) * (4 * float(np.pi) / (ntheta * nphi))
        p2 = (coeff.conj() * coeff).real
        for l in range(L + 1):
            desc[ri, l] = p2[band_masks[l]].sum()
    return desc.detach().cpu().numpy()


def match_sh_descriptor(a, b, L=8, nradii=12, device="cpu"):
    """SH 記述子同士のコサイン類似度(回転不変な形状照合)。1 に近いほど同形状。voxel × SH 列。

    ``sh_descriptor(a, L, nradii)`` と ``sh_descriptor(b, L, nradii)`` を平坦化して L2 正規化し、
    内積を float で返す。帯域エネルギーは非負なので値は **[0, 1]**(負にならない)。どちらかの
    記述子が全 0(空 volume)なら 0。
    - ``a``, ``b`` は立方体 volume(``sh_descriptor`` の前提)。形が違ってもよいが、shell 半径が
    各 N で決まるので **スケールが違う物体は別物**として低く出る(スケール不変ではない)。
    中心ずれにも弱い(重心で中心合わせしてから)。
    - 回転には不変(帯域エネルギー)。ただし鏡像も同じ値になる。
    - ``ntheta``/``nphi`` は既定(32×64)固定。同じ設定同士の比較にだけ意味がある。
    - 位置は返さない。「どこにあるか」は ``match_shape_3d`` 等、「同じ形か」は本 op。
    """
    da = sh_descriptor(a, L, nradii, device=device).reshape(-1)
    db = sh_descriptor(b, L, nradii, device=device).reshape(-1)
    da = da / (np.linalg.norm(da) + 1e-9)
    db = db / (np.linalg.norm(db) + 1e-9)
    return float((da * db).sum())


# ═══════════════════════════════════════════════════════════════════════════
# 反復精緻化(粗推定 → Newton / Gauss-Newton / LM / ICP で高精度収束)
# 手段を1つに絞らず発散(Workflow で6手法を並行プロトタイプ+実測検証、全PASS)。
# 粗推定(整数 NCC / Fourier-Mellin ±3° / Hough ±0.5voxel)を下流で締め上げる。
#   refine_peak_newton   : スコア面の 3D Newton サブボクセルピーク(全Hessian、放物線比~9×)
#   refine_translation_lk: 逆合成 Lucas-Kanade 並進(0.008voxel、NCC比~60×)
#   refine_lm            : Levenberg-Marquardt 並進+等方スケール+輝度ゲイン(スケール新規回復)
#   refine_rotation_z    : Gauss-Newton z軸回転(Fourier-Mellin ±3° → 0.01°、~5000×)
#   icp_point2point_3d   : ICP 点-点(Kabsch/SVD、Trimmed で部分重なり)
#   icp_point2plane      : ICP 点-面(Gauss-Newton、表面に高速収束、Low 2004)
# ═══════════════════════════════════════════════════════════════════════════


def _peak_neighbors27(vol_t, pos, device):
    """pos=(z,y,x) 連続座標まわりの {-1,0,1}³ = 27 近傍を trilinear 補間で取得 → (3,3,3)。

    vol_t は (1,1,D,H,W)。grid_sample の grid 最終軸は (x,y,z) 順・正規化 [-1,1]。
    """
    D, H, W = vol_t.shape[-3:]
    o = torch.tensor([-1.0, 0.0, 1.0], device=device)
    gz, gy, gx = torch.meshgrid(o, o, o, indexing="ij")
    nx = 2.0 * (pos[2] + gx) / (W - 1) - 1.0
    ny = 2.0 * (pos[1] + gy) / (H - 1) - 1.0
    nz = 2.0 * (pos[0] + gz) / (D - 1) - 1.0
    grid = torch.stack([nx, ny, nz], dim=-1)[None]           # (1,3,3,3,3)
    out = F.grid_sample(vol_t, grid, mode="bilinear",
                        align_corners=True, padding_mode="border")
    return out[0, 0]                                          # (3,3,3) 添字[dz+1,dy+1,dx+1]


def refine_peak_newton(score, idx, device="cpu", max_iter=12, tol=1e-4):
    """スコア/相関 volume の整数ピークを 3D Newton でサブボクセル精緻化する(反復最適化)。

    粗いマッチ(整数 NCC / Fourier-Mellin ±3° / Hough ±0.5voxel)が返す整数ピーク idx を、局所の
    2 次モデル f(x)≈f0+gᵀΔ+½ΔᵀHΔ の停留点 Δ=-H⁻¹g へ反復更新して連続座標へ収束させる。
    軸別の放物線サブピクセルと違い **全 3x3 Hessian(交差曲率 fzy,fzx,fyx を含む)** を使うため、
    回転した(相互曲率のある)異方性ピークでも座標軸間の結合バイアスを除去できる。

    各反復: 現在位置まわりの 27 近傍を trilinear で取得 → 中心差分で勾配 g と 6 成分 Hessian H を
    組み、Δ=solve(H,-g)。各成分を ±1 voxel にクリップ(信頼領域)して位置を更新、|Δ|<tol で収束。
    ガウス山では中心差分勾配の零点が真のピークに一致するため停留点へ収束する(単一ステップでは
    2 次モデル誤差が残り ±0.05voxel を割れないが、反復で ~0.02voxel まで収束)。H が負定値でない
    (=極大でない)real な相関面では上昇方向へ退避(勾配上昇ステップ)して発散を防ぐ。

    Parameters
    ----------
    score : array_like または torch.Tensor
        3D スコア/相関 volume (D,H,W)。値が大きいほどピーク。
    idx : tuple[int,int,int]
        整数ピーク座標 (z,y,x)(通常 argmax の unravel 結果)。
    device : str
        "cpu" / "cuda"。torch 演算の device。
    max_iter : int
        最大反復回数(既定 12)。
    tol : float
        収束判定(更新量 L2 ノルム、既定 1e-4)。

    Returns
    -------
    numpy.ndarray
        [score_peak, z, y, x](精緻化後)。score_peak は精緻化位置での trilinear 補間スコア。
    """
    vol = torch.as_tensor(np.asarray(score, np.float32), device=device)
    D, H, W = vol.shape
    vol_t = vol[None, None]                                   # (1,1,D,H,W)
    eye = torch.eye(3, device=device)

    pos = torch.tensor([float(idx[0]), float(idx[1]), float(idx[2])],
                       device=device)
    for _ in range(max_iter):
        # 端に寄ると ±1 近傍が範囲外 → クランプ(border 補間で安全だが数値安定のため)
        pos = torch.stack([
            pos[0].clamp(1.0, D - 2.0),
            pos[1].clamp(1.0, H - 2.0),
            pos[2].clamp(1.0, W - 2.0),
        ])
        f = _peak_neighbors27(vol_t, pos, device)            # (3,3,3)
        c = f[1, 1, 1]

        # 中心差分の勾配(step=1)
        g = torch.stack([
            0.5 * (f[2, 1, 1] - f[0, 1, 1]),
            0.5 * (f[1, 2, 1] - f[1, 0, 1]),
            0.5 * (f[1, 1, 2] - f[1, 1, 0]),
        ])
        # 6 成分 Hessian(2 階中心差分 + 交差差分)
        fzz = f[2, 1, 1] - 2 * c + f[0, 1, 1]
        fyy = f[1, 2, 1] - 2 * c + f[1, 0, 1]
        fxx = f[1, 1, 2] - 2 * c + f[1, 1, 0]
        fzy = 0.25 * (f[2, 2, 1] - f[2, 0, 1] - f[0, 2, 1] + f[0, 0, 1])
        fzx = 0.25 * (f[2, 1, 2] - f[2, 1, 0] - f[0, 1, 2] + f[0, 1, 0])
        fyx = 0.25 * (f[1, 2, 2] - f[1, 2, 0] - f[1, 0, 2] + f[1, 0, 0])
        Hm = torch.stack([
            torch.stack([fzz, fzy, fzx]),
            torch.stack([fzy, fyy, fyx]),
            torch.stack([fzx, fyx, fxx]),
        ])

        # 停留点への Newton ステップ Δ = -H⁻¹g(微小 ridge で数値安定化)
        ridge = 1e-6 * (Hm.diagonal().abs().mean() + 1e-9)
        try:
            delta = torch.linalg.solve(Hm + ridge * eye, -g)
        except Exception:
            delta = -g / Hm.diagonal().abs().clamp_min(1e-6)  # 退避: 軸別
        # 上昇方向でなければ(H が極大でない=負定値でない)勾配上昇へ退避
        if float((g * delta).sum()) < 0.0:
            delta = g / torch.linalg.vector_norm(g).clamp_min(1e-9)
        delta = delta.clamp(-1.0, 1.0)                        # 信頼領域 ±1 voxel

        pos = pos + delta
        if float(torch.linalg.vector_norm(delta)) < tol:
            break

    pos = torch.stack([
        pos[0].clamp(0.0, D - 1.0),
        pos[1].clamp(0.0, H - 1.0),
        pos[2].clamp(0.0, W - 1.0),
    ])
    peak = float(_peak_neighbors27(vol_t, pos, device)[1, 1, 1])
    p = pos.detach().cpu().numpy().astype(np.float64)
    return np.array([peak, p[0], p[1], p[2]])


def _init_pos3(v, op):
    """粗マッチ初期位置 [z,y,x] の検証(fail-closed)。→ (3,) float 配列。

    連鎖ファザー実測(wave-4, refine_rotation_z): プール産物(tuple/dict)が
    そのまま init 引数へ流れ込み float()/添字が生 TypeError/KeyError で落ちる
    穴の兄弟一掃。型・形状不正は明確な ValueError で拒否する。
    """
    try:
        a = np.asarray(v, float).reshape(-1)
    except (TypeError, ValueError) as e:
        raise ValueError("%s: init_pos must be a numeric [z, y, x] position "
                         "(got %s) — pass the coarse-match location"
                         % (op, type(v).__name__)) from e
    if a.shape[0] != 3:
        raise ValueError("%s: init_pos must have exactly 3 components [z, y, x] "
                         "(got %d)" % (op, a.shape[0]))
    return a


def refine_translation_lk(scene, template, init_pos, device="cpu", iters=30, tol=1e-4):
    """Gauss-Newton 逆合成 Lucas-Kanade による 3D 並進サブボクセル精緻化。

    粗マッチ(整数 NCC / Fourier-Mellin / Hough)が与えた整数初期位置 ``init_pos`` を
    出発点に、SSD ``Σ|I(x+p) − T(x)|²`` を最小化してサブボクセル並進 ``p`` へ収束させる。

    逆合成(inverse-compositional, Baker–Matthews)方式のため steepest-descent 画像
    ``SD = ∇T`` と Hessian ``H = Σ SDᵀSD`` を **反復前に一度だけ**前計算し、各反復は
    「scene の trilinear ワープ + 残差 + 3×3 線形解 ``Δp = H⁻¹ Σ SDᵀ(I(x+p)−T)``」のみ。
    並進の合成は ``p ← p − Δp``。純並進ワープでは ∂W/∂p=I なので SD=∇T がそのまま使える。

    座標系: ``init_pos`` と戻り値はいずれも **テンプレート原点(corner, index 0,0,0)** が
    scene のどの (dz,dy,dx) に載るか。``sobel3d`` / ``grid_sample`` の corner 規約に一致
    (NCC(ncc_locate_3d)の中心規約とは T//2 だけ異なる点に注意)。

    Parameters
    ----------
    scene : (D,H,W) array_like
        探索対象ボリューム。
    template : (Td,Th,Tw) array_like
        位置合わせするテンプレート(scene より小)。
    init_pos : (3,) sequence
        整数初期位置 (dz,dy,dx) = テンプレート原点の scene 座標。
    device : str
        "cpu" / "cuda" 等。device 非依存。
    iters : int
        最大反復数。
    tol : float
        ‖Δp‖ がこの値を下回ったら収束打ち切り。

    Returns
    -------
    pos : (3,) np.ndarray(float64)
        精緻化されたサブボクセル位置 (dz,dy,dx)。

    Notes
    -----
    - 滑らか(帯域制限)な密度場を仮定。整数初期値が真値の ±0.5〜1 voxel 内であれば
      通常 5〜8 反復で ‖err‖ < 0.05 voxel(低ノイズ時)。実測(独立 cubic-spline GT):
      ノイズ無し mean 0.008 / max 0.013 voxel(≈6 反復, ≈1.2ms/回)、NCC サブボクセル
      baseline(mean 0.56 voxel)を約60×改善。
    - ``grad_scale=32`` は分離 sobel3d(導関数[-1,0,1]×平滑[1,2,1]²)の固定スケール
      (線形ランプで実測 32.0)。真の勾配へ正規化して Δp のスケールを正す。
    - H には微小 Levenberg 正則化を加え、勾配の乏しい平坦テンプレートでの数値破綻を防ぐ。
    """
    init_pos = _init_pos3(init_pos, "refine_translation_lk")
    D, H, W = np.asarray(scene).shape
    Td, Th, Tw = np.asarray(template).shape
    scene_t = torch.as_tensor(np.asarray(scene, np.float32)[None, None], device=device)
    tmpl_flat = torch.as_tensor(np.asarray(template, np.float32).reshape(-1), device=device)

    # テンプレート整数格子(corner 原点)
    zz, yy, xx = torch.meshgrid(
        torch.arange(Td, dtype=torch.float32, device=device),
        torch.arange(Th, dtype=torch.float32, device=device),
        torch.arange(Tw, dtype=torch.float32, device=device),
        indexing="ij")

    def _sample(pz, py, px):
        """scene を template 座標 + (pz,py,px) で trilinear サンプル → (N,) flat。"""
        gz = 2.0 * (zz + pz) / (D - 1) - 1.0
        gy = 2.0 * (yy + py) / (H - 1) - 1.0
        gx = 2.0 * (xx + px) / (W - 1) - 1.0
        grid = torch.stack([gx, gy, gz], dim=-1)[None]        # last axis = (x,y,z)
        s = F.grid_sample(scene_t, grid, mode="bilinear",
                          align_corners=True, padding_mode="border")
        return s.reshape(-1)

    # steepest-descent 画像 SD=∇T と Hessian H=Σ SDᵀSD を前計算(反復不変)
    gz, gy, gx = sobel3d(template, device)
    grad_scale = 32.0                                          # sobel3d 固定スケール(ramp 実測)
    sd = torch.stack([gz.reshape(-1) / grad_scale,
                      gy.reshape(-1) / grad_scale,
                      gx.reshape(-1) / grad_scale], dim=0)     # (3,N)
    hess = sd @ sd.t()                                         # (3,3)
    # 正則化の大きさを Hessian 自身の対角平均から取っているので、**勾配が
    # まったく無いテンプレート**(定数ボリューム)では正則化項も 0 になり、
    # 全ゼロ行列の逆行列で生の LinAlgError が漏れていた(2026-09-01、連鎖
    # ファザーが SUSPECT として検出)。位置合わせは勾配に沿ってしか進めない
    # ので、これは数値の失敗ではなく**入力に情報が無い**という事実である。
    scale = float(hess.diagonal().mean())
    if not np.isfinite(scale) or scale <= 0.0:
        raise ValueError(
            "refine_translation_lk: the template has no usable gradient "
            "(Hessian diagonal mean %r), so there is no direction to refine "
            "along — a constant or empty template cannot be aligned" % scale)
    hess = hess + 1e-3 * torch.eye(3, device=device) * scale
    hinv = torch.linalg.inv(hess)

    p = torch.tensor([float(init_pos[0]), float(init_pos[1]), float(init_pos[2])],
                     dtype=torch.float32, device=device)
    for _ in range(int(iters)):
        resid = _sample(p[0], p[1], p[2]) - tmpl_flat         # I(x+p) − T(x)
        dp = -(hinv @ (sd @ resid))                           # Δp = −H⁻¹ Σ SDᵀ resid
        p = p + dp
        if float(torch.linalg.norm(dp)) < tol:
            break
    return p.detach().cpu().numpy().astype(np.float64)


def refine_lm(scene, template, init_pos, device="cpu", iters=50,
              scale=True, gain=False, lam0=1e-3, tol=1e-8):
    """Levenberg-Marquardt による並進(+等方スケール/輝度ゲイン)サブボクセル精緻化。

    粗いマッチ位置 init_pos(テンプレ中心の scene 内座標 [z,y,x])を出発点に、
    forward-additive Lucas-Kanade を減衰付き Gauss-Newton(LM)で解き SSD
        E(p) = Σ_x [ I(W(x;p)) - g·T(x) ]²
    を最小化する。整数 NCC / Fourier-Mellin / Hough の粗推定を連続座標へ収束させる後段。

    ワープ        W(x;p) = t + s·(x - c_T)   (c_T=テンプレ中心, t=並進, s=等方スケール)
    ヤコビアン    ∂I(W)/∂p は grid_sample を自動微分に通して厳密取得(三線形補間の解析勾配。
                  固定点が真の SSD 最小に一致 → sobel 定数倍のバイアスを避け高精度)。
    LM           Δp = -(H + λ·diag(H))⁻¹ b、成功(コスト減)で λ×0.4 減衰・失敗で λ×5 増加。

    引数:
        scene      : シーン volume (D,H,W)。
        template   : テンプレ volume (Td,Th,Tw)。scene より小。
        init_pos   : 粗いテンプレ中心位置 [z,y,x](voxel。NCC locate の [d,h,w] 等)。
        device     : "cpu" / "cuda"。device 非依存。
        iters      : 最大反復数(通常 4-6 で収束)。
        scale      : True で等方スケール s を同時最適化(4パラメータ)。False なら並進のみ。
        gain       : True で輝度ゲイン g(残差 I(W)-g·T)を追加最適化。明るさ差/ノイズに頑健。
        lam0, tol  : 初期減衰係数 / 収束閾値(ステップノルム・相対コスト減)。

    返り値(dict):
        pos   : 精緻化テンプレ中心 [z,y,x](連続座標)
        scale : 等方スケール(scale=False なら 1.0)
        gain  : 輝度ゲイン(gain=False なら 1.0)
        cost  : 最終 SSD、rms: 1voxel あたり残差 RMS、iters: 実行反復数
    """
    init_pos = _init_pos3(init_pos, "refine_lm")
    dev = device
    sc = torch.as_tensor(np.asarray(scene, np.float64)[None, None], device=dev)   # (1,1,D,H,W)
    tp = torch.as_tensor(np.asarray(template, np.float64)[None, None], device=dev)
    D, H, W = sc.shape[2], sc.shape[3], sc.shape[4]
    Tt, Th, Tw = tp.shape[2], tp.shape[3], tp.shape[4]
    cz, cy, cx = (Tt - 1) / 2.0, (Th - 1) / 2.0, (Tw - 1) / 2.0

    # テンプレ中心基準の voxel 座標(∂W/∂s の係数)
    zz, yy, xx = torch.meshgrid(
        torch.arange(Tt, dtype=torch.float64, device=dev),
        torch.arange(Th, dtype=torch.float64, device=dev),
        torch.arange(Tw, dtype=torch.float64, device=dev), indexing="ij")
    oz, oy, ox = zz - cz, yy - cy, xx - cx
    t_col = tp[0, 0].reshape(-1)                      # ∂r/∂g = -T 用

    t = torch.tensor([float(init_pos[0]), float(init_pos[1]), float(init_pos[2])],
                     dtype=torch.float64, device=dev)
    s = torch.tensor(1.0, dtype=torch.float64, device=dev)
    g = torch.tensor(1.0, dtype=torch.float64, device=dev)

    def _sample(tt, ss, with_grad=True):
        """W=tt+ss·offset で I(W)(と自動微分勾配 gz,gy,gx)・valid mask を返す。"""
        sz = tt[0] + ss * oz
        sy = tt[1] + ss * oy
        sx = tt[2] + ss * ox
        nz = 2.0 * sz / (D - 1) - 1.0
        ny = 2.0 * sy / (H - 1) - 1.0
        nx = 2.0 * sx / (W - 1) - 1.0
        grid = torch.stack([nx, ny, nz], dim=-1)[None]     # (1,Tt,Th,Tw,3), (x,y,z)順
        valid = ((sz >= 0) & (sz <= D - 1) & (sy >= 0) & (sy <= H - 1)
                 & (sx >= 0) & (sx <= W - 1)).to(torch.float64)
        if not with_grad:
            with torch.no_grad():
                iw = F.grid_sample(sc, grid.detach(), mode="bilinear",
                                   padding_mode="border", align_corners=True)
            return iw[0, 0], None, None, None, valid
        grid = grid.detach().requires_grad_(True)
        iw = F.grid_sample(sc, grid, mode="bilinear",
                           padding_mode="border", align_corners=True)
        gn = torch.autograd.grad(iw.sum(), grid, create_graph=False)[0][0]  # (Tt,Th,Tw,3)
        gz = gn[..., 2] * (2.0 / (D - 1))                 # 正規化座標→voxel 座標へ変換
        gy = gn[..., 1] * (2.0 / (H - 1))
        gx = gn[..., 0] * (2.0 / (W - 1))
        return iw[0, 0].detach(), gz, gy, gx, valid

    def _cost(tt, ss, gg):
        iw, _, _, _, valid = _sample(tt, ss, with_grad=False)
        r = (iw - gg * tp[0, 0]) * valid
        return float((r * r).sum())

    lam = float(lam0)
    prev = _cost(t, s, g)
    used = 0
    eye = torch.eye((3 + int(scale) + int(gain)), dtype=torch.float64, device=dev)
    for it in range(iters):
        used = it + 1
        iw, gz, gy, gx, valid = _sample(t, s, with_grad=True)
        w = valid.reshape(-1)
        r = (iw - g * tp[0, 0]).reshape(-1)
        cols = [gz.reshape(-1), gy.reshape(-1), gx.reshape(-1)]
        if scale:
            cols.append((gz * oz + gy * oy + gx * ox).reshape(-1))
        if gain:
            cols.append(-t_col)
        jac = torch.stack(cols, dim=1)                    # (N,P)
        jw = jac * w[:, None]
        h_mat = jw.transpose(0, 1) @ jac                  # Σ w JᵀJ
        b = jw.transpose(0, 1) @ r                        # Σ w Jᵀr
        diag = torch.diag(torch.diagonal(h_mat))
        accepted = False
        step = improved = 0.0
        for _ in range(12):                               # λ を段階調整し降下する更新を探索
            a_mat = h_mat + lam * diag + 1e-12 * eye
            try:
                dp = torch.linalg.solve(a_mat, -b)
            except Exception:
                lam = min(lam * 5.0, 1e9)
                continue
            tn = t + dp[:3]
            sn = s + dp[3] if scale else s
            gn = g + dp[3 + int(scale)] if gain else g
            cnew = _cost(tn, sn, gn)
            if cnew < prev:
                t, s, g = tn, sn, gn
                lam = max(lam * 0.4, 1e-9)
                step = float(torch.linalg.norm(dp))
                improved = prev - cnew
                prev = cnew
                accepted = True
                break
            lam = min(lam * 5.0, 1e9)
        if not accepted:
            break
        if step < tol or improved < tol * max(1.0, prev):
            break

    rms = float(np.sqrt(prev / max(1.0, float(tp.numel()))))
    return {
        "pos": [float(t[0]), float(t[1]), float(t[2])],
        "scale": float(s),
        "gain": float(g),
        "cost": float(prev),
        "rms": rms,
        "iters": used,
    }


def _warp_rot_z(vol_t, angle_deg, device="cpu"):
    """torch volume (1,1,D,H,W) を z 軸(D 軸)まわりに angle_deg 回転して返す(trilinear)。

    affine_grid の grid 座標順は (x=W, y=H, z=D)。z を固定し H-W 平面のみ回す。回転方向は
    scipy.ndimage.rotate(v, angle_deg, axes=(1,2)) と一致(検証済)。境界外は 0 詰め。
    """
    a = torch.as_tensor(np.deg2rad(angle_deg), dtype=torch.float32, device=device)
    c, s = torch.cos(a), torch.sin(a)
    z = torch.zeros((), device=device)
    o = torch.ones((), device=device)
    theta = torch.stack([                       # (x,y,z) 順の 3x4 アフィン
        torch.stack([c, -s, z, z]),
        torch.stack([s,  c, z, z]),
        torch.stack([z,  z, o, z]),
    ]).unsqueeze(0)
    grid = F.affine_grid(theta, vol_t.shape, align_corners=False)
    return F.grid_sample(vol_t, grid, align_corners=False,
                         mode="bilinear", padding_mode="zeros")


def refine_rotation_z(scene, template, init_angle_deg=0.0, device="cpu",
                      iters=40, tol=1e-3, max_step_deg=5.0):
    """z 軸回転角の **Gauss-Newton 精緻化**(Lucas-Kanade on SSD、1 パラメータ)。

    Fourier-Mellin 等の粗い z 軸回転推定(±3° 級)を、SSD を回転角 θ だけで最小化して高精度化
    する下流精緻化器。scene ≈ rotate_z(template, θ_true) を仮定し、warp_z(template, θ) が scene に
    一致する θ を求める。返り値の角は match_logpolar_z と同符号(scene = template を θ 回転)。

    定式化: 残差 r(θ)=T_warp(θ)−S を θ で線形化。回転の steepest-descent image(解析ヤコビアン)
    は、中心化格子 (X=W−cx, Y=H−cy) と warp 済みテンプレの空間勾配 (gx,gy) から
    J = ∂T_warp/∂θ = (−gx·Y + gy·X)(rad あたり)。1 パラメータ GN 更新は Δθ = −(JᵀWr)/(JᵀWJ)。
    回転で 0 詰めされた隅は valid マスク W で除外。step は max_step_deg で制限し発散を防ぐ。

    実測(48³ 非対称 volume, CPU, 別補間器 scipy order=3 で scene 生成=inverse crime 回避):
    clean 誤差 ~0.0006°、5% ノイズ 0.009°、10% ノイズ 0.017°(いずれも <0.3°)。捕捉レンジは
    最低 ±10°、収束 3-5 反復・~12ms。粗推定 ±3° をそのまま使う場合(誤差 3°)比で ~5000 倍改善。

    Parameters
    ----------
    scene : array_like (D,H,W)     基準 volume(この姿勢へ template を合わせる)。
    template : array_like (D,H,W)  回転させて scene に合わせるテンプレ volume。同一格子・同一中心。
    init_angle_deg : float         粗推定角(deg)。Fourier-Mellin 等の初期値。
    device : str                   "cpu" / "cuda"。device 非依存。
    iters : int                    最大反復数。
    tol : float                    |Δθ|(deg)がこれ未満で収束打ち切り。
    max_step_deg : float           1 反復あたりの角ステップ上限(deg、発散防止)。

    Returns
    -------
    (angle_deg, n_iters) : (float, int)  精緻化角(deg)と実行反復数。
    """
    _va, _vb = np.asarray(scene), np.asarray(template)
    if _va.shape != _vb.shape:
        raise ValueError("refine_rotation_z: both volumes must share one shape "
                         "(got %r vs %r) — this operator correlates them "
                         "voxel-for-voxel" % (_va.shape, _vb.shape))
    if not isinstance(init_angle_deg, (int, float, np.integer, np.floating)):
        # 連鎖ファザー実測(wave-4): 本 op 自身の返り値 (angle, n_iters) tuple が
        # そのまま init_angle_deg に流れ込み float() が生 TypeError で落ちていた。
        raise ValueError("refine_rotation_z: init_angle_deg must be a scalar "
                         "angle in degrees (got %s) — this op returns "
                         "(angle_deg, n_iters); pass result[0] when chaining"
                         % type(init_angle_deg).__name__)
    scene_t = torch.as_tensor(np.asarray(scene, np.float32)[None, None], device=device)
    tmpl_t = torch.as_tensor(np.asarray(template, np.float32)[None, None], device=device)
    D, H, W = tmpl_t.shape[2:]

    # 出力格子の中心化座標(x=W, y=H)。回転流れ場に使う。
    ys = torch.arange(H, dtype=torch.float32, device=device) - (H - 1) / 2.0
    xs = torch.arange(W, dtype=torch.float32, device=device) - (W - 1) / 2.0
    Y = ys.view(1, 1, 1, H, 1)
    X = xs.view(1, 1, 1, 1, W)
    ones = torch.ones_like(tmpl_t)              # valid マスク生成用

    theta = float(init_angle_deg)
    used = 0
    for used in range(1, iters + 1):
        warped = _warp_rot_z(tmpl_t, theta, device)
        valid = (_warp_rot_z(ones, theta, device) > 0.999).float()

        # warp 済みテンプレの空間勾配(中心差分)。gx=∂/∂W, gy=∂/∂H。
        gx = torch.zeros_like(warped)
        gy = torch.zeros_like(warped)
        gx[..., 1:-1] = (warped[..., 2:] - warped[..., :-2]) * 0.5
        gy[..., 1:-1, :] = (warped[..., 2:, :] - warped[..., :-2, :]) * 0.5

        J = (-gx * Y + gy * X) * valid          # 回転 steepest-descent image(per rad)
        r = (warped - scene_t) * valid          # 残差
        jtj = float((J * J).sum())
        jtr = float((J * r).sum())
        if jtj < 1e-12:
            break
        dtheta_deg = float(np.rad2deg(-jtr / jtj))          # GN 更新(deg)
        dtheta_deg = max(-max_step_deg, min(max_step_deg, dtheta_deg))
        theta += dtheta_deg
        if abs(dtheta_deg) < tol:
            break
    return float(theta), used


def icp_point2point_3d(src, dst, iters=50, init_R=None, init_t=None,
                       tol=1e-6, max_corr_dist=None, trim_ratio=None,
                       device="cpu"):
    """点群を point-to-point ICP(Kabsch/SVD)で精緻化する。

    粗いマッチ推定(整数NCC / Fourier-Mellin±3° / Hough±0.5voxel)で得た
    初期姿勢 (init_R, init_t) を出発点に、src 側点群を dst 側点群へ剛体変換で
    位置合わせする。各反復で最近傍対応(cKDTree)を張り直し、Kabsch アルゴリズム
    (SVD)で相対回転・並進を求めて累積することで、対応が既知でなくても
    サブボクセル精度へ収束させる。

    部分重なり・外れ値には Trimmed ICP(距離の小さい対応のみ採用)と
    絶対距離ゲート(max_corr_dist)で対処する。最終 RMSE は実際に採用した
    対応(インライア)上で評価するため、部分観測でも姿勢品質を正しく反映する。

    引数:
        src: (N,3) 移動側点群(torch.Tensor か numpy.ndarray)。
        dst: (M,3) 固定側(参照)点群。
        iters: 最大反復回数。
        init_R: (3,3) 初期回転。None なら単位行列。
        init_t: (3,) 初期並進。None なら零ベクトル。
        tol: RMSE の相対改善がこの値を下回れば収束打ち切り。
        max_corr_dist: この距離を超える対応を外れ値として棄却(None で無効)。
        trim_ratio: 0<r<=1。各反復で最近傍距離の小さい上位 r 割の対応のみ
            採用する Trimmed ICP。部分重なり(重なり率 r)に有効。None で無効。
        device: torch デバイス("cpu" 等)。SVD をこのデバイス上で解く。

    返り値:
        R: (3,3) 回転。dst ~= src @ R.T + t を満たす。**torch がある環境では
           ``torch.Tensor``、無ければ同じ値の ``numpy.ndarray``**(2026-09-07 に
           本体を numpy 化したときも、互換のため型は据え置いた)。
           ★同じ族の :func:`icp_point2plane` は**常に numpy を返す** —— 族の中で
           型が揃っていないので、下流では ``np.asarray(R)`` を通すのが安全
           (どちらでも動く。破壊的変更を避けてこの不揃いを残してある)。
        t: (3,) 並進(R と同じ型)。
        info: dict。"rmse"(採用対応上の最終RMSE), "iters"(実反復数),
              "converged"(bool), "inliers"(採用対応数), "rmse_history"(list)。
    """
    try:
        _s, _d = np.asarray(src, float), np.asarray(dst, float)
    except (TypeError, ValueError) as e:
        raise ValueError("icp_point2point_3d: src/dst must be numeric (N, 3) "
                         "point arrays (got %s / %s)"
                         % (type(src).__name__, type(dst).__name__)) from e
    if _s.ndim != 2 or _s.shape[1] != 3 or _d.ndim != 2 or _d.shape[1] != 3:
        raise ValueError("icp_point2point_3d: src/dst must be (N, 3) point arrays, got %r / %r"
                         % (_s.shape, _d.shape))
    if len(_s) < 3 or len(_d) < 3:
        # 連鎖ファザー実測: 空/1点入力が深部の index/SVD で生エラー・NaN 化する
        raise ValueError("icp_point2point_3d: need at least 3 points on each side "
                         "(got %d / %d) — a rigid pose is undefined below that"
                         % (len(_s), len(_d)))
    from scipy.spatial import cKDTree

    # ★2026-09-07: 本体を numpy に書き換えた。この ICP は **最近傍探索が cKDTree、
    # 姿勢の更新が 3x3 の SVD** で、torch でやる仕事が 1 つも無いのに torch を
    # 必須にしていた。torch を入れない CI(py3.10 / 3.12)で PoC 4 本が
    # `ImportError: this operator needs the optional 'torch' backend` で落ちて
    # 発覚(手元には torch があるので気づけなかった —— 門は事故の起きる場所に
    # 立てる、の実例)。数値は float64 の同じ式なので**環境で結果が変わらない**。
    # 返り値の型は互換のため据え置き: torch があれば torch.Tensor、無ければ
    # numpy.ndarray(値は同一)。device に "cpu" 以外を頼まれたら fail-closed。
    if str(device) not in ("cpu", "None") and not _HAS_TORCH:
        raise ValueError(
            "icp_point2point_3d: device=%r needs the optional 'torch' backend "
            "(numpy path runs on the CPU only)" % (device,))

    src_np = np.ascontiguousarray(_s, np.float64)
    dst_np = np.ascontiguousarray(_d, np.float64)

    # --- 初期姿勢(累積 R, t)--------------------------------------------
    def _np3(a, shape):
        if a is None:
            return None
        v = a.detach().cpu().numpy() if hasattr(a, "detach") else np.asarray(a)
        return np.ascontiguousarray(v, np.float64).reshape(shape)

    R = np.eye(3, dtype=np.float64) if init_R is None else _np3(init_R, (3, 3))
    t = np.zeros(3, dtype=np.float64) if init_t is None else _np3(init_t, (3,))

    tree = cKDTree(dst_np)                      # dst は不変なので 1 回だけ

    rmse_history = []
    prev_rmse = float("inf")
    converged = False
    used_iters = 0

    def _select(dists):
        """外れ値棄却: 絶対距離ゲート + Trimmed ICP(距離の小さい上位割合)。"""
        keep = np.ones(len(dists), dtype=bool)
        if max_corr_dist is not None:
            keep &= (dists <= max_corr_dist)
        if trim_ratio is not None and 0.0 < trim_ratio < 1.0:
            n_keep = max(3, int(round(len(dists) * trim_ratio)))
            order = np.argsort(dists)
            tm = np.zeros(len(dists), dtype=bool)
            tm[order[:n_keep]] = True
            keep &= tm
        return keep

    for it in range(iters):
        used_iters = it + 1

        src_moved = src_np @ R.T + t            # 現在の累積姿勢
        dists, idx = tree.query(src_moved, k=1)

        keep = _select(dists)
        if keep.sum() < 3:
            keep = np.ones(len(idx), dtype=bool)  # 退避: 全採用

        P = src_moved[keep]
        Q = dst_np[idx[keep]]

        rmse = float(np.sqrt(np.mean(np.sum((P - Q) ** 2, axis=1))))
        rmse_history.append(rmse)

        # --- Kabsch: P を Q に合わせる相対 (dR, dt) を SVD で解く ----------
        p_bar = P.mean(axis=0)
        q_bar = Q.mean(axis=0)
        H = (P - p_bar).T @ (Q - q_bar)         # (3,3) 相互共分散
        U, _S, Vh = np.linalg.svd(H)
        V = Vh.T
        d = np.sign(np.linalg.det(V @ U.T))     # 反射補正
        dR = V @ np.diag([1.0, 1.0, d]) @ U.T
        dt = q_bar - dR @ p_bar

        # 累積姿勢へ合成(src_moved は既に R,t 適用済み -> 左から dR,dt)
        R = dR @ R
        t = dR @ t + dt

        # 収束判定: RMSE が絶対的に十分小さい、または相対改善が閾値未満
        if rmse < 1e-9:
            converged = True
            break
        if prev_rmse < float("inf"):
            if abs(prev_rmse - rmse) / (prev_rmse + 1e-12) < tol:
                converged = True
                break
        prev_rmse = rmse

    # 収束後の最終 RMSE を採用対応(インライア)上で再評価
    dists, _ = tree.query(src_np @ R.T + t, k=1)
    fkeep = _select(dists)
    if fkeep.sum() < 1:
        fkeep = np.ones(len(dists), dtype=bool)
    final_rmse = float(np.sqrt(np.mean(dists[fkeep] ** 2)))
    rmse_history.append(final_rmse)

    info = {
        "rmse": final_rmse,
        "iters": used_iters,
        "converged": converged,
        "inliers": int(fkeep.sum()),
        "rmse_history": rmse_history,
    }
    if _HAS_TORCH:                    # 互換: これまでどおり torch を返す
        dev = torch.device(device)
        return (torch.as_tensor(R, dtype=torch.float64, device=dev),
                torch.as_tensor(t, dtype=torch.float64, device=dev), info)
    return R, t, info


def _skew(v):
    """3ベクトル → 歪対称行列 [v]×  (torch, (...,3,3))。"""
    z = torch.zeros_like(v[..., 0])
    return torch.stack([
        torch.stack([z, -v[..., 2], v[..., 1]], -1),
        torch.stack([v[..., 2], z, -v[..., 0]], -1),
        torch.stack([-v[..., 1], v[..., 0], z], -1),
    ], -2)


def _rodrigues(omega, device):
    """回転ベクトル ω → 回転行列 R = expm([ω]×)  (Rodrigues, torch 3×3)。"""
    theta = torch.linalg.norm(omega)
    eye = torch.eye(3, dtype=omega.dtype, device=device)
    if float(theta) < 1e-12:
        return eye
    k = omega / theta
    K = _skew(k)
    return eye + torch.sin(theta) * K + (1.0 - torch.cos(theta)) * (K @ K)


def _rodrigues_np(omega):
    """回転ベクトル ω → 回転行列 R = expm([ω]×)(Rodrigues, numpy 3x3)。

    :func:`_rodrigues` の numpy 版(2026-09-07)。式は同じで、torch を入れない
    環境でも点-面 ICP が走るようにするためだけに分けてある。
    """
    theta = float(np.linalg.norm(omega))
    eye = np.eye(3, dtype=np.float64)
    if theta < 1e-12:
        return eye
    k = np.asarray(omega, np.float64) / theta
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return eye + np.sin(theta) * K + (1.0 - np.cos(theta)) * (K @ K)


def _nearest(cur, Q, chunk=4096):
    """cur(N,3) 各点の Q(M,3) 内最近傍 index。torch.cdist をチャンク分割(device 非依存)。"""
    N = cur.shape[0]
    idx = torch.empty(N, dtype=torch.long, device=cur.device)
    for s in range(0, N, chunk):
        e = min(s + chunk, N)
        d = torch.cdist(cur[s:e], Q)          # (chunk, M)
        idx[s:e] = torch.argmin(d, dim=1)
    return idx


def icp_point2plane(src, dst, dst_normals, iters=30, tol=1e-9,
                    init=None, trim=None, device="cpu"):
    """点-面 ICP(Gauss-Newton, 小角近似)で剛体変換を高精度に精緻化する。

    粗マッチ(整数 NCC / Fourier-Mellin ±3° / Hough ±0.5voxel)の初期姿勢を
    表面点群の点-面距離最小化で締め上げる精緻化手法。各反復で src 各点の dst
    最近傍を対応付け、**点-面残差** ``r_i = n_i·(R·p_i + t - q_i)`` を最小化する。
    R を小角近似 ``R ≈ I + [ω]×`` で線形化すると各対応のヤコビアンは
    ``J_i = [p_i×n_i | n_i]``(スカラー三重積 ``n·(ω×p)=ω·(p×n)`` より)、
    定数項 ``b_i = -n_i·(p_i - q_i)``。正規方程式 ``(JᵀJ)x = Jᵀb`` を 6×6 で
    解いて増分 ``x=[ω|t]`` を得、Rodrigues で回転に戻して累積する。点-面は
    接平面内の滑りを許すため、point-to-point より少ない反復で表面にタイトに
    収束する(Low 2004)。

    実測(波打つ表面 N=2025, CPU float64): 初期6°/並進0.06 を 4 反復で euclid
    RMSE 1.7e-16・回転誤差 0° に回復(point-to-point は 17 反復で RMSE 4e-2・
    回転 1.9° 停滞)。初期角 3〜20° でも 4〜5 反復で機械精度。

    引数:
        src (N,3): 動かす側の点群(粗マッチ後の初期姿勢)。
        dst (M,3): 参照側の点群(固定)。
        dst_normals (M,3): dst の単位法線(未正規化でも内部で正規化)。
                           未知なら pointcloud.estimate_normals(dst) 等で事前推定。
        iters: 最大反復数。
        tol: RMSE 変化がこの値未満で収束打ち切り。
        init ((R0,t0)): 初期姿勢(粗マッチの R,t を渡す)。None なら単位。
        trim (float|None): [0,1) の割合。点-面残差の大きい上位を毎反復捨てる
                           Trimmed ICP(部分重なり・外れ値に頑健)。
        device: "cpu"/"cuda" 等。torch device 文字列(device 非依存)。

    返り値:
        R (3,3), t (3,), aligned (N,3)=R·src+t, rmse(採用点の点-面 RMSE),
        n_iter(実反復数)。
    """
    try:
        _s, _d = np.asarray(src, float), np.asarray(dst, float)
        _n = np.asarray(dst_normals, float)
    except (TypeError, ValueError) as e:
        raise ValueError("icp_point2plane: src/dst/dst_normals must be numeric "
                         "(N, 3) arrays (got %s / %s / %s)"
                         % (type(src).__name__, type(dst).__name__,
                            type(dst_normals).__name__)) from e
    if _s.ndim != 2 or _s.shape[1] != 3 or _d.ndim != 2 or _d.shape[1] != 3:
        raise ValueError("icp_point2plane: src/dst must be (N, 3) point arrays, got %r / %r"
                         % (_s.shape, _d.shape))
    if len(_s) < 3 or len(_d) < 3:
        # 連鎖ファザー実測: 空/1点入力が深部の index/SVD で生エラー・NaN 化する
        raise ValueError("icp_point2plane: need at least 3 points on each side "
                         "(got %d / %d) — a rigid pose is undefined below that"
                         % (len(_s), len(_d)))
    if _n.ndim != 2 or _n.shape[1] != 3:
        raise ValueError("icp_point2plane: dst_normals must be an (M, 3) normal "
                         "array, got %r" % (_n.shape,))
    if len(_n) != len(_d):
        # 連鎖ファザー実測(wave-4): dst と別サイズの法線が最近傍 index 参照
        # Nn[idx] で生 IndexError 化する(index N out of bounds)。
        raise ValueError("icp_point2plane: dst_normals must pair one normal with "
                         "each dst point (got %d normals for %d points) — "
                         "estimate normals on this dst cloud (e.g. "
                         "pointcloud.estimate_normals(dst))" % (len(_n), len(_d)))
    # ★2026-09-07: 本体を numpy に書き換えた。最近傍探索・6x6 の正規方程式・
    # Rodrigues のどれも CPU の小さい線形代数で、torch でやる必要が無かったのに
    # 必須になっていた。torch を入れない CI(py3.10 / 3.12)で PoC が
    # ImportError で落ちて発覚。式は同じ float64 なので結果は変わらない
    # (torch 版との差は R/t で 0、RMSE で 0 を実測)。
    if str(device) not in ("cpu", "None") and not _HAS_TORCH:
        raise ValueError(
            "icp_point2plane: device=%r needs the optional 'torch' backend "
            "(the numpy path runs on the CPU only)" % (device,))
    from scipy.spatial import cKDTree

    P0 = np.ascontiguousarray(_s, np.float64)
    Q = np.ascontiguousarray(_d, np.float64)
    Nn = np.ascontiguousarray(_n, np.float64)
    Nn = Nn / np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-12)

    n_src = P0.shape[0]
    if init is None:
        R_tot = np.eye(3, dtype=np.float64)
        t_tot = np.zeros(3, dtype=np.float64)
        cur = P0.copy()
    else:
        R_tot = np.ascontiguousarray(np.asarray(init[0], np.float64)).reshape(3, 3).copy()
        t_tot = np.ascontiguousarray(np.asarray(init[1], np.float64)).reshape(3).copy()
        cur = P0 @ R_tot.T + t_tot
    keep_n = n_src if trim is None else max(3, int(round((1.0 - float(trim)) * n_src)))

    prev = float("inf")
    rmse = float("inf")
    n_iter = 0
    reg = np.eye(6, dtype=np.float64) * 1e-12   # 特異回避の微小正則化
    tree = cKDTree(Q)                           # dst は不変(torch.cdist と同じ最近傍)
    for it in range(int(iters)):
        n_iter = it + 1
        _, idx = tree.query(cur, k=1)
        q = Q[idx]
        n = Nn[idx]
        resid = np.einsum("ij,ij->i", cur - q, n)             # 符号付き点-面距離
        if keep_n < n_src:                                    # Trimmed: 残差小さい keep_n 点のみ
            sel = np.argsort(np.abs(resid))[:keep_n]
        else:
            sel = slice(None)
        p_s, q_s, n_s, r_s = cur[sel], q[sel], n[sel], resid[sel]
        # J_i = [p×n | n],  b_i = -(p-q)·n = -r_s  (正規方程式 (JᵀJ)x=Jᵀb を 6×6 で)
        J = np.concatenate([np.cross(p_s, n_s), n_s], axis=1)  # (K,6)
        x = np.linalg.solve(J.T @ J + reg, J.T @ (-r_s))
        R_inc = _rodrigues_np(x[:3])
        t_inc = x[3:]
        cur = cur @ R_inc.T + t_inc
        R_tot = R_inc @ R_tot
        t_tot = R_inc @ t_tot + t_inc
        # 更新後の点-面 RMSE(採用点のみで評価。同じ対応で単調性を判定)
        rmse = float(np.sqrt(np.mean(np.einsum("ij,ij->i", cur[sel] - q_s, n_s) ** 2)))
        if abs(prev - rmse) < tol:
            break
        prev = rmse

    return R_tot, t_tot, cur, rmse, n_iter


# ═══════════════════════════════════════════════════════════════════════════
# scene flow(2D optical flow → 3D)= voxel ごとの運動場(運動/変形の推定)
# ═══════════════════════════════════════════════════════════════════════════
def _flow_box3(t, r):
    """(1,1,D,H,W) の一様窓和(分離 conv3d)。Lucas-Kanade の構造テンソル窓和用。"""
    k = torch.ones(2 * r + 1, device=t.device)
    for ax in range(3):
        shp = [1, 1, 1, 1, 1]; shp[2 + ax] = 2 * r + 1
        pad = [0, 0, 0, 0, 0, 0]; pad[(2 - ax) * 2] = r; pad[(2 - ax) * 2 + 1] = r
        t = F.conv3d(F.pad(t, tuple(pad), mode="replicate"), k.view(*shp))
    return t


def _flow_warp(vol_t, flow, device):
    """vol_t(1,1,D,H,W) を flow(3,D,H,W)=(dz,dy,dx) で trilinear ワープ。"""
    _, _, D, H, W = vol_t.shape
    zz, yy, xx = torch.meshgrid(
        torch.arange(D, device=device, dtype=torch.float32),
        torch.arange(H, device=device, dtype=torch.float32),
        torch.arange(W, device=device, dtype=torch.float32), indexing="ij")
    sz = zz + flow[0]; sy = yy + flow[1]; sx = xx + flow[2]
    grid = torch.stack([2 * sx / (W - 1) - 1, 2 * sy / (H - 1) - 1,
                        2 * sz / (D - 1) - 1], dim=-1)[None]
    return F.grid_sample(vol_t, grid, align_corners=True, mode="bilinear",
                         padding_mode="border")


def scene_flow_lk(vol0, vol1, device="cpu", win=3, levels=3, iters=3, reg=1e-3):
    """Lucas-Kanade scene flow(2D optical flow の 3D 版)。voxel ごとの運動場 d=(dz,dy,dx)。

    テンプレ照合と違い **密な運動/変形**を推定する。明るさ一定 ∇I·d + I_t = 0 を窓内最小二乗で
    per-voxel に解く(3x3 構造テンソル A=Σ∇I∇Iᵀ, b=-Σ∇I·I_t を窓和 conv3d で)。pyramid + warp の
    coarse-to-fine で大変位に対応(各 level で I1 を現 flow で戻し残差を反復補正=Gauss-Newton)。
    vol1(x) ≈ vol0(x - d)。返り値 flow (3,D,H,W)。並進・拡大(発散)・回転(渦)場を捉える。

    実測: 一様並進 [1.5,-2,1] を中央領域平均で誤差 0.044 voxel、拡大場で外向き発散を正しく検出。
    grad_scale=32 は sobel3d(deriv[-1,0,1]×smooth[1,2,1]²)の実測スケール。GPU 対応(全 conv3d)。

    引数: ``vol0``, ``vol1`` は同形の 3-D(違えば ValueError。NaN/Inf や float32 桁あふれも
    ValueError)。``win`` は窓の半幅(窓は一辺 ``2·win+1``)、``levels`` はピラミッド段数(各段
    ``avg_pool3d`` で 2 倍縮小。大変位ほど段数を増やす)、``iters`` は各段の warp 反復、``reg`` は
    構造テンソル対角への正則化(平坦部の 0 除算回避。大きいほど平坦部の flow が 0 に寄る)。
    1 反復の更新は各軸 ±2 voxel に clamp される。
    返り値 ``(3, D, H, W)`` float32 numpy、``flow[0]``=dz, ``flow[1]``=dy, ``flow[2]``=dx
    (voxel 単位)。``vol1(x) ≈ vol0(x − d)``、すなわち vol0 の構造が ``+d`` 動いて vol1 になる。
    端は border 補間で埋まるので端 1〜2 voxel の値は信用しない。剛体運動の R,t が欲しいなら
    点群にして ``icp_point2point_3d`` / ``fit_rigid`` へ。
    """
    _va, _vb = np.asarray(vol0), np.asarray(vol1)
    if _va.shape != _vb.shape:
        raise ValueError("scene_flow_lk: both volumes must share one shape "
                         "(got %r vs %r) — this operator correlates them "
                         "voxel-for-voxel" % (_va.shape, _vb.shape))
    v0 = torch.as_tensor(_f32_finite(vol0, "scene_flow_lk: vol0")[None, None],
                         device=device)
    v1 = torch.as_tensor(_f32_finite(vol1, "scene_flow_lk: vol1")[None, None],
                         device=device)
    pyr0 = [v0]; pyr1 = [v1]
    for _ in range(levels - 1):
        pyr0.append(F.avg_pool3d(pyr0[-1], 2)); pyr1.append(F.avg_pool3d(pyr1[-1], 2))
    flow = torch.zeros(3, *pyr0[-1].shape[2:], device=device)
    for lv in range(levels - 1, -1, -1):
        I0 = pyr0[lv]; I1 = pyr1[lv]; d, h, w = I0.shape[2:]
        if flow.shape[1:] != (d, h, w):
            flow = F.interpolate(flow[None], size=(d, h, w), mode="trilinear",
                                 align_corners=True)[0] * 2
        for _ in range(iters):
            Iw = _flow_warp(I1, flow, device)
            gz, gy, gx = sobel3d(Iw[0, 0], device)
            gz, gy, gx = gz / 32.0, gy / 32.0, gx / 32.0     # sobel3d 実測スケール
            It = Iw - I0
            Axx = _flow_box3(gx * gx, win); Ayy = _flow_box3(gy * gy, win)
            Azz = _flow_box3(gz * gz, win); Axy = _flow_box3(gx * gy, win)
            Axz = _flow_box3(gx * gz, win); Ayz = _flow_box3(gy * gz, win)
            bx = -_flow_box3(gx * It, win); by = -_flow_box3(gy * It, win)
            bz = -_flow_box3(gz * It, win)
            a = Azz + reg; b = Ayy + reg; c = Axx + reg      # 行列 (z,y,x 順)
            det = (a * (b * c - Axy * Axy) - Ayz * (Ayz * c - Axy * Axz)
                   + Axz * (Ayz * Axy - b * Axz)).clamp_min(1e-6)
            rz, ry, rx = bz, by, bx
            dz = ((b * c - Axy * Axy) * rz + (Axz * Axy - Ayz * c) * ry
                  + (Ayz * Axy - Axz * b) * rx) / det
            dy = ((Axy * Axz - Ayz * c) * rz + (a * c - Axz * Axz) * ry
                  + (Ayz * Axz - a * Axy) * rx) / det
            dx = ((Ayz * Axy - b * Axz) * rz + (Axz * Ayz - a * Axy) * ry
                  + (a * b - Ayz * Ayz) * rx) / det
            upd = torch.stack([dz[0, 0], dy[0, 0], dx[0, 0]], 0)
            flow = flow + upd.clamp(-2, 2)
    return flow.detach().cpu().numpy()


# ═══════════════════════════════════════════════════════════════════════════
# データ形式の変換グラフ拡張(構造=行を増やす)+ 3D モルフォロジー
# 「3D データを手法が効く表現へ変換する」= マトリクスの核。形式間を繋ぐ。
# ═══════════════════════════════════════════════════════════════════════════
def signed_distance_field(vol, device="cpu", iso=0.5):
    """occupancy/密度 voxel → 符号付き距離場 SDF(内側<0・外側>0)。edt_jfa を両側に。

    SDF はマッチングに優れた表現(滑らか・勾配=法線・0 等値面=表面)。inside/outside の
    ユークリッド距離差で作る。GPU native。voxel↔SDF↔occupancy を相互変換できる。

    定義: ``occ = vol > iso`` として ``d_out = edt_jfa(occ)``(各 voxel から最寄りの占有 voxel
    までの距離、占有内では 0)、``d_in = edt_jfa(~occ)``(最寄りの非占有 voxel まで)、
    ``sdf = d_out − d_in``。外側は +距離、内側は −距離(voxel 単位、ユークリッド)。
    voxel 中心同士の距離なので **0 になる voxel は無く**、境界の占有 voxel は −1、隣接する
    非占有 voxel は +1(0 等値面は voxel の間)。
    ``iso`` は密度→占有の閾値(既定 0.5。個数密度なら「1 点以上」)。全占有・全空の volume は
    seed の無い側の距離が 1e6 に飽和し、全占有では −1e6、全空では +1e6 になる(例外は出ない)。
    返り値 ``(D,H,W)`` float32 numpy。
    後段: ``sdf_to_occupancy`` で戻す、``voxel_to_mesh(sdf, iso=0.0)`` で面、``sobel3d`` で法線場。
    """
    occ = np.asarray(vol) > iso
    d_out = edt_jfa(occ, device)                            # 外側→最近表面
    d_in = edt_jfa(~occ, device)                            # 内側→最近外側
    sdf = d_out - d_in
    return sdf.detach().cpu().numpy() if torch.is_tensor(sdf) else np.asarray(sdf)


def sdf_to_occupancy(sdf, iso=0.0):
    """SDF → occupancy voxel(iso 以下=内側=1)。SDF から voxel へ戻す。

    ``(sdf <= iso).astype(float64)`` だけの op。``signed_distance_field`` の規約(内側 <0)なら
    ``iso=0.0`` で内側=1、外側=0。**等号を含む**ので、ちょうど ``iso`` の voxel は内側に入る。
    ``iso`` を正にすると外側へ ``iso`` voxel ぶん膨らんだ占有、負にすると縮んだ占有になる
    (SDF が真の距離なら等方 dilation/erosion と同じ)。``tsdf_from_depth`` の出力(表面手前 +・
    奥 −・未観測 +1)にも同じ ``iso=0.0`` で使えるが、未観測領域は 0 側(外)になる。
    入力の形は問わず、返り値は同形の float64(0.0 / 1.0)。NaN は比較が偽なので 0 になる
    (警告なし)。
    """
    return (np.asarray(sdf) <= iso).astype(np.float64)


def estimate_point_normals(points, k=16, viewpoint=None):
    """点群 (N,3) → 単位法線(局所 k 近傍共分散の最小固有ベクトル=PCA)。

    FPFH/SHOT/点-面 ICP が要る法線を raw 点群から生成。向きの規約は 2 面:
    **viewpoint=None(既定)= 重心から外向き**(閉じた物体の全周点群向け)/
    **viewpoint 指定 = 視点(センサ)向き**(Hoppe 1992 / PCL 規約。単一視点スキャンの
    可視面はセンサ側を向くのが物理的に正しい。`pointcloud.estimate_normals` と同規約)。
    旧版(〜2026-08-30)は viewpoint 指定でも「視点から遠ざける」符号で、単一視点
    スキャンという本来用途で全点が裏返っていた。返り値 normals (N,3)。

    手順: ``cKDTree`` で各点の ``k`` 近傍(自分自身を含む。``k > N`` なら N に切り詰め)を取り、
    その共分散の最小固有ベクトルを法線にする。返り値 ``(N,3)`` float64 の単位ベクトル。
    ``viewpoint`` は 3 次元の座標(センサ位置)。点数が 3 未満・近傍が同一直線上だと法線は
    不定のまま返る(検証は無い)。``k`` が小さいとノイズに弱く、大きいと角が丸まる。
    後段: ``icp_point2plane`` の ``dst_normals``、``render_shaded`` 用の法線、``normals_to_egi``。
    ``pointcloud.estimate_normals``(台帳 ``estimate_normals``)と同じ規約。
    """
    from scipy.spatial import cKDTree
    P = np.asarray(points, np.float64)
    tree = cKDTree(P)
    _, idx = tree.query(P, k=min(k, len(P)))
    nn = P[idx]
    Q = nn - nn.mean(1, keepdims=True)
    cov = np.einsum("nki,nkj->nij", Q, Q) / Q.shape[1]
    _, v = np.linalg.eigh(cov)
    nrm = v[:, :, 0]                                        # 最小固有値の固有ベクトル
    if viewpoint is None:
        # 重心基準=外向き: 重心の方を向いた法線を裏返す
        flip = np.einsum("ni,ni->n", nrm, P.mean(0) - P) > 0
    else:
        # センサ基準=視点向き(Hoppe/PCL): 視点から離れる法線を裏返す
        flip = np.einsum("ni,ni->n", nrm,
                         np.asarray(viewpoint, np.float64) - P) < 0
    nrm[flip] *= -1
    return nrm / np.linalg.norm(nrm, axis=1, keepdims=True).clip(1e-12)


def mesh_to_points(vertices, faces, samples=20000, seed=0):
    """mesh(頂点+面)→ 表面点群(面積重み一様サンプリング)。mesh→point cloud 変換。

    手順: 三角形 ``tri = vertices[faces]`` の面積 ``0.5·|(b−a)×(c−a)|`` を確率にして ``samples``
    個の面を復元抽出し、各面で ``u, v ~ U(0,1)``、``u + v > 1`` なら ``(1−u, 1−v)`` に折り返す
    (一様 barycentric)。点 ``= a + u(b−a) + v(c−a)``。``seed`` で ``default_rng`` を固定するので
    同じ引数なら同じ点群。

    - ``vertices`` (V,3) float、``faces`` (F,3) int(0 始まりの頂点 index)。
    - 返り値 ``(samples, 3)`` float64。面の数に関係なくちょうど ``samples`` 点。
    - 全面が退化(面積和 0)なら確率が NaN になり ``rng.choice`` が ValueError。
    - 法線は付かない(``estimate_point_normals`` で付ける)。面積重みなので大きな面ほど点が多く、
    頂点密度には依存しない。
    後段: ``points_to_voxel`` / ``icp_point2point_3d`` / ``match_pca``。
    """
    V = np.asarray(vertices, np.float64); Fc = np.asarray(faces, np.int64)
    tri = V[Fc]
    areas = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0],
                                          tri[:, 2] - tri[:, 0]), axis=1)
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(Fc), size=samples, p=areas / areas.sum())
    u = rng.random(samples); v = rng.random(samples); over = u + v > 1
    u[over] = 1 - u[over]; v[over] = 1 - v[over]
    t = tri[pick]
    return t[:, 0] + u[:, None] * (t[:, 1] - t[:, 0]) + v[:, None] * (t[:, 2] - t[:, 0])


def voxel_to_mesh(vol, iso=0.5):
    """voxel → mesh(marching cubes、skimage)。返り値 (verts, faces, normals)。voxel→mesh 変換。

    ``skimage.measure.marching_cubes(vol, level=iso)`` の薄い包み(spacing 指定なし = 1 voxel
    単位)。``verts`` (V,3) float は **voxel index 座標**で、列は入力の軸順(``vol`` が (D,H,W)
    なら (z,y,x))。``faces`` (F,3) int は verts への index、``normals`` (V,3) は skimage が
    勾配から与える頂点法線。4 番目の返り値(values)は捨てる。

    - ``iso``: 等値面のレベル。**入力の値域の外だと skimage が ValueError** を出す(全 0 の
    volume で iso=0.5 など)。個数密度なら 0.5、SDF なら 0.0 を渡す。
    - 境界に接する等値面は開いたまま(端で閉じない)。
    - ★**巻き順は内向き**。そのまま ``mesh_volume`` に渡すと**普通の中身のある形でも
    負**になる(実測: 1000 voxel の立方体で -985.67)。体積が欲しいだけなら
    ``abs()``、向きを揃えたいなら ``faces[:, ::-1]`` で巻き直す。
    - skimage は呼び出し時 import(未導入なら ImportError)。
    後段: ``mesh_to_points`` で点群化、``mesh_area`` / ``face_areas`` / ``mesh_volume`` /
    ``boundary_vertices`` / ``mesh_edge_stats`` で計測。
    """
    from skimage import measure
    v, f, n, _ = measure.marching_cubes(np.asarray(vol, np.float64), level=iso)
    return v, f, n


def tsdf_from_depth(depth, fx, fy, cx, cy, size=64, bounds=None, trunc=3.0):
    """深度マップ(2.5D)→ TSDF volume(RGB-D 再構成の標準表現)。depth→TSDF 変換。

    各 voxel を画像へ投影し、視線上の観測深度との符号付き切詰め距離 [-1,1] を格納
    (表面手前 +・奥 −・表面 0)。KinectFusion 系の基本表現。

    格子: ``bounds=(lo, hi)`` は **(X, Y, Z) のカメラ座標**(``depth_to_points`` と同じ)で、
    None なら深度を逆投影した点群の min−2 / max+2(深度の単位)。出力は ``(size,size,size)``
    float32 で **軸順は (Z, Y, X)**、voxel 中心 ``= lo + (i + 0.5)/size·(hi − lo)``。
    bounds の並び (x,y,z) と配列の軸 (z,y,x) が逆なことに注意。

    値: 各 voxel 中心を ``u = X·fx/Z + cx``、``v = Y·fy/Z + cy`` で画素へ丸め、その画素の観測深度
    ``d`` から ``clip((d − Z)/trunc, −1, 1)``(``trunc`` は深度と同じ単位)。画像外に落ちる
    voxel・観測深度が 0 以下・Z が 0 以下の voxel は **+1(未観測=自由)** にする(端画素へ
    clip して観測済みに見せかけない)。深度 0 が無効値の規約。

    - 深度が全て 0 で bounds=None だと点群が空になり numpy の min で例外。
    - 1 視点の TSDF なので視線の裏側は −1 で埋まる(閉じた物体にはならない)。
    後段: ``voxel_to_mesh(tsdf, iso=0.0)`` で面を取る。占有にするなら ``sdf_to_occupancy``。
    """
    d = np.asarray(depth, np.float64); H, W = d.shape
    pts = depth_to_points(d, fx, fy, cx, cy)
    if bounds is None:
        lo, hi = pts.min(0) - 2, pts.max(0) + 2
    else:
        lo, hi = _lo_hi(bounds)
    span = np.maximum(hi - lo, 1e-9)
    zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
    wz = lo[2] + (zz + 0.5) / size * span[2]
    wy = lo[1] + (yy + 0.5) / size * span[1]
    wx = lo[0] + (xx + 0.5) / size * span[0]
    uf = (wx * fx / np.maximum(wz, 1e-6) + cx).round()
    vf = (wy * fy / np.maximum(wz, 1e-6) + cy).round()
    # 視野外に落ちる voxel を端画素へ clip して「観測済み」に化けさせない。
    # clip したまま depth を引くと、bounds が視野より広い正当な入力で volume の
    # 端に実在しないゼロ交差が並び、marching cubes が幻の壁を作る。
    inside = (uf >= 0) & (uf <= W - 1) & (vf >= 0) & (vf <= H - 1)
    ui = np.clip(uf, 0, W - 1).astype(int)      # 索引を安全にするためだけの clip
    vi = np.clip(vf, 0, H - 1).astype(int)
    dz = d[vi, ui]
    tsdf = np.clip((dz - wz) / trunc, -1, 1)
    tsdf[~(inside & (dz > 0) & (wz > 0))] = 1.0   # 視野外・無効深度 = 未観測
    return tsdf.astype(np.float32)


# ── 3D モルフォロジー(グレースケール)────────────────────────────────────────
# 実装は 2 経路: torch(max_pool3d、cube SE、GPU 可)と scipy.ndimage(CPU、
# cube/ball SE)。torch 不在でも全 op が scipy で動く(コア= numpy+scipy 主義)。
# 境界規約は両経路とも「外は dilation で −inf / erosion で +inf」= 画像内の
# 値だけで局所 max/min を取る(torch の implicit padding と同一。パリティは
# tests/test_match3d_morph.py でビット単位検証)。
def _mdil(t, r):
    return F.max_pool3d(t, 2 * r + 1, stride=1, padding=r)


def _mero(t, r):
    return -F.max_pool3d(-t, 2 * r + 1, stride=1, padding=r)


def _morph_in(vol, device):
    return torch.as_tensor(np.asarray(vol, np.float32)[None, None], device=device)


def _ball_footprint(r):
    z, y, x = np.ogrid[-r:r + 1, -r:r + 1, -r:r + 1]
    return (z * z + y * y + x * x) <= r * r


def _gray_morph3d(vol, r, device, se, kind):
    """kind='dil'|'ero'。se='cube'|'ball'(ball は scipy 経路のみ)。"""
    if se not in ("cube", "ball"):
        raise ValueError(f"se は 'cube' か 'ball'(got {se!r})")
    if se == "cube" and _HAS_TORCH:
        t = _morph_in(vol, device)
        out = _mdil(t, r) if kind == "dil" else _mero(t, r)
        return out[0, 0].detach().cpu().numpy()
    from scipy import ndimage as _ndi
    v = np.asarray(vol, np.float32)
    kw = ({"size": (2 * r + 1,) * 3} if se == "cube"
          else {"footprint": _ball_footprint(r)})
    if kind == "dil":
        return _ndi.grey_dilation(v, mode="constant", cval=-np.inf, **kw)
    return _ndi.grey_erosion(v, mode="constant", cval=np.inf, **kw)


def morph_dilate3d(vol, r=1, device="cpu", se="cube"):
    """3D グレースケール dilation(SE 半径 r の局所 max)。明領域を膨張。

    se="cube"(既定、torch 経路で GPU 可)/ "ball"(等方 SE、scipy 経路)。

    SE は一辺 ``2r+1`` の立方体(cube)か ``z²+y²+x² <= r²`` の球(ball)。``r=0`` は恒等。
    境界の外は −∞ 扱い(画像内の値だけで max を取る。torch の ``max_pool3d`` の implicit
    padding と scipy の ``cval=-inf`` で同じ結果)。cube は torch があれば ``max_pool3d``
    (``device`` 有効)、ball または torch 不在なら ``scipy.ndimage.grey_dilation``(``device`` は
    無視)。入力は float32 に変換され、返り値 ``(D,H,W)`` float32 numpy。``se`` がその 2 つ以外なら
    ValueError。2 値 volume(0/1)ならそのまま 2 値 dilation になる。``se="ball"`` は r が
    大きいと footprint 走査で遅い。
    後段: ``morph_erode3d`` と組で ``morph_open3d`` / ``morph_close3d`` / ``morph_gradient3d``。
    """
    return _gray_morph3d(vol, r, device, se, "dil")


def morph_erode3d(vol, r=1, device="cpu", se="cube"):
    """3D グレースケール erosion(SE の局所 min)。明領域を収縮。se は dilate と同じ。

    一辺 ``2r+1`` の cube か半径 r の ball の中で最小値を取る。境界の外は +∞ 扱い(画像内の
    値だけで min。torch 経路は ``-max_pool3d(-v)``、scipy 経路は ``cval=+inf``)ので、端で 0 に
    落ちることはない。``r=0`` は恒等。``se`` が "cube"/"ball" 以外なら ValueError。``device`` は
    cube+torch のときだけ効く。返り値 ``(D,H,W)`` float32 numpy。
    2 値 volume では「SE が丸ごと入る voxel だけ残す」= 細い構造・薄い殻の除去。
    後段: ``morph_dilate3d`` と組で opening/closing、``vol − erosion`` で内側境界。
    """
    return _gray_morph3d(vol, r, device, se, "ero")


def morph_open3d(vol, r=1, device="cpu", se="cube"):
    """3D opening = erosion → dilation。SE より小さい**明構造(棘・粒)**を除く。

    ``morph_dilate3d(morph_erode3d(vol, r, ...), r, ...)`` と同じ SE を 2 回。出力は入力以下
    (``open <= vol``)で、SE(一辺 ``2r+1`` の cube か半径 r の ball)が入り切らない明るい突起・
    孤立点・細いブリッジが消え、大きな構造の形は保たれる(等冪: 2 回掛けても同じ)。
    ``r`` は voxel 単位、``se`` は "cube"/"ball"(他は ValueError)、``device`` は cube+torch の
    ときだけ有効。返り値 ``(D,H,W)`` float32 numpy。
    用途: ``vol − open`` が ``morph_tophat3d``(小さな明構造の抽出)。点密度 voxel の孤立ノイズ
    点除去、2 値占有の細線除去。
    """
    return morph_dilate3d(morph_erode3d(vol, r, device, se), r, device, se)


def morph_close3d(vol, r=1, device="cpu", se="cube"):
    """3D closing = dilation → erosion。SE より小さい**暗構造(隙間・空洞)**を埋める。

    ``morph_erode3d(morph_dilate3d(vol, r, ...), r, ...)``。出力は入力以上(``close >= vol``)で、
    SE(一辺 ``2r+1`` の cube か半径 r の ball)より小さい暗い穴・亀裂・面の隙間が周囲の
    明るさで埋まり、大きな暗領域は残る(等冪)。境界外は dilation で −∞、erosion で +∞ 扱い
    なので端が勝手に埋まることはない。``se`` は "cube"/"ball"(他は ValueError)、``device`` は
    cube+torch のときだけ有効。返り値 ``(D,H,W)`` float32 numpy。
    用途: ``close − vol`` が ``morph_blackhat3d``(小さな暗構造の抽出)。点群 splat の表面の
    穴埋め、``signed_distance_field`` 前の占有の穴埋め。
    """
    return morph_erode3d(morph_dilate3d(vol, r, device, se), r, device, se)


def morph_gradient3d(vol, r=1, device="cpu", se="cube"):
    """3D モルフォロジー勾配 = dilation − erosion。**境界/表面**を抽出(sobel 代替のエッジ源)。

    同じ SE(一辺 ``2r+1`` の cube か半径 r の ball)での局所 max − 局所 min。値は常に 0 以上、
    一様な領域で 0、明暗の境界で段差の大きさ(``r`` が大きいほど境界が太い。``r=1`` で 2 voxel
    幅)。方向情報は無い(方向が要るなら ``sobel3d``)。``sobel3d`` と違い利得の補正が要らず、
    2 値 volume では「境界 voxel = 1」の殻がそのまま出る。``se`` は "cube"/"ball"(他は
    ValueError)、``device`` は cube+torch のときだけ有効。返り値 ``(D,H,W)`` float32 numpy。
    用途: ``match_chamfer_3d`` 用のエッジ源、``hough_plane_3d`` に渡す前の表面抽出の代替。
    """
    return (morph_dilate3d(vol, r, device, se)
            - morph_erode3d(vol, r, device, se))


def morph_tophat3d(vol, r=1, device="cpu", se="cube"):
    """3D white top-hat = vol − opening。SE より小さい **明構造**を抽出(keypoint 前処理)。

    ``vol(float32) − morph_open3d(vol, r, ...)``。値は 0 以上で、SE(一辺 ``2r+1`` の cube か
    半径 r の ball)に入り切らない明るい突起・粒・細線だけがその高さで残り、それより大きな
    明領域と滑らかな背景は 0 になる。背景の緩い明るさムラも除けるので、閾値化の前処理に。
    ``r`` は「残したい構造の半径」より大きく取る。``se`` は "cube"/"ball"(他は ValueError)、
    ``device`` は cube+torch のときだけ有効。返り値 ``(D,H,W)`` float32 numpy。
    暗い構造を取るなら ``morph_blackhat3d``。
    """
    return np.asarray(vol, np.float32) - morph_open3d(vol, r, device, se)


def morph_blackhat3d(vol, r=1, device="cpu", se="cube"):
    """3D black-hat = closing − vol。SE より小さい **暗構造/穴**を抽出。

    ``morph_close3d(vol, r, ...) − vol(float32)``。値は 0 以上で、SE(一辺 ``2r+1`` の cube か
    半径 r の ball)より小さい暗い穴・亀裂・隙間だけがその深さで残り、大きな暗領域と背景は
    0 になる。占有 voxel なら「SE で埋まる空洞 = 1」。``r`` は検出したい穴の半径より大きく取る。
    ``se`` は "cube"/"ball"(他は ValueError)、``device`` は cube+torch のときだけ有効。
    返り値 ``(D,H,W)`` float32 numpy。明るい構造を取るなら ``morph_tophat3d``。
    """
    return morph_close3d(vol, r, device, se) - np.asarray(vol, np.float32)


# ═══════════════════════════════════════════════════════════════════════════
# 幾何プリミティブ / メトロロジー(2点→線・3点→面/角度、2D/3D 共通)
# 検出/マッチを「計測」に変える層(HALCON の 2D/3D metrology 相当)。全て閉形式。
# ═══════════════════════════════════════════════════════════════════════════
def _u(v):
    """単位ベクトル化。"""
    v = np.asarray(v, float)
    return v / np.linalg.norm(v).clip(1e-12)


def _vec(v, op, name):
    """幾何プリミティブ引数の検証: 数値の 2/3 ベクトルへ fail-closed に正規化。

    連鎖ファザー実測(wave-4): プール産物の dict がそのまま座標引数へ流れ込み、
    np.asarray(…, float) が生 TypeError で落ちていた。型・形状不正は明確な
    ValueError で拒否する(契約=CONTRACT に変える)。
    """
    try:
        a = np.asarray(v, float)
    except (TypeError, ValueError) as e:
        raise ValueError("%s: %s must be a numeric coordinate/direction vector "
                         "(got %s) — pass (x, y) or (x, y, z)"
                         % (op, name, type(v).__name__)) from e
    if a.ndim != 1 or a.shape[0] not in (2, 3):
        raise ValueError("%s: %s must be a 2- or 3-vector (got shape %r) — "
                         "pass (x, y) or (x, y, z)" % (op, name, a.shape))
    return a


def _vecs(op, **named):
    """複数ベクトル引数を一括検証し、次元(2D/3D)の混在も拒否。→ kwargs 順の tuple。"""
    out = [(k, _vec(v, op, k)) for k, v in named.items()]
    dims = {a.shape[0] for _, a in out}
    if len(dims) > 1:
        raise ValueError("%s: all arguments must share one dimensionality "
                         "(got %s) — mixing 2D and 3D coordinates is undefined"
                         % (op, ", ".join("%s=%d-vector" % (k, a.shape[0])
                                          for k, a in out)))
    return tuple(a for _, a in out)


def _pts(points, op, min_pts, name="points"):
    """点群引数の検証: 数値 (N,3) 配列へ fail-closed に正規化(最小点数も強制)。"""
    try:
        P = np.asarray(points, float)
    except (TypeError, ValueError) as e:
        raise ValueError("%s: %s must be a numeric (N, 3) point array (got %s)"
                         % (op, name, type(points).__name__)) from e
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError("%s: %s must be an (N, 3) point array, got %r"
                         % (op, name, P.shape))
    if len(P) < min_pts:
        raise ValueError("%s: need at least %d points (got %d) — the fit is "
                         "undefined below that" % (op, min_pts, len(P)))
    return P


def line_from_2points(a, b):
    """2 点 → 直線(通過点, 単位方向)。2 座標で線が定まる(2D/3D 共通)。

    返り値 ``(a, u)``: ``a`` は入力の 1 点目(float 配列)、``u = (b − a)/|b − a|``。引数は数値の
    2 または 3 ベクトル(それ以外・次元の混在は ValueError)。``a == b`` のときは方向が零ベクトルの
    まま返る(例外は出ない。呼び手で ``|u| > 0`` を確かめる)。座標の並び順は問わない(入力の
    順のまま返る)ので、(x,y,z) でも (z,y,x) でも一貫していればよい。
    後段: ``distance_point_line`` / ``distance_line_line`` / ``intersect_line_plane`` /
    ``angle_between_lines`` にこの ``(a, u)`` を渡す。点群から直線を取るなら ``fit_line_3d``。
    """
    a, b = _vecs("line_from_2points", a=a, b=b)
    return a, _u(b - a)


def plane_from_3points(a, b, c):
    """3 点 → 平面(通過点, 単位法線)。3 座標で面が定まる(2D/3D 共通)。

    返り値 ``(a, n)``: ``a`` は 1 点目、``n = (b−a)×(c−a)`` を単位化したもの(向きは a→b→c の
    右ねじ)。引数は数値の 2 または 3 ベクトル(それ以外・次元の混在は ValueError)。3 点が同一
    直線上なら ``n`` は零ベクトルのまま返る(例外は出ない)。
    2 次元の点を渡すと ``np.cross`` がスカラー(符号つき面積の 2 倍)を返すので、``n`` はベクトルで
    なく ±1 のスカラーになる。2-D で線の法線が欲しい場合は ``line_from_2points`` の方向を 90°
    回して使うこと。
    後段: ``distance_point_plane`` / ``intersect_line_plane`` / ``intersect_planes`` /
    ``angle_between_planes`` にこの ``(a, n)`` を渡す。点群からは ``fit_plane_3d``。
    """
    a, b, c = _vecs("plane_from_3points", a=a, b=b, c=c)
    return a, _u(np.cross(b - a, c - a))


def angle_3points(a, b, c):
    """3 点のなす角(頂点 b、度)。∠ABC。

    ``arccos(û·v̂)``(``u = a − b``, ``v = c − b``)を度で返す(float)。値は **[0, 180]** で符号は
    無い(2-D でも回転の向きは区別しない)。引数は数値の 2 または 3 ベクトル、次元の混在は
    ValueError。``a == b`` か ``c == b`` だと零ベクトルの内積 0 で 90 が返る(例外は出ない)。
    内積は [−1,1] に clip するので数値誤差で NaN にはならない。
    用途: 曲げ角・関節角の計測、``fit_line_3d`` で得た 2 直線の交点まわりの角度。
    """
    a, b, c = _vecs("angle_3points", a=a, b=b, c=c)
    return float(np.degrees(np.arccos(np.clip(_u(a - b) @ _u(c - b), -1, 1))))


def angle_between_lines(d1, d2):
    """2 直線方向のなす鋭角(度)。

    ``arccos(|d̂1·d̂2|)`` を度で返す(float)。絶対値を取るので **[0, 90]**(向きの前後を区別しない。
    鈍角側が要るなら ``180 −`` する)。``d1``, ``d2`` は方向ベクトル(長さは問わない、内部で単位化)、
    数値の 2 または 3 ベクトルで次元の混在は ValueError。零ベクトルは 90 が返る。
    用途: ``fit_line_3d`` / ``line_from_2points`` の方向同士の平行度・直角度チェック(0 に近いほど
    平行、90 に近いほど直交)。
    """
    d1, d2 = _vecs("angle_between_lines", d1=d1, d2=d2)
    return float(np.degrees(np.arccos(np.clip(abs(_u(d1) @ _u(d2)), -1, 1))))


def angle_between_planes(n1, n2):
    """2 平面の二面角(法線 n1,n2、度)。

    法線同士の角 ``arccos(|n̂1·n̂2|)`` を度で返す(float)。絶対値を取るので **[0, 90]** の鋭角側
    (法線の向きに依らない。鈍角側が要るなら ``180 −``)。0 = 平行、90 = 直交。``n1``, ``n2`` は
    数値の 2 または 3 ベクトル(長さは問わない)、次元の混在は ValueError。零ベクトルは 90 が返る。
    用途: ``fit_plane_3d`` / ``hough_plane_3d`` で取った 2 面の平行度・直角度、``intersect_planes``
    の前の平行判定。
    """
    n1, n2 = _vecs("angle_between_planes", n1=n1, n2=n2)
    return float(np.degrees(np.arccos(np.clip(abs(_u(n1) @ _u(n2)), -1, 1))))


def angle_line_plane(d, n):
    """直線(方向 d)と平面(法線 n)のなす角(度)。

    ``90 − arccos(|d̂·n̂|)`` を度で返す(float)。値は **[0, 90]**、0 = 直線が平面に平行、90 = 垂直。
    ``d``, ``n`` は数値の 2 または 3 ベクトル(長さは問わない)、次元の混在は ValueError。零ベクトル
    は 0 が返る。
    用途: 穴軸と基準面の直角度、``intersect_line_plane`` の前の平行判定(0 に近いと交点が遠くへ
    飛ぶ)。
    """
    d, n = _vecs("angle_line_plane", d=d, n=n)
    return float(90.0 - np.degrees(np.arccos(np.clip(abs(_u(d) @ _u(n)), -1, 1))))


def distance_point_plane(p, plane_pt, n):
    """点-平面距離(符号なし)。

    ``|(p − plane_pt)·n̂|`` を float で返す(``n`` は内部で単位化)。符号は捨てるので、面のどちら側か
    が要るなら ``(p − plane_pt) @ n̂`` を直接計算する。``p``, ``plane_pt``, ``n`` は数値の 2 または
    3 ベクトル、次元の混在は ValueError。2-D では ``n`` を直線の法線として点-直線距離になる。
    零ベクトルの ``n`` は 0 を返す。単位は入力座標の単位。
    用途: ``fit_plane_3d`` / ``hough_plane_3d`` の面からの高さ、``surface_form_error`` の点群版
    (残差を 1 点ずつ)。
    """
    p, plane_pt, n = _vecs("distance_point_plane", p=p, plane_pt=plane_pt, n=n)
    return float(abs((p - plane_pt) @ _u(n)))


def distance_point_line(p, line_pt, d):
    """点-直線距離。

    ``w = p − line_pt`` の、方向 ``d̂`` に直交する成分の長さ ``|w − (w·d̂)d̂|`` を float で返す
    (``d`` は内部で単位化。2-D/3-D 共通)。``p``, ``line_pt``, ``d`` は数値の 2 または 3 ベクトル、
    次元の混在は ValueError。``d`` が零ベクトルなら ``|w|`` がそのまま返る。単位は入力座標の単位。
    用途: ``fit_line_3d`` の軸からの偏心、``line_from_2points`` の線に対する点群のばらつき
    (1 点ずつ)。
    """
    p, line_pt, d = _vecs("distance_point_line", p=p, line_pt=line_pt, d=d)
    d = _u(d); w = p - line_pt
    return float(np.linalg.norm(w - (w @ d) * d))


def distance_line_line(p1, d1, p2, d2):
    """2 直線間距離(ねじれの位置=skew も可)。平行なら点-線距離に退避。

    ``n = d̂1 × d̂2`` を取り、``|n| < 1e-9``(平行)なら ``distance_point_line(p2, p1, d1)``、それ
    以外は ``|(p2 − p1)·n̂|``(共通垂線の長さ)を float で返す。交わる直線では 0。
    ``p1, d1, p2, d2`` は数値の 2 または 3 ベクトル、次元の混在は ValueError。
    2-D の非平行な直線は交わるので距離 0 のはずだが、``np.cross`` がスカラーになるため ``@`` が
    失敗する(2-D は平行な場合しか通らない)。3-D で使うこと。単位は入力座標の単位。
    用途: 2 本の軸(``fit_line_3d``)の同軸度、穴ピッチ。
    """
    p1, d1, p2, d2 = _vecs("distance_line_line", p1=p1, d1=d1, p2=p2, d2=d2)
    d1 = _u(d1); d2 = _u(d2); n = np.cross(d1, d2); ln = np.linalg.norm(n)
    if ln < 1e-9:
        return distance_point_line(p2, p1, d1)
    return float(abs((p2 - p1) @ (n / ln)))


def intersect_line_plane(line_pt, d, plane_pt, n):
    """直線 ∩ 平面 → 点(平行なら None)。

    ``t = ((plane_pt − line_pt)·n̂)/(d·n̂)`` で ``line_pt + t·d`` を返す(float 配列)。``d`` は単位化
    しない(``t`` は ``d`` の長さ単位)。``|d·n̂| < 1e-9`` なら **None**(例外ではない。返り値を使う
    前に None チェック)。面に含まれる直線(距離 0 かつ平行)も None。引数は数値の 2 または 3
    ベクトル、次元の混在は ValueError。2-D では ``n`` を直線の法線として線と線の交点になる。
    用途: 視線(``depth_to_points`` の点 − 原点)と ``fit_plane_3d`` の面との交点、レイと基準面。
    """
    line_pt, d, plane_pt, n = _vecs("intersect_line_plane",
                                    line_pt=line_pt, d=d, plane_pt=plane_pt, n=n)
    n = _u(n); dn = d @ n
    if abs(dn) < 1e-9:
        return None
    t = (plane_pt - line_pt) @ n / dn
    return line_pt + t * d


def intersect_planes(p1, n1, p2, n2):
    """平面 ∩ 平面 → 直線(通過点, 方向)。平行なら None。

    方向 ``d = n̂1 × n̂2`` を単位化し、``n̂1·p = n̂1·p1``、``n̂2·p = n̂2·p2``、``d·p = 0`` の 3×3 を
    解いて通過点 ``p`` を求める(``d·p = 0`` なので **原点に最も近い点**)。返り値 ``(p(3,), d(3,))``。
    ``|n1 × n2| < 1e-9``(平行・同一面)なら **None**。
    引数は数値 3 ベクトル(``np.cross`` と 3×3 の solve を使うので **3-D 専用**。2-D を渡すと
    配列構築で失敗する)。次元の混在は ValueError。
    用途: ``fit_plane_3d`` した 2 面の稜線、箱のエッジの抽出 → ``distance_point_line`` でエッジ
    からの距離。
    """
    p1, n1, p2, n2 = _vecs("intersect_planes", p1=p1, n1=n1, p2=p2, n2=n2)
    n1 = _u(n1); n2 = _u(n2); d = np.cross(n1, n2); ld = np.linalg.norm(d)
    if ld < 1e-9:
        return None
    d = d / ld
    A = np.array([n1, n2, d]); bb = np.array([n1 @ p1, n2 @ p2, 0.0])
    return np.linalg.solve(A, bb), d


def fit_line_3d(points):
    """点群 → 最小二乗直線(通過点=重心, 方向=最大主軸)。返り値 (point, direction)。

    ``(N,3)`` の点群(数値・列数 3 でなければ ValueError、2 点未満も ValueError)の重心 ``c`` と
    散布行列 ``(P−c)ᵀ(P−c)`` の最大固有値の固有ベクトルを返す(直交距離の二乗和を最小化する直線。
    z=f(x) 型の回帰ではない)。``direction`` は単位ベクトルで **符号は任意**(``eigh`` 次第。向きを
    揃えるなら ``(P[-1] − P[0]) @ direction`` の符号で反転)。
    2 点だけなら 2 点を通る直線。点が平面状に広がっていると最大軸は「最も長い方向」になるだけで
    直線とは限らない(残差は返さないので ``distance_point_line`` で確かめる)。外れ値に弱い
    (ロバストには ``ransac_line``)。3-D 専用(2-D 点は ValueError)。
    """
    P = _pts(points, "fit_line_3d", 2); c = P.mean(0)
    _, v = np.linalg.eigh((P - c).T @ (P - c))
    return c, v[:, -1]


def fit_plane_3d(points):
    """点群 → 最小二乗平面(通過点=重心, 法線=最小主軸, 残差 RMS)。返り値 (point, normal, resid)。

    ``(N,3)`` の点群(列数 3 でない・3 点未満は ValueError)の重心 ``c`` と散布行列の最小固有値の
    固有ベクトルを法線にする(直交距離の二乗和を最小化。``resid = sqrt(λ_min/N)`` = 面からの直交
    距離の RMS)。``normal`` は単位ベクトルで **符号は任意**(外向きにするなら視点や重心との関係で
    反転する)。3 点なら厳密に通る面で resid=0(BLAS の負の丸めは 0 に clamp)。
    点が直線状(2 番目の固有値も 0)だと法線は不定。外れ値に弱い(``ransac_plane`` /
    ``plane_segmentation`` で先にインライアを取る)。3-D 専用。
    後段: ``distance_point_plane`` / ``angle_between_planes`` / ``intersect_planes``、高さ場の
    平面度なら ``surface_form_error(degree=1)``。
    """
    P = _pts(points, "fit_plane_3d", 3); c = P.mean(0)
    w, v = np.linalg.eigh((P - c).T @ (P - c))
    # 完全平面では最小固有値が BLAS により -1e-16 側に落ちることがある(sqrt→nan)。
    # A perfectly planar cloud can yield a tiny NEGATIVE smallest eigenvalue on
    # some BLAS builds (caught by CI's OpenBLAS) — clamp before the sqrt.
    return c, v[:, 0], float(np.sqrt(max(w[0], 0.0) / len(P)))


def fit_sphere_3d(points):
    """点群 → 最小二乗球(代数フィット)。返り値 (center, radius)。配管/ボール計測に。

    ``|p|² = 2c·p + (r² − |c|²)`` を ``[2p, 1]`` の線形最小二乗(``lstsq``)で解く代数フィット
    (幾何距離の最小化ではないので、球の一部しか見えていない・ノイズが大きいと半径が偏る)。
    ``(N,3)`` で 4 点未満は ValueError。``radius`` は ``sqrt(max(s + |c|², 0))`` で負は 0 に clamp。
    点が同一平面上・共線だと ``lstsq`` の最小ノルム解が黙って返る(検証は無い。残差も返さないので
    ``|p − c| − r`` で確かめる)。
    幾何距離で追い込むなら本 op の結果を初期値にして非線形最小二乗、外れ値には ``ransac_sphere``。
    voxel からの検出は ``hough_sphere_3d``。
    """
    P = _pts(points, "fit_sphere_3d", 4)
    A = np.hstack([2 * P, np.ones((len(P), 1))]); b = (P ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 0.0)))


def fit_circle_3d(points):
    """点群 → 3D 円(平面フィット → 面内で 2D 円フィット)。返り値 (center, radius, normal)。

    ``fit_plane_3d`` で面 ``(c, n)`` を取り、面内の正規直交基底 ``(e1, e2)`` に点を射影して 2-D の
    代数円フィット(``|q|² = 2·cc·q + k`` の ``lstsq``)を解き、中心を 3-D に戻す。``(N,3)`` で
    3 点未満は ValueError(3 点なら面は厳密、円は 3 点を通る)。
    ``center`` は面上の 3-D 点、``radius`` は float(負の根は 0 に clamp)、``normal`` は面の単位法線
    (符号任意)。円弧の一部だけ・面から外れた点が多いと半径が偏る(代数フィットの性質。面内残差は
    返さない)。
    用途: 穴・フランジ・リングの中心と径、``distance_point_line`` で軸からの偏心。
    """
    P = _pts(points, "fit_circle_3d", 3); c, n, _ = fit_plane_3d(P)
    e1 = _u(np.cross(n, [1, 0, 0]) if abs(n[0]) < 0.9 else np.cross(n, [0, 1, 0]))
    e2 = np.cross(n, e1)
    xy = np.stack([(P - c) @ e1, (P - c) @ e2], 1)
    A = np.hstack([2 * xy, np.ones((len(xy), 1))]); b = (xy ** 2).sum(1)
    s, *_ = np.linalg.lstsq(A, b, rcond=None); cc = s[:2]
    return c + cc[0] * e1 + cc[1] * e2, float(np.sqrt(max(s[2] + cc @ cc, 0.0))), n


# ═══════════════════════════════════════════════════════════════════════════
# 曲面近似 z=f(x,y)(2変数→1変数、最小二乗)= 画像の背景/シェーディング補正・
# 計測の平面度/形状誤差。多数の観測を少数係数で表す情報圧縮。
# ═══════════════════════════════════════════════════════════════════════════
def _poly_terms(x, y, degree):
    """{x^i y^j : i+j<=degree} の基底行列 (N,T) とべき指数。"""
    x = np.asarray(x, float).ravel(); y = np.asarray(y, float).ravel()
    cols, powers = [], []
    for d in range(degree + 1):
        for i in range(d + 1):
            cols.append(x ** i * y ** (d - i)); powers.append((i, d - i))
    return np.stack(cols, 1), powers


def fit_poly_surface(x, y, z, degree=2):
    """散布 (x,y,z) → z=f(x,y) 多項式最小二乗。返り値 model(coef/powers/degree/rms/pv)。

    基底 ``{x^i·y^j : i + j <= degree}``(項数 ``(degree+1)(degree+2)/2``。degree=1 で 3 項の平面、
    2 で 6 項の 2 次曲面)を ``lstsq`` で当てる。``x, y, z`` は同じ要素数なら形は問わない(内部で
    ravel。格子なら ``np.mgrid`` の出力をそのまま)。
    返り値 dict: ``coef`` (T,) 係数、``powers`` は各係数の ``(i, j)``(項 ``x**i * y**j``)、
    ``degree``、``rms`` は残差 RMS、``pv`` は残差の peak-to-valley(max − min)。単位は z。
    - 点数が項数より少ないと最小ノルム解が黙って返る。x, y の桁が大きいと高次で条件が悪くなる
    (座標を中心化・正規化してから)。NaN の検証は無い。
    後段: ``eval_poly_surface(model, x, y)`` で任意点を評価。格子の高さ場なら ``surface_form_error``
    / ``background_flatten`` がこれを内部で呼ぶ。
    """
    A, powers = _poly_terms(x, y, degree); zz = np.asarray(z, float).ravel()
    coef, *_ = np.linalg.lstsq(A, zz, rcond=None)
    resid = zz - A @ coef
    return {"coef": coef, "powers": powers, "degree": degree,
            "rms": float(np.sqrt(np.mean(resid ** 2))), "pv": float(resid.max() - resid.min())}


def eval_poly_surface(model, x, y):
    """model を (x,y) で評価 → z(x の shape で返す)。

    *model* は :func:`fit_poly_surface` の返り(dict)。**fail-closed**: B スプライン
    曲面/曲線の tck(FITPACK の list)を渡すと、以前は ``model["degree"]`` が
    ``TypeError: list indices must be integers...`` で落ちていた(2026-09-01 実測 7 回)。
    多項式モデルと B スプラインモデルは中身が違うので、ここで明示的に拒否する
    (ops3d 台帳側でも poly_surface / bspline_surface と型を分けてある)。

    Raises ValueError: model が多項式モデル dict でない / 必須キー欠落。
    """
    if not isinstance(model, dict):
        raise ValueError(
            "eval_poly_surface: model must be the dict returned by fit_poly_surface "
            f"(got {type(model).__name__}). B-spline models (FITPACK tck lists/tuples) "
            "belong to bspline_surf.eval_bspline_surface / eval_bspline_curve")
    missing = [k for k in ("coef", "powers", "degree") if k not in model]
    if missing:
        raise ValueError(
            "eval_poly_surface: model is missing key(s) %s; expected the dict from "
            "fit_poly_surface (coef/powers/degree/rms/pv)" % ", ".join(missing))
    A, _ = _poly_terms(x, y, model["degree"])
    return (A @ model["coef"]).reshape(np.asarray(x).shape)


def surface_form_error(height, degree=1):
    """高さ場 grid → 理想曲面(多項式)残差=形状誤差(平面度 deg1/球面度 deg2)。→ (residual, rms, pv)。

    ``(H,W)`` の高さ場に ``x = 列 index``、``y = 行 index`` で ``fit_poly_surface(degree)`` を当て、
    ``residual = height − fit`` を返す。``degree=1`` は最小二乗平面(平面度=pv)、``degree=2`` は
    2 次曲面(球面の近似。真の球ではない)。
    返り値 ``(residual (H,W) float64, rms, pv)``、単位は高さの単位(横方向は画素単位なので傾き
    係数は「高さ/画素」)。NaN があると lstsq が失敗する(欠損は先に埋める)。2-D 以外の入力は
    形の unpack で失敗する。
    用途: 平面度・うねりの評価。``background_flatten`` は同じ計算の「画像版」。点群の平面度は
    ``fit_plane_3d`` の resid。
    """
    H, W = np.asarray(height).shape; yy, xx = np.mgrid[0:H, 0:W]
    m = fit_poly_surface(xx, yy, height, degree)
    r = np.asarray(height, float) - eval_poly_surface(m, xx, yy)
    return r, float(np.sqrt(np.mean(r ** 2))), float(r.max() - r.min())


def background_flatten(image, degree=2):
    """画像の低次曲面(照明ムラ)をフィット減算=シェーディング補正。→ flattened。

    ``(H,W)`` 画像に ``x = 列``、``y = 行`` で ``fit_poly_surface(degree)``(既定 2 次)を当て、
    ``image − fit`` を float64 で返す。出力は平均がほぼ 0 で **負の値を含む**(表示・閾値化には
    ``min`` を引くか定数を足す)。前景が広いと前景もフィットに引かれて削られる(前景を除いた点で
    ``fit_poly_surface`` → ``eval_poly_surface`` で減算する方が安全)。
    グレースケール 2-D のみ(3-D は失敗)。NaN があると lstsq が失敗する。
    用途: 閾値化の前処理、``polar_unwrap`` した円環画像の照明補正。
    """
    H, W = np.asarray(image).shape; yy, xx = np.mgrid[0:H, 0:W]
    m = fit_poly_surface(xx, yy, image, degree)
    return np.asarray(image, float) - eval_poly_surface(m, xx, yy)


# ═══════════════════════════════════════════════════════════════════════════
# 曲座標系への展開(デカルトに限らない)= 極/円筒アンラップ検査・Zernike(円板の
# 直交基底=極座標の曲面近似、光学/波面計測)
# ═══════════════════════════════════════════════════════════════════════════
def polar_unwrap(image, center=None, r_in=0.0, r_out=None, ntheta=360, nr=64, device="cpu"):
    """画像の円環/円板を (θ×r) 矩形へアンラップ(工業: ラベル/リング/回転体の検査)。

    円周方向に並ぶ特徴を「縦」に伸ばして通常の 2D 手法(直線探索/相関)を適用できる。grid_sample。
    θ 軸は endpoint 無し(行 k の角度 = k·2π/ntheta)= 0° と 360° を重複サンプルしない
    周期グリッド(θ 方向 FFT/循環相関の前提を満たす。2026-08-30 修正、旧版は先頭行=末尾行)。

    Raises ValueError: 入力が 2-D でない・2x2 未満・NaN/Inf/float32 桁あふれ。

    引数: ``center=(cy, cx)`` は **(行, 列)** の順(既定は画像中心 ``((H−1)/2, (W−1)/2)``)。
    ``r_in``〜``r_out``(画素、既定 ``min(H,W)/2 − 1``)を ``nr`` 等分、角度を ``ntheta`` 等分。
    出力 ``(ntheta, nr)`` float32: 行 k の角度 ``θ = k·2π/ntheta``、列 j の半径
    ``r = r_in + j·(r_out − r_in)/(nr−1)``、サンプル点は ``(cy + r sinθ, cx + r cosθ)``(θ=0 が
    +列方向、θ が増えると +行方向へ回る)。画像外は 0 で埋まる(bilinear)。
    後段: 行方向(θ)の直線探索・``ncc_locate``、θ 方向の 1-D 相関で回転角。
    """
    img = _f32_finite(image, "polar_unwrap: image")
    if img.ndim != 2:
        raise ValueError("polar_unwrap: image must be 2-D, got %d-D" % (img.ndim,))
    H, W = img.shape
    # 幅 or 高さ 1 だと正規化格子の (W-1) / (H-1) が 0 除算になり、grid_sample が
    # 全 NaN を無言で返す(連鎖ファザー wave-8 実測: spectrogram の (129,1)
    # 産物。fit_zernike と同クラスで、そちらだけ塞いでいた取りこぼし)。
    if H < 2 or W < 2:
        raise ValueError("polar_unwrap: image must be at least 2x2, got %dx%d "
                         "(the polar grid divides by W-1/H-1)" % (H, W))
    cy, cx = ((H - 1) / 2, (W - 1) / 2) if center is None else center
    if r_out is None:
        r_out = min(H, W) / 2 - 1
    # ★2026-09-07: **輪が画像の外にあるなら fail-closed**。``r_in``/``r_out`` は
    # 画素単位なので、mm のまま渡すと視野の外を読み、例外なしに**全部 0** が返る
    # (`poc_pipe_wall_loss` が真っ黒な図を 1 枚出して発覚)。中心から画像の四隅
    # までの最大距離より内側の半径が 1 つも無ければ、返るのは空以外にありえない。
    _reach = max(np.hypot(cy - y, cx - x) for y in (0, H - 1) for x in (0, W - 1))
    if float(min(r_in, r_out)) > _reach:
        raise ValueError(
            "polar_unwrap: the requested ring (r_in=%g..r_out=%g, **pixels**) lies "
            "entirely outside the %dx%d image (the farthest corner is %.1f px from "
            "the centre) — the result would be all zeros. If these are millimetres, "
            "divide by the pixel size first." % (r_in, r_out, H, W, _reach))
    # ★2026-09-07: grid_sample(bilinear, align_corners=True, zeros padding)を
    # scipy の map_coordinates(order=1, mode="constant", cval=0)に置き換えた ——
    # 同じ双線形補間で、torch を入れない CI(py3.10 / 3.12)でも走る。
    # 実測差は最大 6.0e-06(値域 0..1 の乱数画像。float32 と float64 の丸めぶん)。
    if str(device) not in ("cpu", "None") and not _HAS_TORCH:
        raise ValueError(
            "polar_unwrap: device=%r needs the optional 'torch' backend "
            "(the numpy path runs on the CPU only)" % (device,))
    from scipy.ndimage import map_coordinates
    th = np.arange(ntheta, dtype=np.float64) * (2 * float(np.pi) / ntheta)
    rr = np.linspace(r_in, r_out, nr, dtype=np.float64)
    ys = cy + rr[None, :] * np.sin(th[:, None])
    xs = cx + rr[None, :] * np.cos(th[:, None])
    out = map_coordinates(np.asarray(img, np.float64), [ys, xs], order=1,
                          mode="grid-constant", cval=0.0)
    return out.astype(np.float32)


def cylinder_unwrap(vol, center=None, r_in=0.0, r_out=None, ntheta=180, nr=32, device="cpu"):
    """voxel の円筒面を (height×θ×r) へアンラップ(円筒部品/配管の内外面検査)。軸=z(D 軸)。

    θ 軸は endpoint 無しの周期グリッド(polar_unwrap と同じ 2026-08-30 修正)。

    Raises ValueError: 入力に NaN/Inf/float32 桁あふれがある場合。

    引数: ``vol`` は ``(D,H,W)``、``center=(cy, cx)`` は各 z スライス内の **(行, 列)**(既定は
    スライス中心)。``r_in``〜``r_out``(voxel、既定 ``min(H,W)/2 − 1``)を ``nr`` 等分、角度を
    ``ntheta`` 等分。出力 ``(D, ntheta, nr)`` float32: 軸 0 は z(高さ、入力と同じ)、行 k の角度
    ``θ = k·2π/ntheta``、列 j の半径。サンプル点は ``(z, cy + r sinθ, cx + r cosθ)``、volume 外は 0。
    D, H, W が 1 の軸は正規化で 0 除算になる(``polar_unwrap`` と違い検査は無い)。
    後段: ``[:, :, j]`` を取れば半径 j の円筒面が (D×θ) の 2-D 画像になり、2-D の傷検査・
    ``ncc_locate`` が使える。
    """
    v = _f32_finite(vol, "cylinder_unwrap: vol"); D, H, W = v.shape
    cy, cx = ((H - 1) / 2, (W - 1) / 2) if center is None else center
    if r_out is None:
        r_out = min(H, W) / 2 - 1
    # polar_unwrap と同じ fail-closed(半径は **voxel 単位**)。
    _reach = max(np.hypot(cy - y, cx - x) for y in (0, H - 1) for x in (0, W - 1))
    if float(min(r_in, r_out)) > _reach:
        raise ValueError(
            "cylinder_unwrap: the requested ring (r_in=%g..r_out=%g, **voxels**) lies "
            "entirely outside the %dx%d slice (the farthest corner is %.1f voxels from "
            "the centre) — the result would be all zeros. If these are millimetres, "
            "divide by the voxel size first." % (r_in, r_out, H, W, _reach))
    # ★2026-09-07: polar_unwrap と同じ理由で map_coordinates に置き換え(双線形・
    # 範囲外 0)。torch 不在でも走る。実測差は最大 7.6e-06。
    if str(device) not in ("cpu", "None") and not _HAS_TORCH:
        raise ValueError(
            "cylinder_unwrap: device=%r needs the optional 'torch' backend "
            "(the numpy path runs on the CPU only)" % (device,))
    from scipy.ndimage import map_coordinates
    th = np.arange(ntheta, dtype=np.float64) * (2 * float(np.pi) / ntheta)
    rr = np.linspace(r_in, r_out, nr, dtype=np.float64)
    zz = np.arange(D, dtype=np.float64)
    Z = zz[:, None, None]; TH = th[None, :, None]; RR = rr[None, None, :]
    ys = cy + RR * np.sin(TH) + 0 * Z
    xs = cx + RR * np.cos(TH) + 0 * Z
    zs = Z + 0 * TH + 0 * RR
    out = map_coordinates(np.asarray(v, np.float64), [zs, ys, xs], order=1,
                          mode="grid-constant", cval=0.0)
    return out.astype(np.float32)


def _zernike_basis(nr, nt, n_max):
    """円板上 Zernike 多項式基底(ρ,θ)。radial R_n^m × 角度。返り (nz, nr*nt), 添字, ρ。"""
    from math import factorial
    rho = np.linspace(0, 1, nr); theta = np.linspace(0, 2 * np.pi, nt, endpoint=False)
    R, T = np.meshgrid(rho, theta, indexing="ij")
    rows, idx = [], []
    for n in range(n_max + 1):
        for m in range(-n, n + 1, 2):
            am = abs(m); Rnm = np.zeros_like(R)
            for k in range((n - am) // 2 + 1):
                c = ((-1) ** k * factorial(n - k)
                     / (factorial(k) * factorial((n + am) // 2 - k)
                        * factorial((n - am) // 2 - k)))
                Rnm += c * R ** (n - 2 * k)
            Z = Rnm * (np.cos(am * T) if m >= 0 else np.sin(am * T))
            rows.append(Z.ravel()); idx.append((n, m))
    return np.stack(rows, 0), idx, R.ravel()


def fit_zernike(disk_image, n_max=6, device="cpu", nr=48, nt=72):
    """円板画像 → Zernike 係数(光学/波面計測の**極座標曲面近似**)。返り値 {(n,m): coef}。

    直交多項式で円板上の曲面(波面収差、レンズ形状)を少数係数に。tilt/defocus/astigmatism/
    coma/spherical 等が特定の (n,m) に対応し、回転で m が混ざる(帯域=回転不変)。

    honest 開示(2026-08-30 レビュー実測): 離散サンプリング(既定 nr=48, nt=72)では
    理論上直交のモード間に**最大 ~10% のクロストーク**が残る(例: 純 (2,0) defocus 入力で
    係数回収 0.95、リーク先は (4,0))。支配モードの特定には十分だが、係数の定量比較が
    要るときは nr/nt を上げる(誤差は解像度に対し単調減少)。

    Raises ValueError: 入力が 2-D でない・2x2 未満・NaN/Inf/float32 桁あふれ。
    """
    img = _f32_finite(disk_image, "fit_zernike: disk_image")
    if img.ndim != 2:
        raise ValueError("fit_zernike: disk_image must be 2-D, got %d-D"
                         % (img.ndim,))
    H, W = img.shape
    if H < 2 or W < 2:
        raise ValueError("fit_zernike: disk_image must be at least 2x2, "
                         "got %dx%d (the polar grid divides by W-1/H-1)"
                         % (H, W))
    nr, nt = int(nr), int(nt)
    B, idx, rho = _zernike_basis(nr, nt, n_max)
    cy, cx = (H - 1) / 2, (W - 1) / 2; rad = min(H, W) / 2 - 1
    rr = np.linspace(0, 1, nr); th = np.linspace(0, 2 * np.pi, nt, endpoint=False)
    Rg, Tg = np.meshgrid(rr, th, indexing="ij")
    ys = cy + Rg * rad * np.sin(Tg); xs = cx + Rg * rad * np.cos(Tg)
    grid = torch.stack([torch.as_tensor(xs / (W - 1) * 2 - 1, dtype=torch.float32),
                        torch.as_tensor(ys / (H - 1) * 2 - 1, dtype=torch.float32)], -1)[None]
    samp = F.grid_sample(torch.as_tensor(img, device=device)[None, None], grid.to(device),
                         align_corners=True)[0, 0].detach().cpu().numpy().ravel()
    mask = rho <= 1.0
    coef, *_ = np.linalg.lstsq(B[:, mask].T, samp[mask], rcond=None)
    return {idx[i]: float(coef[i]) for i in range(len(idx))}


# ═══════════════════════════════════════════════════════════════════════════
# 光学プリミティブ: 反射(鏡面)/ 屈折(Snell、透明体+屈折率)/ Fresnel /
# deflectometry(反射で鏡面法線を測る)。鏡面計測・透明体(ガラス/レンズ)検査。
# ═══════════════════════════════════════════════════════════════════════════
def _uo(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True).clip(1e-12)


def reflect(d, n):
    """入射方向 d を法線 n の面で鏡面反射。r = d − 2(d·n)n。

    ``d``, ``n`` は内部で単位化する(長さは問わない)ので、返り値 ``r`` も単位ベクトル。最後の軸を
    ベクトルとみなすので ``(3,)`` でも ``(N,3)`` のバッチでも動く(2-D の ``(2,)`` も可)。``n`` の
    向きは問わない(``n`` と ``−n`` で同じ ``r``)。``d`` は「面へ向かう」向き(光線の進行方向)で
    渡す。零ベクトルは 1e-12 で割って 0 のまま返る(例外は出ない)。
    用途: ``normal_from_reflection`` の逆問題、鏡面レンダの視線追跡(``refract`` と対)。
    """
    d = _uo(d); n = _uo(n)
    return d - 2 * np.sum(d * n, -1, keepdims=True) * n


def refract(d, n, eta1=1.0, eta2=1.5):
    """Snell 屈折(ベクトル形)。d=入射(面へ向かう), n=入射側外向き法線, 屈折率 eta1→eta2。

    透明体を通る光線の曲がりを厳密に。全反射(TIR)なら None。ガラス/レンズ/水中の像歪み計算に。
    契約は単一ベクトル。(N,3) バッチも通るが、**1 本でも TIR ならバッチ全体が None**
    (per-ray マスクはしない)— バッチで使うなら呼び出し側で 1 本ずつ回すこと。

    ``d``, ``n`` は最後の軸をベクトルとして単位化する。``n`` は入射側(``d·n < 0`` になる向き)で
    渡すこと。逆向きに渡すと ``cos θi`` が負になり、例外なく誤った方向が返る。返り値は単位ベクトル
    (``eta·d + (eta·cosθi − cosθt)·n``、``eta = eta1/eta2``)。``eta1 == eta2`` なら ``d`` がそのまま
    返る。角度で扱うなら ``snell_angle``、反射率は ``fresnel_reflectance(cos_i, eta1, eta2)``。
    """
    d = _uo(d); n = _uo(n); eta = eta1 / eta2
    cosi = -np.sum(d * n, -1, keepdims=True)
    sin2t = eta * eta * (1 - cosi * cosi)
    if np.any(sin2t > 1):
        return None
    cost = np.sqrt(1 - sin2t)
    return eta * d + (eta * cosi - cost) * n


def fresnel_reflectance(cos_i, eta1=1.0, eta2=1.5):
    """Fresnel 反射率(無偏光=s/p 平均)。透明体界面で反射/透過に分かれる割合。

    垂直入射で ((n1−n2)/(n1+n2))²(air→glass=0.04)。臨界角超で 1.0(全反射)。透明体レンダ/検査に。

    ``cos_i`` は入射角の余弦(実数スカラー。配列・None は ValueError)。符号は捨てる(``|cos_i|``)。
    ``eta1`` は入射側、``eta2`` は透過側の屈折率。s 偏光 ``rs`` と p 偏光 ``rp`` の平均を float で
    返す(**[0, 1]**)。Brewster 角では ``rp = 0`` になるが平均は 0 にならない。``cos_i = 0``(かすめ
    入射)で 1.0。透過率は ``1 −`` 反射率(吸収なし)。
    用途: ``refract`` で曲げた光線の重み、透明体の輝度予測。
    """
    try:
        cos_i = float(cos_i)
    except (TypeError, ValueError):
        raise ValueError("fresnel_reflectance: cos_i must be a real scalar, got %r"
                         % (type(cos_i).__name__,)) from None
    ci = abs(float(cos_i)); s2 = (eta1 / eta2) ** 2 * (1 - ci * ci)
    if s2 > 1:
        return 1.0
    ct = float(np.sqrt(1 - s2))
    rs = ((eta1 * ci - eta2 * ct) / (eta1 * ci + eta2 * ct)) ** 2
    rp = ((eta1 * ct - eta2 * ci) / (eta1 * ct + eta2 * ci)) ** 2
    return float(0.5 * (rs + rp))


def normal_from_reflection(incident, reflected):
    """入射+反射から鏡面の法線を復元(deflectometry)。n ∝ (r − d)、入射に逆らう向きへ。

    既知パターンの反射を観測 → 面法線 → 積分して鏡面形状。鏡面(反射)物体の形状計測の要。

    ``incident``(面へ向かう入射方向)と ``reflected``(面から出る反射方向)を単位化し、
    ``n = unit(r − d)`` を **``n·d <= 0``(入射に逆らう=入射側外向き)** になるよう符号を決めて
    返す(単位ベクトル)。``r == d`` なら零ベクトル。最後の軸をベクトルとするので ``(N,3)``
    バッチも通る(符号判定は全体の内積和で 1 回だけ行う)。
    用途: 既知パターンの反射像から画素ごとに法線を作り(法線マップ)、``integrate_normals`` で
    高さに積分、``render_shaded`` で見た目を再現、``reflect`` で検算。
    """
    d = _uo(incident); r = _uo(reflected); n = _uo(r - d)
    if np.sum(n * d) > 0:                                # 入射側(外向き)へ向ける
        n = -n
    return n


def snell_angle(theta_i_deg, eta1=1.0, eta2=1.5):
    """入射角(度)→ 屈折角(度)。n1 sinθi = n2 sinθt。臨界角超は NaN(全反射)。

    ``θt = arcsin((eta1/eta2)·sin θi)`` を度で返す(float)。``theta_i_deg`` は実数スカラー(配列・
    None は ValueError)。符号は保たれる(負の入射角は負の屈折角)。``|(eta1/eta2) sin θi| > 1`` なら
    ``nan``(全反射。``eta1 > eta2`` のときだけ起きる)。臨界角は ``degrees(arcsin(eta2/eta1))``。
    ``eta1 == eta2`` なら入射角そのまま。
    ベクトルで曲げるなら ``refract``、反射率は ``fresnel_reflectance(cos(radians(θi)))``。
    """
    try:
        theta_i_deg = float(theta_i_deg)
    except (TypeError, ValueError):
        raise ValueError("snell_angle: theta_i_deg must be a real scalar, got %r"
                         % (type(theta_i_deg).__name__,)) from None
    st = eta1 / eta2 * np.sin(np.radians(theta_i_deg))
    return float(np.degrees(np.arcsin(np.clip(st, -1, 1)))) if abs(st) <= 1 else float("nan")


# ═══════════════════════════════════════════════════════════════════════════
# 射影 / レンダリング(3D → 2D 合成)= 変換の逆向きでループを閉じる。
# 世界モデルの観測合成・外観検査のサンプル生成・3D 計測のサンプル空間生成。
# ═══════════════════════════════════════════════════════════════════════════
def project_points(points, K, R=None, t=None):
    """3D 点群 (N,3) → 画像座標 (u,v) と深度。ピンホール(depth_to_points の順方向)。

    K=カメラ内部行列 [[fx,0,cx],[0,fy,cy],[0,0,1]]。R,t で外部姿勢。世界モデルの観測写像。

    ``P_cam = R @ P + t``(``R`` (3,3)、``t`` (3,)。None は恒等・零)を ``u = fx·X/Z + cx``、
    ``v = fy·Y/Z + cy`` で投影する。返り値 ``(uv (N,2), depth (N,))``: ``uv[:,0] = u``(列)、
    ``uv[:,1] = v``(行)、``depth`` はカメラ座標の Z(clip 前の生値で、負もそのまま)。
    ``K`` は ``K[0,0]`` 等で添字するので numpy 配列(nested list は不可)。
    Z は ``1e-6`` 以上に clip してから割るので、**カメラ後方の点も捨てず**巨大な u,v になる
    (``depth > 0`` で呼び手が除く)。画像外の点も返す(``render_point_depth`` が範囲で切る)。
    ``depth_to_points`` の逆で、``depth_to_points(render_point_depth(...))`` が往復になる。
    """
    P = np.asarray(points, float)
    if R is not None:
        P = (np.asarray(R) @ P.T).T
    if t is not None:
        P = P + np.asarray(t)
    z = P[:, 2].clip(1e-6)
    u = K[0, 0] * P[:, 0] / z + K[0, 2]
    v = K[1, 1] * P[:, 1] / z + K[1, 2]
    return np.stack([u, v], 1), P[:, 2]


def render_point_depth(points, K, size, R=None, t=None):
    """点群 → 深度画像(z-buffer、各画素に最近点の深度)。観測合成/外観検査サンプル。

    ``project_points(points, K, R, t)`` で ``(u, v, z)`` を取り、``round`` した画素 ``(row=v,
    col=u)`` が ``size=(H, W)`` 内かつ ``z > 0`` の点だけを、遠い順に書いて近い点で上書きする
    (同一画素は最小 z が残る)。点が無い画素は **0**(``tsdf_from_depth`` / ``depth_to_points`` が
    無効値として扱う規約)。返り値 ``(H, W)`` float64、単位は点の座標の単位。
    - 1 点 = 1 画素なので疎な点群は穴だらけになる(``mesh_to_points`` で密にしてから)。splat
    半径は無い。
    - ``K`` は numpy (3,3)、``R``/``t`` は省略可。
    後段: ``depth_to_points`` で戻す、``normals_from_depth`` で法線、``tsdf_from_depth``。
    """
    H, W = size
    uv, z = project_points(points, K, R, t)
    ui = np.round(uv[:, 0]).astype(int); vi = np.round(uv[:, 1]).astype(int)
    ok = (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H) & (z > 0)
    ui, vi, z = ui[ok], vi[ok], z[ok]
    depth = np.full((H, W), np.inf)
    order = np.argsort(-z)                                   # 遠い順に書く→近点で上書き
    depth[vi[order], ui[order]] = z[order]
    depth[~np.isfinite(depth)] = 0
    return depth


def render_volume_projection(vol, azimuth=0.0, elevation=0.0, mode="xray", device="cpu"):
    """voxel を任意視点で 2D 投影(mode=xray=減衰積算 / mip=最大値)。DRR(X線)・世界モデル観測。

    view 方向へ volume を grid_sample で回して軸投影。voxel_to_mips の任意視点版。

    回転は ``affine_grid``(座標順 x=W, y=H, z=D)で volume 中心まわり: ``azimuth`` は H 軸まわり
    (W と D を混ぜる)、``elevation`` は W 軸まわり(H と D を混ぜる)、いずれも度、``Rx @ Ry`` の順。
    回転後の volume を **軸 0(D)方向に潰す**ので、視線は回転後の D 軸。``mode="mip"`` は最大値、
    それ以外はすべて総和(``"xray"`` は Beer-Lambert の指数ではなく **単純な積算**。減衰像にするなら
    ``exp(−Σ)`` を呼び手で)。返り値 ``(H, W)`` float32 numpy。
    volume 外は 0 で埋まるので、回転で隅が欠けると総和が下がる(立方体に近い volume で、物体を
    中心に置く)。``azimuth=elevation=0`` の mip は ``voxel_to_mips()[0]`` と同じ向き。
    用途: DRR の合成、``ncc_locate`` 用の 2-D テンプレ生成、``match_mip_2d`` の任意視点化。
    """
    # ★2026-09-07: affine_grid + grid_sample(align_corners=False, zeros padding)を
    # numpy の座標計算 + scipy の map_coordinates(order=1)に置き換えた。torch は
    # 双線形の再標本化にしか使われておらず、torch を入れない環境(CI の py3.10 /
    # 3.12)でこの op が ImportError になっていた。規約はそのまま写した:
    # 出力ボクセル (d,h,w) の正規化座標は ((i+0.5)/N)*2-1、回転後に
    # (g+1)/2*N-0.5 で入力の画素座標へ戻す(align_corners=False の定義)。
    # grid の最終軸は (x, y, z) = (W, H, D) の順。torch 版との実測差は最大 7.6e-06。
    if str(device) not in ("cpu", "None") and not _HAS_TORCH:
        raise ValueError(
            "render_volume_projection: device=%r needs the optional 'torch' backend "
            "(the numpy path runs on the CPU only)" % (device,))
    from scipy.ndimage import map_coordinates
    v = np.asarray(vol, np.float32)
    D, H, W = v.shape
    az = np.radians(azimuth); el = np.radians(elevation)
    Ry = np.array([[np.cos(az), 0, np.sin(az)], [0, 1, 0], [-np.sin(az), 0, np.cos(az)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(el), -np.sin(el)], [0, np.sin(el), np.cos(el)]])
    Rm = (Rx @ Ry).astype(np.float64)
    d_i = (np.arange(D, dtype=np.float64) + 0.5) / D * 2.0 - 1.0
    h_i = (np.arange(H, dtype=np.float64) + 0.5) / H * 2.0 - 1.0
    w_i = (np.arange(W, dtype=np.float64) + 0.5) / W * 2.0 - 1.0
    nz, ny, nx = np.meshgrid(d_i, h_i, w_i, indexing="ij")
    gx = Rm[0, 0] * nx + Rm[0, 1] * ny + Rm[0, 2] * nz
    gy = Rm[1, 0] * nx + Rm[1, 1] * ny + Rm[1, 2] * nz
    gz = Rm[2, 0] * nx + Rm[2, 1] * ny + Rm[2, 2] * nz
    zin = (gz + 1.0) / 2.0 * D - 0.5
    yin = (gy + 1.0) / 2.0 * H - 0.5
    xin = (gx + 1.0) / 2.0 * W - 0.5
    # mode は **grid-constant**。素の "constant" は [0, N-1] の外を丸ごと cval に
    # するので、-1e-16 のような端の丸めが黒い列を作る(実測: 恒等変換で差 1.0)。
    # grid-constant は範囲外の**寄与だけ**を cval にするので、grid_sample の
    # zeros padding と同じ半画素の端の扱いになる。
    rot = map_coordinates(v.astype(np.float64), [zin, yin, xin], order=1,
                          mode="grid-constant", cval=0.0)
    if mode == "mip":
        return rot.max(axis=0).astype(np.float32)
    return rot.sum(axis=0).astype(np.float32)               # xray=Beer-Lambert 近似の積算


def render_shaded(normals_img, light=(0, 0, 1), ambient=0.1):
    """法線マップ (H,W,3) + 光源方向 → Lambertian 陰影画像(外観サンプル生成、光学と接続)。

    ``I = ambient + (1 − ambient)·clip(n·L̂, 0, 1)`` を ``(H, W)`` float64、値域 **[0, 1]** で返す。
    ``light`` は内部で単位化する(零ベクトルは 0 除算で NaN)が、**法線は単位化しない**(単位法線を
    渡す。``estimate_point_normals`` / ``normals_from_depth`` の出力は単位)。法線の成分順と
    ``light`` の成分順は揃える(既定 ``(0,0,1)`` は第 3 成分=カメラ向きを正面光とする規約)。
    光源と反対を向く面は ``ambient`` の値になる。最後の軸を法線とみなすので ``(N,3)`` の点ごとの
    法線でも動く。鏡面ハイライトは無い(``fresnel_reflectance`` / ``reflect`` で別途)。
    用途: ``photometric_stereo`` の検算(法線 → 画像の順方向)、外観検査の合成サンプル。
    """
    n = np.asarray(normals_img, float); L = np.asarray(light, float)
    L = L / np.linalg.norm(L)
    ndl = np.clip((n * L).sum(-1), 0, 1)
    return np.clip(ambient + (1 - ambient) * ndl, 0, 1)
