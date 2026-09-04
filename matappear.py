# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""matappear — 構造色と異方性反射(材質の「見え方」を波長から作る)。

動機(2026-09-04、ユーザー「鏡面とかガラスとかは作れないの?」「CD の面みたいな虹色は?」
「ヘアライン入りのは?」): fullseye のレンダラはラスタライザで、鏡・ガラスは光線追跡が要る。
一方で **CD の虹・シャボン玉の膜・ヘアライン(異方性ハイライト)は光線追跡を必要としない** ――
どれも「面の微細構造が波長ごとに違う反射を返す」だけだからである。この 3 つは色を
*絵の具として塗る*のではなく、**回折・干渉・微小面の統計から波長ごとに計算して
CIE の等色関数で RGB に落とす**。だから角度を変えれば色が変わり、格子ピッチを変えれば
虹の開き方が変わる ―― 「それらしい色」ではなく物理量の関数になっている。

内容(6 op):
  * ``cie_xyz_from_wavelength`` — CIE 1931 等色関数 x̄ȳz̄(多ローブ Gauss 近似)
  * ``spectrum_to_srgb``        — 分光反射率 × D65 → XYZ → 線形 sRGB
  * ``thin_film_reflectance``   — 薄膜干渉の分光反射率(Airy、2 光束)
  * ``grating_wavelengths``     — 回折格子の式 d(sinθ_out − sinθ_in) = mλ
  * ``grating_rgb``             — 法線・光源・視線 → CD 面の虹色 (H,W,3)
  * ``thin_film_rgb``           — 同・シャボン膜/陽極酸化被膜の干渉色 (H,W,3)
  * ``ward_anisotropic``        — ヘアライン(異方性)ハイライトの分布関数

来歴(公開文献のみ):
  * Wyman, Sloan & Shirley, *JCGT* 2(2) 2013 — CIE 1931 等色関数の多ローブ Gauss 近似。
  * Born & Wolf, *Principles of Optics* §1.6(薄膜の Airy 公式)/ §8.6(回折格子)。
  * Ward, *SIGGRAPH* 1992 — 異方性反射モデル(楕円ガウス微小面)。
  * Stam, *SIGGRAPH* 1999 — 回折による光沢(CD の虹の由来)。

規約:
  * 波長は **nm**(可視域 360–830 を既定の積分範囲にする)。
  * 返す RGB は **線形 sRGB**(ガンマ前)。レンダラのトーンマップに渡す前提。
  * 方向ベクトルは面から外向き(法線・光源方向・視線方向)で、いずれも正規化して扱う。
"""
from __future__ import annotations

import numpy as np

#: CIE 1931 2° 等色関数の多ローブ Gauss 近似(Wyman et al. 2013, Table 1)。
#: 各行 (振幅, 中心 nm, 左側 σ, 右側 σ) の「片側幅が違うガウス」。
_CMF_X = ((1.056, 599.8, 37.9, 31.0), (0.362, 442.0, 16.0, 26.7), (-0.065, 501.1, 20.4, 26.2))
_CMF_Y = ((0.821, 568.8, 46.9, 40.5), (0.286, 530.9, 16.3, 31.1))
_CMF_Z = ((1.217, 437.0, 11.8, 36.0), (0.681, 459.0, 26.0, 13.8))

#: sRGB が基準にする白色点 D65 の XYZ(Y=1 正規化、IEC 61966-2-1)。
_D65_XYZ = np.array([0.95047, 1.00000, 1.08883])

#: 線形 sRGB の変換行列(IEC 61966-2-1, D65)。
_XYZ_TO_SRGB = np.array([[3.2406, -1.5372, -0.4986],
                         [-0.9689, 1.8758, 0.0415],
                         [0.0557, -0.2040, 1.0570]])


def _lobes(nm: np.ndarray, lobes) -> np.ndarray:
    out = np.zeros_like(nm)
    for amp, mu, s1, s2 in lobes:
        t = (nm - mu) * np.where(nm < mu, 1.0 / s1, 1.0 / s2)
        out = out + amp * np.exp(-0.5 * t * t)
    return out


def _as_nm(nm, op: str) -> np.ndarray:
    a = np.asarray(nm, dtype=np.float64)
    if a.size == 0:
        raise ValueError(f"{op}: wavelength array is empty")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{op}: wavelength contains non-finite values")
    if np.any(a <= 0.0):
        raise ValueError(f"{op}: wavelength must be positive [nm]")
    return a


def _unit(v, name: str, op: str) -> np.ndarray:
    a = np.asarray(v, dtype=np.float64)
    if a.shape[-1] != 3 or not np.all(np.isfinite(a)):
        raise ValueError(f"{op}: {name} must be a finite vector/array with last axis 3")
    n = np.linalg.norm(a, axis=-1, keepdims=True)
    if np.any(n < 1e-12):
        raise ValueError(f"{op}: {name} contains a zero-length direction")
    return a / n


def _tangent_field(tangent, shape, op: str) -> np.ndarray:
    """接線を (H,W,3) の**場**に正規化する。3 ベクトルなら全画素へ広げる。

    2026-09-04 に場を受けられるようにした理由: 加工面の筋は一定方向とは限らない ――
    旋盤の削り目は同心円、ローレットは交差、ビーズブラストは無方向。定ベクトルしか
    受けないと「ヘアラインだけ」しか作れず、`metalfinish` の族が成立しない。
    """
    a = np.asarray(tangent, dtype=np.float64)
    if a.ndim == 1:
        return _unit(a, "tangent", op)[None, None, :]
    if a.shape != shape:
        raise ValueError(f"{op}: tangent field shape {a.shape} does not match normals {shape}")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{op}: tangent field contains non-finite values")
    n = np.linalg.norm(a, axis=-1, keepdims=True)
    if np.any(n < 1e-12):
        raise ValueError(f"{op}: tangent field contains a zero-length direction")
    return a / n


def _normal_map(normals, op: str):
    """(H,W,3) 法線マップ → 単位法線とマスク(長さ 0 = 背景)。

    ★ 非有限値は **fail-closed で断る**(2026-09-04、敵対的検証で摘発)。以前は
    NaN/Inf をそのまま通しており、`ward_anisotropic` / `grating_rgb` / `oren_nayar` /
    `finish_shade` など**この入口を共有する外観 op すべてが、例外を出さずに NaN 画像を
    返していた**。下流(トーンマップや保存)は NaN を黒や 0 に丸めるので、
    「暗いだけの絵」になって原因が見えなくなる ―― 壊れた入力は入口で止める。
    背景は長さ 0 のベクトルで表すという約束なので、NaN で表す必要は無い。
    """
    a = np.asarray(normals, dtype=np.float64)
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError(f"{op}: normals must be an (H, W, 3) map: got shape={a.shape}")
    if a.size and not np.all(np.isfinite(a)):
        bad = int((~np.isfinite(a)).sum())
        raise ValueError(f"{op}: normals contain {bad} non-finite value(s) "
                         "(NaN/Inf); background must be the zero vector, not NaN")
    n = np.linalg.norm(a, axis=-1, keepdims=True)
    mask = n[..., 0] > 1e-9
    return np.divide(a, np.maximum(n, 1e-12)), mask


# --------------------------------------------------------------------------- #
# 1. 等色関数と分光 → sRGB                                                      #
# --------------------------------------------------------------------------- #
def cie_xyz_from_wavelength(nm) -> np.ndarray:
    """波長 [nm] → CIE 1931 2° 等色関数 (x̄, ȳ, z̄)。入力形状 + 末尾 3 の配列を返す。

    Wyman, Sloan & Shirley (JCGT 2013) の多ローブ Gauss 近似。表引きより粗いが、
    可視域全体で表の値に対し最大誤差 ~1% で、**補間も外挿も要らない**(閉じた式なので
    任意の波長格子でそのまま評価できる)。可視域の外は自然に 0 へ落ちる。

    nm: スカラまたは配列(正、単位 nm)。
    返り値: (..., 3) の float64。
    """
    a = _as_nm(nm, "cie_xyz_from_wavelength")
    return np.stack([_lobes(a, _CMF_X), _lobes(a, _CMF_Y), _lobes(a, _CMF_Z)], axis=-1)


def _d65(nm: np.ndarray) -> np.ndarray:
    """D65 の相対分光分布(平滑近似)。絶対値は正規化で消えるので形だけ使う。"""
    return (1.0 + 0.30 * np.exp(-0.5 * ((nm - 460.0) / 55.0) ** 2)
            - 0.10 * np.exp(-0.5 * ((nm - 590.0) / 45.0) ** 2))


def spectrum_to_srgb(nm, reflectance, illuminant=None) -> np.ndarray:
    """分光反射率 → **線形 sRGB**(ガンマ前)。白い面(反射率 1)が (1,1,1) になる正規化。

    nm:           波長格子 (K,) [nm]。単調増加。
    reflectance:  (..., K) の分光反射率(0–1 想定、範囲外でも計算は通る)。
    illuminant:   (K,) の光源分光分布。既定は D65 の平滑近似。

    返り値: (..., 3) の線形 sRGB。**負の値はクリップしない** — 色域外は負で返るのが正直で、
    クリップしたい呼び手が明示的にやる(黙って丸めると「表現できない色」が見えなくなる)。

    正規化: 反射率 1 の完全拡散面が sRGB の基準白 D65 に落ちるよう、同じ光源・同じ格子で
    計算した白の XYZ で**成分ごとに**割る(von Kries 型の白色順応の最小形)。実測で
    反射率 1 → (1.000000, 1.000000, 0.999999)、0.5 → 0.5。したがって**絶対輝度ではなく
    相対値**であり、レンダラの露出に掛ける使い方を想定している。
    """
    w = _as_nm(nm, "spectrum_to_srgb")
    if w.ndim != 1 or w.size < 2:
        raise ValueError(f"spectrum_to_srgb: nm must be a 1-D grid of >=2 points: got shape={w.shape}")
    if np.any(np.diff(w) <= 0):
        raise ValueError("spectrum_to_srgb: nm must be strictly increasing")
    r = np.asarray(reflectance, dtype=np.float64)
    if r.ndim == 0:
        # ★ 0 次元(スカラ)を渡すと `r.shape[-1]` が**素の IndexError** を投げていた
        #   (2026-09-04 の敵対的監査で摘発)。分光反射率は最低でも波長軸を持つ ――
        #   スカラは「波長ごとの値」ではないので、番人で明示的に断る。
        raise ValueError("spectrum_to_srgb: reflectance must have a wavelength axis "
                         "(got a 0-d scalar); pass an array whose last axis is len(nm)")
    if r.shape[-1] != w.size:
        raise ValueError(f"spectrum_to_srgb: reflectance last axis {r.shape[-1]} != len(nm) {w.size}")
    ill = _d65(w) if illuminant is None else np.asarray(illuminant, dtype=np.float64)
    if ill.shape != w.shape:
        raise ValueError(f"spectrum_to_srgb: illuminant shape {ill.shape} != nm shape {w.shape}")
    cmf = cie_xyz_from_wavelength(w)                     # (K, 3)
    dw = np.gradient(w)
    weight = (ill * dw)[:, None] * cmf                   # (K, 3)
    white = weight.sum(axis=0)                           # 反射率 1 の XYZ
    # 白色点合わせ: 反射率 1 の面が sRGB の基準白 D65 に落ちるよう XYZ を成分ごとに
    # 規格化する(von Kries 型の順応を XYZ で行う最小形)。これを Y だけの正規化に
    # すると、光源の分光形の粗さがそのまま**白の色かぶり**として出る ―― 実測: 平坦な
    # 反射率 1 が (1.02, 0.98, 1.17) になり、青に 17% 転んでいた。
    xyz = np.tensordot(r, weight, axes=(-1, 0)) * (_D65_XYZ / np.maximum(white, 1e-30))
    return xyz @ _XYZ_TO_SRGB.T


# --------------------------------------------------------------------------- #
# 2. 薄膜干渉                                                                   #
# --------------------------------------------------------------------------- #
def thin_film_reflectance(nm, thickness_nm=350.0, n_film=1.33, n_sub=1.0,
                          cos_theta=1.0, n_out=1.0) -> np.ndarray:
    """薄膜(厚さ d、屈折率 n_film)の分光反射率。Airy(多重反射)の閉じた式。

    nm:           波長 [nm] (配列可)。
    thickness_nm: 膜厚 [nm]。シャボン玉なら 200–800、陽極酸化被膜なら 50–300。
    n_film/n_sub/n_out: 膜 / 基板 / 入射側の屈折率(実数、吸収なし)。
    cos_theta:    入射側での入射角の cos(配列可、nm とブロードキャストできる形)。

    返り値: 反射率 R(0–1)。nm と cos_theta のブロードキャスト形。

    物理: 膜内の伝搬による位相差 δ = 2π·(2 n_film d cosθ_film)/λ。境界のフレネル係数
    (s 偏光と p 偏光の平均 = 無偏光)を r1, r2 として R = |r1 + r2 e^{-iδ}|² / |1 + r1 r2 e^{-iδ}|²。
    λ/4 の奇数倍で反射が極大(n_film > n_sub のとき)になり、**厚みを変えると色が動く**のが
    シャボン玉の色。膜厚 0 では R が基板単体のフレネル反射に一致する(テストで確認)。
    """
    w = _as_nm(nm, "thin_film_reflectance")
    d = float(thickness_nm)
    if d < 0.0 or not np.isfinite(d):
        raise ValueError(f"thin_film_reflectance: thickness_nm must be >= 0: got {thickness_nm}")
    n0, n1, n2 = float(n_out), float(n_film), float(n_sub)
    for nm_, v in (("n_out", n0), ("n_film", n1), ("n_sub", n2)):
        if not np.isfinite(v) or v <= 0.0:
            raise ValueError(f"thin_film_reflectance: {nm_} must be a positive real index: got {v}")
    c0 = np.clip(np.asarray(cos_theta, dtype=np.float64), 1e-9, 1.0)
    sin0 = np.sqrt(np.maximum(1.0 - c0 ** 2, 0.0))
    sin1 = np.clip(n0 * sin0 / n1, 0.0, 1.0)             # Snell
    c1 = np.sqrt(np.maximum(1.0 - sin1 ** 2, 0.0))
    sin2 = np.clip(n0 * sin0 / n2, 0.0, 1.0)
    c2 = np.sqrt(np.maximum(1.0 - sin2 ** 2, 0.0))

    def fresnel(na, ca, nb, cb):
        rs = (na * ca - nb * cb) / np.maximum(na * ca + nb * cb, 1e-30)
        rp = (nb * ca - na * cb) / np.maximum(nb * ca + na * cb, 1e-30)
        return rs, rp

    r1s, r1p = fresnel(n0, c0, n1, c1)
    r2s, r2p = fresnel(n1, c1, n2, c2)
    delta = 4.0 * np.pi * n1 * d * c1 / w                # 2·(2π n d cosθ)/λ
    ph = np.exp(-1j * delta)
    out = 0.0
    for r1, r2 in ((r1s, r2s), (r1p, r2p)):
        num = r1 + r2 * ph
        den = 1.0 + r1 * r2 * ph
        out = out + np.abs(num / den) ** 2
    return 0.5 * out                                     # 無偏光 = s と p の平均


# --------------------------------------------------------------------------- #
# 3. 回折格子(CD の虹)                                                         #
# --------------------------------------------------------------------------- #
def grating_wavelengths(pitch_um, sin_in, sin_out, orders=(1, 2, 3)) -> np.ndarray:
    """回折格子の式 d(sinθ_out − sinθ_in) = mλ を λ について解く。

    pitch_um: 溝間隔 d [µm]。CD は 1.6、DVD は 0.74(公開規格値)。
    sin_in / sin_out: 入射 / 出射方向の格子面内成分の sin(配列可、ブロードキャスト)。
    orders:   次数 m のシーケンス(0 は無限大になるので除外する)。

    返り値: (..., len(orders)) の波長 [nm]。可視域外の解もそのまま返す(呼び手が
    等色関数に通せば自動的に 0 になる — ここで黙って切ると「なぜ色が出ないか」が消える)。
    """
    d = float(pitch_um)
    if not np.isfinite(d) or d <= 0.0:
        raise ValueError(f"grating_wavelengths: pitch_um must be positive: got {pitch_um}")
    m = np.asarray(orders, dtype=np.float64)
    if m.ndim != 1 or m.size == 0:
        raise ValueError("grating_wavelengths: orders must be a non-empty 1-D sequence")
    if np.any(m == 0):
        raise ValueError("grating_wavelengths: order 0 has no wavelength solution (m=0 => any λ)")
    si = np.asarray(sin_in, dtype=np.float64)
    so = np.asarray(sin_out, dtype=np.float64)
    diff = (so - si)[..., None]
    return 1000.0 * d * diff / m                          # µm → nm


def grating_rgb(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0), tangent=(1.0, 0.0, 0.0),
                pitch_um=1.6, orders=(1, 2), strength=1.0, width_nm=60.0) -> np.ndarray:
    """法線マップ + 光源 + 視線 → **回折による虹色** (H, W, 3) の線形 sRGB。

    CD/DVD の記録トラックは等間隔の溝 = 反射型回折格子である。溝に直交する方向の
    「入射と出射の sin の差」が波長を選ぶので、面の向きが変わると色が変わる。

    normals: (H, W, 3) 法線マップ(長さ 0 = 背景 → 0 を返す)。
    light / view: 面から光源 / 視点への方向(3,)。
    tangent: 溝の方向(3,)。法線に射影して面内成分を使う。
    pitch_um: 溝間隔 [µm] (CD 1.6 / DVD 0.74 / BD 0.32)。
    orders:   使う回折次数(内部で ±両方を使う — 対称な溝は両側へ回折する)。
    strength: 全体の強さ。
    width_nm: 1 本の回折線に与える波長方向の幅 [nm] (有限のスポットサイズ・帯域の効果)。

    返り値: (H, W, 3) 線形 sRGB(負値は残す = 色域外がそのまま見える)。
    """
    op = "grating_rgb"
    N, mask = _normal_map(normals, op)
    L = _unit(light, "light", op)
    V = _unit(view, "view", op)
    T = _tangent_field(tangent, N.shape, op)
    # 溝方向を面内へ落とし、それに直交する面内軸(= 分散が起きる向き)を作る
    t_in = T - N * np.sum(N * T, axis=-1, keepdims=True)
    nt = np.linalg.norm(t_in, axis=-1, keepdims=True)
    t_in = np.divide(t_in, np.maximum(nt, 1e-12))
    disp = np.cross(N, t_in)                              # 格子ベクトル方向(面内・溝に直交)
    sin_in = np.sum(disp * L[None, None, :], axis=-1)
    sin_out = np.sum(disp * V[None, None, :], axis=-1)
    # ★ 実際の格子は**両側**に回折する(溝が対称なら ±m の効率はほぼ同じ)。ここで
    # ±両方を入れないと、光源と視線の位置関係によっては解が全部負になり、
    # 「正の λ だけ残す」フィルタが**全部落として真っ黒**になる。実測: 溝に直交して
    # 照らした CD(Δsin = −0.55)は m=+1,+2 が λ<0 で全消え、m=−2 の 440 nm が本命だった。
    ords = tuple(int(o) for o in orders)
    ords = ords + tuple(-o for o in ords)
    lam = grating_wavelengths(pitch_um, sin_in, sin_out, ords)     # (H, W, 2M) [nm]

    grid = np.linspace(380.0, 720.0, 69)
    # 各次数の解を「幅 width_nm のガウス線」として分光反射率に足す
    spd = np.zeros(N.shape[:2] + grid.shape)
    for k in range(lam.shape[-1]):
        c = lam[..., k]
        ok = np.isfinite(c) & (c > 0)
        spd += np.where(ok[..., None],
                        np.exp(-0.5 * ((grid[None, None, :] - c[..., None]) / width_nm) ** 2), 0.0)
    rgb = spectrum_to_srgb(grid, spd) * float(strength)
    return rgb * mask[..., None]


def thin_film_rgb(normals, view=(0.0, 0.0, 1.0), thickness_nm=350.0, n_film=1.33,
                  n_sub=1.0, strength=1.0) -> np.ndarray:
    """法線マップ + 視線 → **薄膜干渉の色** (H, W, 3) の線形 sRGB。

    面が視線に対して寝ているほど膜内の光路が伸び、色が短波長側へ動く ―― シャボン玉や
    焼けたチタンの色が縁で変わるのはこれ。角度依存は cosθ = |n·v| から出す。

    normals / view: (H,W,3) 法線マップ / 面から視点への方向。
    thickness_nm / n_film / n_sub: :func:`thin_film_reflectance` と同じ。
    strength: 全体の強さ。
    """
    op = "thin_film_rgb"
    N, mask = _normal_map(normals, op)
    V = _unit(view, "view", op)
    cos_t = np.abs(np.sum(N * V[None, None, :], axis=-1))
    grid = np.linspace(380.0, 720.0, 69)
    R = thin_film_reflectance(grid[None, None, :], thickness_nm, n_film, n_sub,
                              cos_theta=cos_t[..., None])
    return spectrum_to_srgb(grid, R) * float(strength) * mask[..., None]


# --------------------------------------------------------------------------- #
# 4. 異方性(ヘアライン)                                                        #
# --------------------------------------------------------------------------- #
def ward_anisotropic(normals, light=(0.0, 0.0, 1.0), view=(0.0, 0.0, 1.0),
                     tangent=(1.0, 0.0, 0.0), alpha_x=0.30, alpha_y=0.03) -> np.ndarray:
    """Ward の異方性反射(楕円ガウス微小面)。ヘアライン仕上げの**伸びたハイライト**。

    normals: (H, W, 3) 法線マップ。
    light / view: 面から光源 / 視点への方向(3,)。
    tangent: 研磨の筋の方向(3,)。面内へ射影して使う。
    alpha_x / alpha_y: 筋方向 / 直交方向の粗さ。**この比がハイライトの伸び**になる
                       (等方なら円、alpha_x >> alpha_y なら筋に沿って伸びた線)。

    返り値: (H, W) の鏡面反射強度(非負)。背景は 0。

    式: ρ = exp(−tan²δ·(cos²φ/αx² + sin²φ/αy²)) / (4π αx αy √(cosθi cosθo)) で、
    δ はハーフベクトルと法線の角、φ は接線からの方位角(Ward 1992)。
    """
    op = "ward_anisotropic"
    N, mask = _normal_map(normals, op)
    L = _unit(light, "light", op)
    V = _unit(view, "view", op)
    T = _tangent_field(tangent, N.shape, op)
    ax, ay = float(alpha_x), float(alpha_y)
    if not (np.isfinite(ax) and np.isfinite(ay)) or ax <= 0 or ay <= 0:
        raise ValueError(f"ward_anisotropic: alpha_x/alpha_y must be positive: got {ax}, {ay}")

    ndl = np.sum(N * L[None, None, :], axis=-1)
    ndv = np.sum(N * V[None, None, :], axis=-1)
    H = L[None, None, :] + V[None, None, :]
    H = H / np.maximum(np.linalg.norm(H, axis=-1, keepdims=True), 1e-12)
    ndh = np.clip(np.sum(N * H, axis=-1), 1e-9, 1.0)

    x = T - N * np.sum(N * T, axis=-1, keepdims=True)
    x = x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), 1e-12)
    y = np.cross(N, x)
    hx = np.sum(H * x, axis=-1)
    hy = np.sum(H * y, axis=-1)

    tan2 = (1.0 - ndh ** 2) / (ndh ** 2)
    denom = np.maximum(1.0 - ndh ** 2, 1e-18)
    cos2phi = hx ** 2 / denom
    sin2phi = hy ** 2 / denom
    expo = -tan2 * (cos2phi / (ax * ax) + sin2phi / (ay * ay))
    norm = 1.0 / (4.0 * np.pi * ax * ay * np.sqrt(np.maximum(ndl * ndv, 1e-12)))
    lobe = np.exp(np.clip(expo, -80.0, 0.0)) * norm
    lit = (ndl > 0) & (ndv > 0) & mask
    return np.where(lit, lobe, 0.0)
