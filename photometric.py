# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""photometric — フォトメトリックステレオと法線積分(Physical AI 外観検査・形状復元)。

既知の複数光源方向で撮った Lambertian 画像から画素ごとに法線 + アルベドを復元し、
Frankot-Chellappa の FFT 積分で法線場から深度(高さ場)を復元する。すべて閉形式で
ground-truth 数値検証できる。差別化 = 検査(法線マップで微小凹凸を顕在化)+ 世界モデル/
検査サンプル生成(render_lambertian で逆に合成 = 順方向レンダでループを閉じる)。

honest な前提: Lambertian + 既知光源 + 影なし(N·L>0)で線形最小二乗が厳密。影(N·L<0)や
スペキュラは線形性を破るので、頑健版(median / RANSAC over lights)が別途要る。
"""
import numpy as np

import accel_seam


def _as_stack(images):
    a = np.asarray(images, dtype=np.float64)
    if a.ndim != 3:
        raise ValueError("images must have shape (N,H,W)")
    return a


#: 「アルベドが 0」とみなす相対床(入力の最大 |輝度| に対する比)。
_ALBEDO_RTOL = 1e-8


def _albedo_floor(intensities):
    """アルベドの退化判定の床 ``_ALBEDO_RTOL × max|I|``(2026-11-05 敵対的検証 第 2 巡 K4)。

    以前は絶対値 1e-8 で、強度を 1e-8 倍(物理単位の放射輝度では普通の桁)にすると
    全画素が「アルベド 0」扱いになり法線が (0, 0, 1) で返った(球で誤差 74.5°)。
    全画素が 0 なら床も 0(``albedo > 0`` の画素は無い)。
    """
    a = np.asarray(intensities, dtype=np.float64)
    if a.size == 0:
        return 0.0
    return _ALBEDO_RTOL * float(np.max(np.abs(a)))


def photometric_stereo(images, lights, mask=None, normalize=True, *,
                       lit_only=False, lit_thresh=1e-3):
    """Lambertian フォトメトリックステレオ: 既知光源方向の N 枚から法線とアルベドを復元。→ (normals HxWx3, albedo HxW)。

    I_n = albedo * max(N·L_n, 0)。各画素で g = albedo*N を最小二乗 g = pinv(L) @ I で解き、
    albedo=|g|, normal=g/|g|。N>=3 必要。albedo~0 や mask 外の画素は normal=(0,0,1)。
    「albedo~0」は入力の最大輝度に対する相対量(``1e-8 × max|I|``)。
    輝度の単位・桁(W/m² でも 8 bit でも)に依らず同じ画素が退化と判定される。
    normalize=True で光源ベクトルを単位方向に正規化(render_lambertian と同一規約 = アルベド絶対値が正しく出る)。
    強度重み付き光源を使うなら normalize=False にし、合成側も生ベクトルで揃えること。

    lit_only(2026-09-04 追加): **付着影(attached shadow)を外して解く**。モデルの
    max(·, 0) は非線形なので、N·L < 0 の観測(真の値は 0)を線形最小二乗にそのまま入れると
    解が偏る ―― 実測: 影も AO も無い球で中央値 **9°**、点灯している光源だけで解くと
    **0.000°**。既定は False(従来の挙動を変えない)。True にすると画素ごとに
    `I > lit_thresh` の光源だけを使って解き直す。**同じ点灯パターンの画素をまとめて**
    1 回の疑似逆行列で処理するので、追加コストは光源数ぶんのパターン数に比例する程度
    (6 灯なら最大 64 群)。点灯光源が 3 未満の画素は全光源の解に戻す(fail-open:
    解けない画素を NaN にするより、偏っていても値がある方が下流の積分が壊れない)。

    lit_thresh: 「点灯している」とみなす輝度の下限。撮影ノイズより上に置く。
    """
    I = _as_stack(images)                       # (N,H,W)
    L = np.asarray(lights, dtype=np.float64)    # (N,3)
    if L.ndim != 2 or L.shape[1] != 3:
        raise ValueError("lights must have shape (N,3)")
    N, H, W = I.shape
    if L.shape[0] != N:
        raise ValueError("images and lights count mismatch")
    if N < 3:
        raise ValueError("at least 3 light directions are required")
    if normalize:
        L = L / (np.linalg.norm(L, axis=1, keepdims=True) + 1e-12)
    Iv = I.reshape(N, H * W)                     # (N,P)
    Lpinv = np.linalg.pinv(L)                    # (3,N)  最小二乗
    gpu = accel_seam.kernel("photometric.solve")
    if gpu is not None and not lit_only:
        normals, albedo = gpu(Iv, Lpinv, H, W)
        if mask is not None:
            m = np.asarray(mask, bool)
            normals[~m] = (0.0, 0.0, 1.0)
            albedo[~m] = 0.0
        return normals.astype(np.float32), albedo.astype(np.float32)
    g = Lpinv @ Iv                              # (3,P)  = albedo*normal
    albedo = np.linalg.norm(g, axis=0)          # (P,)
    normals = np.zeros((3, H * W))
    floor = _albedo_floor(Iv)
    good = albedo > floor
    normals[:, good] = g[:, good] / albedo[good]
    normals[2, ~good] = 1.0
    if lit_only:
        # 点灯パターン(どの光源で明るかったか)ごとに画素をまとめて解き直す。
        lit = Iv > float(lit_thresh)                        # (N,P)
        n_lit = lit.sum(axis=0)
        pat = np.zeros(H * W, dtype=np.int64)
        for k in range(N):
            pat |= (lit[k].astype(np.int64) << k)
        for code in np.unique(pat[n_lit >= 3]):
            sel = np.flatnonzero((pat == code) & (n_lit >= 3))
            if sel.size == 0:
                continue
            use = [k for k in range(N) if (int(code) >> k) & 1]
            if len(use) == N:
                continue                                     # 全灯 = 既に解けている
            Lsub = L[use]
            if np.linalg.matrix_rank(Lsub) < 3:
                continue                                     # 同一平面上の 3 灯などは解けない
            g[:, sel] = np.linalg.pinv(Lsub) @ Iv[np.ix_(use, sel)]
        albedo = np.linalg.norm(g, axis=0)
        normals = np.zeros((3, H * W))
        good = albedo > floor
        normals[:, good] = g[:, good] / albedo[good]
        normals[2, ~good] = 1.0

    normals = normals.T.reshape(H, W, 3)
    albedo = albedo.reshape(H, W)
    if mask is not None:
        m = np.asarray(mask, bool)
        normals[~m] = (0.0, 0.0, 1.0)
        albedo[~m] = 0.0
    return normals.astype(np.float32), albedo.astype(np.float32)


def normals_to_gradients(normals):
    """法線 (...,3) → 勾配 (p,q)=(dz/dx, dz/dy)。n ∝ (-p,-q,1) ゆえ p=-nx/nz, q=-ny/nz。"""
    n = np.asarray(normals, float)
    nz = n[..., 2]
    # ★2026-10-02: 以前は ``np.sign(nz) * 1e-6 + 1e-12`` で、nz がちょうど 0(真横を向く法線)のとき
    #   np.sign(0) = 0 になり分母が 1e-12 → p = -1e12 を返していた(±1e-6 で抑えるつもりが効かない)。
    #   0 は正の側に寄せる。真横の法線の勾配は本来無限大で、ここでは |p|, |q| ≤ 1e6 に抑えた値になる。
    nz = np.where(np.abs(nz) < 1e-6, np.where(nz < 0, -1e-6, 1e-6), nz)
    p = -n[..., 0] / nz
    q = -n[..., 1] / nz
    return p, q


def integrate_gradients(p, q):
    """勾配場 (p,q) → 高さ場 z を Frankot-Chellappa(FFT)で最小二乗積分。→ z HxW(平均0基準)。

    Z_hat(wx,wy) = (-j wx P_hat - j wy Q_hat) / (wx^2 + wy^2)、原点=0。周期境界前提ゆえ端に歪み。
    ★周期境界の解は勾配の平均(直流 = 全体の傾き)を表せず、黙って 0 にする: 傾き 0.2 の平面は
    水平に戻る。これは素の Frankot-Chellappa の性質としてそのまま残す(周期的な面で厳密に戻ること、
    鏡像拡張した ``sfpolar.sfp_height`` の土台であることを保つため)。傾きを残したい法線は
    :func:`integrate_normals`(平均の勾配の一次の項を足し戻す)へ。
    """
    p = np.asarray(p, float)
    q = np.asarray(q, float)
    H, W = p.shape
    wy = (2.0 * np.pi * np.fft.fftfreq(H))[:, None]
    wx = (2.0 * np.pi * np.fft.fftfreq(W))[None, :]
    P = np.fft.fft2(p)
    Q = np.fft.fft2(q)
    denom = wx ** 2 + wy ** 2
    denom[0, 0] = 1.0
    Z = (-1j * wx * P - 1j * wy * Q) / denom
    Z[0, 0] = 0.0
    z = np.real(np.fft.ifft2(Z))
    return (z - z.mean()).astype(np.float64)


def integrate_normals(normals, mask=None):
    """法線場 → 高さ場 z を Frankot-Chellappa 積分。→ z HxW(定数分の自由度あり・平均0基準)。

    手順: 法線 ``(H,W,3)`` を勾配 ``p = -nx/nz``、``q = -ny/nz`` に直し(``|nz| < 1e-6`` の
    画素は nz を ±1e-6 に置き換えて零割を避ける)、FFT 領域で最小二乗解
    ``Z(wx,wy) = (-j·wx·P - j·wy·Q) / (wx² + wy²)`` を求め(直流成分は 0)、逆変換して
    平均を 0 に引く。``mask`` (bool HxW) を与えると mask 外の勾配を 0 にしてから積分する
    (その領域は平坦として扱われる)。返り値は float64 の ``(H,W)``。
    注意点:
    - 周期境界を仮定するため、画像の上下・左右がつながるように端が歪む(全体の傾きは下の★で戻す)。
    - 絶対高さは決まらない(平均 0)。格子間隔 1 画素で積分するので ``z`` も画素単位の
      高さになり、実寸には画素ピッチを掛ける。
    - ``nz ≈ 0``(輪郭付近・視線に平行な面)は勾配が発散し、波打ちを周囲へ広げる。
      ``mask`` で除くか法線を事前に平滑する。
    ``surface_normals`` が逆変換で、``photometric_stereo`` の法線をここへ渡すと形状(高さ場)が得られる。
    空の入力(``normals`` が 0 要素)は ValueError。

    ★全体の傾き(2026-11-09): 周期境界の Frankot-Chellappa は勾配の平均(直流)を 0 に落とし、
    傾いた平面を水平に戻していた(傾き 0.2 px/px → 復元 0.0000、rms 5.5 px)。積分の後に平均の
    勾配の一次の項 ``mean(p)·(x − x̄) + mean(q)·(y − ȳ)`` を足し戻す(平均は ``mask`` 外の 0 も含む
    格子全体)。傾いた平面は厳密に戻り、平均の勾配が 0 の面(マスクした球など)は丸め屑しか動かない。
    素の周期解が要るときは :func:`integrate_gradients`。
    ★足し戻す傾きは**平均**なので外れ値に弱い(独立レビュー 2026-11-09): 平らな面に、同じ向きに大きく
    傾いた法線(nz 0.002、1e-3 の切りは通る)が 20 画素あるだけで rms 誤差 10.7 → 27.9 px(2.6 倍悪化)。
    輪郭の片側に並ぶ斜めの法線は実データで普通に出るので、``mask`` で外してから渡す。中央値などの
    頑健な推定に替えないのは、段差の壁のように「少数の大きな勾配」が正しい傾きを担う面で傾きを失うため。
    もう 1 つの限界: 傾きは**測れた法線**の平均で、照度差ステレオが撮れない段差の壁などは入らない ——
    段差のある部品では足し戻した傾きが真値の平均勾配と違う(3-D 方式比べの PoC で −0.066〜−0.084
    vs 真値 +0.0125 px/px)。
    ★入力の門: ``(H,W,3)`` 以外・非有限の法線(NaN 1 画素で FFT が全画素を NaN にしていた)は
    ValueError。``|nz| < 1e-3``(勾配が 1000 を超える、輪郭・視線に平行な面)の画素は勾配を 0 に
    して積分から外し、件数を RuntimeWarning で知らせる(nz=0 の 1 画素が高さを 2.3e5 px 振っていた)。
    """
    if np.asarray(normals).size == 0:   # ★2026-10-11 台帳の空入力の門: 生の例外でなく名指しで拒否
        raise ValueError("integrate_normals: normals is empty — pass at least one element")
    n = np.asarray(normals, dtype=np.float64)
    if n.ndim != 3 or n.shape[-1] != 3:
        raise ValueError("integrate_normals: normals must be (H, W, 3), got shape %s" % (n.shape,))
    if not np.isfinite(n).all():
        raise ValueError("integrate_normals: normals has %d non-finite values (nan/inf) — fill or mask "
                         "them before integrating (one NaN turns every height NaN through the FFT)"
                         % int(np.count_nonzero(~np.isfinite(n))))
    p, q = normals_to_gradients(n)
    steep = np.abs(n[..., 2]) < 1e-3
    if mask is not None:
        m = np.asarray(mask, bool)
        if m.shape != n.shape[:2]:
            raise ValueError("integrate_normals: mask shape %s does not match normals %s"
                             % (m.shape, n.shape[:2]))
        steep &= m
        keep = m & ~steep
    else:
        keep = ~steep
    n_steep = int(np.count_nonzero(steep))
    if n_steep:
        import warnings  # noqa: PLC0415
        warnings.warn("integrate_normals: %d pixel(s) have |nz| < 1e-3 (slope > 1000); their gradient "
                      "is set to 0 and they are left out of the integration" % n_steep,
                      RuntimeWarning, stacklevel=2)
    if mask is not None or n_steep:
        p = np.where(keep, p, 0.0)
        q = np.where(keep, q, 0.0)
    z = integrate_gradients(p, q)
    H, W = z.shape
    pm, qm = float(np.mean(p)), float(np.mean(q))
    x = np.arange(W, dtype=np.float64) - (W - 1) / 2.0
    y = np.arange(H, dtype=np.float64) - (H - 1) / 2.0
    z = z + pm * x[None, :] + qm * y[:, None]
    return (z - z.mean()).astype(np.float64)


def surface_normals(z):
    """高さ場 z(HxW)→ 単位法線 (H,W,3)。n ∝ (-dz/dx, -dz/dy, 1)。深度→法線の順変換。

    ``np.gradient`` の中心差分(端は片側差分)で行方向の ``dz/dy`` と列方向の ``dz/dx`` を
    取り、``n = (-dz/dx, -dz/dy, 1)`` を長さ 1 に正規化する(``+1e-12`` で零割を避ける)。
    格子間隔を 1 画素とみなすので、``z`` の単位が画素と異なる(mm 等)場合は事前に
    ``z / 画素ピッチ`` へ換算しないと傾きが実際より強く/弱く出る。法線の z 成分は常に正
    (カメラ向き)。返り値は float32 の ``(H,W,3)``、第 3 軸は (x, y, z) 成分で x は列方向、
    y は行方向。入力検証は無く、2-D 以外を渡すと ``np.gradient`` の展開で失敗する。
    ``integrate_normals`` の逆変換にあたり、``photometric_stereo`` の出力と同じ法線規約
    なので、そのまま ``render_lambertian`` に渡して陰影画像を合成できる。
    """
    zy, zx = np.gradient(np.asarray(z, float))
    n = np.stack([-zx, -zy, np.ones_like(zx)], axis=-1)
    n /= (np.linalg.norm(n, axis=-1, keepdims=True) + 1e-12)
    return n.astype(np.float32)


def render_lambertian(normals, albedo, light, ambient=0.0):
    """法線 + アルベド + 光源方向 → Lambertian 画像(検査サンプル生成 / GT 検証 / 逆レンダの順方向)。→ HxW。

    ``I = albedo * (max(n·L, 0) + ambient)``。``light`` は (3,) の光源方向ベクトルで内部で
    単位長に正規化する(長さは強度として効かない)。``n·L < 0`` の画素は 0 にクリップ
    される(付着影)。``ambient`` は法線に依らず一様に足す定数で、アルベドは掛かる
    (既定 0)。``normals`` は ``(H,W,3)`` の法線(単位長を仮定し正規化しない)、``albedo``
    は ``(H,W)`` またはブロードキャスト可能な配列・スカラ。返り値は float32 の ``(H,W)``。
    上限は ``albedo * (1 + ambient)`` で、[0,1] へのクリップはしない。入力検証は無い。
    ``photometric_stereo`` の順方向モデルそのもの(光源正規化の規約は ``normalize=True``
    に対応)なので、復元した法線・アルベドから再合成して元画像と比べる往復検証に使える。
    鏡面・相互反射・投影影(cast shadow)は含まない。

    空の入力(``normals`` が 0 要素)は ValueError。
    """
    if (len(normals) if isinstance(normals, (list, tuple)) else np.asarray(normals).size) == 0:   # ★2026-10-12 空入力の方針 A: 黙って値を返さず、何が空かを名指しで拒否
        raise ValueError("render_lambertian: normals is empty — pass at least one element")
    n = np.asarray(normals, float)
    L = np.asarray(light, float)
    L = L / (np.linalg.norm(L) + 1e-12)
    ndotl = np.clip(n[..., 0] * L[0] + n[..., 1] * L[1] + n[..., 2] * L[2], 0.0, None)
    a = np.asarray(albedo, float)
    return (a * (ndotl + ambient)).astype(np.float32)


def synthesize_ps_images(normals, albedo, lights, ambient=0.0):
    """既知の法線 + アルベド + 光源群 → フォトメトリックステレオ入力画像列 (N,H,W)。テスト / サンプル生成用。"""
    L = np.asarray(lights, float)
    return np.stack([render_lambertian(normals, albedo, L[i], ambient) for i in range(L.shape[0])], axis=0)


def angular_error_deg(n_a, n_b):
    """2 つの法線場の画素ごと角度誤差(度)。→ HxW。検証用。

    角は atan2(|a × b|, a·b) で取る(正規化は要らない)。長さ 0 のベクトルを含む画素は従来どおり 90°。
    ★2026-10-05 まで acos(â·b̂) で、さらに正規化の分母に足した 1e-12 が内積を 1 − 2e-12 にずらしていたため、平行に近い組は
    約 1.15e-4° の床に張り付いた(1e-7° も 1e-5° も 1.146e-4° と答えた)。acos は 1 の近くで √ε の床を持つ —— 小さい角は外積の大きさで読む。"""
    a = np.asarray(n_a, float)
    b = np.asarray(n_b, float)
    cr = np.linalg.norm(np.cross(a, b), axis=-1)
    dt = np.sum(a * b, axis=-1)
    zero = (np.linalg.norm(a, axis=-1) == 0.0) | (np.linalg.norm(b, axis=-1) == 0.0)
    return np.where(zero, 90.0, np.degrees(np.arctan2(cr, dt)))
