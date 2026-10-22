# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""semsim —— 走査電子顕微鏡(SEM)像の物理モデルで、縁の明るさを真値つきで作る。

CD-SEM(半導体の寸法計測)でも外観検査でも、**二次電子は斜面でよけいに出る**ので
段差の縁が明るく縁取られる。この縁取りが寸法計測を太らせる —— 明るい帯ごと
しきい値を超えて拾ってしまうからである。その縁取りを「見た目」ではなく
**閉形式の真値**として作るのがこの module の役目で、作った像は他の PoC の
合成入力(真値つき)にもなる(``opsgenerative`` 族の方針そのまま)。

物理(Reimer, *Scanning Electron Microscopy*; Goldstein ほか *SEM and X-ray
Microanalysis* の教科書的モデルを、採点できる最小形に落としたもの):

  * **二次電子の縁効果**: 局所の表面傾き θ に対し放出は δ(θ) = δ0·sec θ で増える
    (脱出深さが 1/cos θ で伸びるため)。平らな面(θ=0)では一様、斜面では
    sec θ 倍。θ は高さ場の勾配から ``arctan|∇h|`` で測る。
  * **ビームの PSF**: 有限のビーム径をガウシアン(σ = ``psf_px``)で畳む。段差の
    縁の明るい線は、この PSF 幅ぶんだけ広がる(= 明るい縁の幅 ≈ PSF 幅)。
  * **ショット雑音**: 画素あたりの電子数をポアソンで散らす(``dose`` 電子/画素)。
  * **帯電**(任意): 緩い横方向の輝度勾配(``charging``)。

真値の 3 本(``tests/test_semsim.py`` が閉形式で確かめる):
  1. 平らな高さ場 → 出力は一様(雑音を切れば ptp = 0)。
  2. 傾き θ の一様斜面 → 平面に対する輝度比はちょうど sec θ。
  3. 段差 → 明るい縁の輝度プロファイルの幅(2 次モーメント)は PSF 幅 σ に一致する。

**上位の選択肢 —— 仮想 SEM(電子と固体の相互作用のモンテカルロ)**。``sem_render`` の
sec θ は「そう仮定した」式だが、下の op 群は一次電子を固体の中で 1 個ずつ追い
(Joy の単散乱モデル、弾性散乱は Browning 1994 の Mott 近似、阻止能は Joy-Luo)、
sec θ も縁の明るさも反射電子の Z コントラストも**軌跡の集計として**出す:

  * ``sem_electron_mc`` —— 平らな試料の η・δ・到達深さ・深さ分布(信頼区間で止める)。
  * ``sem_yield_curve`` / ``sem_se_universal_curve`` —— δ(E) と Lin & Joy の普遍曲線。
  * ``sem_line_profile`` / ``sem_cd_measure`` —— CD-SEM の線プロファイルと寸法計測
    (しきい値法・最大傾斜法)。加速電圧・ビーム径・側壁角で測れる線幅が動く。
  * ``sem_image`` —— 高さ場と材料の地図(埋もれた箱も)に画素ごとに電子を撃つ像。
    検出器はレンズ内 / 側方(Everhart-Thornley 型)/ 反射電子。
  * ``sem_charging_series`` / ``sem_se_escape_fraction`` —— 絶縁物の帯電のコマ送り。

外部真値の門(``tests/test_semsim_mc.py``): η(Z, E) が Joy のデータベースの実測の幅に入る /
η(θ) が Arnal の式 / 到達深さが Kanaya-Okayama / δ の形と Emax が Lin & Joy 2005。
材料の Z・A・密度・二次電子の定数は ``materials.material_electron_properties`` が持つ。

この族が新しい型語彙を 1 つも作らないのは ``opsgenerative`` と同じ:
入力も出力も既存の ``image2d``(H×W, [0,1] の float)で、作った SEM 像に
既存の 2-D op(しきい値・連結成分・採点)がそのまま掛かることに値打ちがある。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as _ndi

__all__ = ["sem_render", "sem_electron_mc", "sem_se_universal_curve", "sem_yield_curve",
           "sem_line_profile", "sem_cd_measure", "sem_image", "sem_se_escape_fraction",
           "sem_charging_series", "SEM_DETECTORS"]


def _as_height(height, op: str) -> np.ndarray:
    """高さ場を 2-D の有限な float64 にして返す(fail-closed)。"""
    h = np.asarray(height, dtype=np.float64)
    if h.ndim != 2:
        raise ValueError("%s: height must be 2-D (H, W), got shape %r" % (op, h.shape))
    if h.size == 0:
        raise ValueError("%s: height is empty" % op)
    if not np.isfinite(h).all():
        raise ValueError("%s: height has non-finite values (NaN/Inf)" % op)
    return h


def _positive(v, name: str, op: str) -> float:
    f = float(v)
    if not np.isfinite(f) or f <= 0.0:
        raise ValueError("%s: %s must be a positive finite number, got %r" % (op, name, v))
    return f


def sem_render(height, *, pixel_nm: float = 1.0, psf_px: float = 1.5,
               edge_gain: float = 1.0, base: float = 0.25, dose: float = 0.0,
               charging: float = 0.0, seed: int = 0,
               tilt_max_deg: float = 80.0) -> np.ndarray:
    """高さ場から SEM 像(二次電子の縁効果 + ビーム PSF + ショット雑音)を描く。

    Parameters
    ----------
    height : array_like
        2-D の高さ場[同じ単位は ``pixel_nm``]。欠陥の形そのもの。
    pixel_nm : float
        画素 1 個の一辺[nm]。傾きは ``arctan(|∇h| / pixel_nm)`` で測る。
    psf_px : float
        ビーム PSF のガウシアン σ[px]。段差の明るい縁はこの幅に広がる。
    edge_gain : float
        縁効果の強さの指数。``sec(θ) ** edge_gain``。既定 1.0 が sec θ の素のモデル。
    base : float
        平らな面(θ=0)の明るさ[0,1]。斜面は ``base·sec θ`` に乗る(飽和で 1 に頭打ち)。
    dose : float
        画素あたりの電子数。``> 0`` でポアソン雑音を載せる。``0`` は雑音なし(決定論)。
    charging : float
        帯電による緩い横方向の輝度勾配(0 で無効)。収差でなく系統的な明暗。
    seed : int
        ポアソン雑音の種(``dose > 0`` のときだけ効く)。
    tilt_max_deg : float
        sec θ が発散しないよう θ を頭打ちにする角度[度]。既定 80 度(sec ≈ 5.76)。

    Returns
    -------
    numpy.ndarray
        ``(H, W)`` の float64、[0,1]。平らな面は ``base``、斜面は ``base·sec θ``。

    Notes
    -----
    正規化は**画素ごとでなく固定の線形写像**(``·base`` と [0,1] クリップ)。
    1 枚ごとに min/max で正規化すると平面に対する比が壊れ、sec θ の真値を
    測れなくなる(``poc_real_defect_floor`` が ``colorize_depth`` の per-image
    正規化で踏んだ罠と同じ)。

    Examples
    --------
    >>> import numpy as np
    >>> flat = np.zeros((16, 16))
    >>> img = sem_render(flat)
    >>> float(np.ptp(img))            # 平らな面は一様
    0.0
    >>> ramp = np.tile(np.linspace(0, 15, 16), (16, 1))   # 一様斜面
    >>> r = sem_render(ramp, pixel_nm=1.0)
    >>> theta = np.arctan(1.0)                            # 勾配 1 → 45 度
    >>> abs(float(r[8, 8]) / 0.25 - 1.0 / np.cos(theta)) < 1e-6
    True
    """
    op = "sem_render"
    h = _as_height(height, op)
    pixel_nm = _positive(pixel_nm, "pixel_nm", op)
    psf_px = _positive(psf_px, "psf_px", op)
    base = float(base)
    if not (0.0 < base <= 1.0):
        raise ValueError("%s: base must be in (0, 1], got %r" % (op, base))
    edge_gain = _positive(edge_gain, "edge_gain", op)
    tilt_max = np.radians(_positive(tilt_max_deg, "tilt_max_deg", op))
    if tilt_max >= np.pi / 2:
        raise ValueError("%s: tilt_max_deg must be < 90, got %r" % (op, tilt_max_deg))

    # 傾き θ を高さ場の勾配から。np.gradient は端で片側差分に落ちるが、同じ
    # 傾きなので一様斜面では全面一定のまま(縁の 2 次モーメント検査は内側で測る)。
    gy, gx = np.gradient(h, pixel_nm)
    theta = np.arctan(np.hypot(gx, gy))
    theta = np.minimum(theta, tilt_max)

    # 二次電子の縁効果。δ(θ) = δ0·sec θ(脱出深さが 1/cos θ で伸びる)。
    yield_ = (1.0 / np.cos(theta)) ** edge_gain

    if charging:
        w = h.shape[1]
        ramp = (np.arange(w, dtype=np.float64) / max(w - 1, 1)) - 0.5   # [-0.5, 0.5]
        yield_ = yield_ * (1.0 + float(charging) * ramp[None, :])

    # ビーム PSF。段差の縁の明るい線は、この σ ぶんだけ広がる。
    inten = _ndi.gaussian_filter(yield_, psf_px, mode="nearest")

    if dose > 0.0:
        lam = np.clip(inten * float(dose), 0.0, None)
        rng = np.random.default_rng(int(seed))
        inten = rng.poisson(lam).astype(np.float64) / float(dose)

    return np.clip(inten * base, 0.0, 1.0)


# =========================================================================== #
# 仮想 SEM: 電子と固体の相互作用をモンテカルロで解く                            #
# =========================================================================== #
# ``sem_render`` は「縁が sec θ で明るい」を閉形式で描く最小形だった。ここから下は、
# その sec θ も縁の明るさも**電子の軌跡から出てくる**ように、一次電子を 1 個ずつ
# 固体の中で追う(Joy の単散乱モデル)。像も線幅の偏りも、その追跡の集計である。
#
# 物理(式はすべて公開の一次資料から。コードはどこからも写していない):
#   * 弾性散乱: 遮蔽ラザフォードの全断面積と角度分布(Joy 1995, *Monte Carlo
#     Modeling for Electron Microscopy and Microanalysis*, 第 3 章)。化合物は元素ごとの
#     断面積を数密度で足し、散乱する元素を断面積の重みで選ぶ。
#   * エネルギー損失: Bethe の連続減速近似に Joy-Luo の低エネルギー補正
#     (Joy & Luo 1989, Scanning 11:176)。平均イオン化エネルギーは Berger-Seltzer の式。
#   * 二次電子: 一次電子・反射電子が失ったエネルギー ΔE から ΔE/ε 個が生まれ、最寄りの
#     表面までの距離 d に対し 0.5·exp(−d/λ) で脱出する(Joy の「高速二次電子モデル」)。
#     λ と ε は対の量なので、両方とも表面の直下の材料(抜けて出る層)から取る。
#     SE1 と SE2(反射電子が表面近くで作る分)を区別せず同じ規則で数えるので、
#     δ = δ_PE (1 + β η) の形は**仮定でなく集計の結果**として出る。
#   * 検出器: 脱出した二次電子の向きを余弦分布で振り、幾何に遮られずに出られるかと、
#     検出器の位置で重みをつける(レンズ内 = 出られれば集まる、側方 = 検出器を向く面が
#     明るく、反射電子が試料室で作る SE3 も拾う)。反射電子検出器は真上の環状で、
#     受ける反射電子をエネルギーで重みづけする。
#
# 幾何は 2 種類:
#   * ``_ProfileGeom`` —— y に一様な断面(線・溝・側壁角つきの台形、埋もれた矩形)。
#     表面との交差は折れ線との厳密な交点で解く。CD-SEM の線プロファイルはこれで出す。
#   * ``_HeightGeom`` —— 2-D の高さ場と材料の地図(画素ごとの材料・埋もれた箱)。
#     交差は画素の半分の刻みで探して二分法で詰める。表面までの距離は局所の接平面と
#     3-D 距離変換の小さいほう。像(``sem_image``)はこれで、画素ごとに電子を撃つ。
#
# 近似(正直な一覧。どれも docstring と能力ノートに書く):
#   * 遮蔽ラザフォードは低エネルギー・高 Z で弾性散乱を誤る(Mott 断面積が要る)。
#     1 keV の Au・W では η を過大に出す —— 門は 5 keV 以上で採点し、1 keV の
#     ずれは表に出す。
#   * 1 歩の途中で材料の境界を跨いでも、その歩は出発点の材料で進む。
#   * 二次電子は輸送しない(脱出確率の期待値で数える)。異種材料の境界を跨ぐ脱出は、
#     表面の層の λ だけで減衰させる。帯電は別のモデル(``sem_charging_series``)。
#   * 停止エネルギー ``e_stop`` 未満の電子は捨てる(既定 min(0.5, max(0.05, 0.03 E0)) keV)。

#: アボガドロ数 [1/mol]。
_NA = 6.02214076e23
#: 遮蔽ラザフォードの全断面積の前係数 [cm²·keV²] (Joy 1995)。
_SR_PREF = 5.21e-21
#: Bethe の阻止能の前係数 [keV·cm²/g] (Joy-Luo 1989 の CSDA 形)。
_BETHE_PREF = 78500.0
#: 電子の静止エネルギー [keV] (全断面積の相対論補正の項)。
_MC2 = 511.0
#: 検出器の名前(信号の列の順)。
SEM_DETECTORS = ("se_total", "inlens", "everhart", "bse")


def _mean_ionization_kev(z):
    """平均イオン化エネルギー J = 9.76 Z + 58.5 Z^−0.19 [eV] (Berger-Seltzer)を keV で。"""
    z = np.asarray(z, dtype=np.float64)
    return (9.76 * z + 58.5 * z ** -0.19) * 1e-3


def _joy_luo_k(z):
    """Joy-Luo の低エネルギー補正の係数 k(Z) = 0.731 + 0.0688 log10 Z。"""
    return 0.731 + 0.0688 * np.log10(np.asarray(z, dtype=np.float64))


def _ko_range_nm(mat, e_kev):
    """Kanaya-Okayama の電子の到達深さ R = 0.0276 A E^1.67 / (Z^0.889 ρ) [µm] を nm で。

    化合物は質量分率で平均した Z・A を使う(到達深さの比較の目安としての慣例)。
    """
    zbar = float((mat.w * mat.z).sum())
    abar = float((mat.w * mat.a).sum())
    return 1e3 * 0.0276 * abar * float(e_kev) ** 1.67 / (zbar ** 0.889 * mat.rho)


class _Mat:
    """MC が引く材料 1 つ(元素ごとの Z・A・質量分率、密度、二次電子の 2 定数)。"""

    def __init__(self, rec, model="browning"):
        if model not in ("browning", "rutherford"):
            raise ValueError("cross_section must be 'browning' or 'rutherford', got %r" % (model,))
        self.model = model
        comp = rec["composition"]
        self.name = rec["name"]
        self.z = np.array([c[0] for c in comp], dtype=np.float64)
        self.a = np.array([c[1] for c in comp], dtype=np.float64)
        self.w = np.array([c[2] for c in comp], dtype=np.float64)
        self.rho = float(rec["density_g_cm3"])
        self.j = _mean_ionization_kev(self.z)
        self.k = _joy_luo_k(self.z)
        self.nd = _NA * self.rho * self.w / self.a           # 原子の数密度 [1/cm³]
        self.lam_se = float(rec["se_escape_nm"])             # 二次電子の脱出深さ λ [nm]
        self.eps_se = float(rec["se_energy_ev"]) * 1e-3      # 二次電子 1 個あたりのエネルギー ε [keV]
        self.insulator = bool(rec.get("insulator", False))

    def alpha(self, e):
        """遮蔽パラメータ α_i(E) = 3.4e−3 Z^0.67 / E(元素ごと、(n, n_elem))。"""
        return 3.4e-3 * self.z[None, :] ** 0.67 / e[:, None]

    def sigma(self, e):
        """弾性散乱の全断面積 σ_i(E) [cm²] ((n, n_elem))。

        ``browning``: Browning ほか 1994 の経験式(Mott 断面積の当てはめ、0.1〜30 keV、Z ≤ 92)
        σ = 3.0e−18 Z^1.7 / (E + 0.005 Z^1.7 √E + 0.0007 Z² / √E)。
        ``rutherford``: 遮蔽ラザフォード(相対論補正つき、Joy 1995)。
        """
        if self.model == "browning":
            z = self.z[None, :]
            se = np.sqrt(e)[:, None]
            return 3.0e-18 * z ** 1.7 / (e[:, None] + 0.005 * z ** 1.7 * se + 0.0007 * z ** 2 / se)
        a = self.alpha(e)
        rel = ((e[:, None] + _MC2) / (e[:, None] + 2.0 * _MC2)) ** 2
        return (_SR_PREF * self.z[None, :] ** 2 / e[:, None] ** 2
                * 4.0 * np.pi / (a * (1.0 + a)) * rel)

    def sample_cos(self, e, pick, rng):
        """選んだ元素 ``pick`` での散乱角 cos φ を引く。

        ``browning``: r = 300 E/Z + Z³/(3e5 E) とし、確率 r/(1+r) で遮蔽ラザフォード
        (α = 7.0e−3/E)、残りは等方(cos φ = 1 − 2R)。``rutherford``: α = 3.4e−3 Z^0.67/E。
        cos φ = 1 − 2αR/(1 + α − R) が遮蔽ラザフォードの逆変換。
        """
        z = self.z[pick]
        r1 = rng.random(e.size); r2 = rng.random(e.size)
        if self.model == "browning":
            rr = 300.0 * e / z + z ** 3 / (3.0e5 * e)
            a = 7.0e-3 / e
            ruth = 1.0 - 2.0 * a * r2 / (1.0 + a - r2)
            return np.where(r1 <= rr / (1.0 + rr), ruth, 1.0 - 2.0 * r2)
        a = 3.4e-3 * z ** 0.67 / e
        return 1.0 - 2.0 * a * r2 / (1.0 + a - r2)

    def stopping(self, e):
        """Joy-Luo の阻止能 |dE/ds| [keV/nm] (化合物は質量分率で足す)。"""
        arg = 1.166 * (e[:, None] + self.k[None, :] * self.j[None, :]) / self.j[None, :]
        lnv = np.log(np.maximum(arg, 1.0 + 1e-6))
        s = (_BETHE_PREF * self.rho / e) * ((self.w * self.z / self.a)[None, :] * lnv).sum(axis=1)
        return s * 1e-7                                       # keV/cm → keV/nm


def _electron_material(name, op, model="browning"):
    """材料表(``materials.material_electron_properties``)から MC の材料を作る。"""
    import materials as _materials
    try:
        rec = _materials.material_electron_properties(name)
    except ValueError as exc:
        raise ValueError("%s: %s" % (op, exc)) from None
    return _Mat(rec, model)


def _hemisphere_dirs(m=96):
    """余弦分布の半球の向き(+z 軸まわり、決定論的な層別。乱数を引かない)。

    面積を等分する同心の輪(r = √((i+0.5)/n_r))と黄金角の方位で、``m`` 本の単位
    ベクトル (m, 3) を返す。z 成分 = cos θ が余弦分布に従う。
    """
    i = np.arange(m, dtype=np.float64)
    r = np.sqrt((i + 0.5) / m)
    phi = i * np.pi * (3.0 - np.sqrt(5.0))
    return np.stack([r * np.cos(phi), r * np.sin(phi), np.sqrt(1.0 - r * r)], axis=1)


def _detector_weights(u):
    """脱出した二次電子の向き u(上向きの単位ベクトル、z は上が正)の検出器ごとの重み。

    列は (inlens, everhart)。レンズ内は強い場が全部を引き込むので 1。側方の検出器は
    +x 方向・仰角 30 度にあるとして 0.6 + 0.4 (u·d)(検出器を向く面ほど明るい)。
    """
    d = np.array([np.cos(np.radians(30.0)), 0.0, np.sin(np.radians(30.0))])
    et = 0.6 + 0.4 * (u @ d)
    return np.stack([np.ones(u.shape[0]), et], axis=1)


class _ProfileGeom:
    """y に一様な断面。表面 z = s(x)(z は下向きが正)を節 (xk, zk) の折れ線で持つ。

    両端の外側は水平に無限に延びる。``z < 0`` で表面より深い点は上の層(線)の
    材料 0、``z ≥ 0`` は基板の材料 1。``buried`` は (材料番号, x0, x1, z0, z1) の
    埋もれた矩形(基板の中)。
    """

    def __init__(self, xk, zk, buried=(), coll_window=None):
        self.xk = np.asarray(xk, dtype=np.float64)
        self.zk = np.asarray(zk, dtype=np.float64)
        big = 1e9
        self.px = np.concatenate([[self.xk[0] - big], self.xk])
        self.pz = np.concatenate([[self.zk[0]], self.zk])
        self.qx = np.concatenate([self.xk, [self.xk[-1] + big]])
        self.qz = np.concatenate([self.zk, [self.zk[-1]]])
        self.ex, self.ez = self.qx - self.px, self.qz - self.pz
        self.len = np.hypot(self.ex, self.ez)
        self.buried = list(buried)
        self.z_free = float(self.zk.max())          # これより深い点は x に依らず固体
        # 弧長の座標(左の無限線分は x − x0、以降は節からの弧長)。
        self.arc0 = np.concatenate([[0.0], np.cumsum(self.len[1:-1])])
        self.arc0 = np.concatenate([[0.0], self.arc0])            # 線分 k の始点の弧長
        relief = float(self.zk.max() - self.zk.min())
        win = float(coll_window) if coll_window is not None else 6.0 * relief + 40.0
        self._build_collection(win)

    # -- 表面 ------------------------------------------------------------------ #
    def surface(self, x, y=None):
        return np.interp(x, self.xk, self.zk)

    def entry(self, x0, y0):
        return self.surface(x0) + 1e-6

    def material(self, x, y, z):
        m = np.where(z < 0.0, 0, 1)
        for idx, x0, x1, z0, z1 in self.buried:
            m = np.where((x >= x0) & (x <= x1) & (z >= z0) & (z <= z1), idx, m)
        return m

    def material_t(self, x, y, z, ux, uy, uz, s, m0):
        """材料の境界(線と基板の面 z = 0、埋もれた矩形の 4 辺)を最初に横切る t(無ければ inf)。

        自由行程は材料ごとに違うので、境界で歩を切って新しい材料で引き直す(指数分布は
        無記憶なので、これで厳密)。横切った先で材料が本当に変わる交点だけを数える。
        """
        best = np.full(x.shape, np.inf)
        cands = []
        if float(self.zk.min()) < 0.0:
            cands.append(("z", 0.0))
        for _, x0, x1, z0, z1 in self.buried:
            cands += [("x", x0), ("x", x1), ("z", z0), ("z", z1)]
        for axis, v in cands:
            u = ux if axis == "x" else uz
            p = x if axis == "x" else z
            ok = np.abs(u) > 1e-15
            t = np.where(ok, (v - p) / np.where(ok, u, 1.0), np.inf)
            good = ok & (t > 1e-9) & (t <= s) & (t < best)
            if not good.any():
                continue
            gi = np.nonzero(good)[0]
            t2 = t[gi] + 1e-6
            m1 = self.material(x[gi] + t2 * ux[gi], y[gi], z[gi] + t2 * uz[gi])
            ch = m1 != m0[gi]
            best[gi[ch]] = t[gi[ch]]
        return best

    def _hit(self, x, z, ux, uz, tmax):
        """折れ線との最初の交点の t ∈ (1e−6, tmax] (無ければ inf)。"""
        best = np.full(np.shape(x), np.inf)
        for k in range(self.px.size):
            ex, ez = self.ex[k], self.ez[k]
            den = ux * ez - uz * ex
            ok = np.abs(den) > 1e-15
            den_s = np.where(ok, den, 1.0)
            wx, wz = self.px[k] - x, self.pz[k] - z
            t = (wx * ez - wz * ex) / den_s
            s = (wx * uz - wz * ux) / den_s
            hit = ok & (t > 1e-6) & (t <= tmax) & (s >= 0.0) & (s <= 1.0)
            best = np.where(hit & (t < best), t, best)
        return best

    def exit_t(self, x, y, z, ux, uy, uz, s):
        out = np.full(x.shape, np.inf)
        cand = ~((z > self.z_free) & (z + s * uz > self.z_free))
        if cand.any():
            out[cand] = self._hit(x[cand], z[cand], ux[cand], uz[cand], s[cand])
        return out

    def reenter_t(self, x, y, z, ux, uy, uz):
        return self._hit(x, z, ux, uz, np.inf)

    def _nearest(self, x, z):
        dbest = np.full(x.shape, np.inf)
        abest = np.zeros(x.shape)
        for k in range(self.px.size):
            ex, ez = self.ex[k], self.ez[k]
            s = np.clip(((x - self.px[k]) * ex + (z - self.pz[k]) * ez) / (self.len[k] ** 2), 0.0, 1.0)
            d = np.hypot(x - (self.px[k] + s * ex), z - (self.pz[k] + s * ez))
            if k == 0:
                arc = (self.px[k] + s * ex) - self.xk[0]               # 負の側
            else:
                arc = self.arc0[k] + s * self.len[k]
            better = d < dbest
            dbest = np.where(better, d, dbest)
            abest = np.where(better, arc, abest)
        return dbest, abest

    def _build_collection(self, win):
        """表面に沿って 0.25 nm おきに、脱出できる割合と検出器の重みを前計算する。"""
        total = float(self.arc0[-1])
        arc = np.arange(-win, total + win + 0.25, 0.25)
        # 弧長 → 表面の点と外向き法線。
        px = np.empty(arc.size); pz = np.empty(arc.size); nx = np.empty(arc.size); nz = np.empty(arc.size)
        for i, a in enumerate(arc):
            if a < 0.0:
                k, s = 0, None
                px[i], pz[i] = self.xk[0] + a, self.zk[0]
            elif a >= total:
                k = self.px.size - 1
                px[i], pz[i] = self.xk[-1] + (a - total), self.zk[-1]
            else:
                k = int(np.searchsorted(self.arc0, a, side="right") - 1)
                k = min(max(k, 1), self.px.size - 2)
                f = (a - self.arc0[k]) / self.len[k]
                px[i], pz[i] = self.px[k] + f * self.ex[k], self.pz[k] + f * self.ez[k]
            nx[i], nz[i] = self.ez[k] / self.len[k], -self.ex[k] / self.len[k]
        dirs = _hemisphere_dirs(96)                                    # z 上向きが正
        coll = np.zeros((arc.size, 2))
        for i in range(arc.size):
            # 局所の基底: 法線 n(上向きを正とする座標で)= (nx, 0, −nz)。
            n3 = np.array([nx[i], 0.0, -nz[i]])
            t1 = np.array([n3[2], 0.0, -n3[0]])
            t2 = np.array([0.0, 1.0, 0.0])
            u = dirs[:, 0:1] * t1[None, :] + dirs[:, 1:2] * t2[None, :] + dirs[:, 2:3] * n3[None, :]
            ox = np.full(u.shape[0], px[i] + 1e-3 * nx[i])
            oz = np.full(u.shape[0], pz[i] + 1e-3 * nz[i])
            # 断面の幾何は y に一様なので、xz 面に射影した向きで当たりを調べる。
            blocked = np.isfinite(self._hit(ox, oz, u[:, 0], -u[:, 2], np.inf))
            w = _detector_weights(u)
            coll[i] = (w * (~blocked)[:, None]).sum(axis=0) / u.shape[0]
        self._coll_arc = arc
        self._coll = coll

    def se_escape(self, x, y, z):
        d, arc = self._nearest(x, z)
        a = np.clip(arc, self._coll_arc[0], self._coll_arc[-1])
        i = np.clip(np.rint((a - self._coll_arc[0]) / 0.25).astype(np.int64), 0, self._coll_arc.size - 1)
        return d, self._coll[i]


class _HeightGeom:
    """2-D の高さ場(画素中心、z = −h)と材料の地図。

    ``labels`` (H, W) は表面から ``bottom`` (H, W) [nm] までの柱の材料番号、それより
    深い所は基板 ``substrate``。``buried`` は (材料番号, 2-D マスク, 上端 z, 下端 z)。
    像の外は端の画素の値で延ばす。
    """

    def __init__(self, height_nm, pixel_nm, labels, bottom, substrate, buried, lam_max):
        self.h = np.asarray(height_nm, dtype=np.float64)
        self.H, self.W = self.h.shape
        self.p = float(pixel_nm)
        self.labels = labels
        self.bottom = bottom
        self.substrate = int(substrate)
        self.buried = list(buried)
        self.zs = -self.h
        self.z_top = float(self.zs.min())           # いちばん高い表面
        self.z_free = float(self.zs.max())          # これより深い点は必ず固体
        self.ds = 0.5 * self.p                      # 交差を探す刻み
        # 材料の境界があり得る深さの範囲(柱の下端と埋もれた箱。無ければ None)。
        zs_b = [float(np.min(self.bottom)), float(np.max(self.bottom))] if np.any(self.bottom > self.zs) else []
        for _, mask, z0, z1 in self.buried:
            zs_b += [float(z0), float(z1)]
        self._zmat = (min(zs_b + [self.z_top]) - 1e-6, max(zs_b) + 1e-6) if zs_b else None
        gy, gx = np.gradient(self.h, self.p)
        self.cos_t = 1.0 / np.sqrt(1.0 + gx * gx + gy * gy)
        self.nx, self.ny = -gx * self.cos_t, -gy * self.cos_t   # 外向き法線の水平成分
        self._build_distance(lam_max)
        self._build_collection()

    def _ij(self, x, y):
        j = np.clip(np.rint(x / self.p).astype(np.int64), 0, self.W - 1)
        i = np.clip(np.rint(y / self.p).astype(np.int64), 0, self.H - 1)
        return i, j

    def surface(self, x, y):
        fx = np.clip(x / self.p, 0.0, self.W - 1.0)
        fy = np.clip(y / self.p, 0.0, self.H - 1.0)
        j0 = np.minimum(np.floor(fx).astype(np.int64), self.W - 2) if self.W > 1 else np.zeros_like(fx, dtype=np.int64)
        i0 = np.minimum(np.floor(fy).astype(np.int64), self.H - 2) if self.H > 1 else np.zeros_like(fy, dtype=np.int64)
        tx = fx - j0; ty = fy - i0
        j1 = np.minimum(j0 + 1, self.W - 1); i1 = np.minimum(i0 + 1, self.H - 1)
        z = self.zs
        return ((1 - ty) * ((1 - tx) * z[i0, j0] + tx * z[i0, j1])
                + ty * ((1 - tx) * z[i1, j0] + tx * z[i1, j1]))

    def entry(self, x0, y0):
        return self.surface(x0, y0) + 1e-6

    def material(self, x, y, z):
        i, j = self._ij(x, y)
        m = np.where(z < self.bottom[i, j], self.labels[i, j], self.substrate)
        for idx, mask, z0, z1 in self.buried:
            m = np.where(mask[i, j] & (z >= z0) & (z <= z1), idx, m)
        return m

    def _inside(self, x, y, z):
        return z > self.surface(x, y)

    def material_t(self, x, y, z, ux, uy, uz, s, m0):
        """材料の境界を最初に横切る t(無ければ inf)。画素の半分の刻みで探して二分法で詰める。

        境界があり得る深さ(材料の柱の下端と埋もれた箱の範囲)を通る歩だけを調べる。
        """
        out = np.full(x.shape, np.inf)
        if self._zmat is None:
            return out
        zlo, zhi = self._zmat
        z2 = z + s * uz
        cand = np.nonzero(~(((z < zlo) & (z2 < zlo)) | ((z > zhi) & (z2 > zhi))))[0]
        if cand.size == 0:
            return out
        xc, yc, zc = x[cand], y[cand], z[cand]
        uxc, uyc, uzc, sc, mc = ux[cand], uy[cand], uz[cand], s[cand], m0[cand]
        nsub = np.ceil(sc / self.ds).astype(np.int64)
        res = np.full(cand.size, np.inf)
        live = np.ones(cand.size, dtype=bool)
        tprev = np.zeros(cand.size)
        for k in range(1, int(nsub.max()) + 1):
            live &= k <= nsub
            if not live.any():
                break
            li = np.nonzero(live)[0]
            t = np.minimum(k * self.ds, sc[li])
            m1 = self.material(xc[li] + t * uxc[li], yc[li] + t * uyc[li], zc[li] + t * uzc[li])
            ch = m1 != mc[li]
            if ch.any():
                hi = li[ch]
                t0, t1 = tprev[hi], t[ch]
                for _ in range(14):
                    tm = 0.5 * (t0 + t1)
                    mm = self.material(xc[hi] + tm * uxc[hi], yc[hi] + tm * uyc[hi], zc[hi] + tm * uzc[hi])
                    same = mm == mc[hi]
                    t0 = np.where(same, tm, t0)
                    t1 = np.where(same, t1, tm)
                res[hi] = t0
                live[hi] = False
            tprev[li] = t
        out[cand] = res
        return out

    def _bisect(self, x, y, z, ux, uy, uz, t0, t1, want_inside_at_t1):
        for _ in range(14):
            tm = 0.5 * (t0 + t1)
            ins = self._inside(x + tm * ux, y + tm * uy, z + tm * uz)
            go = ins == want_inside_at_t1
            t1 = np.where(go, tm, t1)
            t0 = np.where(go, t0, tm)
        return t1

    def exit_t(self, x, y, z, ux, uy, uz, s):
        out = np.full(x.shape, np.inf)
        cand = np.nonzero(~((z > self.z_free) & (z + s * uz > self.z_free)))[0]
        if cand.size == 0:
            return out
        xc, yc, zc = x[cand], y[cand], z[cand]
        uxc, uyc, uzc, sc = ux[cand], uy[cand], uz[cand], s[cand]
        nsub = np.ceil(sc / self.ds).astype(np.int64)
        res = np.full(cand.size, np.inf)
        live = np.ones(cand.size, dtype=bool)
        tprev = np.zeros(cand.size)
        for k in range(1, int(nsub.max()) + 1):
            live &= k <= nsub
            if not live.any():
                break
            li = np.nonzero(live)[0]
            t = np.minimum(k * self.ds, sc[li])
            ins = self._inside(xc[li] + t * uxc[li], yc[li] + t * uyc[li], zc[li] + t * uzc[li])
            hit = ~ins
            if hit.any():
                hi = li[hit]
                res[hi] = self._bisect(xc[hi], yc[hi], zc[hi], uxc[hi], uyc[hi], uzc[hi],
                                       tprev[hi], t[hit], False)
                live[hi] = False
            tprev[li] = t
        out[cand] = res
        return out

    def reenter_t(self, x, y, z, ux, uy, uz):
        """真空を直進する電子が、また表面に当たるまでの t(当たらなければ inf)。"""
        n = x.size
        res = np.full(n, np.inf)
        up = uz < -1e-9
        down = uz > 1e-9
        # 上向きはいちばん高い表面より上に出たら脱出、下向きは最も低い面より下で必ず当たる。
        diag = self.p * np.hypot(self.H, self.W) + 1.0
        tend = np.where(up, (z - self.z_top) / np.maximum(-uz, 1e-9),
                        np.where(down, (self.z_free - z) / np.maximum(uz, 1e-9) + self.ds, diag))
        tend = np.minimum(tend, diag + (self.z_free - self.z_top) / np.maximum(np.abs(uz), 1e-3))
        nsub = np.ceil(np.maximum(tend, 0.0) / self.ds).astype(np.int64)
        live = nsub > 0
        tprev = np.zeros(n)
        for k in range(1, int(nsub.max(initial=0)) + 1):
            live &= k <= nsub
            if not live.any():
                break
            li = np.nonzero(live)[0]
            t = np.minimum(k * self.ds, tend[li])
            ins = self._inside(x[li] + t * ux[li], y[li] + t * uy[li], z[li] + t * uz[li])
            if ins.any():
                hi = li[ins]
                res[hi] = self._bisect(x[hi], y[hi], z[hi], ux[hi], uy[hi], uz[hi], tprev[hi], t[ins], True)
                live[hi] = False
            tprev[li] = t
        return res

    def _build_distance(self, lam_max):
        """表面近くの殻の 3-D 距離変換(壁を通って出る二次電子のため)。"""
        from scipy import ndimage as ndi
        relief = self.z_free - self.z_top
        if relief <= 1e-9:
            self._edt = None
            return
        depth = relief + 8.0 * lam_max
        nz = int(min(400, max(16, np.ceil(depth / min(0.5, self.p)))))
        self._dz = (depth + self.p) / nz
        self._z0 = self.z_top - 0.5 * self.p
        zc = self._z0 + (np.arange(nz) + 0.5) * self._dz
        solid = zc[:, None, None] > self.zs[None, :, :]
        self._edt = ndi.distance_transform_edt(solid, sampling=(self._dz, self.p, self.p))
        self._nz = nz

    def _build_collection(self):
        """表面の画素ごとの、脱出できる割合と検出器の重み(地平線から)。"""
        import demops
        svf = demops.dem_sky_view_factor(self.h, self.p, n_azimuth=16)
        d = np.array([np.cos(np.radians(30.0)), np.sin(np.radians(30.0))])
        # 面の向きの効き: 法線が検出器(+x、仰角 30 度)を向くほど明るい。
        # 余弦分布の平均の向きは (2/3)·n なので、平均の重みは 0.6 + 0.4·(2/3)(n·d)。
        et = (0.6 + 0.4 * (2.0 / 3.0) * (self.nx * d[0] + self.cos_t * d[1])) * svf
        self._coll = np.stack([svf, et], axis=-1)

    def se_escape(self, x, y, z):
        i, j = self._ij(x, y)
        dp = np.maximum(z - self.surface(x, y), 0.0) * self.cos_t[i, j]
        if self._edt is not None:
            k = np.floor((z - self._z0) / self._dz).astype(np.int64)
            ok = (k >= 0) & (k < self._nz)
            de = np.where(ok, self._edt[np.clip(k, 0, self._nz - 1), i, j], np.inf)
            d = np.minimum(dp, de)
        else:
            d = dp
        return d, self._coll[i, j]


def _rotate(ux, uy, uz, cphi, psi):
    """向き u を極角 φ(cos)・方位 ψ だけ回す(ベクトル化)。"""
    sphi = np.sqrt(np.maximum(0.0, 1.0 - cphi * cphi))
    near = np.abs(uz) > 0.99
    ax = np.where(near, 1.0, 0.0)
    az = np.where(near, 0.0, 1.0)
    e1x = -az * uy
    e1y = az * ux - ax * uz
    e1z = ax * uy
    n1 = np.sqrt(e1x * e1x + e1y * e1y + e1z * e1z)
    e1x, e1y, e1z = e1x / n1, e1y / n1, e1z / n1
    e2x = uy * e1z - uz * e1y
    e2y = uz * e1x - ux * e1z
    e2z = ux * e1y - uy * e1x
    c, s = np.cos(psi), np.sin(psi)
    nx = cphi * ux + sphi * (c * e1x + s * e2x)
    ny = cphi * uy + sphi * (c * e1y + s * e2y)
    nz = cphi * uz + sphi * (c * e1z + s * e2z)
    nn = np.sqrt(nx * nx + ny * ny + nz * nz)
    return nx / nn, ny / nn, nz / nn


def _e_stop(e0):
    """追跡を打ち切るエネルギー [keV]: min(0.5, max(0.05, 0.03·E0))。"""
    return float(min(0.5, max(0.05, 0.03 * float(e0))))


def _transport(mats, geom, x0, y0, e0, rng, *, tally=None, keep=0, max_steps=100000, tilt_deg=0.0):
    """一次電子 ``x0.size`` 個を固体の中で追う(Joy の単散乱 MC、ベクトル化)。

    返す dict(電子 1 個ごと):
      ``bse`` 反射電子か / ``e_exit`` 脱出時のエネルギー / ``uz_exit`` 脱出時の向きの z 成分 /
      ``se`` (n, 3) 二次電子の脱出の期待値 [全部, レンズ内, 側方] / ``max_depth`` 最大の z /
      ``tracks`` 最初の ``keep`` 個の軌跡(各 (K, 3))。
    ``tally(x, y, z, dE)`` があれば、各歩の沈着エネルギーをその位置で渡す。``tilt_deg`` は
    ビームを xz 面で傾ける角(平らな試料なら、試料を同じ角だけ傾けたのと同じ)。
    """
    e_stop = _e_stop(e0)
    n = x0.size
    x = x0.astype(np.float64).copy()
    y = y0.astype(np.float64).copy()
    z = geom.entry(x, y)
    tr = np.radians(float(tilt_deg))
    ux = np.full(n, np.sin(tr)); uy = np.zeros(n); uz = np.full(n, np.cos(tr))
    e = np.full(n, float(e0))
    alive = np.ones(n, dtype=bool)
    bse = np.zeros(n, dtype=bool)
    e_exit = np.zeros(n); uz_exit = np.zeros(n)
    se = np.zeros((n, 3))
    max_depth = z.copy()
    tracks = [[(x[i], y[i], z[i])] for i in range(min(keep, n))]
    lam_se = np.array([m.lam_se for m in mats])
    eps_se = np.array([m.eps_se for m in mats])
    for _ in range(max_steps):
        act = np.nonzero(alive)[0]
        if act.size == 0:
            break
        xa, ya, za = x[act], y[act], z[act]
        uxa, uya, uza, ea = ux[act], uy[act], uz[act], e[act]
        mi_a = geom.material(xa, ya, za)
        lam = np.empty(act.size); sp = np.empty(act.size); cph = np.empty(act.size)
        for mi, m in enumerate(mats):
            sel = mi_a == mi
            if not sel.any():
                continue
            es = ea[sel]
            mu = m.sigma(es) * m.nd[None, :]                 # 元素ごとの 1/cm
            mut = mu.sum(axis=1)
            lam[sel] = 1e7 / mut                             # nm
            sp[sel] = m.stopping(es)
            cum = np.cumsum(mu, axis=1) / mut[:, None]
            pick = np.minimum((rng.random(es.size)[:, None] > cum).sum(axis=1), m.z.size - 1)
            cph[sel] = m.sample_cos(es, pick, rng)
        step = -lam * np.log1p(-rng.random(act.size))
        # 材料の境界で歩を切る(新しい材料の自由行程で引き直す。散乱はしない)。
        tm = geom.material_t(xa, ya, za, uxa, uya, uza, step, mi_a)
        mcross = tm < step
        step = np.where(mcross, tm + 1e-6, step)
        th = geom.exit_t(xa, ya, za, uxa, uya, uza, step)
        cross = np.isfinite(th)
        mcross &= ~cross
        s_in = np.where(cross, th, step)
        de = np.minimum(sp * s_in, ea)
        # 二次電子: 固体の中の区間の一様な 1 点で ΔE/ε 個が生まれ、0.5·exp(−d/λ) で出る。
        u = rng.random(act.size)
        gx, gy, gz = xa + u * s_in * uxa, ya + u * s_in * uya, za + u * s_in * uza
        d, coll = geom.se_escape(gx, gy, gz)
        # λ と ε は対で決まる量(Lin & Joy の表は δ ∝ λ/ε で合わせてある)ので、両方とも
        # 抜けて出る表面の層(表面の直下)の材料から取る。埋もれた W の中で生まれた二次電子も
        # 上の Si の λ・ε で数える —— 埋もれた材料は、沈着エネルギーと反射電子を通してだけ効く。
        sm = geom.material(gx, gy, geom.surface(gx, gy) + 1e-3)
        w_se = de / eps_se[sm] * 0.5 * np.exp(-d / lam_se[sm])
        se[act, 0] += w_se
        se[act, 1:] += w_se[:, None] * coll
        if tally is not None:
            tally(gx, gy, gz, de)
        xa = xa + s_in * uxa; ya = ya + s_in * uya; za = za + s_in * uza
        ea = ea - de
        if cross.any():
            ci = np.nonzero(cross)[0]
            t2 = geom.reenter_t(xa[ci], ya[ci], za[ci], uxa[ci], uya[ci], uza[ci])
            back = np.isfinite(t2)
            ri = ci[back]
            tt = t2[back] + 1e-6
            xa[ri] += tt * uxa[ri]; ya[ri] += tt * uya[ri]; za[ri] += tt * uza[ri]
            out = ci[~back]
            g = act[out]
            bse[g] = ea[out] > e_stop
            e_exit[g] = ea[out]; uz_exit[g] = uza[out]
            alive[g] = False
        scat = alive[act] & ~cross & ~mcross
        if scat.any():
            cphi = cph[scat]
            psi = 2.0 * np.pi * rng.random(cphi.size)
            uxa[scat], uya[scat], uza[scat] = _rotate(uxa[scat], uya[scat], uza[scat], cphi, psi)
        x[act], y[act], z[act] = xa, ya, za
        ux[act], uy[act], uz[act], e[act] = uxa, uya, uza, ea
        max_depth[act] = np.maximum(max_depth[act], za)
        dead = alive[act] & (ea <= e_stop)
        alive[act[dead]] = False
        if keep:
            for i in act[act < keep]:
                tracks[i].append((x[i], y[i], z[i]))
    return {"bse": bse, "e_exit": e_exit, "uz_exit": uz_exit, "se": se,
            "max_depth": max_depth, "tracks": [np.array(t) for t in tracks]}


def _signals(res, e0, se3_gain=0.2, bse_cone_deg=60.0):
    """電子 1 個ごとの検出器信号 (n, 4) = [SE 全部, レンズ内, 側方, 反射電子検出器]。

    側方(Everhart-Thornley 型)には、反射電子が試料室・対物レンズで作る SE3 を
    ``se3_gain`` × 反射電子の数で足す。反射電子検出器は真上の環状(向きが鉛直から
    ``bse_cone_deg`` 以内)で、受けた反射電子のエネルギー E/E0 で重みづけする。
    """
    se = res["se"]
    up = -res["uz_exit"]                                   # 上向きの cos(脱出した電子だけ意味がある)
    in_cone = res["bse"] & (up >= np.cos(np.radians(bse_cone_deg)))
    bse_sig = np.where(in_cone, res["e_exit"] / float(e0), 0.0)
    et = se[:, 2] + se3_gain * res["bse"]
    return np.stack([se[:, 0], se[:, 1], et, bse_sig], axis=1)


def _ci95(v):
    v = np.asarray(v, dtype=np.float64)
    if v.size < 2:
        return float("inf")
    return float(1.96 * v.std(ddof=1) / np.sqrt(v.size))


def _check_energy(e, op):
    e = float(e)
    if not np.isfinite(e) or not (0.1 <= e <= 50.0):
        raise ValueError("%s: energy_kev must be in [0.1, 50] keV, got %r" % (op, e))
    return e


def sem_electron_mc(material="SI", energy_kev: float = 10.0, *, tol: float = 0.01,
                    batch: int = 1000, max_electrons: int = 20000, seed: int = 0,
                    n_tracks: int = 0, depth_bins: int = 60, tilt_deg: float = 0.0) -> dict:
    """平らな試料に電子を撃つモンテカルロ: 反射電子係数 η・二次電子収率 δ・相互作用体積。

    Joy の単散乱モデル(遮蔽ラザフォード + Joy-Luo の阻止能)で一次電子を 1 個ずつ
    追い、``batch`` 個ずつ足して 95 % 信頼区間の半幅が η で ``tol``、δ で ``tol``·max(δ, 1)
    を切ったら止める(``max_electrons`` で打ち切り、その時は ``converged`` が False)。

    Parameters
    ----------
    material : str
        材料表の名前(``materials.material_electron_properties`` が引ける物。SI / W / AU /
        SILICA / PMMA …)。Z・A・密度・二次電子の 2 定数はそこから取る。
    energy_kev : float
        加速電圧 [keV] (0.1〜50)。
    tol : float
        信頼区間の半幅の目標。
    batch, max_electrons : int
        1 回に足す電子の数と上限。
    seed : int
        乱数の種(同じ種なら同じ結果)。
    n_tracks : int
        軌跡を返す電子の数(図用)。
    depth_bins : int
        深さ分布の区間の数(0〜1.2 R_KO)。
    tilt_deg : float
        試料の傾き [度] (0〜80)。ビームが法線から θ 傾いて入る。δ(θ)/δ(0) を sec θ と、
        η(θ) を Arnal ほかの (1 + cos θ)^(−9/√Z) と比べるのに使う。

    Returns
    -------
    dict
        ``eta`` / ``eta_ci95`` / ``se_yield`` / ``se_yield_ci95`` / ``n_electrons`` /
        ``converged`` / ``range_ko_nm``(Kanaya-Okayama)/ ``depth_max_nm``・
        ``depth_p95_nm``・``depth_p50_nm``(電子ごとの最大の深さ)/ ``lateral_p95_nm``
        (沈着エネルギーの 95 % が入る半径)/ ``depth_dose``(``pairs``: 深さ [nm] と
        沈着エネルギーの割合)/ ``bse_energy``(``pairs``: E/E0 と反射電子の割合)/
        ``tracks``(各 (K, 3) [nm]、z は下向きが正)。

    Examples
    --------
    >>> r = sem_electron_mc("SI", 5.0, tol=0.03, batch=400, max_electrons=800)
    >>> 0.1 < r["eta"] < 0.3 and r["depth_max_nm"] < r["range_ko_nm"]
    True
    """
    op = "sem_electron_mc"
    e0 = _check_energy(energy_kev, op)
    tol = _positive(tol, "tol", op)
    batch = int(batch)
    max_electrons = int(max_electrons)
    if batch < 2 or max_electrons < batch:
        raise ValueError("%s: need batch >= 2 and max_electrons >= batch, got %r / %r"
                         % (op, batch, max_electrons))
    tilt = float(tilt_deg)
    if not (0.0 <= tilt <= 80.0):
        raise ValueError("%s: tilt_deg must be in [0, 80], got %r" % (op, tilt_deg))
    mat = _electron_material(material, op)
    geom = _ProfileGeom([0.0, 1.0], [0.0, 0.0], coll_window=1.0)
    rko = _ko_range_nm(mat, e0)
    zedges = np.linspace(0.0, 1.2 * rko, int(depth_bins) + 1)
    redges = np.linspace(0.0, 1.2 * rko, 241)
    dose_z = np.zeros(zedges.size - 1)
    dose_r = np.zeros(redges.size - 1)

    def tally(gx, gy, gz, de):
        dose_z[:] += np.histogram(gz, bins=zedges, weights=de)[0]
        dose_r[:] += np.histogram(np.hypot(gx, gy), bins=redges, weights=de)[0]

    rng = np.random.default_rng(int(seed))
    bse, se, depth, eexit, tracks = [], [], [], [], []
    n = 0
    converged = False
    while n < max_electrons:
        k = min(batch, max_electrons - n)
        res = _transport([mat, mat], geom, np.zeros(k), np.zeros(k), e0, rng, tally=tally,
                         keep=max(0, int(n_tracks) - n), tilt_deg=tilt)
        bse.append(res["bse"]); se.append(res["se"][:, 0]); depth.append(res["max_depth"])
        eexit.append(res["e_exit"][res["bse"]])
        tracks.extend(res["tracks"])
        n += k
        b = np.concatenate(bse); s = np.concatenate(se)
        if n >= 2 * batch or n >= max_electrons:
            if _ci95(b) <= tol and _ci95(s) <= tol * max(float(s.mean()), 1.0):
                converged = True
                break
    b = np.concatenate(bse).astype(np.float64); s = np.concatenate(se); dmax = np.concatenate(depth)
    ee = np.concatenate(eexit) / e0
    hist_e = np.histogram(ee, bins=20, range=(0.0, 1.0))[0].astype(np.float64)
    tot = dose_z.sum()
    cum_r = np.cumsum(dose_r) / max(dose_r.sum(), 1e-300)
    return {
        "material": mat.name, "energy_kev": e0, "tilt_deg": tilt, "n_electrons": int(n), "converged": converged,
        "eta": float(b.mean()), "eta_ci95": _ci95(b),
        "se_yield": float(s.mean()), "se_yield_ci95": _ci95(s),
        "range_ko_nm": rko,
        "depth_max_nm": float(dmax.max()), "depth_p95_nm": float(np.percentile(dmax, 95)),
        "depth_p50_nm": float(np.percentile(dmax, 50)),
        "lateral_p95_nm": float(redges[1:][np.searchsorted(cum_r, 0.95)]),
        "depth_dose": np.stack([0.5 * (zedges[1:] + zedges[:-1]), dose_z / max(tot, 1e-300)], axis=1),
        "bse_energy": np.stack([np.linspace(0.025, 0.975, 20), hist_e / max(hist_e.sum(), 1.0)], axis=1),
        "tracks": tracks[: int(n_tracks)],
        "e_stop_kev": _e_stop(e0),
    }


def sem_se_universal_curve(e_over_emax=None):
    """二次電子収率の普遍曲線 δ/δmax = 1.28 (E/Emax)^−0.67 [1 − exp(−1.614 (E/Emax)^1.67)]。

    Lin & Joy 2005(Surf. Interface Anal. 37:895)が 44 元素の実測をまとめた形。
    最大値は E/Emax ≈ 1 で約 1.0(式の定数のまま。正規化はしない)。``e_over_emax`` を
    省くと 0.1〜30 の対数等間隔 64 点で返す(``signal``)。

    Examples
    --------
    >>> round(float(sem_se_universal_curve(1.0)), 3)
    1.025
    """
    if e_over_emax is None:
        e_over_emax = np.geomspace(0.1, 30.0, 64)
    x = np.asarray(e_over_emax, dtype=np.float64)
    if np.any(~np.isfinite(x)) or np.any(x <= 0):
        raise ValueError("sem_se_universal_curve: e_over_emax must be positive and finite")
    return 1.28 * x ** -0.67 * (1.0 - np.exp(-1.614 * x ** 1.67))


def sem_yield_curve(material="SI", energies_kev=None, *, n_electrons: int = 2000,
                    seed: int = 0) -> dict:
    """加速電圧を振って η(E) と δ(E) を MC で出し、δ の形を普遍曲線と比べる。

    δ の山の位置 Emax は、山の周りの 3 点に log E の放物線を当てて求める。
    ``universal`` は Lin & Joy 2005 の普遍曲線を、この MC の Emax・δmax で戻した値。
    ``shape_rms`` は E/Emax ∈ [0.25, 8] の点での δ/δmax と普遍曲線の差の RMS。

    Returns
    -------
    dict
        ``energies_kev`` / ``eta`` / ``se_yield`` / ``emax_kev`` / ``delta_max`` /
        ``universal`` / ``shape_rms`` / ``shape_max_abs``。

    Examples
    --------
    >>> r = sem_yield_curve("SI", [0.2, 0.4, 0.8, 1.6, 3.2], n_electrons=300)
    >>> r["emax_kev"] > 0.1 and len(r["se_yield"]) == 5
    True
    """
    op = "sem_yield_curve"
    if energies_kev is None:
        energies_kev = np.geomspace(0.1, 20.0, 16)
    es = np.array([_check_energy(e, op) for e in np.atleast_1d(energies_kev)])
    if es.size < 3:
        raise ValueError("%s: need at least 3 energies, got %d" % (op, es.size))
    es = np.sort(es)
    mat = _electron_material(material, op)
    geom = _ProfileGeom([0.0, 1.0], [0.0, 0.0], coll_window=1.0)
    eta, dl = [], []
    for i, e in enumerate(es):
        rng = np.random.default_rng(int(seed) + i)
        res = _transport([mat, mat], geom, np.zeros(int(n_electrons)), np.zeros(int(n_electrons)), e, rng)
        eta.append(float(res["bse"].mean())); dl.append(float(res["se"][:, 0].mean()))
    eta = np.array(eta); dl = np.array(dl)
    i = int(np.argmax(dl))
    if 0 < i < es.size - 1:
        lx = np.log(es[i - 1:i + 2]); c = np.polyfit(lx, dl[i - 1:i + 2], 2)
        lxm = -c[1] / (2 * c[0]) if c[0] < 0 else lx[1]
        emax = float(np.exp(np.clip(lxm, lx[0], lx[2])))
        dmax = float(np.polyval(c, np.log(emax)))
    else:
        emax, dmax = float(es[i]), float(dl[i])
    x = es / emax
    uni = dmax * sem_se_universal_curve(x)
    sel = (x >= 0.25) & (x <= 8.0)
    dev = (dl - uni)[sel] / dmax
    return {"material": mat.name, "energies_kev": es, "eta": eta, "se_yield": dl,
            "emax_kev": emax, "delta_max": dmax, "universal": uni,
            "shape_rms": float(np.sqrt(np.mean(dev ** 2))) if dev.size else float("nan"),
            "shape_max_abs": float(np.abs(dev).max()) if dev.size else float("nan")}


def _trapezoid(width_nm, height_nm, sidewall_deg, center_nm=0.0):
    """底辺の幅 ``width_nm`` の台形の線の節(z は下向き、上面は z = −height)。"""
    ang = min(float(sidewall_deg), 89.99)
    run = float(height_nm) / np.tan(np.radians(ang))
    half = 0.5 * float(width_nm)
    if run >= half:
        raise ValueError("line too narrow for this sidewall angle: top width would be <= 0")
    c = float(center_nm)
    return [c - half, c - half + run, c + half - run, c + half], [0.0, -height_nm, -height_nm, 0.0]


def sem_line_profile(line_material="PMMA", substrate="SI", energy_kev: float = 1.0, *,
                     width_nm: float = 40.0, height_nm: float = 40.0, sidewall_deg: float = 88.0,
                     beam_sigma_nm: float = 1.0, x_half_range_nm=None, x_step_nm: float = 1.0,
                     electrons_per_point: int = 200, buried=None, seed: int = 0) -> dict:
    """1 本の線(台形の断面)を横切って電子線を走査した線プロファイルを MC で出す(CD-SEM)。

    線は y に一様。底辺の幅 ``width_nm``・高さ ``height_nm``・側壁角 ``sidewall_deg``
    (90 = 垂直)の台形で、材料 ``line_material`` が基板 ``substrate`` の上に乗る
    (``height_nm = 0`` なら平らな基板)。ビームは幅 ``beam_sigma_nm`` のガウシアン、
    位置ごとに ``electrons_per_point`` 個を撃つ。``buried`` は基板に埋もれた矩形の列
    ``[(材料名, x0, x1, 上端の深さ, 下端の深さ), ...]`` [nm]。

    Returns
    -------
    dict
        ``x_nm`` / 検出器ごとの信号 ``se_total``・``inlens``・``everhart``・``bse``
        (電子 1 個あたり)/ ``eta`` / ``profile``(``pairs``: x と inlens)/
        真の寸法 ``width_bottom_nm``・``width_top_nm``・``width_mid_nm``。

    Examples
    --------
    >>> r = sem_line_profile(energy_kev=1.0, width_nm=30, height_nm=20, x_half_range_nm=30,
    ...                      x_step_nm=10, electrons_per_point=40)
    >>> r["profile"].shape
    (7, 2)
    """
    op = "sem_line_profile"
    e0 = _check_energy(energy_kev, op)
    width = _positive(width_nm, "width_nm", op)
    height = float(height_nm)
    if not np.isfinite(height) or height < 0:
        raise ValueError("%s: height_nm must be >= 0, got %r" % (op, height_nm))
    ang = float(sidewall_deg)
    if not (1.0 <= ang <= 90.0):
        raise ValueError("%s: sidewall_deg must be in [1, 90], got %r" % (op, sidewall_deg))
    sig = float(beam_sigma_nm)
    if not np.isfinite(sig) or sig < 0:
        raise ValueError("%s: beam_sigma_nm must be >= 0, got %r" % (op, beam_sigma_nm))
    step = _positive(x_step_nm, "x_step_nm", op)
    npp = int(electrons_per_point)
    if npp < 1:
        raise ValueError("%s: electrons_per_point must be >= 1" % op)
    mats = [_electron_material(line_material, op), _electron_material(substrate, op)]
    rows = []
    for b in (buried or ()):
        name, bx0, bx1, bz0, bz1 = b
        mats.append(_electron_material(name, op))
        rows.append((len(mats) - 1, float(bx0), float(bx1), float(bz0), float(bz1)))
    if height > 0:
        xk, zk = _trapezoid(width, height, ang)
        run = height / np.tan(np.radians(min(ang, 89.99)))
        w_top = width - 2 * run
    else:
        xk, zk = [-0.5 * width, 0.5 * width], [0.0, 0.0]
        w_top = width
    geom = _ProfileGeom(xk, zk, buried=rows)
    half = float(x_half_range_nm) if x_half_range_nm is not None else width
    xs = np.arange(-half, half + 0.5 * step, step)
    rng = np.random.default_rng(int(seed))
    x0 = np.repeat(xs, npp) + (sig * rng.standard_normal(xs.size * npp) if sig > 0 else 0.0)
    res = _transport(mats, geom, x0, np.zeros(x0.size), e0, rng)
    sg = _signals(res, e0).reshape(xs.size, npp, 4).mean(axis=1)
    eta = res["bse"].reshape(xs.size, npp).mean(axis=1)
    out = {"x_nm": xs, "eta": eta, "energy_kev": e0,
           "width_bottom_nm": width, "width_top_nm": float(w_top), "width_mid_nm": 0.5 * (width + w_top),
           "height_nm": height, "sidewall_deg": ang}
    for j, nm in enumerate(SEM_DETECTORS):
        out[nm] = sg[:, j]
    out["profile"] = np.stack([xs, sg[:, 1]], axis=1)
    return out


def sem_cd_measure(profile, *, method: str = "threshold", threshold: float = 0.5,
                   smooth_nm: float = 0.0) -> dict:
    """線プロファイル(``pairs``: x と信号)から線幅を出す(CD-SEM の 2 方式)。

    1 本の線の左右の縁は、それぞれ明るい山(縁の効果)になる。各山の**外側の斜面**で:

      * ``threshold``: 外側の地の水準 b と山の高さ p の間の ``b + t·(p − b)`` を横切る位置
        (線形補間)。t = ``threshold``(既定 0.5 = 50 % しきい値)。
      * ``max_slope``: 外側の斜面で勾配の絶対値が最大になる位置(3 点放物線で詰める)。

    地の水準は両端それぞれ外側 10 % の中央値。``smooth_nm > 0`` なら先にガウシアンで均す。

    Returns
    -------
    dict
        ``width_nm`` / ``left_nm`` / ``right_nm`` / ``method`` / ``threshold`` /
        ``peak_left_nm`` / ``peak_right_nm``。

    Examples
    --------
    >>> import numpy as np
    >>> x = np.arange(-50.0, 51.0)
    >>> y = 0.2 + np.exp(-0.5 * ((x + 20) / 3) ** 2) + np.exp(-0.5 * ((x - 20) / 3) ** 2)
    >>> r = sem_cd_measure(np.stack([x, y], axis=1), method="threshold", threshold=0.5)
    >>> bool(abs(r["width_nm"] - 2 * (20 + 3 * np.sqrt(2 * np.log(2)))) < 0.2)
    True
    """
    op = "sem_cd_measure"
    p = np.asarray(profile, dtype=np.float64)
    if p.ndim != 2 or p.shape[1] != 2 or p.shape[0] < 8:
        raise ValueError("%s: profile must be pairs (K>=8, 2), got shape %r" % (op, p.shape))
    if not np.isfinite(p).all():
        raise ValueError("%s: profile has non-finite values" % op)
    x, y = p[:, 0], p[:, 1].copy()
    if np.any(np.diff(x) <= 0):
        raise ValueError("%s: x must be strictly increasing" % op)
    if method not in ("threshold", "max_slope"):
        raise ValueError("%s: method must be 'threshold' or 'max_slope', got %r" % (op, method))
    t = float(threshold)
    if not (0.0 < t < 1.0):
        raise ValueError("%s: threshold must be in (0, 1), got %r" % (op, threshold))
    dx = float(np.median(np.diff(x)))
    if smooth_nm and float(smooth_nm) > 0:
        y = _ndi.gaussian_filter1d(y, float(smooth_nm) / dx, mode="nearest")
    n = y.size
    mid = n // 2
    il = int(np.argmax(y[:mid])); ir = mid + int(np.argmax(y[mid:]))
    m10 = max(1, n // 10)
    bl, br = float(np.median(y[:m10])), float(np.median(y[-m10:]))
    if not (y[il] > bl and y[ir] > br):
        raise ValueError("%s: no edge peaks above the background" % op)

    def _cross(i0, i1, level):
        # i0 → i1 の向きに走り、level を最初に越える区間で線形補間。
        stepi = 1 if i1 > i0 else -1
        for i in range(i0, i1, stepi):
            a, b = y[i], y[i + stepi]
            if (a - level) * (b - level) <= 0 and a != b:
                f = (level - a) / (b - a)
                return float(x[i] + f * (x[i + stepi] - x[i]))
        raise ValueError("%s: threshold level not crossed on the outer flank" % op)

    def _maxslope(lo, hi):
        g = np.gradient(y, x)
        seg = np.abs(g[lo:hi + 1])
        k = lo + int(np.argmax(seg))
        if 0 < k < n - 1:
            a, b, c = abs(g[k - 1]), abs(g[k]), abs(g[k + 1])
            den = a - 2 * b + c
            off = 0.5 * (a - c) / den if den != 0 else 0.0
            return float(x[k] + np.clip(off, -0.5, 0.5) * dx)
        return float(x[k])

    if method == "threshold":
        left = _cross(0, il, bl + t * (y[il] - bl))
        right = _cross(n - 1, ir, br + t * (y[ir] - br))
    else:
        left = _maxslope(0, il)
        right = _maxslope(ir, n - 1)
    return {"width_nm": right - left, "left_nm": left, "right_nm": right, "method": method,
            "threshold": t if method == "threshold" else None,
            "peak_left_nm": float(x[il]), "peak_right_nm": float(x[ir])}


#: 検出器ごとの既定の利得(電子 1 個あたりの信号 → [0,1] の固定の線形写像)。
_IMAGE_GAIN = {"inlens": 0.35, "everhart": 0.3, "se_total": 0.3, "bse": 1.5}


def sem_image(height, material_map=None, *, materials=("SI",), substrate="SI",
              energy_kev: float = 5.0, pixel_nm: float = 2.0, beam_sigma_nm: float = 1.0,
              electrons_per_pixel: int = 30, detector: str = "inlens", layer_bottom_nm=0.0,
              buried=None, gain=None, seed: int = 0, return_signals: bool = False):
    """高さ場と材料の地図から、画素ごとに電子を撃って SEM 像を作る(MC の直接計算)。

    各画素に ``electrons_per_pixel`` 個の一次電子(ビーム幅 ``beam_sigma_nm`` のガウシアン)
    を撃ち、検出器の信号を電子 1 個あたりで平均する。**雑音は撃った電子の数そのもの**
    (反射電子も二次電子も 1 個ずつの統計)なので、別のポアソン雑音は載せない。

    Parameters
    ----------
    height : array_like
        (H, W) の高さ場 [nm] (上が正)。
    material_map : array_like of int, optional
        (H, W) の材料番号(``materials`` の添字)。表面から ``layer_bottom_nm`` までの柱の
        材料。それより深い所は ``substrate``。``None`` は全部 ``materials[0]``。
    materials : sequence of str
        材料表の名前の列。
    substrate : str
        基板の材料。
    energy_kev, pixel_nm, beam_sigma_nm : float
        加速電圧 [keV]・画素の一辺 [nm]・ビームの σ [nm]。
    electrons_per_pixel : int
        画素あたりの一次電子の数(像の S/N を決める)。
    detector : str
        ``inlens``(レンズ内の二次電子)/ ``everhart``(側方の二次電子、+x 側、SE3 込み)/
        ``bse``(真上の環状の反射電子、エネルギー重み)/ ``se_total``(検出器なしの全収率)。
    layer_bottom_nm : float or array_like
        材料の柱の下端の z [nm] (0 = 基板の上面。正は基板の中へ)。
    buried : list, optional
        埋もれた箱 ``[(材料名, (H, W) のマスク, 上端の深さ, 下端の深さ), ...]`` [nm]。
    gain : float, optional
        信号 → [0,1] の固定の倍率(既定は検出器ごとの定数。画像ごとに正規化しない)。
    seed : int
        乱数の種。
    return_signals : bool
        True なら像の代わりに dict(4 検出器の信号の地図と η の地図)を返す。

    Returns
    -------
    numpy.ndarray
        (H, W) の float64、[0,1]。

    Examples
    --------
    >>> import numpy as np
    >>> img = sem_image(np.zeros((6, 6)), energy_kev=1.0, electrons_per_pixel=5)
    >>> img.shape, bool(0.0 <= img.min() and img.max() <= 1.0)
    ((6, 6), True)
    """
    op = "sem_image"
    h = _as_height(height, op)
    e0 = _check_energy(energy_kev, op)
    p = _positive(pixel_nm, "pixel_nm", op)
    sig = float(beam_sigma_nm)
    if not np.isfinite(sig) or sig < 0:
        raise ValueError("%s: beam_sigma_nm must be >= 0, got %r" % (op, beam_sigma_nm))
    if detector not in SEM_DETECTORS:
        raise ValueError("%s: detector must be one of %s, got %r" % (op, SEM_DETECTORS, detector))
    npp = int(electrons_per_pixel)
    if npp < 1:
        raise ValueError("%s: electrons_per_pixel must be >= 1" % op)
    names = [str(m) for m in (materials if not isinstance(materials, str) else (materials,))]
    if not names:
        raise ValueError("%s: materials is empty" % op)
    mats = [_electron_material(m, op) for m in names]
    if material_map is None:
        labels = np.zeros(h.shape, dtype=np.int64)
    else:
        labels = np.asarray(material_map)
        if labels.shape != h.shape:
            raise ValueError("%s: material_map shape %r != height shape %r" % (op, labels.shape, h.shape))
        if not np.issubdtype(labels.dtype, np.integer):
            raise ValueError("%s: material_map must be integer labels" % op)
        labels = labels.astype(np.int64)
        if labels.min() < 0 or labels.max() >= len(mats):
            raise ValueError("%s: material_map labels must be in [0, %d)" % (op, len(mats)))
    mats.append(_electron_material(substrate, op))
    sub_idx = len(mats) - 1
    bottom = np.broadcast_to(np.asarray(layer_bottom_nm, dtype=np.float64), h.shape).copy()
    if not np.isfinite(bottom).all():
        raise ValueError("%s: layer_bottom_nm must be finite" % op)
    rows = []
    for b in (buried or ()):
        name, mask, bz0, bz1 = b
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != h.shape:
            raise ValueError("%s: buried mask shape %r != height shape %r" % (op, mask.shape, h.shape))
        mats.append(_electron_material(name, op))
        rows.append((len(mats) - 1, mask, float(bz0), float(bz1)))
    geom = _HeightGeom(h, p, labels, bottom, sub_idx, rows, max(m.lam_se for m in mats))
    H, W = h.shape
    rng = np.random.default_rng(int(seed))
    jj, ii = np.meshgrid(np.arange(W), np.arange(H))
    x0 = np.repeat(jj.ravel() * p, npp)
    y0 = np.repeat(ii.ravel() * p, npp)
    if sig > 0:
        x0 = x0 + sig * rng.standard_normal(x0.size)
        y0 = y0 + sig * rng.standard_normal(y0.size)
    res = _transport(mats, geom, x0, y0, e0, rng)
    sg = _signals(res, e0).reshape(H * W, npp, 4).mean(axis=1).reshape(H, W, 4)
    if return_signals:
        out = {nm: sg[..., j] for j, nm in enumerate(SEM_DETECTORS)}
        out["eta"] = res["bse"].reshape(H * W, npp).mean(axis=1).reshape(H, W)
        return out
    g = _IMAGE_GAIN[detector] if gain is None else _positive(gain, "gain", op)
    return np.clip(sg[..., SEM_DETECTORS.index(detector)] * g, 0.0, 1.0)


def sem_se_escape_fraction(potential_v=None, *, phi_ev: float = 2.0):
    """正に帯電した面(電位 V > 0)から、二次電子が出ていける割合 F(V)。

    二次電子のエネルギー分布を Chung-Everhart の f(E) ∝ E / (E + φ)⁴ とし、E > V の
    割合を閉形式で積分した F(V) = φ² (3u − 2φ) / u³(u = V + φ)。F(0) = 1、V → ∞ で 0。
    V ≤ 0 は 1(負の面は二次電子を押し出す側。明るくなる分は ``sem_charging_series`` が別に扱う)。
    ``potential_v`` を省くと 0〜20 V の 41 点で返す(``signal``)。

    Examples
    --------
    >>> float(sem_se_escape_fraction(0.0)), round(float(sem_se_escape_fraction(2.0)), 4)
    (1.0, 0.5)
    """
    phi = _positive(phi_ev, "phi_ev", "sem_se_escape_fraction")
    if potential_v is None:
        potential_v = np.linspace(0.0, 20.0, 41)
    v = np.asarray(potential_v, dtype=np.float64)
    if not np.isfinite(v).all():
        raise ValueError("sem_se_escape_fraction: potential_v must be finite")
    u = np.maximum(v, 0.0) + phi
    return phi * phi * (3.0 * u - 2.0 * phi) / u ** 3


#: 負の帯電で二次電子が押し出されて明るくなる分の現象論の 2 定数(上限の倍率と、半分になる電位 [V])。
#: 一次資料の値ではない —— 公開引数にしないのは、測って決めた量のように見せないため。
_NEG_GAIN = 1.0
_NEG_SCALE_V = 20.0


def sem_charging_series(height, material_map=None, *, materials=("PMMA",), substrate="SI",
                        energy_kev: float = 1.0, pixel_nm: float = 2.0, beam_sigma_nm: float = 1.0,
                        electrons_per_pixel: int = 30, detector: str = "inlens", frames: int = 12,
                        layer_bottom_nm=0.0, volts_per_electron: float = 0.05, leak_frames: float = 0.0,
                        spread_px: float = 1.0, phi_ev: float = 2.0, gain=None, seed: int = 0,
                        return_potential: bool = False):
    """絶縁物の帯電を走査のコマごとに進め、像の時間変化(``video``、(T, H, W))を返す。

    1 コマで画素あたり ``electrons_per_pixel`` 個の電子が入り、η + δ·F(V) 個が出ていく。
    差し引き 1 − η − δ·F(V) 個が絶縁物の面に溜まり、電位を ``volts_per_electron`` [V/個]
    ずつ動かす(負の電子が溜まれば V は下がる)。電位は ``spread_px`` で横に広がり、
    ``leak_frames``(> 0 なら)の時定数で抜ける。導体の面は接地(V = 0)。

    * **正の帯電**(η + δ > 1、低加速で多い): 二次電子が面に引き戻され(F(V)、
      :func:`sem_se_escape_fraction`)、像は暗くなる。放出が減ると正味の流れも 0 に
      近づくので、電位は η + δ·F(V*) = 1 の V* で止まる(自己調整)。
    * **負の帯電**(η + δ < 1、高加速): 面の負の電位が二次電子を押し出し、像は
      ``1 + |V| / (|V| + 20 V)`` 倍に明るくなる(★現象論の式で、2 定数は固定 ——
      ``_NEG_GAIN``・``_NEG_SCALE_V``。
      着地エネルギーの低下とビームの曲がりは入れない)。

    η と δ は :func:`sem_image` のモンテカルロ(``return_signals``)で 1 回だけ求め、
    コマごとの雑音は検出された電子の数のポアソンで載せる。

    Returns
    -------
    numpy.ndarray
        (frames, H, W) の float64、[0,1] (``sem_image`` と同じ固定の倍率)。
        ``return_potential`` なら dict(``video`` と、コマごとの電位 ``potential_v`` (T, H, W)、
        絶縁物の面のマスク ``insulator``)。

    Examples
    --------
    >>> import numpy as np
    >>> v = sem_charging_series(np.zeros((4, 4)), materials=("PMMA",), substrate="PMMA",
    ...                         electrons_per_pixel=5, frames=3)
    >>> v.shape
    (3, 4, 4)
    """
    op = "sem_charging_series"
    h = _as_height(height, op)
    nfr = int(frames)
    if nfr < 1:
        raise ValueError("%s: frames must be >= 1" % op)
    vpe = _positive(volts_per_electron, "volts_per_electron", op)
    leak = float(leak_frames)
    if not np.isfinite(leak) or leak < 0:
        raise ValueError("%s: leak_frames must be >= 0 (0 = no leakage)" % op)
    spread = float(spread_px)
    if not np.isfinite(spread) or spread < 0:
        raise ValueError("%s: spread_px must be >= 0" % op)
    phi = _positive(phi_ev, "phi_ev", op)
    sig = sem_image(h, material_map, materials=materials, substrate=substrate, energy_kev=energy_kev,
                    pixel_nm=pixel_nm, beam_sigma_nm=beam_sigma_nm, electrons_per_pixel=electrons_per_pixel,
                    detector=detector, layer_bottom_nm=layer_bottom_nm, seed=seed, return_signals=True)
    names = [str(m) for m in (materials if not isinstance(materials, str) else (materials,))]
    ins_of = [_electron_material(m, op).insulator for m in names]
    sub_ins = _electron_material(substrate, op).insulator
    labels = np.zeros(h.shape, dtype=np.int64) if material_map is None else np.asarray(material_map).astype(np.int64)
    bottom = np.broadcast_to(np.asarray(layer_bottom_nm, dtype=np.float64), h.shape)
    in_layer = -h < bottom                                    # 面が材料の柱の中にある
    insulator = np.where(in_layer, np.array(ins_of)[labels], sub_ins)
    eta, delta, s_det = sig["eta"], sig["se_total"], sig[detector]
    se_part = s_det if detector != "bse" else np.zeros_like(s_det)
    g = _IMAGE_GAIN[detector] if gain is None else _positive(gain, "gain", op)
    npp = float(electrons_per_pixel)
    rng = np.random.default_rng(int(seed) + 1)
    v = np.zeros(h.shape)
    video = np.empty((nfr,) + h.shape)
    pots = np.empty((nfr,) + h.shape)
    decay = np.exp(-1.0 / leak) if leak > 0 else 1.0
    for t in range(nfr):
        f = sem_se_escape_fraction(v, phi_ev=phi)
        boost = 1.0 + _NEG_GAIN * np.maximum(-v, 0.0) / (np.maximum(-v, 0.0) + _NEG_SCALE_V)
        mean = s_det - se_part + se_part * f * boost
        counts = rng.poisson(np.clip(mean, 0.0, None) * npp)
        video[t] = np.clip(counts / npp * g, 0.0, 1.0)
        pots[t] = v
        net = 1.0 - eta - delta * f                             # 溜まる電子の数(1 個あたり)
        v = v * decay - vpe * npp * net
        if spread > 0:
            v = _ndi.gaussian_filter(v, spread, mode="nearest")
        v = np.where(insulator, v, 0.0)
    if return_potential:
        return {"video": video, "potential_v": pots, "insulator": insulator}
    return video
