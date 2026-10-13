# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Pulse-echo ultrasound in layered stacks and scanning acoustic microscopy (SAM) C-scans (numpy + scipy).

貼り合わせた積層(ハイブリッド接合のダイ・ウェーハ)の中の**空洞(ボイド)**を、超音波の
エコーの**位相**で見つける。反射の振幅だけを見る C スキャンでは、小さなボイド(ビームより
小さく、反射が面積で薄まる)と銅のパッド(強い反射体)が同じ明るさに写る。ところが
エコーの符号は違う: 音響インピーダンスが**下がる**界面(Si → 空気)では圧力の反射係数
``R = (Z2 − Z1)/(Z2 + Z1)`` が負になり、エコーが**反転**する。符号は面積で薄まらない。

7 つの op(並びは物理の順):

  * :func:`acoustic_material_table` — 材料の表(密度 ρ・縦波音速 c・Z = ρc・減衰
    ``α(f) = α0 f^n``)と、**値ごとの出典と確かめたかどうかの印**。
  * :func:`acoustic_layer_stack` — 結合液(水)・層(材料, 厚さ)の列・基板(半無限)の積層。
    確かめていない材料は ``allow_unverified=True`` を言わない限り拒む。
  * :func:`acoustic_interface_coefficients` — 界面ごとの R・T・エネルギー保存・反転の印。
  * :func:`pulse_echo_ascan` — 広帯域パルス(ガウス型スペクトル)の垂直入射平面波の
    A スキャン。積層の応答は**伝達行列**(Thomson 1950 / Haskell 1953 の流儀、流体近似の
    縦波だけ)、水の往復の伝搬と減衰 ``exp(−2 α_w(f) z_w)`` を含む。
  * :func:`sam_cscan` — 集束探触子の C スキャン。接合面の 2-D の地図(ラベル = 積層の種類)
    を周波数ごとのガウス PSF(半値全幅 ``k_res · λ_w(f) · F#``)でぼかし、時間ゲートの中の
    包絡線の山で**振幅像**、基準(表面エコー)に対する解析信号の位相で**位相像**、その
    同相成分で**符号つき像**を返す。
  * :func:`echo_phase_polarity` — エコーを位相で 3 つに分ける: 同相(Z が上がる)・反転
    (Z が下がる)・直交(薄い層の微分形のエコー。1 点の符号は意味を持たない)。
  * :func:`sam_frequency_tradeoff` — 横分解能(∝ 1/f)と減衰(∝ exp(−2∫α(f)))の取引。
    大きさ a のボイドの信号 ``S(f) = (1 − 2^{−(a/w(f))²}) · exp(−β f²)`` を最大にする周波数を、
    減衰がすべて f² のとき**閉形式** ``f* = (k/a)·sqrt(log2(1 + a² ln2 / (β k²)))``
    (``k = k_res c_w F#``、``w = k/f``)で、そうでなければ数値で。

約束(単位はすべて SI): 厚さ・距離・画素は **m**、周波数は **Hz**、時間は **s**、
減衰 α0 は **Np/m/Hz^n**、インピーダンスは **Rayl = kg/(m² s)**。µm を m の場所に渡すと
桁が 6 つずれるので、厚さ 1 m 超・周波数 10 GHz 超は拒む。
符号の約束: 圧力の反射係数 ``R = (Z2 − Z1)/(Z2 + Z1)``、透過係数 ``T = 2 Z2/(Z1 + Z2)``、
エネルギー保存は ``R² + (Z1/Z2) T² = 1``。時間の約束: ``x(t) = Σ X(f) e^{+i2πft}``、
伝搬は ``e^{−ikz}``、損失は ``k = 2πf/c − iα(f)``。振幅の単位: 焦点に置いた**完全反射体**
(水の損失なし)のエコーの包絡線の山が 1。

真値(``tests/test_ultrasound.py`` の門):
  * 界面: ``R² + (Z1/Z2)T² = 1``、符号は ``Z2 < Z1`` のときに限り負。
  * 伝達行列の A スキャン = 独立な計算(下から積み上げる多重反射の Airy 再帰、
    時間領域の経路の和)と一致。単層の λ/2 層は透明、``Z = sqrt(Z0 Z2)`` の λ/4 層は無反射。
    光学の薄膜の Airy 式(``matappear.thin_film_reflectance``、n ↔ Z の写像)とも一致。
  * 減衰: 2 つの厚さの裏面エコーのスペクトル比から α(f) のべき乗則を取り戻す。
  * 横分解能: 点反射体の像の半値全幅が ``λ_w · F#`` に比例(周波数の log-log 傾き −1)。

★正直に書いておくこと(範囲):
  * 1-D の平面波・垂直入射・縦波だけの層モデル。モード変換(横波)・表面波・斜入射の
    角度スペクトル(V(z) 曲線)は入っていない。集束は**ガウスの横 PSF を周波数ごとに掛ける**
    近似で、平らな水/Si 界面で屈折したビームの収差(焦点ずれ・球面収差)は無視する。
    横の空間周波数は平らな界面で保存されるので、埋もれた面の横分解能は**水側の**
    波長と開口で決まる(この近似の中では厳密)。開口が Si の臨界角(縦波)を超える
    ``F#`` は、超えた分の光線が横波・表面波に化けるのでこのモデルの外 —— 拒む。
  * 表面粗さ・層の厚さむら・界面の部分接触(Baik & Thompson 1984 のばねモデル、
    弱い接合・kissing bond)は入っていない。ボイドは**薄い空気の層**で表す
    (ギャップ 0.1 µm 程度は平均自由行程と同程度で連続体の近似は怪しいが、反射は
    数 nm 以上ならほぼ −1 で、ギャップの値にほとんど依らない)。
  * 減衰の分散(Kramers–Kronig)は入れず、インピーダンスは実数のまま。
  * 材料定数は下の表の出典どおり(読んだ一次・二次情報)。Si の減衰は確かめた値が
    無いので 0(100 µm 程度の Si では水の経路の損失が支配的だという想定 —— 確かめていない)。
    ポリイミド・エポキシは**確かめていない代表値**で、既定では使えない。

出典(手法): W. T. Thomson, J. Appl. Phys. 21:89, 1950(層の行列法、抄録で確認)/
M. J. S. Lowe, IEEE TUFFC 42(4):525, 1995(行列法のレビュー、抄録で確認)/
R. A. Lemons & C. F. Quate, Appl. Phys. Lett. 24:163, 1974(走査型音響顕微鏡、抄録で確認)/
S. C. Hwang, 2013(位相反転で剥離を判定するアルゴリズムが装置・探触子・操作者に依存する
という報告、抄録で確認)/ MIL-HDBK-1823A(POD は ``pod`` モジュール)。閉形式
(伝達行列・界面係数・ガウス PSF・最適周波数)は本文を読まずに第一原理から導いた。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "acoustic_material_table",
    "acoustic_layer_stack",
    "acoustic_interface_coefficients",
    "pulse_echo_ascan",
    "sam_cscan",
    "echo_phase_polarity",
    "sam_frequency_tradeoff",
]

#: 1 本の積層に置ける層の数の上限。
MAX_LAYERS = 256
#: C スキャンの地図の画素数の上限(パディング前)。
MAX_MAP_PIXELS = 1 << 20
#: C スキャンで使える積層の種類(ラベル)の数の上限。
MAX_CLASSES = 64
#: A スキャンのサンプル数の上限。
MAX_SAMPLES = 1 << 20
#: C スキャンで和を取る周波数の本数の上限(作業量を確保する前に拒む)。
MAX_BINS = 4096
#: Np → dB。
DB_PER_NP = 20.0 / math.log(10.0)
#: ガウスの半値全幅 / 標準偏差。
FWHM_PER_SIGMA = 2.0 * math.sqrt(2.0 * math.log(2.0))


def _cl_from_E_nu(E, nu, rho):
    """等方弾性体の縦波音速 ``sqrt(E(1−ν) / (ρ(1+ν)(1−2ν)))``。"""
    return math.sqrt(E * (1.0 - nu) / (rho * (1.0 + nu) * (1.0 - 2.0 * nu)))


def _cl_from_K_G(K, G, rho):
    """等方弾性体の縦波音速 ``sqrt((K + 4G/3) / ρ)``。"""
    return math.sqrt((K + 4.0 * G / 3.0) / rho)


# --------------------------------------------------------------------------- #
# 材料の表 —— 値ごとに出典と「確かめたか」の印
# --------------------------------------------------------------------------- #
#: 水の減衰: 2.17e-3 dB/(cm·MHz²)(Szabo 2004 のべき乗則。オープンソースの k-Wave の
#: attenuationWater の説明文が Pinkerton 1949 の多項式と並べて引いている)→ Np/m/Hz²。
_WATER_ALPHA0 = 2.17e-3 / DB_PER_NP * 100.0 / 1.0e12

_MATERIALS = {
    "water": {
        "rho": 998.0, "c": 1481.0, "alpha0": _WATER_ALPHA0, "alpha_n": 2.0, "verified": True,
        "source": "c = 1481 m/s at 20 C (Wikipedia 'Speed of sound', fresh water); rho = 998 kg/m3 "
                  "lies between the tabulated 999.84 (0 C) and 997.05 (25 C) of Wikipedia "
                  "'Properties of water' (interpolated, +-0.2 %%); attenuation 2.17e-3 dB/(cm MHz^2) "
                  "(Szabo 2004 power law, as quoted beside Pinkerton 1949 in the open-source k-Wave "
                  "attenuationWater help) = %.4g Np/(m Hz^2)" % _WATER_ALPHA0,
        "uncertainty": "c and rho ~0.2 % (temperature: c moves ~3 m/s per K near 20 C); alpha ~10 %",
    },
    "silicon": {
        "rho": 2329.0, "c": 8430.0, "alpha0": 0.0, "alpha_n": 2.0, "verified": True,
        "source": "[100] longitudinal V_L = sqrt(C11/rho) = 8.43e5 cm/s with C11 = 16.60e11 dyn/cm2 "
                  "(McSkimin 1953) and rho = 2.329 g/cm3, Ioffe Institute NSM database 'Si - "
                  "mechanical properties'. Attenuation NOT verified: set to 0 (assumption)",
        "uncertainty": "c, rho < 1 % for [100]; [110]/[111] are 9.13e5 / 9.36e5 cm/s (anisotropy); "
                       "attenuation unverified",
    },
    "sio2": {
        "rho": 2203.0, "c": _cl_from_E_nu(71.7e9, 0.17, 2203.0), "alpha0": 0.0, "alpha_n": 2.0,
        "verified": True,
        "source": "fused silica: rho = 2.203 g/cm3, E = 71.7 GPa, nu = 0.17 (Wikipedia 'Fused quartz'); "
                  "c = sqrt(E(1-nu)/(rho(1+nu)(1-2nu))) computed here. Attenuation set to 0 (thin layers)",
        "uncertainty": "bulk fused silica; deposited bonding oxides (PECVD, thermal) differ by an "
                       "unverified amount - treat as representative",
    },
    "copper": {
        "rho": 8935.0, "c": _cl_from_K_G(140e9, 48e9, 8935.0), "alpha0": 0.0, "alpha_n": 1.0,
        "verified": True,
        "source": "rho = 8.935 g/cm3 at 20 C, bulk modulus 140 GPa, shear modulus 48 GPa "
                  "(Wikipedia 'Copper' infobox); c = sqrt((K + 4G/3)/rho) computed here. "
                  "Attenuation set to 0 (micrometre layers)",
        "uncertainty": "polycrystalline average; the same infobox gives E = 110-128 GPa, nu = 0.34, "
                       "which spans c = 4.4-4.8 km/s - about +-5 %",
    },
    "air": {
        "rho": 1.2041, "c": 343.0, "alpha0": 0.0, "alpha_n": 2.0, "verified": True,
        "source": "c = 343 m/s and rho = 1.2041 kg/m3 at 20 C (Wikipedia 'Speed of sound'). "
                  "Attenuation irrelevant for sub-micrometre gaps (set to 0)",
        "uncertainty": "continuum value; a 0.1 um gap is comparable to the mean free path, but the "
                       "echo is ~-1 for any gap above a few nm",
    },
    "polyimide": {
        "rho": 1420.0, "c": 2300.0, "alpha0": 1.0e-6, "alpha_n": 1.0, "verified": False,
        "source": "UNVERIFIED representative placeholder (no freely readable primary source was "
                  "read). Pass allow_unverified=True and replace with your own measured values",
        "uncertainty": "unknown",
    },
    "epoxy_underfill": {
        "rho": 1800.0, "c": 2800.0, "alpha0": 2.0e-6, "alpha_n": 1.0, "verified": False,
        "source": "UNVERIFIED representative placeholder for a filled epoxy (no source read). Pass "
                  "allow_unverified=True and replace with your own measured values",
        "uncertainty": "unknown",
    },
}


# --------------------------------------------------------------------------- #
# 入力の検証(fail-closed)
# --------------------------------------------------------------------------- #
def _num(v, name, op, lo=None, hi=None, lo_open=True, hi_open=False):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v))
    v = float(v)
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, v))
    if lo is not None and (v < lo or (lo_open and v == lo)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, ">" if lo_open else ">=", lo, v))
    if hi is not None and (v > hi or (hi_open and v == hi)):
        raise ValueError("%s: %s must be %s %g, got %g" % (op, name, "<" if hi_open else "<=", hi, v))
    return v


def _int(v, name, op, lo, hi):
    if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)):
        raise ValueError("%s: %s must be an integer, got %r" % (op, name, v))
    v = int(v)
    if not lo <= v <= hi:
        raise ValueError("%s: %s must be in [%d, %d], got %d" % (op, name, lo, hi, v))
    return v


def _material(spec, op, allow_unverified):
    """材料名(表の鍵)か、``{"rho", "c"[, "alpha0", "alpha_n", "name"]}`` の dict。"""
    if isinstance(spec, str):
        key = spec.strip().lower()
        if key not in _MATERIALS:
            raise ValueError("%s: unknown material %r (known: %s; or pass a dict with rho and c)"
                             % (op, spec, ", ".join(sorted(_MATERIALS))))
        m = dict(_MATERIALS[key])
        if not m["verified"] and not allow_unverified:
            raise ValueError("%s: material %r has unverified constants (%s); pass "
                             "allow_unverified=True to use it knowingly" % (op, key, m["source"]))
        m["name"] = key
        m["Z"] = m["rho"] * m["c"]
        return m
    if isinstance(spec, dict):
        for k in ("rho", "c"):
            if k not in spec:
                raise ValueError("%s: a custom material needs %r" % (op, k))
        rho = _num(spec["rho"], "rho", op, 0.0, 1.0e5)
        c = _num(spec["c"], "c", op, 0.0, 1.0e5)
        a0 = _num(spec.get("alpha0", 0.0), "alpha0", op, 0.0, None, lo_open=False)
        an = _num(spec.get("alpha_n", 2.0), "alpha_n", op, 0.0, 4.0, lo_open=False)
        name = spec.get("name", "custom")
        if not isinstance(name, str):
            raise ValueError("%s: material name must be a string" % op)
        return {"name": name, "rho": rho, "c": c, "Z": rho * c, "alpha0": a0, "alpha_n": an,
                "verified": "user", "source": "user-supplied", "uncertainty": "user-supplied"}
    raise ValueError("%s: a material is a name or a dict, got %r" % (op, type(spec).__name__))


def _stack(stack, op):
    if not isinstance(stack, dict) or stack.get("kind") != "acoustic_stack":
        raise ValueError("%s: expected an acoustic_layer_stack table (kind='acoustic_stack')" % op)
    return stack


def _alpha(m, f):
    """α(f) [Np/m]。f は Hz の配列。"""
    if m["alpha0"] == 0.0:
        return np.zeros_like(f, dtype=np.float64)
    return m["alpha0"] * np.power(f, m["alpha_n"])


def _freq_range(f0, bw, op):
    f0 = _num(f0, "f0", op, 0.0, 1.0e10)
    bw = _num(bw, "bandwidth", op, 0.02, 1.5)
    sig = bw * f0 / FWHM_PER_SIGMA            # −6 dB(振幅 1/2)の全幅 = bw · f0
    return f0, bw, sig


# --------------------------------------------------------------------------- #
# 材料の表と積層
# --------------------------------------------------------------------------- #
def acoustic_material_table():
    """Built-in acoustic material table: density, longitudinal speed, impedance Z = rho*c, attenuation alpha0*f^n, with a source and a verified flag per entry (``table``).

    返り: ``{"kind": "acoustic_materials", "materials": {name: {rho, c, Z, alpha0, alpha_n,
    verified, source, uncertainty}}}``。``verified`` が False の材料は代表値の置き場で、
    :func:`acoustic_layer_stack` は ``allow_unverified=True`` が無い限り拒む。
    単位: rho [kg/m³]、c [m/s]、Z [Rayl]、alpha0 [Np/m/Hz^n]。
    Raises: 何も拒まない(引数が無い)。返す dict は毎回の複製で、書き換えても表は変わらない。
    """
    out = {}
    for k, m in _MATERIALS.items():
        e = dict(m)
        e["Z"] = m["rho"] * m["c"]
        out[k] = e
    return {"kind": "acoustic_materials", "materials": out}


def acoustic_layer_stack(layers=(("silicon", 100e-6), ("sio2", 2e-6)), substrate="silicon",
                         couplant="water", allow_unverified=False):
    """Layered stack for normal-incidence pulse-echo: couplant, layers (material, thickness in m) from the top, and a half-space substrate (``table``).

    ``layers`` は ``[(材料, 厚さ [m]), ...]``(上から)。材料は表の名前
    (:func:`acoustic_material_table`)か ``{"rho", "c", "alpha0", "alpha_n", "name"}`` の dict。
    層は 0 枚でもよい(結合液と基板の 1 界面)。返りの ``interfaces`` は上から
    ``couplant|layer0``, ``layer0|layer1``, …, ``layerN-1|substrate`` の名前、``t_interfaces`` は
    最初の界面からの往復時間 [s] で ``2 Σ d_j / c_j``、``depth`` はその深さ [m]。

    Raises ValueError: 厚さが 0 以下・1 m 超・非有限、未知の材料、確かめていない材料
    (``allow_unverified`` 無し)、ρ・c が 0 以下、減衰が負、層が 256 枚超。
    """
    op = "acoustic_layer_stack"
    if isinstance(allow_unverified, (bool, np.bool_)):
        allow = bool(allow_unverified)
    else:
        raise ValueError("%s: allow_unverified must be a bool" % op)
    try:
        items = list(layers)
    except TypeError:
        raise ValueError("%s: layers must be a sequence of (material, thickness)" % op) from None
    if len(items) > MAX_LAYERS:
        raise ValueError("%s: at most %d layers, got %d" % (op, MAX_LAYERS, len(items)))
    out_layers = []
    for i, it in enumerate(items):
        try:
            spec, d = it
        except (TypeError, ValueError):
            raise ValueError("%s: layer %d must be (material, thickness_m)" % (op, i)) from None
        m = _material(spec, op, allow)
        m["thickness"] = _num(d, "thickness of layer %d" % i, op, 0.0, 1.0)
        out_layers.append(m)
    cpl = _material(couplant, op, allow)
    sub = _material(substrate, op, allow)
    names = [cpl["name"]] + [m["name"] for m in out_layers] + [sub["name"]]
    t, z, tt, zz = [0.0], [0.0], 0.0, 0.0
    for m in out_layers:
        tt += 2.0 * m["thickness"] / m["c"]
        zz += m["thickness"]
        t.append(tt)
        z.append(zz)
    return {"kind": "acoustic_stack", "couplant": cpl, "layers": out_layers, "substrate": sub,
            "interfaces": ["%s|%s" % (a, b) for a, b in zip(names[:-1], names[1:])],
            "t_interfaces": np.array(t), "depth": np.array(z),
            "verified": all(m["verified"] is True for m in [cpl, sub] + out_layers)}


def acoustic_interface_coefficients(stack):
    """Pressure reflection/transmission at every interface of a stack, energy check R^2 + (Z1/Z2) T^2 = 1, and the phase-inversion flag Z2 < Z1 (``table``).

    ``R = (Z2 − Z1)/(Z2 + Z1)``(圧力)、``T = 2 Z2/(Z1 + Z2)``。``R < 0`` ⇔ ``Z2 < Z1``
    (エコーの反転)。半無限どうしの界面の値で、薄い層の多重反射は入らない
    (それは :func:`pulse_echo_ascan`)。返り: ``names`` ``z1`` ``z2`` ``R`` ``T`` ``energy``
    ``inverted`` ``t_interfaces`` ``depth``。
    Raises ValueError: 印(kind='acoustic_stack')の無い table。
    """
    op = "acoustic_interface_coefficients"
    s = _stack(stack, op)
    media = [s["couplant"]] + list(s["layers"]) + [s["substrate"]]
    z = np.array([m["Z"] for m in media], dtype=np.float64)
    z1, z2 = z[:-1], z[1:]
    R = (z2 - z1) / (z2 + z1)
    T = 2.0 * z2 / (z1 + z2)
    return {"kind": "acoustic_interfaces", "names": list(s["interfaces"]), "z1": z1, "z2": z2,
            "R": R, "T": T, "energy": R ** 2 + (z1 / z2) * T ** 2, "inverted": z2 < z1,
            "t_interfaces": np.array(s["t_interfaces"]), "depth": np.array(s["depth"])}


def _stack_reflection(s, f):
    """積層の入力反射係数 R(f)(結合液側から見た、水の経路を含まない)。伝達行列。

    層 j の行列 ``[[cos kd, i Z sin kd], [i sin kd / Z, cos kd]]`` は層の下面の (p, v) を
    上面の (p, v) へ写す(``p = A e^{−ikz} + B e^{ikz}``、``v = (A e^{−ikz} − B e^{ikz})/Z``)。
    基板は透過波だけ(``p = Z_s v``)。オーバーフローを避けるため層ごとに正規化する
    (入力インピーダンス ``p/v`` は比なので変わらない)。
    """
    f = np.asarray(f, dtype=np.float64)
    p = np.full(f.shape, s["substrate"]["Z"], dtype=np.complex128)
    v = np.ones(f.shape, dtype=np.complex128)
    for m in reversed(s["layers"]):
        k = 2.0 * np.pi * f / m["c"] - 1j * _alpha(m, f)
        kd = k * m["thickness"]
        c_, s_ = np.cos(kd), np.sin(kd)
        p, v = c_ * p + 1j * m["Z"] * s_ * v, 1j * s_ / m["Z"] * p + c_ * v
        sc = np.maximum(np.abs(p), np.abs(v) * m["Z"])
        sc = np.where(sc > 0, sc, 1.0)
        p, v = p / sc, v / sc
    z0 = s["couplant"]["Z"]
    zin_num, zin_den = p, v                      # Z_in = p / v
    return (zin_num - z0 * zin_den) / (zin_num + z0 * zin_den)


def _pulse_weights(f, f0, sig):
    """ガウス型スペクトルの重み(和で正規化 → 完全反射体の包絡線の山が 1)。"""
    w = np.exp(-0.5 * ((f - f0) / sig) ** 2)
    w[f <= 0] = 0.0
    tot = w.sum()
    if not tot > 0:
        raise ValueError("pulse spectrum has no energy on the frequency grid (rate too low?)")
    return w / tot


def _water_factor(cpl, f, zw):
    k = 2.0 * np.pi * f / cpl["c"] - 1j * _alpha(cpl, f)
    return np.exp(-2j * k * zw)


def _grid(s, f0, sig, zw, rate, duration, n_reverb, op):
    """A スキャンの時間格子(t0, rate, N)。"""
    sig_t = 1.0 / (2.0 * np.pi * sig)            # 包絡線の時間の標準偏差
    f_max = f0 + 6.0 * sig
    if rate is None:
        rate = 4.0 * f_max
    rate = _num(rate, "rate", op, 0.0, 1.0e12)
    if rate < 2.0 * (f0 + 4.0 * sig):
        raise ValueError("%s: rate %.4g Hz is below twice the pulse band edge %.4g Hz"
                         % (op, rate, f0 + 4.0 * sig))
    t_front = 2.0 * zw / s["couplant"]["c"]
    t_stack = float(s["t_interfaces"][-1])
    pad = 6.0 * sig_t
    if duration is None:
        reverb = n_reverb * max(t_stack, 4.0 * sig_t)
        duration = 2.0 * pad + t_stack + reverb
    duration = _num(duration, "duration", op, 0.0, 1.0)
    n = 1 << max(8, int(math.ceil(math.log2(max(duration * rate, 2.0)))))
    if n > MAX_SAMPLES:
        raise ValueError("%s: %d samples exceed the limit %d (shorten duration or lower rate)"
                         % (op, n, MAX_SAMPLES))
    return t_front - pad, rate, n, t_front, sig_t


def pulse_echo_ascan(stack, f0=100e6, bandwidth=0.6, water_path=2e-3, rate=None, duration=None,
                     n_reverb=40):
    """RF A-scan of a layered stack for a broadband pulse at normal incidence: transfer-matrix stack response, water path and power-law attenuation (``table``).

    パルスはガウス型スペクトル(中心 ``f0`` [Hz]、−6 dB の比帯域 ``bandwidth``)。
    応答 ``S(f) = w(f) · exp(−2ik_w z_w) · R_stack(f)``、``k = 2πf/c − iα(f)``。
    振幅の単位は「焦点の完全反射体・水の損失なし」の包絡線の山 = 1。
    時間窓は表面エコーの手前から始まり、``n_reverb`` 回分の積層の往復(残響)を含む。
    FFT の周期で窓の外の残響が先頭へ折り返すので、長い残響の積層は ``duration`` を伸ばす。

    返り: ``t`` [s] ``rf`` ``analytic``(複素)``envelope`` ``rate`` ``f0`` ``bandwidth``
    ``sigma_t``(包絡線の標準偏差)``water_path`` ``t_front``(表面エコーの時刻)
    ``t_interfaces``(各界面のエコーの時刻 = 表面 + 層の往復)``freqs`` ``weights``
    ``response``(各周波数の水の経路込みの複素応答)``names``。
    Raises ValueError: 印の無い table、f0 ≤ 0 / 10 GHz 超、比帯域 0.02–1.5 の外、水の経路 ≤ 0、
    サンプリングが帯域の 2 倍未満、サンプル数が上限超え。
    """
    op = "pulse_echo_ascan"
    s = _stack(stack, op)
    f0, bw, sig = _freq_range(f0, bandwidth, op)
    zw = _num(water_path, "water_path", op, 0.0, 1.0)
    nr = _int(n_reverb, "n_reverb", op, 0, 10000)
    t0, rate, n, t_front, sig_t = _grid(s, f0, sig, zw, rate, duration, nr, op)
    freqs = np.arange(n // 2 + 1) * rate / n
    w = _pulse_weights(freqs, f0, sig)
    band = w > 1e-12 * w.max()
    resp = np.zeros(freqs.shape, dtype=np.complex128)
    fb = freqs[band]
    resp[band] = _water_factor(s["couplant"], fb, zw) * _stack_reflection(s, fb)
    spec = np.zeros(n, dtype=np.complex128)
    spec[: n // 2 + 1] = w * resp * np.exp(2j * np.pi * freqs * t0)
    spec[n // 2] = 0.0
    a = np.fft.ifft(spec) * n                     # a_n = Σ_k w_k G_k e^{i2πf_k (t0 + n/rate)}
    t = t0 + np.arange(n) / rate
    return {"kind": "ascan", "t": t, "rf": a.real.copy(), "analytic": a, "envelope": np.abs(a),
            "rate": rate, "f0": f0, "bandwidth": bw, "sigma_t": sig_t, "water_path": zw,
            "t_front": t_front, "t_interfaces": t_front + np.array(s["t_interfaces"]),
            "freqs": freqs, "weights": w, "response": resp, "names": list(s["interfaces"])}


# --------------------------------------------------------------------------- #
# 位相の読み方
# --------------------------------------------------------------------------- #
def _peak_in_gate(t, a, f0, lo, hi):
    """ゲートの中の包絡線の山(放物線で細分)とその時刻の解析信号(復調して補間)。

    ``a`` の最後の軸が時間。返り: (時刻, 複素値, 振幅)。
    """
    sel = np.nonzero((t >= lo) & (t <= hi))[0]
    if sel.size < 3:
        raise ValueError("gate [%.4g, %.4g] s holds fewer than 3 samples" % (lo, hi))
    tg = t[sel]
    ag = a[..., sel]
    env = np.abs(ag)
    i = np.argmax(env, axis=-1)
    i_c = np.clip(i, 1, sel.size - 2)
    take = lambda arr, j: np.take_along_axis(arr, j[..., None], axis=-1)[..., 0]
    em, e0, ep = take(env, i_c - 1), take(env, i_c), take(env, i_c + 1)
    den = em - 2.0 * e0 + ep
    with np.errstate(invalid="ignore", divide="ignore"):
        d = np.where(den < 0, 0.5 * (em - ep) / den, 0.0)
    d = np.where(i == i_c, np.clip(d, -0.5, 0.5), 0.0)
    i = np.where(i == i_c, i_c, i)
    dt = tg[1] - tg[0]
    tstar = tg[i] + d * dt
    b = ag * np.exp(-2j * np.pi * f0 * tg)        # 復調(包絡線と位相はゆっくり)
    j2 = np.clip(np.where(d >= 0, i + 1, i - 1), 0, sel.size - 1)
    bstar = take(b, i) + np.abs(d) * (take(b, j2) - take(b, i))
    astar = bstar * np.exp(2j * np.pi * f0 * tstar)
    return tstar, astar, np.abs(astar)


def _wrap(phi):
    return (np.asarray(phi) + np.pi) % (2.0 * np.pi) - np.pi


def _classify(phase, tol):
    """+1 = 同相、−1 = 反転、0 = 直交(どちらでもない)。"""
    ph = np.abs(_wrap(phase))
    return np.where(ph <= tol, 1, np.where(ph >= np.pi - tol, -1, 0)).astype(np.int8)


def echo_phase_polarity(echo, interface=1, half_width=None, reference_interface=0, tol_deg=45.0):
    """Classify an interface echo by its phase relative to the front-surface echo: in phase (Z rises), inverted (Z drops) or quadrature (thin-layer, sign not meaningful) (``table``).

    ``echo`` は :func:`pulse_echo_ascan` の A スキャン(``kind='ascan'``)か :func:`sam_cscan` の
    C スキャン(``kind='cscan'``、既に位相を持つので分類だけする)。
    A スキャンでは界面のエコーの**期待時刻** ``t_interfaces[interface]`` での解析信号の偏角から、
    基準エコー(``reference_interface``、既定 = 表面)の期待時刻での偏角を引く(解析信号は
    スペクトルから任意の時刻で厳密に足す)。振幅は ``±half_width``(既定 2σ_t)のゲートの中の
    包絡線の山。★包絡線の山の時刻で位相を読まないのは、山は平らで雑音が時刻を動かし、位相が
    ``2π f0 δt`` だけ回るから(1 ns で 200 MHz なら 72°)。代わりに、積層の厚さの誤差 δd は
    位相を ``4π f0 δd / c`` 回す(Si・200 MHz で 1 µm あたり 17°)。
    分類: ``|位相| ≤ tol`` → 同相 (+1)、``|位相| ≥ 180° − tol`` → 反転 (−1)、それ以外 → 直交 (0)。
    ★基準は**表面エコー**。表面そのものが Z の下がる界面(水より柔らかい最上層)なら表面
    エコーが反転しているので、Z の上がる深い界面が「反転」と読まれる —— 分類は「表面に対して
    同じ向きか逆向きか」であって、絶対の Z の上下ではない(``tests/test_ultrasound.py`` の門)。
    ★``signed_peak``(ゲート内で |RF| が最大のサンプルの符号)も返す —— 現場で言う
    「極性」はこれだが、直交のエコー(薄い層の微分形)では帯域と標本化でどちらにも
    転ぶ。``signed_peak_agrees`` が False の行はそれ。
    返り(A スキャン): ``phase`` [rad] ``phase_deg`` ``amplitude`` ``t_peak`` ``polarity``
    (+1/−1/0)``label`` ``signed_peak`` ``signed_peak_agrees``。
    返り(C スキャン): ``polarity`` の地図と各分類の画素数。
    Raises ValueError: A/C スキャンの印の無い入力、界面の番号が範囲外、tol_deg が [0, 90) の外、
    ゲートの中の標本が 3 未満。
    """
    op = "echo_phase_polarity"
    tol = math.radians(_num(tol_deg, "tol_deg", op, 0.0, 90.0, hi_open=True))
    if not isinstance(echo, dict) or echo.get("kind") not in ("ascan", "cscan"):
        raise ValueError("%s: expected a pulse_echo_ascan or sam_cscan table" % op)
    if echo["kind"] == "cscan":
        pol = _classify(echo["phase"], tol)
        return {"kind": "polarity_map", "polarity": pol, "tol_deg": math.degrees(tol),
                "n_in_phase": int((pol == 1).sum()), "n_inverted": int((pol == -1).sum()),
                "n_quadrature": int((pol == 0).sum())}
    ti = echo["t_interfaces"]
    k = _int(interface, "interface", op, 0, len(ti) - 1)
    kr = _int(reference_interface, "reference_interface", op, 0, len(ti) - 1)
    hw = 2.0 * echo["sigma_t"] if half_width is None else _num(half_width, "half_width", op, 0.0, 1.0)
    t, a, f0 = echo["t"], echo["analytic"], echo["f0"]
    tp, _, amp = _peak_in_gate(t, a, f0, ti[k] - hw, ti[k] + hw)
    fq, g = echo["freqs"], echo["weights"] * echo["response"]
    at = lambda tt: complex(np.sum(g * np.exp(2j * np.pi * fq * tt)))
    ap, ar = at(ti[k]), at(ti[kr])
    phase = float(_wrap(np.angle(ap) - np.angle(ar)))
    pol = int(_classify(phase, tol))
    sel = (t >= ti[k] - hw) & (t <= ti[k] + hw)
    rf = echo["rf"][sel]
    sp = int(np.sign(rf[np.argmax(np.abs(rf))]))
    sp_ref = np.sign(np.cos(np.angle(ar)))       # 基準の符号(R > 0 の表面なら +1)
    sp = int(sp * sp_ref) if sp_ref != 0 else sp
    return {"kind": "polarity", "phase": phase, "phase_deg": math.degrees(phase),
            "amplitude": float(amp), "t_peak": float(tp), "polarity": pol,
            "label": {1: "in_phase", -1: "inverted", 0: "quadrature"}[pol],
            "signed_peak": sp, "signed_peak_agrees": bool(pol != 0 and sp == pol),
            "interface": echo["names"][k], "tol_deg": math.degrees(tol)}


# --------------------------------------------------------------------------- #
# C スキャン
# --------------------------------------------------------------------------- #
def _na_limit(s):
    """最初の固体層(または基板)の縦波の臨界角で決まる水側の開口数の上限。"""
    first = s["layers"][0] if s["layers"] else s["substrate"]
    cw, c1 = s["couplant"]["c"], first["c"]
    return cw / c1 if c1 > cw else 1.0


def _fnum_min(na):
    return 1.0 / (2.0 * math.tan(math.asin(min(na, 1.0 - 1e-12))))


def sam_cscan(bond_map, stacks, pixel_size=2e-6, f0=150e6, bandwidth=0.6, f_number=3.0,
              water_path=1e-3, gate_interface=1, half_width=None, k_res=1.02, noise_rms=0.0,
              seed=0, n_reverb=40, psf_nodes=32):
    """Focused-transducer C-scan of a 2-D bond map: per-frequency Gaussian lateral PSF, time gate at an interface, amplitude, phase, in-phase (signed) and signed-peak images (``table``).

    ``bond_map`` は整数ラベルの 2-D 配列、``stacks`` は ``{ラベル: acoustic_layer_stack}``
    (例: 0 = 誘電体、1 = Cu パッド、2 = ボイド、3 = パッド上のボイド)。
    各周波数 f で、ラベルごとの反射 ``R_c(f)`` を地図に置いてガウスの横 PSF
    (半値全幅 ``k_res · (c_w/f) · F#``、往復の振幅 PSF、無限の平面で利得 1)で畳み込み、
    水の経路と減衰を掛けて、ゲートの時刻での解析信号に和を取る。
    ゲートは ``t_interfaces[gate_interface] ± half_width``(既定 2σ_t)。
    出力の像:
      * ``amplitude`` — ゲート内の包絡線の山(振幅の C スキャン)
      * ``phase`` — 界面のエコーの**期待時刻**(表面エコーの時刻 + 積層の往復)での解析信号の
        偏角 − 表面エコーの期待時刻での偏角 [rad]
      * ``inphase`` — 期待時刻の解析信号の同相成分 ``|a| cos(phase)``(符号つき。反転したエコーは負)
      * ``signed_peak`` — ゲート内で |RF| が最大のサンプルの値(従来の極性の読み方)
      * ``tof`` — 包絡線の山の時刻 [s]
    ``plane_phasor`` は ``{ラベル: 複素数}`` —— そのラベルが一面に広がっていたときの期待時刻の
    値(雑音なし、基準の偏角を引いた後)。地図の設計(どこがパッドか)が分かっていれば、
    良品の基準として ``inphase`` / ``amplitude`` から引ける。
    ★位相を包絡線の山の時刻でなく期待時刻で読む理由は :func:`echo_phase_polarity` と同じ
    (山の時刻の揺れが位相を ``2π f0 δt`` 回す。期待時刻なら位相の雑音は 雑音/振幅 だけ)。
    代わりにダイの厚さの誤差 δd は位相を ``4π f0 δd / c`` 回す —— 厚さが場所で変わる部品では
    ``tof`` から期待時刻を画素ごとに直す必要がある(この op はしていない)。
    ``noise_rms`` は受信の加法雑音(RF の実部の RMS、探触子の帯域の形の色つき雑音)。
    ``psf_nodes`` は横 PSF を厳密に作る周波数の節点の数(その間は f の 1 次補間)。
    ★ボイドの中心でも節点を倍にして変わる量は 1e-3 未満(``tests/test_ultrasound.py``)。
    Raises ValueError: 印の無い積層・地図のラベルに積層が無い・結合液が積層ごとに違う・
    ``F#`` が最初の固体層の縦波の臨界角を超える(横波に化ける光線はこのモデルの外)・
    画素 ≤ 0・地図が大きすぎる・周波数の本数が上限超え。
    """
    op = "sam_cscan"
    m = np.asarray(bond_map)
    if m.ndim != 2 or m.size == 0 or not np.issubdtype(m.dtype, np.integer):
        raise ValueError("%s: bond_map must be a non-empty 2-D integer label array" % op)
    if m.size > MAX_MAP_PIXELS:
        raise ValueError("%s: bond_map has %d pixels, limit %d" % (op, m.size, MAX_MAP_PIXELS))
    if not isinstance(stacks, dict) or not stacks:
        raise ValueError("%s: stacks must be a non-empty {label: acoustic_layer_stack} dict" % op)
    labels = [int(v) for v in np.unique(m)]
    if len(labels) > MAX_CLASSES:
        raise ValueError("%s: %d labels exceed the limit %d" % (op, len(labels), MAX_CLASSES))
    st = {}
    for lab in labels:
        if lab not in stacks:
            raise ValueError("%s: label %d in bond_map has no stack" % (op, lab))
        st[lab] = _stack(stacks[lab], op)
    s0 = st[labels[0]]
    cw = s0["couplant"]
    for lab, s in st.items():
        if (s["couplant"]["Z"], s["couplant"]["c"]) != (cw["Z"], cw["c"]):
            raise ValueError("%s: all stacks must share one couplant (label %d differs)" % (op, lab))
    px = _num(pixel_size, "pixel_size", op, 0.0, 1.0)
    f0, bw, sig = _freq_range(f0, bandwidth, op)
    fn = _num(f_number, "f_number", op, 0.0, 1000.0)
    kr = _num(k_res, "k_res", op, 0.0, 10.0)
    zw = _num(water_path, "water_path", op, 0.0, 1.0)
    nrms = _num(noise_rms, "noise_rms", op, 0.0, None, lo_open=False)
    nr = _int(n_reverb, "n_reverb", op, 0, 10000)
    pn = _int(psf_nodes, "psf_nodes", op, 1, MAX_BINS)
    na = 1.0 / math.sqrt(1.0 + (2.0 * fn) ** 2)      # sin(atan(1/(2F#)))
    for lab, s in st.items():
        lim = _na_limit(s)
        if na > lim * (1.0 + 1e-9):
            raise ValueError("%s: f_number %.3g opens the beam beyond the longitudinal critical "
                             "angle of the first solid (need F# >= %.3g for label %d); those rays "
                             "convert to shear/surface waves, which this model does not have"
                             % (op, fn, _fnum_min(lim), lab))
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)):
        raise ValueError("%s: seed must be an integer" % op)
    # 時間格子は最も長い積層で決める(残響が折り返さないように)
    s_long = max(st.values(), key=lambda s: float(s["t_interfaces"][-1]))
    t0, rate, n, t_front, sig_t = _grid(s_long, f0, sig, zw, None, None, nr, op)
    freqs = np.arange(n // 2 + 1) * rate / n
    w = _pulse_weights(freqs, f0, sig)
    band = np.nonzero(w > 1e-4 * w.max())[0]
    if band.size > MAX_BINS:
        raise ValueError("%s: %d frequency bins exceed the limit %d" % (op, band.size, MAX_BINS))
    fb = freqs[band]
    wb = w[band] / w[band].sum()                  # 帯域で切った分を正規化し直す
    hw_ = _water_factor(cw, fb, zw)
    ti = s0["t_interfaces"]
    gi = _int(gate_interface, "gate_interface", op, 0, len(ti) - 1)
    for lab, s in st.items():
        if len(s["t_interfaces"]) <= gi:
            raise ValueError("%s: stack for label %d has no interface %d" % (op, lab, gi))
    hw = 2.0 * sig_t if half_width is None else _num(half_width, "half_width", op, 0.0, 1.0)
    tg_c = t_front + float(ti[gi])
    rate_g = 16.0 * sig                          # 解析信号は正確に足すので搬送波の標本化は要らない
    ng = int(math.ceil(2.0 * hw * rate_g)) + 1
    # ゲートの標本 ng 個 + 期待時刻 tg_c の 1 個(位相はここで読む)
    tg = np.append(tg_c - hw + np.arange(ng) / rate_g, tg_c)
    # 基準(表面エコー)の偏角: ラベル 0 の積層の表面エコーの期待時刻 t_front で読む
    r0 = _stack_reflection(s0, fb)
    phi_ref = float(np.angle(np.sum(wb * hw_ * r0 * np.exp(2j * np.pi * fb * t_front))))
    # ラベルの地図の FFT(端は複製でパディング)
    sig_x_max = kr * (cw["c"] / fb[0]) * fn / FWHM_PER_SIGMA
    pad = int(min(max(m.shape), math.ceil(4.0 * sig_x_max / px)))
    mp = np.pad(m, pad, mode="edge")
    ny, nx = mp.shape
    refl = {lab: _stack_reflection(st[lab], fb) for lab in labels}
    # 横 PSF でぼかしたラベルの地図 B_c(f) は f についてゆっくり変わる: 周波数の節点
    # (psf_nodes 本)で厳密に作り、その間は f の 1 次補間(帽子関数の重み λ_kn)。
    # A(t_g) = Σ_c Σ_n [Σ_k w_k H_k R_c(f_k) λ_kn e^{i2πf_k t_g}] B_c(n)。
    nodes = np.linspace(fb[0], fb[-1], min(pn, fb.size)) if fb.size > 1 else fb.copy()
    lam = np.zeros((fb.size, nodes.size))
    if nodes.size == 1:
        lam[:, 0] = 1.0
    else:
        pos = (fb - nodes[0]) / (nodes[1] - nodes[0])
        i0 = np.clip(np.floor(pos).astype(int), 0, nodes.size - 2)
        fr = pos - i0
        lam[np.arange(fb.size), i0] = 1.0 - fr
        lam[np.arange(fb.size), i0 + 1] = fr
    eg = np.exp(2j * np.pi * np.outer(fb, tg))             # (nf, ng + 1)
    acc = np.zeros((ng + 1,) + m.shape, dtype=np.complex128)
    sl = (slice(pad, pad + m.shape[0]), slice(pad, pad + m.shape[1]))
    u = np.fft.fftfreq(ny, d=px)[:, None]
    v = np.fft.rfftfreq(nx, d=px)[None, :]
    q2 = u ** 2 + v ** 2
    rmasks = {lab: np.fft.rfft2((mp == lab).astype(np.float64)) for lab in labels}
    for lab in labels:
        coef = ((wb * hw_ * refl[lab])[:, None] * lam).T @ eg        # (nodes, ng)
        for n_ in range(nodes.size):
            sx = kr * (cw["c"] / nodes[n_]) * fn / FWHM_PER_SIGMA
            blur = np.fft.irfft2(rmasks[lab] * np.exp(-2.0 * np.pi ** 2 * sx ** 2 * q2),
                                 s=(ny, nx))[sl]
            acc += coef[n_][:, None, None] * blur[None, :, :]
    if nrms > 0:
        # 受信雑音: 探触子の帯域の形(振幅 sqrt(w))の白色雑音を、ゲートの標本の共分散
        # C = s² Σ_k g_k² e^{i2πf_k (t_g − t_g')} どおりに作る(実部の RMS = noise_rms)。
        g2 = wb / wb.max()
        s2 = 2.0 * nrms ** 2 / float(np.sum(g2))
        cov = s2 * (eg.T * g2[None, :]) @ eg.conj()           # (ng+1, ng+1) エルミート
        ev, evec = np.linalg.eigh(cov)
        lmat = evec * np.sqrt(np.clip(ev, 0.0, None))[None, :]
        rng = np.random.default_rng(int(seed))
        z = (rng.standard_normal((ng + 1, m.size)) + 1j * rng.standard_normal((ng + 1, m.size))) / math.sqrt(2.0)
        acc += (lmat @ z).reshape((ng + 1,) + m.shape)
    a = np.moveaxis(acc[:ng], 0, -1)
    a_c = acc[ng] * np.exp(-1j * phi_ref)                    # 期待時刻の値、基準の偏角を引いた
    tof, _, amp = _peak_in_gate(tg[:ng], a, f0, tg[0], tg[ng - 1])
    phase = np.angle(a_c)
    rf = a.real
    ip = np.argmax(np.abs(rf), axis=-1)
    signed = np.take_along_axis(rf, ip[..., None], axis=-1)[..., 0] * np.sign(np.cos(phi_ref))
    return {"kind": "cscan", "amplitude": amp, "phase": phase, "inphase": a_c.real,
            "amplitude_at_t": np.abs(a_c), "t_expected": tg_c,
            "signed_peak": signed, "tof": tof, "reference_phase": phi_ref,
            "gate": (float(tg[0]), float(tg[ng - 1])), "gate_interface": gi, "pixel_size": px,
            "f0": f0, "bandwidth": bw, "f_number": fn, "k_res": kr, "water_path": zw,
            "psf_fwhm_f0": kr * (cw["c"] / f0) * fn, "f_number_min": max(_fnum_min(_na_limit(s))
                                                                        for s in st.values()),
            "noise_rms": nrms, "n_bins": int(fb.size), "labels": labels,
            "reflection_f0": {lab: complex(_stack_reflection(st[lab], np.array([f0]))[0])
                              for lab in labels},
            "plane_phasor": {lab: complex(np.sum(wb * hw_ * refl[lab] * np.exp(2j * np.pi * fb * tg_c))
                                          * np.exp(-1j * phi_ref)) for lab in labels}}


# --------------------------------------------------------------------------- #
# 周波数の取引
# --------------------------------------------------------------------------- #
def _loss_terms(s, interface, zw):
    """往復の減衰 2(α_w z_w + Σ α_j d_j) を (α0·2d, n) の項の列で。"""
    terms = [(2.0 * s["couplant"]["alpha0"] * zw, s["couplant"]["alpha_n"])]
    for m in s["layers"][:interface]:
        terms.append((2.0 * m["alpha0"] * m["thickness"], m["alpha_n"]))
    return [(c, n) for c, n in terms if c > 0.0]


def sam_frequency_tradeoff(stack, void_diameter, water_path=1e-3, f_number=3.0, interface=None,
                           k_res=1.02, f_min=1e6, f_max=5e9, n_grid=600, bandwidth=0.6,
                           n_sigma_gate=5.0):
    """Optimal SAM frequency for a void of given size at a buried interface: lateral fill (1 - 2^-(a/w)^2, w = k_res*lambda_w*F#) against two-way attenuation; closed form when all losses go as f^2 (``table``).

    信号 ``S(f) = η(f) · exp(−L(f))``、``η = 1 − 2^{−(a/w)²}`` はボイド(直径 a)の中心に
    ガウスの往復 PSF(半値全幅 ``w = k/f``、``k = k_res c_w F#``)が当たったときの充填率、
    ``L(f) = 2 α_w(f) z_w + 2 Σ_{j<interface} α_j(f) d_j``(水の経路と上の層の往復減衰 [Np])。
    減衰がすべて ``f²``(``L = β f²``)なら ``dlnS/df = 0`` から
    ``f* = (k/a) · sqrt(log2(1 + a² ln2 / (β k²)))``(小さなボイドの極限で ``1/√β``)。
    それ以外は対数格子で探して有界の 1-D 最適化で詰める。
    返り: ``freqs`` ``fwhm`` ``fill`` ``loss_np`` ``loss_db`` ``signal`` ``f_opt``(数値)
    ``f_opt_closed``(閉形式が立つときだけ、そうでなければ None)``beta`` ``k``
    ``fwhm_at_opt`` ``f_number_min``(臨界角の上限)。
    時間の分解能の下限も返す: 表面エコーと界面のエコーの間隔 ``t_sep``(積層の往復時間)が
    パルスの包絡線の ``n_sigma_gate`` σ_t(ゲートの半幅 2σ_t + 裾 3σ_t)より短いと、表面エコーの
    裾がゲートに入る。σ_t = FWHM_PER_SIGMA / (2π · bandwidth · f) なので
    ``f_min_time = n_sigma_gate · 2.3548 / (2π · bandwidth · t_sep)``、
    ``f_opt_usable = max(f_opt, f_min_time)``(表面の界面(interface=0)なら下限 0)。
    ★ボイドの反射 |R| は周波数によらず 1 とみなす(薄い空気の層では ~1)。
    Raises ValueError: 印の無い積層、直径 ≤ 0、f_min ≥ f_max、F# が臨界角の上限より小さい、減衰が 0
    (最適周波数が存在しない — 上へ行くほど良い)。
    """
    op = "sam_frequency_tradeoff"
    s = _stack(stack, op)
    a = _num(void_diameter, "void_diameter", op, 0.0, 1.0)
    zw = _num(water_path, "water_path", op, 0.0, 1.0, lo_open=False)
    fn = _num(f_number, "f_number", op, 0.0, 1000.0)
    kr = _num(k_res, "k_res", op, 0.0, 10.0)
    lo = _num(f_min, "f_min", op, 0.0, 1.0e10)
    hi = _num(f_max, "f_max", op, 0.0, 1.0e11)
    if not lo < hi:
        raise ValueError("%s: f_min must be below f_max" % op)
    ng = _int(n_grid, "n_grid", op, 16, 1 << 20)
    bw = _num(bandwidth, "bandwidth", op, 0.02, 1.5)
    nsg = _num(n_sigma_gate, "n_sigma_gate", op, 0.0, 100.0, lo_open=False)
    ni = len(s["layers"]) if interface is None else _int(interface, "interface", op, 0, len(s["layers"]))
    lim = _na_limit(s)
    if 1.0 / math.sqrt(1.0 + (2.0 * fn) ** 2) > lim * (1.0 + 1e-9):
        raise ValueError("%s: f_number %.3g exceeds the longitudinal critical angle (need >= %.3g)"
                         % (op, fn, _fnum_min(lim)))
    terms = _loss_terms(s, ni, zw)
    if not terms:
        raise ValueError("%s: the path has no attenuation, so there is no optimum (higher is "
                         "always better within this model)" % op)
    k = kr * s["couplant"]["c"] * fn

    def lnS(f):
        f = np.asarray(f, dtype=np.float64)
        u = (a * f / k) ** 2
        fill = -np.expm1(-math.log(2.0) * u)
        loss = sum(c * np.power(f, n) for c, n in terms)
        return np.log(np.maximum(fill, 1e-300)) - loss, fill, loss

    freqs = np.geomspace(lo, hi, ng)
    ls, fill, loss = lnS(freqs)
    i = int(np.argmax(ls))
    from scipy.optimize import minimize_scalar          # noqa: PLC0415 — 遅延 import
    xa = math.log(freqs[max(i - 1, 0)])
    xb = math.log(freqs[min(i + 1, ng - 1)])
    if xb > xa:
        res = minimize_scalar(lambda x: -float(lnS(math.exp(x))[0]), bounds=(xa, xb),
                              method="bounded", options={"xatol": 1e-10})
        f_opt = math.exp(res.x)
    else:
        f_opt = float(freqs[i])
    t_sep = float(s["t_interfaces"][ni])
    f_min_time = nsg * FWHM_PER_SIGMA / (2.0 * math.pi * bw * t_sep) if t_sep > 0 else 0.0
    beta = None
    f_closed = None
    if all(n == 2.0 for _, n in terms):
        beta = float(sum(c for c, _ in terms))
        f_closed = (k / a) * math.sqrt(math.log2(1.0 + a * a * math.log(2.0) / (beta * k * k)))
    return {"kind": "sam_tradeoff", "freqs": freqs, "fwhm": k / freqs, "fill": fill,
            "loss_np": loss, "loss_db": loss * DB_PER_NP, "signal": np.exp(ls),
            "f_opt": float(f_opt), "f_opt_closed": f_closed, "beta": beta, "k": k,
            "fwhm_at_opt": k / f_opt, "void_diameter": a, "f_number_min": _fnum_min(lim),
            "at_grid_edge": bool(i == 0 or i == ng - 1), "t_sep": t_sep, "f_min_time": f_min_time,
            "f_opt_usable": max(float(f_opt), f_min_time)}
