# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: テレセントリックレンズと寸法計測 —— 同じレンズの絞りを動かすだけで、高さで変わる倍率が消える。

【問い】ダイのボンディングやコネクタのピンの検査では、**高さの違う面**の寸法を 1 枚の画像で測る。通常の
(エントセントリック)レンズは近い物ほど大きく写すので、段差の上と下では同じ寸法が違う長さに写る。テレセントリック
レンズは絞りを焦点に置いて主光線を光軸に平行にし、これを消す。本当にどれだけ消えるのか、消えないのは何かを、
``raytrace`` の逐次光線追跡で組んだレンズで閉形式と突き合わせる。新 op 7 本(``telecentric``)。実画像の章 + 6 章 + 付録:

  0. **実画像(主役)**: Stark ほか(Sci. Rep. 2025、CC BY 4.0)が figshare に置いたテレセンの生画像 3 枚(2848 × 2848)を
     取得してキャッシュし(``~/.cache/fullseye/poc_telecentric_metrology``、sha256 で確かめる。Zenodo の 2.5 GB は落とさない)、
     Fullseye の計測 op で測る。29.5° 傾いたアライメント板(円の間隔 1 mm)の 8 本のリングの中心線を、中心から放射状の
     測定線(``measuring1d.measure_pos``、強い立ち上がりと次の強い立ち下がりの中点)で取り、中心と形(向き・縦横比)を共有
     する楕円の族で当てる。門: 長軸の伸び 252.13 ± 0.04 px/mm は論文の K1 = 252.0 px/mm と +0.05 %(★論文自身の K1・K2 が
     ±0.25 % 散っているので、それより細かい一致とは読まない)、リングの半径は 1.50〜8.50 mm に 0.33 px 以内で並ぶ、★傾いた
     板の同心円の中心は r² に比例してずれない(形を固定してリングごとに中心を解き直し、β = 0.0035 ± 0.0034 px/mm²。2 章の
     通常 f=25 なら 1.40 で外側のリングの中心が 101 px ずれる)—— 入射瞳は 10.5 m より遠い。
     ★最初の版(2026-10-15)は 250.73 px/mm と出ていた。原因は 2 つ: (1) ``measure_pairs`` の組を閾値 0.15 でそのまま使い、
     組の位相がずれて線を落とし・線の中の粒と組んでいた、(2) リングごとに自由な楕円を当て、影で弧が短い外側のリングの
     長半径を外挿していた(弧 36° のリングで 768 px、族では 2142 px)。元の解像度で点と楕円を重ねて見つけた。
     ★樹脂の 3D プリント球(公称半径 2.5 mm)は輪郭の閾値 0.015 → 0.06 で半径が 8 % 動き(陰の縁が暗い)、真値にならない
     (2.400 / 2.452 mm)。論文の計量級の球(半径 5 mm ±1.6 µm)の生画像は公開データに無い。ネットの無い CI では記録値を
     印字して飛ばす。下の 1〜6 章は合成で、失敗条件を掃引する補助。
  1. **主光線の傾き(テレセン度)**: 同じ BK7 相当の等凸単レンズ f = 100 mm の絞りを、レンズの直後(通常)・後側焦点
     (物体側テレセン)に置き、後側焦点の後ろに 2 枚目(f = 50 mm)を足して両側テレセンを作る(倍率はどれも −0.5)。
     門: 実光線の主光線は絞りの中心を 1e-12 mm 以内で通る、通常のレンズの傾きは近軸の入射瞳 L から tanθ = h/L と一致、
     テレセン 2 種は物高 8 mm でも 0.052° / 0.048°(通常は −1.5°)。★0 にならないのは単レンズの瞳の球面収差で、
     物高 1 → 8 mm で 9e-5° → 0.052°(h³)と育つ。
  2. **高さで変わる倍率**: 像面を固定して物体を ±5 mm 動かす。門: 実光線の m(Δz)/m(0) は閉形式 L/(L − Δz) と 7e-5、
     +5 mm 近づくと 通常 f = 25 mm(作動距離 75 mm の現場の FA レンズ)で +6.9 %、通常 f = 100 mm で +1.7 %、
     テレセンは −0.013 %。オートフォーカスで合わせ直しても倍率は m = −f/(s − f) で +2.6 % 動き、戻らない
     (★この一致 6e-16 は近軸どうしの比較なので当然で、実光線の一致は上の 7e-5 のほう)。
  3. **段差のある部品を描いて測る**: ピン(高さ 5 mm)・ダイ(0.7 mm、電極つき)・穴(深さ 5 mm)を ``render3d`` で、
     レンズの入射瞳に置いたピンホール(``lens_equivalent_pinhole``)から描き、ぼけは光線束の RMS(``defocus_spot_vs_depth``)
     で掛ける。門: 画像から測ったピン上面の径は閉形式 D·L/(L − 5 mm − Δz) と 7e-4 —— 通常 f = 25 mm は真値 1.6 mm を
     6.9 % 大きく読み、ワークが 6 mm 上下すると読みが 8.6 % 動く。穴の底が見える割合 0.948 は 2 つの円の重なりの閉形式
     0.949 と一致し、内壁が 2,053 画素見える。両側テレセンでは底が全部見え、内壁は 0 画素。
     部品は実物の質感で描く: アルミの治具プレート(``metalfinish`` の削り目 × ``glassmirror`` の複素屈折率の色)、
     金めっきのピン(面取りつき)、黒い樹脂モールド(``surfacelib.clearcoat_shade``、捺印つき)と銀色のリード、
     影(``render_shadow``)と AO(``render_ao``)。門: 照明を同軸落射・ドーム・低角リングに変えても、描いた画像だけから
     円の計測モデル(``metrology``、HALCON 流)で測ったピン上面の径は閉形式と 0.34 % 以内、6 mm の上下で通常 f = 25 mm は
     +8.3〜8.4 %、両側テレセンは ±0.13 % 以内(上の門は面の種類の地図なので照明に依らない —— こちらが画像の門)。
     ★物体で 47 µm/画素に粗くすると、低角リング(暗視野)では上面の縁が弱く 2 % 外れた。
  4. **テレセンでも残る誤差**: 絞りが後側焦点から δ ずれると入射瞳は前側焦点から −f²/δ(Newton)。門: 物高 0.5 mm では
     実光線の傾きの増分が閉形式と 0.04 % —— 物高 8 mm では 11.8 % 大きく、その差は物高の 2 乗で育つ(4 → 8 mm で 4.6 倍、
     瞳の球面収差)。視野の端のテレセン度をちょうど 0.1° にする実の δ は −3.16 mm、そのとき段差 5 mm の上下で物高 8 mm の
     点は 9.2 µm ずれて見える(閉形式 5 × tan 0.1° = 8.7 µm。差は上の面で主光線の傾きが少し変わる分)。
  5. **視野は前玉径で決まる**: 門: テレセンの視野の 50 % 点(物体側 11.6 mm、両側 12.2 mm)は光束の中心が前玉の縁
     (半口径 12.5 mm)に来る物高と 0.3 mm 以内。★近軸の閉形式(光束の円の中心 = 物高)は 12.4 mm で、実光線は
     0.8 mm 手前で欠ける —— 瞳の球面収差で光束が外へずれて太り、ケラレの前に光束が 17 % 増える(周辺光量の不均一)。
     通常のレンズは前玉の 1.3 倍の物高まで蹴られない。
  6. **被写界深度と NA の取引**: 門: ぼけの RMS の傾き |m|·NA/√2(一様な円の光束)を NA 0.005 / 0.01 / 0.02 で
     実光線と 0.5 % 以内。許すぼけ 22 µm(物体側)を回折の円の直径 1.22λ/NA が超えない最小の NA は 0.033 で、
     そのとき被写界深度 c/NA は 0.68 mm が上限 —— NA 0.01 なら深さは 2.2 mm あるが回折の円が 72 µm で 22 µm を分解できない。
  付録. **第二の実装**: OSS の光線追跡 optiland(MIT)が手元にあれば同じ処方の主光線の像の高さを突き合わせる
     (2026-10-15 に別の venv で 9e-8 mm。★内訳: 屈折率はどちらも公開の硝材カタログの同じ Sellmeier 係数なので、一致が見ているのは
     面との交点と主光線の狙いの実装だけ。optiland の狙いを近軸にすると物体側テレセンで 0.011 mm 違う)。

【外部真値】閉形式(主光線の幾何、Newton の結像式、薄肉レンズ、円の重なりの面積、一様な円の RMS)と、OSS の
第二の実装 optiland(あれば)。実画像の章は、アライメント板の円の間隔 1 mm と論文の内部パラメータ K1 = 252.0 px/mm。
【学習】0。【較正】0。

【来歴(実画像)】A. W. Stark, A. Osadare, M. Guo, G. J. Gentsch, D. Boettger, G. Brehm, C. Franke, "Telecentric stereo
3D imaging with isotropic micrometer resolution bridges macro- and microscale in small Lepidopterans", Scientific Reports
15, 28690 (2025), doi:10.1038/s41598-025-13795-6(CC BY 4.0)。画像は figshare collection doi:10.6084/m9.figshare.c.7652423
の item 28322132 / 28322006 / 28322036(CC BY 4.0、2026-10-15 に API とページで確認。生データ一式は Zenodo
doi:10.5281/zenodo.15432113、cc-by-4.0)。改変: グレースケール化・縮小・計測の線の描き込み。repo には画像を入れない。

【来歴】Smith, *Modern Optical Engineering*(テレセントリック系)/ Welford, *Aberrations of Optical Systems*
(主光線と瞳)/ Wu, Yue, Yi, Li, Liu, "Phase error analysis and reduction in phase measuring deflectometry",
Opt. Eng. 54(6) 064103 (2015)(非テレセンの撮像が誤差源の 1 つ)/ Marani et al., "A Compact 3D Omnidirectional
Range Sensor of High Resolution for Robust Reconstruction of Environments", Sensors 15, 2283 (2015)
(光切断の撮像にテレセンのレンズ)。後の 2 本は RAD の optical_metrology_inspection_corpus から引いた。

EXTEND: 実機のテレセンは 5〜10 枚の組レンズで、瞳の球面収差(ここでは単レンズなので視野の端で 0.05° 残る)と
歪曲(物体側テレセンの単レンズは物高 8 mm で 3 % —— 両側テレセンの対称な配置では 0.005 %)を設計で潰している。
カタログの処方が手に入れば ``raytrace.lens_system`` に面を並べるだけで同じ op がそのまま使える。IR のウエハ越しの
観察は、``materials`` の Si の屈折率を処方の媒質に入れれば平行平板の焦点ずれ t(1 − 1/n) も同じ追跡に乗る
(ここでは扱っていない)。``lens_equivalent_pinhole`` は近軸の幾何の写しなので、歪曲と瞳収差は描画に入らない
(3 章のテレセンの読みが 0.000 % なのはそのため。実光線の残りは 2 章の 0.013 %)。
"""
from __future__ import annotations

import copy
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import raytrace as RT  # noqa: E402
import glassmirror  # noqa: E402
import metrology  # noqa: E402
import metalfinish  # noqa: E402
import render3d  # noqa: E402
import render_ao  # noqa: E402
import render_shadow  # noqa: E402
import render_tonemap  # noqa: E402
import surfacelib  # noqa: E402
import telecentric as TC  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}

#: 2026-10-15 に optiland 0.6.3(別の venv)で同じ処方を組んで得た主光線の像の高さ [mm](物高 8 mm、
#: 狙い = iterative)。手元に optiland が無いときに所見として印字する(門には使わない)。
OPTILAND_RECORDED = {"ento": -4.000118, "object": -4.131367}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def lenses():
    """比べるレンズ 4 本: 同じ単レンズの 3 種 + 現場でよく使う短い焦点距離の通常レンズ。"""
    return {"fa25": TC.telecentric_lens("entocentric", focal_mm=25.0, front_aperture_mm=6.0),
            "ento": TC.telecentric_lens("entocentric"),
            "object": TC.telecentric_lens("object"),
            "bi": TC.telecentric_lens("bi")}


LABEL = {"fa25": "通常 f=25", "ento": "通常 f=100", "object": "物体側テレセン", "bi": "両側テレセン"}


# --------------------------------------------------------------------------- #
# 1. 主光線の傾き
# --------------------------------------------------------------------------- #
def chapter_chief(L):
    print("\n1. 主光線の傾き(テレセン度)—— 同じレンズで絞りの位置だけを変える")
    for k in ("ento", "object", "bi"):
        d = L[k]["design"]
        print("   %-8s 物体距離 %.2f mm、絞りの半径 %.3f mm、近軸倍率 %.5f"
              % (LABEL[k], d["object_mm"], d["stop_radius_mm"], d["magnification_paraxial"]))
    worst_res = 0.0
    rows = {}
    for k in ("ento", "object", "bi"):
        rows[k] = []
        for h in (1.0, 2.0, 4.0, 6.0, 8.0):
            c = TC.chief_ray_angle(L[k], h)
            worst_res = max(worst_res, c["stop_residual_mm"])
            rows[k].append((h, c["object_angle_deg"], c["image_angle_deg"]))
    gate("実光線の主光線は絞りの中心を通る(Newton 法、3 種 × 5 物高の残差 < 1e-12 mm)", worst_res < 1e-12,
         "最大 %.1e mm" % worst_res)
    para = RT.paraxial_trace(L["ento"])
    Lp = L["ento"]["object_mm"] + para["ep_position"]
    c2 = TC.chief_ray_angle(L["ento"], 2.0)
    cf = -math.degrees(math.atan(2.0 / Lp))
    NUMBERS["ento_L"] = Lp
    gate("通常のレンズ: 物高 2 mm の主光線の傾き %.4f° = 近軸の入射瞳(物体から %.2f mm)の tanθ = h/L = %.4f°(差 < 0.5 %%)"
         % (c2["object_angle_deg"], Lp, cf), abs(c2["object_angle_deg"] / cf - 1) < 5e-3)
    edge = {k: TC.chief_ray_angle(L[k], 8.0)["object_angle_deg"] for k in ("object", "bi")}
    NUMBERS.update({"tele_edge_object": edge["object"], "tele_edge_bi": edge["bi"],
                    "ento_edge": rows["ento"][-1][1]})
    gate("テレセン 2 種は視野の端(物高 8 mm)でも |θ| < 0.1°(物体側 %.4f°、両側 %.4f°。通常は %.3f°)"
         % (edge["object"], edge["bi"], rows["ento"][-1][1]), max(abs(v) for v in edge.values()) < 0.1)
    small = TC.chief_ray_angle(L["object"], 1.0)["object_angle_deg"]
    gate("★テレセンの傾きは単レンズの瞳の球面収差: 物高 1 mm → 8 mm で h³ の程度に育つ(%.2e° → %.4f°、比 > 100)"
         % (small, edge["object"]), abs(edge["object"] / small) > 100, "0 にならないのは収差で、近軸では厳密に 0")
    bi_img = TC.chief_ray_angle(L["bi"], 8.0)["image_angle_deg"]
    ob_img = TC.chief_ray_angle(L["object"], 8.0)["image_angle_deg"]
    gate("像側も: 両側テレセンの像側の主光線は %.3f°(物体側テレセンは %.2f° —— センサの位置ずれにも強いのは両側だけ)"
         % (bi_img, ob_img), abs(bi_img) < 0.2 < abs(ob_img))
    return rows


# --------------------------------------------------------------------------- #
# 2. 高さで変わる倍率
# --------------------------------------------------------------------------- #
def chapter_depth(L):
    print("\n2. 高さで変わる倍率(像面は固定)")
    h = 4.0
    curves = {}
    worst = 0.0
    for k in ("fa25", "ento", "object", "bi"):
        mv = TC.magnification_vs_depth(L[k], h, -5.0, 5.0, 21)
        m0 = mv[10, 1]
        curves[k] = (mv[:, 0], 100.0 * (mv[:, 1] / m0 - 1.0))
        if k in ("fa25", "ento"):
            c = TC.chief_ray_angle(L[k], h)
            Lr = c["pupil_distance_mm"]
            closed = Lr / (Lr - mv[:, 0])
            worst = max(worst, float(np.max(np.abs(mv[:, 1] / m0 / closed - 1.0))))
            curves[k + "_cf"] = (mv[:, 0], 100.0 * (closed - 1.0))
    NUMBERS["depth_cf_worst"] = worst
    gate("通常のレンズ 2 本: 実光線の m(Δz)/m(0) は閉形式 L/(L − Δz) と ±5 mm で 2e-4 以内(L は同じ物高の実の主光線から)",
         worst < 2e-4, "最大 %.1e" % worst)
    s = {k: curves[k][1][-1] for k in curves if not k.endswith("_cf")}
    NUMBERS.update({"pct5_" + k: v for k, v in s.items()})
    gate("+5 mm 近づくと: 通常 f=25 で +%.2f %%、通常 f=100 で +%.2f %%、テレセンは %.3f %% / %.3f %%(どちらも |·| < 0.1 %%)"
         % (s["fa25"], s["ento"], s["object"], s["bi"]), abs(s["object"]) < 0.1 and abs(s["bi"]) < 0.1 and s["fa25"] > 5)
    # オートフォーカス: ピントを合わせ直すと倍率は −f/(s − f)
    sysd = L["ento"]
    para0 = RT.paraxial_trace(sysd)
    f = para0["efl"]
    pp = para0["pp_front"]
    worst_af = 0.0
    af = []
    for dz in np.linspace(-5.0, 5.0, 11):
        s2 = dict(sysd)
        s2 = RT.lens_system([{k2: v for k2, v in sf.items() if k2 not in ("n_value", "dn")} for sf in sysd["surfaces"][:-1]]
                            + [{"R": "inf", "t": None, "n": 1.0, "ap": 1.0}],
                            stop=sysd["stop"], object_mm=sysd["object_mm"] - dz)
        m_af = RT.paraxial_trace(s2)["magnification"]
        so = sysd["object_mm"] - dz + pp
        m_cf = -f / (so - f)
        worst_af = max(worst_af, abs(m_af / m_cf - 1))
        af.append((dz, 100 * (m_af / para0["magnification"] - 1)))
    gate("オートフォーカスで合わせ直しても倍率は m = −f/(s − f) で動く(近軸どうしなので一致は 1e-9。+5 mm で %+.2f %%)"
         % af[-1][1], worst_af < 1e-9, "最大 %.1e —— ★一致が良すぎるのは両方が同じ近軸の式だから" % worst_af)
    return curves, np.array(af)


# --------------------------------------------------------------------------- #
# 3. 段差のある部品を描いて測る
# --------------------------------------------------------------------------- #
HOLE_C, HOLE_R, HOLE_D = (-3.6, 2.2), 1.6, 5.0
HOLE_CH = 0.15                           # 穴の縁の面取り [mm](内壁の半径は HOLE_R、面取りの下端が底を隠す縁)
PIN_C, PIN_R, PIN_H = (3.4, 2.4), 0.8, 5.0
PIN_CHAMFER = 0.12                       # ピン先の面取り [mm](上面の平らな円の半径は PIN_R のまま)
DIE = (-2.2, 2.2, -4.6, -1.4, 0.7)       # 樹脂モールドの外形(x0, x1, y0, y1, 高さ)
DIE_DRAFT = 0.10                         # モールドの抜き勾配(上面が側面より内側へ入る量 [mm])
LEADS = 6                                # 片側のリード数(長辺の 2 辺)

#: 面の種類 → 質感。金属は複素屈折率の色(glassmirror)× 仕上げの異方性ローブ(metalfinish)、
#: 樹脂は拡散 + 上塗り(surfacelib.clearcoat_shade)。
SURF = {
    "plate": ("metal", "al", "linear"),        # アルミの治具プレート(フライスの送り目)
    "wall": ("metal", "al", "linear"),         # 穴の内壁(エンドミルの削り目)
    "bottom": ("metal", "al", "circular"),     # 平底の削り目(同心円)
    "hole_chamfer": ("metal", "al", "circular"),
    "pin_top": ("metal", "au", "random"),      # 金めっきのピン
    "pin_chamfer": ("metal", "au", "random"),
    "pin_side": ("metal", "au", "linear"),
    "lead": ("metal", "ag", "random"),         # 銀色(錫めっき)のリード
    "die_top": ("resin", (0.035, 0.035, 0.040), 0.30),   # 黒い樹脂モールド(梨地)
    "die_side": ("resin", (0.030, 0.030, 0.035), 0.30),
}


def _ring(elev_deg, n, weight, phase):
    c, s = math.cos(math.radians(elev_deg)), math.sin(math.radians(elev_deg))
    return [((c * math.cos(a), c * math.sin(a), s), weight / n)
            for a in np.linspace(0.0, 2 * np.pi, n, endpoint=False) + phase]


#: 照明: (向き [世界、シーン→光源], 重み)。coax = 同軸落射 + 弱いドーム、ring = 45° のリング照明。
LIGHTS = {
    "coax": [((0.0, 0.0, 1.0), 0.55)] + _ring(55.0, 6, 0.45, 0.3),
    "ring": _ring(45.0, 8, 1.0, 0.2),
    "dome": _ring(30.0, 6, 0.5, 0.1) + _ring(65.0, 6, 0.5, 0.6),
    "lowring": _ring(20.0, 8, 1.0, 0.2),
}


def _plate_with_hole(half, c, r, depth, ch=HOLE_CH, n=128, rings=8):
    """穴あきの治具プレート: 上面 → 縁の面取り(半径 r + ch → r、深さ ch)→ 内壁 → 平底。"""
    th = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    dirs = np.stack([np.cos(th), np.sin(th)], 1)
    cc = np.asarray(c, float)
    inner = cc + (r + ch) * dirs
    rim = cc + r * dirs
    t = np.full(n, np.inf)
    for ax in (0, 1):
        with np.errstate(divide="ignore"):
            for wall in (-half, half):
                tt = (wall - cc[ax]) / dirs[:, ax]
                t = np.where((tt > 0) & (tt < t), tt, t)
    outer = cc + t[:, None] * dirs
    V, F, G = [], [], []
    for k in range(rings + 1):
        ring = inner + (outer - inner) * (k / rings)
        V += [(x, y, 0.0) for x, y in ring]
    for k in range(rings):
        for j in range(n):
            a, b = k * n + j, k * n + (j + 1) % n
            c2, d2 = a + n, b + n
            F += [(a, b, d2), (a, d2, c2)]
            G += ["plate", "plate"]
    base = len(V)
    V += [(x, y, 0.0) for x, y in inner] + [(x, y, -ch) for x, y in rim] + [(x, y, -depth) for x, y in rim]
    for k, name in ((0, "hole_chamfer"), (1, "wall")):
        for j in range(n):
            a, b = base + k * n + j, base + k * n + (j + 1) % n
            F += [(a, b + n, b), (a, a + n, b + n)]
            G += [name, name]
    base += n
    ctr = len(V)
    V.append((cc[0], cc[1], -depth))
    for j in range(n):
        F.append((ctr, base + n + j, base + n + (j + 1) % n))
        G.append("bottom")
    return np.array(V), np.array(F), G


def _pin(c, r, hgt, ch=PIN_CHAMFER, n=96):
    """面取りつきのピン: 平らな上面(半径 r)→ 45° の面取り → 胴(半径 r + ch)。"""
    th = np.linspace(0.0, 2 * np.pi, n, endpoint=False)
    cs, sn = np.cos(th), np.sin(th)
    rings = [(r + ch, 0.0), (r + ch, hgt - ch), (r, hgt)]
    V = [(c[0] + rr * a, c[1] + rr * b, z) for rr, z in rings for a, b in zip(cs, sn)] + [(c[0], c[1], hgt)]
    F, G = [], []
    for k, name in ((0, "pin_side"), (1, "pin_chamfer")):
        for j in range(n):
            a, b = k * n + j, k * n + (j + 1) % n
            F += [(a, b, b + n), (a, b + n, a + n)]
            G += [name, name]
    for j in range(n):
        F.append((3 * n, 2 * n + j, 2 * n + (j + 1) % n))
        G.append("pin_top")
    return np.array(V, float), np.array(F), G


def _box(x0, x1, y0, y1, z0, z1, top, side, inset=0.0):
    """直方体(上面を *inset* だけ内側へ入れると抜き勾配のある側面になる)。"""
    V = np.array([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                  (x0 + inset, y0 + inset, z1), (x1 - inset, y0 + inset, z1),
                  (x1 - inset, y1 - inset, z1), (x0 + inset, y1 - inset, z1)], float)
    F = [(4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return V, np.array(F), [top] * 2 + [side] * 8


def _package():
    """黒い樹脂モールドのパッケージ + 長辺のガルウィングのリード(肩・曲げ・足)。"""
    x0, x1, y0, y1, h = DIE
    parts = [_box(x0, x1, y0, y1, 0.15, h, "die_top", "die_side", DIE_DRAFT)]
    pitch = (x1 - x0) / LEADS
    for i in range(LEADS):
        xc = x0 + (i + 0.5) * pitch
        for sgn, ye in ((-1, y0), (1, y1)):
            ys = sorted((ye, ye + sgn * 0.30))
            parts.append(_box(xc - 0.16, xc + 0.16, ys[0], ys[1], 0.30, 0.42, "lead", "lead"))       # 肩
            yk = sorted((ye + sgn * 0.26, ye + sgn * 0.36))
            parts.append(_box(xc - 0.16, xc + 0.16, yk[0], yk[1], 0.0, 0.42, "lead", "lead"))        # 曲げ
            yf = sorted((ye + sgn * 0.30, ye + sgn * 0.85))
            parts.append(_box(xc - 0.16, xc + 0.16, yf[0], yf[1], 0.0, 0.12, "lead", "lead"))        # 足
    return parts


def scene(dz=0.0):
    """部品の網(世界の z = 物体の高さ、z = 0 が合焦面)。*dz* はワーク全体を持ち上げる量。"""
    parts = [_plate_with_hole(9.0, HOLE_C, HOLE_R, HOLE_D), _pin(PIN_C, PIN_R, PIN_H)] + _package()
    Vs, Fs, Gs, off = [], [], [], 0
    for V, F, G in parts:
        Vs.append(V + np.array([0.0, 0.0, dz]))
        Fs.append(F + off)
        Gs += G
        off += len(V)
    return np.concatenate(Vs), np.concatenate(Fs), np.array(Gs)


def _blur_table(sysd, pitch_um):
    """高さごとのぼけ(光線束の RMS、像面 µm)→ ガウスの σ [画素]。"""
    sp = TC.defocus_spot_vs_depth(sysd, 0.0, -7.0, 7.0, 15, samples=41)
    return sp[:, 0], sp[:, 1] / math.sqrt(2.0) / pitch_um


def _project(cam, xy, z):
    """世界の点 (x, y, z) → 画素 (u, v)(ピンホール)。"""
    K = cam["K"]
    d = cam["pupil_distance_mm"] - z
    return K[0, 2] + K[0, 0] * xy[0] / d, K[1, 2] - K[1, 1] * xy[1] / d


#: 同軸の落射で平らな面が返す明るさ(線形)。仕上げのローブの大きさは種類で 1 桁違うので、ここで揃える。
TARGET = {"al": 0.55, "au": 1.0, "ag": 0.9}
_F0 = {}


def _strength(fin, metal):
    """平らな面を同軸の落射で照らしたときに TARGET[metal] になる finish_shade の強さ。"""
    key = (fin, metal)
    if key not in _F0:
        n = np.zeros((9, 9, 3))
        n[..., 2] = 1.0
        _F0[key] = float(np.mean(metalfinish.finish_shade(n, fin, metal, light=(0.0, 0.0, 1.0), center=(4.3, 4.2))))
    return TARGET[metal] / max(_F0[key], 1e-12) * float(np.mean(glassmirror.metal_mirror_rgb(metal, 1.0)))


_VAO = {}
_MARK = []


def _marking():
    """パッケージの捺印の文字(2 行)を白黒の小さな画像として 1 回だけ作る(fullseye の text_box)。"""
    if not _MARK:
        import fullseye as fs
        img = np.zeros((90, 160, 3))
        img = np.asarray(fs.text_box(img, "FS0715" + chr(10) + "T1C 26", (80, 45), anchor="cm", font_size=22, text_color=(1, 1, 1),
                                     box_alpha=0.0, pad=0))
        _MARK.append(np.clip(img.mean(-1), 0.0, 1.0))
    return _MARK[0]


def _vertex_ao(V, F):
    """頂点の AO(物体空間なのでワークの平行移動で変わらない —— 1 回だけ計算して使い回す)。"""
    key = (len(V), len(F))
    if key not in _VAO:
        _VAO[key] = render_ao.vertex_occlusion(V, F, n_dirs=48, max_dist=3.0)
    return _VAO[key]


def _shade(r, kind, cam, X, Y, lighting, V, F, dz, size, shadows=True):
    """面の種類ごとの質感で陰影を付ける(線形の放射輝度 RGB)。仕上げの陰影は種類ごとの外接矩形だけで計算する。"""
    N = r["normals"]
    h, w = N.shape[:2]
    lights = LIGHTS[lighting]
    hu, hv = _project(cam, HOLE_C, dz - HOLE_D)
    vis = []
    for L, _ in lights:
        if shadows and L[2] < 0.99:
            vis.append(render_shadow.cast_shadow(V, F, L, pose=cam["pose"], intrinsics=cam["K"], width=w, height=h,
                                                 penumbra=4.0, samples=6, shadow_res=768, pcf=1))
        else:
            vis.append(np.ones((h, w)))
    out = np.zeros((h, w, 3))
    pitch = max(3.0, size / 110.0)
    for name, spec in SURF.items():
        m = kind == name
        if not m.any():
            continue
        rows, cols = np.nonzero(m)
        r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
        sl = (slice(r0, r1), slice(c0, c1))
        mm = m[sl]
        Nm = N[sl] * mm[..., None]
        acc = np.zeros(mm.shape + (3,))
        if spec[0] == "metal":
            _, metal, fin = spec
            ang = 90.0 if name in ("wall", "pin_side", "lead") else 0.0
            ctr = (hu - c0 + 0.37, hv - r0 + 0.29)            # 中心が画素の中心に乗ると接線が 0 になる
            if fin == "random":
                Nf = metalfinish.blast_normals(Nm, grain=0.015, cell_px=2.5, seed=3)
            else:
                Nf = metalfinish.micro_normals(Nm, fin, pitch_px=pitch, depth=0.012, angle_deg=ang, center=ctr)
            k = _strength(fin, metal)
            for (L, wgt), sv in zip(lights, vis):
                acc += wgt * sv[sl][..., None] * metalfinish.finish_shade(Nf, fin, metal, light=L, angle_deg=ang,
                                                                         center=ctr, strength=k)
            acc += glassmirror.metal_mirror_rgb(metal, 1.0)[None, None, :] * 0.12      # 周囲の映り込みの代わり
        else:
            _, base, rough = spec
            for (L, wgt), sv in zip(lights, vis):
                acc += wgt * sv[sl][..., None] * surfacelib.clearcoat_shade(np.asarray(base), Nm, light=L, coat=0.5,
                                                                            coat_roughness=rough)
            acc += np.asarray(base)[None, None, :] * 0.4
        out[sl][mm] = acc[mm]
    # AO は凹みと部品の根元だけに(平らな基板は網の放射状の三角形を補間の筋として拾うので掛けない)
    if "face" in r:
        vao = _vertex_ao(V, F)
        fidx = np.clip(r["face"], 0, None)
        ao = np.einsum("ijk,ijk->ij", vao[F[fidx]], r["bary"])
        sel = (kind != "plate") & (kind != "")
        out[sel] *= (0.30 + 0.70 * ao[sel])[..., None]
    # 素材のむら: 世界座標に貼った fBm(ワークと一緒に動く)。金属は低い周波数で ±6 %、樹脂は梨地の細かいむら
    P3 = np.stack([X.ravel(), Y.ravel(), np.zeros(X.size)], 1)
    low = render3d.fbm_noise(P3, 1.6, octaves=4, seed=11).reshape(X.shape)
    fine = render3d.fbm_noise(P3, 0.05, octaves=3, seed=5).reshape(X.shape)
    metal = np.isin(kind, ["plate", "wall", "bottom", "hole_chamfer"])
    out[metal] *= (1.0 + 0.06 * low[metal])[..., None]
    resin = np.isin(kind, ["die_top", "die_side"])
    out[resin] *= (1.0 + 0.25 * fine[resin])[..., None]
    # パッケージの捺印(レーザーマーキング: 樹脂の表面が白っぽく荒れる)
    mark = _marking()
    x0, x1, y0, y1, _ = DIE
    xa, xb, ya, yb = x0 + 0.9, x1 - 0.5, y0 + 0.9, y1 - 0.9
    sel = (kind == "die_top") & (X > xa) & (X < xb) & (Y > ya) & (Y < yb)
    if sel.any():
        mu = ((X[sel] - xa) / (xb - xa) * (mark.shape[1] - 1)).astype(int)
        mv = ((yb - Y[sel]) / (yb - ya) * (mark.shape[0] - 1)).astype(int)
        a = mark[mv, mu]
        out[sel] = out[sel] * (1 - a[:, None]) + a[:, None] * 0.10
    # 治具プレートの刻印(0.5 mm ごとの目盛り)と、パッケージの 1 番ピンの印
    near = np.abs(X - np.round(X * 2) / 2) < 0.03
    major = np.abs(X - np.round(X)) < 0.03
    tick = (kind == "plate") & near & (np.abs(X) < 6.0) & (Y > -6.75) & (Y < np.where(major, -6.05, -6.35))
    out[tick] *= 0.18
    x0, x1, y0, y1, _ = DIE
    dot = (kind == "die_top") & (np.hypot(X - (x0 + 0.55), Y - (y1 - 0.55)) < 0.22)
    out[dot] = out[dot] * 0.4 + 0.012
    return out


def render(sysd, dz, size, pitch_um, blur=None, lighting="coax", shadows=True, kinds_only=False):
    """レンズの入射瞳に置いたピンホールで描き、質感・AO・影・ぼけを掛けた RGB と、面の種類の地図を返す。"""
    from scipy import ndimage
    cam = TC.lens_equivalent_pinhole(sysd, pixel_pitch_um=pitch_um, width=size, height=size)
    V, F, G = scene(dz)
    r = render3d.render_mesh(V, F, cam["pose"], cam["K"], size, size, attributes=True)
    face = r["face"]
    kind = np.where(face >= 0, G[np.clip(face, 0, None)], "").astype(object)
    if kinds_only:                                   # 門の幾何(面の種類の地図)だけ要るとき
        return None, kind, cam
    v, u = np.mgrid[0:size, 0:size].astype(float)
    dep = np.where(np.isfinite(r["depth"]), r["depth"], 0.0)
    K = cam["K"]
    X = (u - K[0, 2]) * dep / K[0, 0]
    Y = (K[1, 2] - v) * dep / K[1, 1]
    hdr = _shade(r, kind, cam, X, Y, lighting, V, F, dz, size, shadows)
    rgb = render_tonemap.tonemap_reinhard(hdr, exposure=2.2)
    rgb = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * np.power(np.clip(rgb, 0.0, None), 1 / 2.4) - 0.055)
    if blur is not None:
        z = cam["pupil_distance_mm"] - r["depth"]
        z = np.where(np.isfinite(z), z, 0.0)
        zs, sig = blur
        layers = np.linspace(z.min(), z.max() + 1e-9, 9)
        acc = np.zeros_like(rgb)
        wsum = np.zeros((size, size))
        for a, b in zip(layers[:-1], layers[1:]):
            m = ((z >= a) & (z < b)).astype(float)
            if not m.any():
                continue
            s = float(np.interp(0.5 * (a + b), zs, sig))
            for ch in range(3):
                acc[..., ch] += ndimage.gaussian_filter(rgb[..., ch] * m, s)
            wsum += ndimage.gaussian_filter(m, s)
        rgb = acc / np.maximum(wsum, 1e-9)[..., None]
    return np.clip(rgb, 0.0, 1.0), kind, cam


def measure_pin_top(rgb, size, field):
    """描いた画像だけからピン上面の径 [mm、公称倍率で換算] を測る(HALCON 流の円の計測モデル)。

    1. 金色の領域(R − B)をピンの付近で取り、内接円(距離変換の最大)で中心と外径の当たりを付ける
       (通常のレンズで見える胴の三日月に引っぱられない)。
    2. 当たりの円(図面の比 上面 / 面取りの外径)を参照に ``metrology`` の円の計測モデルを 2 回当て、
       上面と面取りの境のサブピクセルのエッジに円を当て直す(探索の半幅 3 → 2 画素)。
    """
    from scipy import ndimage
    pxmm = size / field
    c0 = (size - 1) / 2 + PIN_C[0] * pxmm
    r0 = (size - 1) / 2 - PIN_C[1] * pxmm
    gold = rgb[..., 0] - rgb[..., 2]
    win = np.zeros(gold.shape, bool)
    h = int(2.5 * pxmm)
    win[max(0, int(r0) - h):int(r0) + h, max(0, int(c0) - h):int(c0) + h] = True
    g = np.where(win, gold, 0.0)
    msk = ndimage.binary_fill_holes(g > 0.5 * g.max())
    dt = ndimage.distance_transform_edt(msk)
    cy, cx = np.unravel_index(int(np.argmax(dt)), dt.shape)
    rad = (float(dt.max()) + 0.5) * PIN_R / (PIN_R + PIN_CHAMFER)
    gray = rgb.mean(-1)
    res = None
    for ml in (3.0, 2.0):
        mod = metrology.create_metrology_model()
        metrology.add_metrology_object_circle_measure(mod, float(cy), float(cx), rad, n=72)
        res = metrology.apply_metrology_model(mod, gray, measure_length=ml, sigma=1.0, threshold=0.003)[0]
        if res["params"] is None:
            return float("nan"), res
        cy, cx, rad = res["params"]["row"], res["params"]["col"], res["params"]["radius"]
    return 2.0 * rad / pxmm, res


def _equiv_diameter_mm(mask, pitch_um, m):
    return 2.0 * math.sqrt(mask.sum() / math.pi) * pitch_um * 1e-3 / abs(m)


def _overlap(r1, r2, d):
    """半径 r1 の円のうち、距離 d 離れた半径 r2 の円に入る割合(閉形式)。"""
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r2 - r1):
        return 1.0 if r1 <= r2 else (r2 / r1) ** 2
    a1 = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
    a2 = r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    a3 = 0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
    return (a1 + a2 - a3) / (math.pi * r1 * r1)


def chapter_render(L):
    print("\n3. 段差のある部品を描いて測る(ピン 5 mm・ダイ 0.7 mm・穴の深さ 5 mm)")
    size = 200 if REDUCED else 560
    field = 14.0                                     # 描く視野 [mm](物体側)
    res = {}
    for k in ("fa25", "object", "bi"):
        m = abs(RT.paraxial_trace(L[k])["magnification"])
        pitch = field / size * m * 1000.0             # 像面の画素 [µm]
        rows = []
        for dz in (-3.0, 0.0, 3.0):
            _, kind, cam = render(L[k], dz, size, pitch, kinds_only=True)
            top = _equiv_diameter_mm(kind == "pin_top", pitch, cam["magnification"])
            rows.append((dz, top))
        Lr = cam["pupil_distance_mm"]
        res[k] = (rows, Lr, pitch, cam)
    worst = 0.0
    for k in ("fa25",):
        rows, Lr, _, _ = res[k]
        for dz, top in rows:
            cf = 2 * PIN_R * Lr / (Lr - PIN_H - dz)
            worst = max(worst, abs(top / cf - 1))
    rows = res["fa25"][0]
    NUMBERS["pin_fa25_pct"] = 100 * (rows[1][1] / (2 * PIN_R) - 1)
    gate("画像から測ったピン上面の径(面積から、通常 f=25): 閉形式 D·L/(L − 5 mm − Δz) と 0.5 % 以内(Δz = −3, 0, +3)",
         worst < 5e-3, "最大 %.2e、Δz = 0 で真値 1.6 mm を %.2f %% 大きく読む" % (worst, NUMBERS["pin_fa25_pct"]))
    spread = {k: 100 * (res[k][0][2][1] / res[k][0][0][1] - 1) for k in res}
    NUMBERS.update({"pin_spread_" + k: v for k, v in spread.items()})
    gate("ワークが 6 mm 上下すると、ピン上面の読みは 通常 f=25 で %.2f %%、物体側テレセン %.3f %%、両側テレセン %.3f %% 変わる"
         % (spread["fa25"], spread["object"], spread["bi"]),
         spread["fa25"] > 5 and abs(spread["object"]) < 0.5 and abs(spread["bi"]) < 0.5,
         "★0 は作りの結果: 代理のピンホールは近軸の理想(入射瞳 1e7 mm)で、実光線の残り(2 章の 0.013 %%)は"
         "この画素(物体で %.0f µm)より小さい" % (field / size * 1000))
    # 穴の底: 見える割合を円の重なりで
    _, kind, cam = render(L["fa25"], 0.0, size, res["fa25"][2], kinds_only=True)
    Lr = cam["pupil_distance_mm"]
    kt, kb = Lr / (Lr + HOLE_CH), Lr / (Lr + HOLE_D)          # 底を隠す縁 = 面取りの下端(深さ HOLE_CH)
    off = math.hypot(*HOLE_C)
    cf = _overlap(HOLE_R * kb, HOLE_R * kt, off * (kt - kb))
    seen = float((kind == "bottom").sum())
    full = math.pi * (HOLE_R * kb / (field / size)) ** 2
    frac = seen / full
    NUMBERS.update({"hole_bottom_fa25": frac, "hole_bottom_cf": cf})
    _, kind_t, _ = render(L["bi"], 0.0, size, res["bi"][2], kinds_only=True)
    frac_t = float((kind_t == "bottom").sum()) / (math.pi * (HOLE_R / (field / size)) ** 2)
    wall_t = int((kind_t == "wall").sum())
    NUMBERS.update({"hole_bottom_bi": frac_t, "wall_px_bi": wall_t, "wall_px_fa25": int((kind == "wall").sum())})
    gate("穴の底の見える割合(通常 f=25): 描画 %.3f = 円の重なりの閉形式 %.3f(差 < 0.02)、内壁が %d 画素見える"
         % (frac, cf, NUMBERS["wall_px_fa25"]), abs(frac - cf) < 0.02 and NUMBERS["wall_px_fa25"] > 50)
    gate("両側テレセンでは穴の底が %.3f 見え(差 < 0.02 で 1)、内壁は %d 画素(真上からは見えない)" % (frac_t, wall_t),
         abs(frac_t - 1) < 0.02 and wall_t == 0)
    # 照明を変えても、描いた画像から測った寸法の読みが閉形式を追うか(上の門は面の種類の地図 = 照明に依らない)
    msize = 400                                      # ★300 画素(物体で 47 µm/画素)では低角リングで 2 % 外れた(エッジが弱い)
    lightings = ("coax", "lowring") if REDUCED else ("coax", "dome", "lowring")
    worst, spreads, reads = 0.0, {}, {}
    for k in ("fa25", "bi"):
        m = abs(RT.paraxial_trace(L[k])["magnification"])
        pitch = field / msize * m * 1000.0
        blur = _blur_table(L[k], pitch)
        for lt in lightings:
            vals = []
            for dz in (-3.0, 3.0) if REDUCED else (-3.0, 0.0, 3.0):
                rgb, _, cam = render(L[k], dz, msize, pitch, blur, lighting=lt, shadows=False)
                d, _r = measure_pin_top(rgb, msize, field)
                Lr = cam["pupil_distance_mm"]
                cf = 2 * PIN_R * Lr / (Lr - PIN_H - dz)
                worst = max(worst, abs(d / cf - 1)) if math.isfinite(d) else math.inf
                vals.append(d)
                reads[(k, lt, dz)] = d
            spreads[(k, lt)] = 100 * (vals[-1] / vals[0] - 1)
    NUMBERS["meas_worst"] = worst
    NUMBERS.update({"meas_spread_%s_%s" % kl: v for kl, v in spreads.items()})
    print("   照明 × Δz のピン上面の読み [mm]: " + "  ".join("%s/%s/%+.0f=%.4f" % (k, lt, dz, v)
                                                    for (k, lt, dz), v in sorted(reads.items())))
    gate("照明を変えても(%s)、画像から円の計測モデルで測ったピン上面の径は閉形式と 1 %% 以内" % " / ".join(lightings),
         worst < 0.01, "最大 %.2f %%" % (100 * worst))
    gate("どの照明でも 6 mm の上下で 通常 f=25 の読みは %s %%、両側テレセンは %s %%"
         % ("/".join("%+.2f" % spreads[("fa25", lt)] for lt in lightings),
            "/".join("%+.2f" % spreads[("bi", lt)] for lt in lightings)),
         all(spreads[("fa25", lt)] > 5 for lt in lightings) and all(abs(spreads[("bi", lt)]) < 0.5 for lt in lightings))
    return res, size, field


# --------------------------------------------------------------------------- #
# 4. テレセンでも残る誤差(絞りの位置ずれ)
# --------------------------------------------------------------------------- #
def chapter_residual(L):
    print("\n4. テレセンでも残る誤差 —— 絞りが後側焦点からずれる")
    base = L["object"]
    lens1 = base["design"]["lens1"]
    f = lens1["efl"]
    h = 8.0
    theta0 = TC.chief_ray_angle(base, h)["object_angle_deg"]
    obj = base["design"]["object_mm"]
    target = 0.1
    Lt = h / math.tan(math.radians(target))
    # 物体から入射瞳まで Lt: 入射瞳は前側焦点から −f²/δ(Newton)、z_E = ffl − f²/δ、L = z_E + obj → δ = −f² / (Lt − obj − ffl)
    delta = -f * f / (Lt - obj - lens1["ffl"])
    shifted = TC.telecentric_lens("object", stop_shift_mm=delta)
    Lpara = obj + RT.paraxial_trace(shifted)["ep_position"]
    gate("Newton の閉形式の入射瞳(物体から %.1f mm)は近軸の追跡と一致(相対 1e-9)" % Lt, abs(Lpara / Lt - 1) < 1e-9,
         "★近軸どうしなので一致して当然。実光線は次の門で")
    excess = []
    for hh in (0.5, 2.0, 4.0, 8.0):
        t_ = TC.chief_ray_angle(shifted, hh)["object_angle_deg"] - TC.chief_ray_angle(base, hh)["object_angle_deg"]
        cf = -math.degrees(math.atan(hh / Lt))
        excess.append((hh, t_, cf, t_ / cf - 1))
    NUMBERS.update({"delta_mm": delta, "excess_05": excess[0][3], "excess_8": excess[-1][3], "theta0": theta0})
    gate("δ = %.3f mm のずれ: 物高 0.5 mm では実光線の傾きの増分が閉形式と %.2f %% —— 物高 8 mm では %.1f %% 大きい"
         % (delta, 100 * excess[0][3], 100 * excess[-1][3]), abs(excess[0][3]) < 1e-3 and 0.05 < excess[-1][3] < 0.2)
    ratio = excess[-1][3] / excess[2][3]
    gate("★その差は瞳の球面収差: 物高を 2 倍(4 → 8 mm)にすると差は %.1f 倍(h² なら 4)" % ratio, 3.5 < ratio < 5.0)
    # 実光線で視野の端の(単レンズの分も込みの)テレセン度をちょうど −0.1° にする δ(割線法)
    def edge(d):
        return TC.chief_ray_angle(TC.telecentric_lens("object", stop_shift_mm=d), h)["object_angle_deg"] + target
    d0, d1 = delta, delta * 0.9
    for _ in range(20):
        e0, e1 = edge(d0), edge(d1)
        if abs(e1) < 1e-9:
            break
        d0, d1 = d1, d1 - e1 * (d1 - d0) / (e1 - e0)
    NUMBERS["delta_real_mm"] = d1
    print("   実光線で視野の端のテレセン度をちょうど −0.1° にする δ = %.3f mm(単レンズ自身の %+.4f° も込み)" % (d1, theta0))
    shifted = TC.telecentric_lens("object", stop_shift_mm=d1)
    sweep = []
    for d in np.linspace(-4.0, 4.0, 17):
        sysd = TC.telecentric_lens("object", stop_shift_mm=float(d))
        t_ = TC.chief_ray_angle(sysd, 2.0)["object_angle_deg"] - TC.chief_ray_angle(base, 2.0)["object_angle_deg"]
        Lcf = (lens1["ffl"] - f * f / d + obj) if d != 0 else math.inf
        cf = -math.degrees(math.atan(2.0 / Lcf)) if math.isfinite(Lcf) else 0.0
        sweep.append((d, t_, cf))
    sweep = np.array(sweep)
    worst = float(np.max(np.abs(sweep[:, 1] / np.where(sweep[:, 2] == 0, 1, sweep[:, 2]) - 1)[sweep[:, 2] != 0]))
    gate("δ を ±4 mm 振ると物高 2 mm の傾きは δ に比例し(閉形式と 1 % 以内)、符号で通常側 / ハイパー側に分かれる",
         worst < 0.01, "最大 %.2f %%" % (100 * worst))
    err = TC.telecentricity_error(shifted, h, 5.0)
    NUMBERS.update({"resid_shift_um": err["lateral_shift_um"], "resid_cf_um": err["closed_form_shift_um"]})
    gate("テレセン度 0.1° が残ると、段差 5 mm の上下で物高 8 mm の点は %.2f µm ずれて見える(主光線の幾何 5 × tan 0.1° = %.2f µm、10 %% 以内)"
         % (err["lateral_shift_um"], err["closed_form_shift_um"]),
         abs(err["lateral_shift_um"] / err["closed_form_shift_um"] - 1) < 0.10, "差は上の面で主光線の傾きが少し変わる分")
    e_fa = TC.telecentricity_error(L["fa25"], 4.0, 5.0)
    NUMBERS["fa25_shift_um"] = e_fa["lateral_shift_um"]
    print("   比較: 通常 f=25 で物高 4 mm・段差 5 mm は %.0f µm(%.2f %%)" % (e_fa["lateral_shift_um"],
                                                                 100 * e_fa["relative_size_error"]))
    return sweep


# --------------------------------------------------------------------------- #
# 5. 視野は前玉径で決まる
# --------------------------------------------------------------------------- #
def _open(sysd):
    """口径を外した複製(光束の足跡を、蹴られる前の形で見るため)。"""
    o = copy.deepcopy(sysd)
    for sf in o["surfaces"]:
        sf["ap"] = None
    return o


def _cone(sysd, h, slopes_y, slopes_x=None):
    """物高 h の点から、傾き (dx/dz, dy/dz) の光線を口径なしの処方に通す(公開 op ``raytrace.trace_rays``)。"""
    sy = np.atleast_1d(np.asarray(slopes_y, float))
    sx = np.zeros_like(sy) if slopes_x is None else np.atleast_1d(np.asarray(slopes_x, float))
    P = np.tile([0.0, h, -sysd["object_mm"]], (len(sy), 1))
    D = np.stack([sx, sy, np.ones_like(sy)], 1)
    return RT.trace_rays(_open(sysd), P, D)


def _footprint(sysd, h):
    """絞りを通る光束が前玉の上に落とす足跡の (中心, 半幅)(子午面、実光線)。"""
    s0 = TC.chief_ray_angle(sysd, h)["object_slope"]
    na = sysd["design"]["na_object"]
    g = np.linspace(-1.6 * na, 1.6 * na, 121)
    SX, SY = np.meshgrid(g, g + s0)
    tr = _cone(sysd, h, SY.ravel(), SX.ravel())
    st = sysd["stop"]
    pts = tr["points"]
    ok = np.hypot(pts[:, st + 1, 0], pts[:, st + 1, 1]) <= sysd["surfaces"][st]["ap"]
    y = pts[ok, 1, 1]
    return 0.5 * (y.min() + y.max()), 0.5 * (y.max() - y.min())


def _half_point(hs, v):
    """v が最大を過ぎてから初めて 0.5 を下回る物高(線形補間)。見つからなければ 0。"""
    i0 = int(np.argmax(v))
    for i in range(i0, len(v) - 1):
        if v[i] >= 0.5 > v[i + 1]:
            return float(hs[i] + (v[i] - 0.5) * (hs[i + 1] - hs[i]) / (v[i] - v[i + 1]))
    return 0.0


def chapter_field(L):
    print("\n5. 視野は前玉径で決まる(ケラレ)")
    out = {}
    n = 21 if REDUCED else 49
    for k in ("ento", "object", "bi"):
        out[k] = TC.vignetting_vs_field(L[k], 16.0, n, 61 if REDUCED else 81)
    res = {}
    for k in ("object", "bi"):
        d = L[k]["design"]
        rb = d["na_object"] * d["object_mm"]
        a = d["front_aperture_mm"]
        hs = out[k][:, 0]
        cf = np.array([_overlap(rb, a, h) for h in hs])
        v = out[k][:, 1]
        plateau = float(np.max(v[hs < a - rb - 0.5]))
        vn = v / plateau
        h50 = _half_point(hs, vn)
        c50 = _half_point(hs, cf)
        lo, hi = 5.0, 15.0                                  # 光束の中心が前玉の縁に来る物高(実光線、二分法)
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if _footprint(L[k], mid)[0] < a else (lo, mid)
        res[k] = (cf, h50, c50, rb, a, plateau, mid)
    NUMBERS.update({"h50_object": res["object"][1], "c50_object": res["object"][2], "rim_object": res["object"][6],
                    "h50_bi": res["bi"][1], "c50_bi": res["bi"][2], "rim_bi": res["bi"][6],
                    "plateau_object": res["object"][5]})
    ok = all(abs(res[k][1] - res[k][6]) < 0.4 and res[k][1] > 8.0 for k in ("object", "bi"))
    gate("テレセンの視野の 50 %% 点(物体側 %.2f mm、両側 %.2f mm)= 光束の中心が前玉の縁(半口径 12.5 mm)に来る物高"
         "(%.2f / %.2f mm、差 < 0.4 mm)" % (res["object"][1], res["bi"][1], res["object"][6], res["bi"][6]), ok,
         "50 % 点が見つからなければ 0 で落とす")
    gate("★近軸の閉形式(光束の円の中心 = 物高、半径 NA·物体距離 %.2f mm)の 50 %% 点は %.2f mm —— 実光線は %.2f mm 手前で欠ける"
         "(瞳の球面収差で光束が外へずれて太る)" % (res["object"][3], res["object"][2], res["object"][2] - res["object"][1]),
         res["object"][2] - res["object"][1] > 0.3)
    gate("通常のレンズは主光線がレンズの中心へ集まるので物高 16 mm(前玉の 1.3 倍)まで蹴られない(%.3f)" % out["ento"][-1, 1],
         out["ento"][-1, 1] > 0.95)
    gate("★ケラレの前に光束が %.0f %% 増える(物体側テレセン):瞳の球面収差で軸外の局所焦点距離が短く、絞りが受ける角が広がる"
         % (100 * (res["object"][5] - 1)), res["object"][5] > 1.02, "周辺光量の不均一の原因")
    return out, res


# --------------------------------------------------------------------------- #
# 6. 被写界深度と NA
# --------------------------------------------------------------------------- #
def chapter_dof(L):
    print("\n6. 被写界深度と NA の取引")
    rows = []
    for na in (0.005, 0.01, 0.02):
        sysd = TC.telecentric_lens("bi", na_object=na)
        sp = TC.defocus_spot_vs_depth(sysd, 0.0, -4.0, 4.0, 17, samples=41 if REDUCED else 61)
        z, r = sp[:, 0], sp[:, 1]
        far = np.abs(z) >= 2.0
        A = np.stack([np.abs(z[far]), np.ones(far.sum())], 1)
        slope = float(np.linalg.lstsq(A, r[far], rcond=None)[0][0])
        cf = 0.5 * na / math.sqrt(2.0) * 1000.0                   # µm / mm(|m| = 0.5)
        rows.append((na, slope, cf, sp))
    worst = max(abs(s / c - 1) for _, s, c, _ in rows)
    NUMBERS["dof_slope_worst"] = worst
    gate("ぼけの RMS の傾き(|Δz| ≥ 2 mm)は |m|·NA/√2 と NA = 0.005 / 0.01 / 0.02 で 3 % 以内", worst < 0.03,
         " / ".join("%.3f→%.2f µm/mm(閉 %.2f)" % (na, s, c) for na, s, c, _ in rows))
    lam = 0.58756e-3
    c_obj = 0.022                                   # 許すぼけの直径 [mm、物体側](5.5 µm 画素 × 2 / |m| 0.5)
    na_opt = 1.22 * lam / c_obj
    NUMBERS.update({"na_opt": na_opt, "dof_at_opt": c_obj / na_opt})
    print("   許すぼけ c = 22 µm(物体側)を回折の円の直径 1.22λ/NA が超えない最小の NA = %.4f、そのとき被写界深度 c/NA = %.2f mm が上限"
          "(NA 0.01 なら深さ %.1f mm だが回折の円が %.0f µm)" % (na_opt, c_obj / na_opt, c_obj / 0.01, 1.22 * lam / 0.01 * 1000))
    return rows


# --------------------------------------------------------------------------- #
# 第二の実装(optiland、あれば)
# --------------------------------------------------------------------------- #
def chapter_second(L):
    print("\n付録. 第二の実装(OSS optiland)")
    try:
        import optiland  # noqa: F401
    except ImportError:
        print("   [skip] optiland が入っていない(pip install optiland で同じ突き合わせが走る)")
        for k, y in OPTILAND_RECORDED.items():
            print("   記録(2026-10-15、optiland 0.6.3): %s %.6f mm / telecentric %.6f mm"
                  % (LABEL[k], y, TC.chief_ray_angle(L[k], 8.0)["image_y_mm"]))
        return None
    from optiland import optic
    bk7 = RT.glass_catalog("BK7")["name"]
    out = {}
    for k in ("ento", "object"):
        s = L[k]
        o = optic.Optic()
        o.add_surface(index=0, thickness=s["object_mm"])
        for i, sf in enumerate(s["surfaces"]):
            R = sf["R"] if math.isfinite(sf["R"]) else np.inf
            mat = bk7 if sf["n"] == bk7 else "air"    # optiland へは同じ硝材のキーを渡す(名前は表から引く)
            kw = dict(index=i + 1, radius=R, thickness=sf["t"], material=mat, is_stop=(i == s["stop"]))
            o.add_surface(**kw)
        o.add_surface(index=len(s["surfaces"]) + 1)
        o.set_aperture(aperture_type="objectNA", value=s["design"]["na_object"])
        o.set_field_type(field_type="object_height")
        o.add_field(y=0.0)
        o.add_field(y=8.0)
        o.add_wavelength(value=0.58756, is_primary=True)
        try:
            o.set_ray_aiming("iterative")
        except Exception:                               # noqa: BLE001
            pass
        o.trace_generic(Hx=0.0, Hy=1.0, Px=0.0, Py=0.0, wavelength=0.58756)
        y = float(np.asarray(o.surface_group.y)[-1].ravel()[0])
        ours = TC.chief_ray_angle(s, 8.0)["image_y_mm"]
        out[k] = (y, ours)
        print("   %s: optiland %.6f mm / telecentric %.6f mm" % (LABEL[k], y, ours))
    worst = max(abs(a - b) for a, b in out.values())
    gate("optiland の主光線の像の高さ(物高 8 mm)と 1e-4 mm 以内", worst < 1e-4,
         "最大 %.1e mm。★内訳: 屈折率はどちらも公開の硝材カタログの同じ Sellmeier 係数(1.5168001)なので、一致が見ているのは"
         "面との交点と主光線の狙いの実装だけ。optiland の狙いを近軸(paraxial)にすると物体側テレセンで 0.011 mm 違う"
         "(主光線が絞りを 0.083 mm 外す)" % worst)
    return out


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def _layout_plot(sysd, title):
    """処方の断面(面の形・絞り)と、物高 0 / ±6 mm からの主光線と周辺光線。"""
    series, styles, colors = [], [], []
    surf = sysd["surfaces"]
    z = 0.0
    zs = []
    for sf in surf:
        zs.append(z)
        z += sf["t"] or 0.0
    z_img = zs[-1] + (surf[-1]["t"] or 0.0)
    for i, sf in enumerate(surf):
        ap = sf["ap"]
        if i == sysd["stop"]:
            for sgn in (1, -1):
                series.append(("絞り" if sgn == 1 else "", np.array([zs[i], zs[i]]), sgn * np.array([ap, ap + 4])))
                styles.append(None)
                colors.append("wrong")
            continue
        if i == len(surf) - 1 and sf["n"] == 1.0 and not math.isfinite(sf["R"]) and i != sysd["stop"]:
            continue
        y = np.linspace(-ap, ap, 41)
        c = 0.0 if not math.isfinite(sf["R"]) else 1.0 / sf["R"]
        sag = c * y * y / (1 + np.sqrt(np.clip(1 - c * c * y * y, 0, None)))
        series.append(("レンズ" if i == 0 else "", zs[i] + sag, y))
        styles.append(None)
        colors.append("neutral")
    obj = sysd["object_mm"]
    for h in (6.0, 0.0, -6.0):
        hh = h if h != 0 else 1e-9
        rays = []
        if h != 0:
            s0 = TC.chief_ray_angle(sysd, h)["object_slope"]
            rays.append((s0, "主光線", "emphasis", None))
        na = sysd["design"]["na_object"]
        s_c = TC.chief_ray_angle(sysd, hh)["object_slope"] if h != 0 else 0.0
        rays += [(s_c + na, "周辺光線", "reference", "dashed"), (s_c - na, "", "reference", "dashed")]
        for s, lab, col, sty in rays:
            tr = _cone(sysd, h, [s])
            p = tr["points"][0]
            series.append((lab if h == 6.0 else "", p[:, 2], p[:, 1]))
            styles.append(sty)
            colors.append(col)
    series.append(("像面", np.array([z_img, z_img]), np.array([-8.0, 8.0])))
    styles.append("dotted")
    colors.append("neutral")
    return figs.render_plot(series, xlabel="光軸 z [mm](物体 = %.0f)" % -obj, ylabel="y [mm]", title=title,
                            size=(760, 250), styles=styles, colors=colors, ylim=(-17, 17))


def make_figures(L, chief, depth, rend, sweep, field, dof):
    import fullseye as fs
    # 1. 断面図
    panels = [_layout_plot(L[k], "%s:主光線は %s" % (LABEL[k], t)) for k, t in
              (("ento", "入射瞳(レンズ)へ集まる"), ("object", "物体側で光軸に平行"), ("bi", "物体側も像側も平行"))]
    figs.save("lens_layouts", np.concatenate(panels, 0),
              "同じ BK7 相当の等凸レンズ(f = 100 mm)で、絞り(赤)の位置だけを変えた 3 種。物高 ±6 mm の主光線(実線)は、"
              "通常のレンズでは絞りへ向かって傾き、絞りを後側焦点に置くと物体側で光軸に平行になる。")
    # 2. 倍率と高さ
    curves, af = depth
    ser = []
    sty, col = [], []
    pal = {"fa25": "wrong", "ento": "emphasis", "object": "right", "bi": "neutral"}
    for k in ("fa25", "ento", "object", "bi"):
        ser.append((LABEL[k] + "(実光線)", curves[k][0], curves[k][1]))
        sty.append(None)
        col.append(pal[k])
    kinds = ["scatter", "scatter", "line", "line", "line", "line"]
    for k in ("fa25", "ento"):
        ser.append(("閉形式 L/(L−Δz)" if k == "fa25" else "", curves[k + "_cf"][0], curves[k + "_cf"][1]))
        sty.append("dashed")
        col.append("reference")
    figs.save_plot("magnification_vs_height", ser, xlabel="物体の高さ Δz [mm](レンズへ近づく向きが正)",
                   ylabel="倍率の変化 [%]", styles=sty, colors=col, kinds=kinds,
                   title="高さで変わる倍率:+5 mm で通常 f=25 は +%.1f %%、テレセンは %.3f %%" % (NUMBERS["pct5_fa25"], NUMBERS["pct5_bi"]),
                   caption="像面を固定して物体だけを動かした実の主光線の像の高さ。破線は主光線の幾何の閉形式。"
                           "テレセン 2 本は 0 の線に重なる。")
    # 3. 描画(静止)と GIF —— 同軸落射 + ドーム、影・AO つき(門の寸法の読みは 3 章で照明を 3 通りに変えて確かめた)
    res, size, fld = rend
    order = ("fa25", "object", "bi")
    names = {"fa25": "通常 f=25 mm", "object": "物体側テレセン", "bi": "両側テレセン"}
    from scipy import ndimage

    def setup(sz):
        out = {}
        for k in order:
            pitch = fld / sz * abs(RT.paraxial_trace(L[k])["magnification"]) * 1000.0
            _, kind, _ = render(L[k], 0.0, sz, pitch, kinds_only=True)
            top = kind == "pin_top"
            hole = (kind == "hole_chamfer") | (kind == "wall") | (kind == "bottom")
            ring = (top ^ ndimage.binary_erosion(top)) | (hole ^ ndimage.binary_erosion(hole))
            out[k] = (pitch, _blur_table(L[k], pitch), ring)
        return out

    def frame(dz, sz, st, fsize):
        tiles = []
        for k in order:
            pitch, blur, ring = st[k]
            rgb, _, _ = render(L[k], dz, sz, pitch, blur)
            rgb = rgb.copy()
            rgb[ring] = (0.1, 0.95, 0.95)
            rgb = np.asarray(fs.text_box(rgb, "%s  Δz=%+.1f mm" % (names[k], dz), (6, 6), anchor="lt", font_size=fsize))
            tiles.append(rgb)
            tiles.append(np.ones((sz, 6, 3)))
        return np.concatenate(tiles[:-1], 1)

    st = setup(size)
    f0 = frame(0.0, size, st, 14)
    still = np.concatenate([f0, np.ones((6, f0.shape[1], 3)), frame(3.0, size, st, 14)], 0)
    figs.save("part_views", still,
              "上段 = 合焦面、下段 = ワークを 3 mm 持ち上げたとき(同軸落射 + ドーム照明)。部品はアルミの治具プレート(穴は深さ 5 mm、"
              "縁は面取り)・金めっきのピン(高さ 5 mm)・黒い樹脂モールドと銀色のリードのパッケージ。水色の線は Δz = 0 のピン上面と穴の縁。"
              "通常のレンズ(左)は穴の内壁とピンの胴が見えて穴の底が欠け、持ち上げるとピンも穴も目盛りも膨らむ。テレセン(中・右)は"
              "真上から見て寸法が変わらない。")
    if figs.target_dir() is not None:
        gsz = 300
        sg = setup(gsz)
        zs = list(np.linspace(-3.0, 3.0, 10)) + list(np.linspace(3.0, -3.0, 10))[1:-1]
        frames = [(np.clip(frame(float(dz), gsz, sg, 12), 0, 1) * 255).astype(np.uint8) for dz in zs]
        figs.save_gif("work_up_down", frames,
                      "ワークを ±3 mm 上下させる。通常のレンズだけ像が伸び縮みし(水色の線 = 合焦面の輪郭)、穴の底が隠れる。", fps=6)
    # 4. 絞りのずれ
    figs.save_plot("stop_shift_telecentricity",
                   [("実光線(単レンズの分を引いた)", sweep[:, 0], sweep[:, 1]),
                    ("Newton の閉形式", sweep[:, 0], sweep[:, 2])],
                   xlabel="絞りの位置ずれ δ [mm](正 = 像側)", ylabel="物高 2 mm の主光線の傾きの増分 [°]",
                   kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                   title="絞りが %.2f mm ずれると視野の端で 0.1°(段差 5 mm で %.1f µm)" % (NUMBERS["delta_real_mm"], NUMBERS["resid_shift_um"]),
                   caption="負 = 主光線が光軸へ寄る(通常のレンズ側)、正 = 遠い物ほど大きく写るハイパーセントリック側。")
    # 5. ケラレ
    out, rr = field
    ser = [(LABEL[k], out[k][:, 0], out[k][:, 1]) for k in ("ento", "object", "bi")]
    ser += [("近軸の円の重なり", out["object"][:, 0], rr["object"][0] * rr["object"][5]),
            ("", out["bi"][:, 0], rr["bi"][0] * rr["bi"][5])]
    figs.save_plot("field_vs_front_lens", ser, xlabel="物高 [mm](前玉の半口径 12.5 mm)", ylabel="届く光束(軸上 = 1)",
                   styles=[None, None, None, "dashed", "dashed"], colors=["wrong", "emphasis", "right", "reference", "reference"],
                   title="テレセンの視野は前玉径で決まる(50 %% 点 %.1f mm)" % NUMBERS["h50_object"],
                   caption="通常のレンズは主光線がレンズの中心へ集まるので前玉より広く見える。テレセンは主光線が平行なので、"
                           "前玉の外の物は写らない。破線は近軸の光束の円と前玉の円の重なり(瞳収差による光束の増え方を掛けた)で、"
                           "実光線はそれより早く欠ける —— 光束が外へずれて太るため。")
    # 6. 被写界深度
    ser, sty, col = [], [], []
    pc = ["right", "emphasis", "wrong"]
    for i, (na, s, c, sp) in enumerate(dof):
        ser.append(("NA %.3f(実光線)" % na, sp[:, 0], sp[:, 1]))
        sty.append(None)
        col.append(pc[i])
        ser.append(("" if i else "|m|·NA·|Δz|/√2", sp[:, 0], c * np.abs(sp[:, 0])))
        sty.append("dashed")
        col.append("reference")
    figs.save_plot("defocus_vs_na", ser, xlabel="物体の高さ Δz [mm]", ylabel="像面のぼけ RMS [µm]", styles=sty, colors=col,
                   title="NA を倍にすると深さは半分(22 µm を分解する NA %.3f で深さ %.2f mm)" % (NUMBERS["na_opt"], NUMBERS["dof_at_opt"]),
                   caption="両側テレセンで NA だけを変えた。破線は一様な円の光束の RMS。NA 0.02 では最良の焦点が近軸の焦点から"
                           "ずれ(球面収差)、Δz = 0 の床も上がる —— NA を上げると深さだけでなく収差の余裕も減る。")


# --------------------------------------------------------------------------- #
# 0. 実画像: 論文の生画像を測って、論文の値と突き合わせる
# --------------------------------------------------------------------------- #
#: 出典(図・figures.json・能力ノートにも同じ文言で載せる)。ライセンスは 2026-10-15 に各ページで確認:
#: figshare の各 item(API の license = "CC BY 4.0")、Zenodo 15432113(cc-by-4.0)、論文本文末尾の
#: "licensed under a Creative Commons Attribution 4.0 International License"。
REAL_SOURCE = ("A. W. Stark, A. Osadare, M. Guo, G. J. Gentsch, D. Boettger, G. Brehm, C. Franke, "
               "\"Telecentric stereo 3D imaging with isotropic micrometer resolution bridges macro- and microscale in "
               "small Lepidopterans\", Scientific Reports 15, 28690 (2025), doi:10.1038/s41598-025-13795-6. "
               "画像: figshare collection doi:10.6084/m9.figshare.c.7652423(item 28322132 / 28322006 / 28322036、"
               "A. Stark)。CC BY 4.0。改変: グレースケール化・縮小・計測の線の描き込み。")
REAL_SOURCE_SHORT = "画像: Stark et al., Sci. Rep. 15, 28690 (2025)、figshare doi:10.6084/m9.figshare.c.7652423、CC BY 4.0(改変あり)"

#: 取得する 3 枚(全体 2.5 GB の Zenodo の zip は落とさない —— 同じ著者が figshare に単品で置いた 3 枚だけ)。
#: md5 は figshare の API の computed_md5、sha256 は 2026-10-15 に取得した実物から。
REAL_FILES = {
    "plate": ("https://ndownloader.figshare.com/files/52055885", "alignment_plate.png", 11649567,
              "307fba7b60361549c9269a8aa89d49f6484f146109cd72e0c6468d5867fde44e"),
    "sphere_cam1": ("https://ndownloader.figshare.com/files/52055744", "sphere_cam1_pos0001.jpg", 454625,
                    "21e5de2b37f26960976ed2f7ca1c3b3027a71b91a5f55040891294a87a8cbf78"),
    "sphere_cam2": ("https://ndownloader.figshare.com/files/52055786", "sphere_cam2_pos0001.jpg", 458249,
                    "41f1452e7b5fb03ba6d1d94820460c17b158fab0a42982e30afa8047c7654e8c"),
}

#: 論文の値(本文から)。
PAPER = {"pitch_mm": 1.0,                    # レンズマウント用のアライメント板、円の間隔 1 mm(Fig. 3a / 6b の説明)
         "K1_px_per_mm": 252.0,              # 式 (3) K1 = diag(252,000, 252,000) [px/m]
         "K2_px_per_mm": (251.8, 253.0),     # 式 (4)
         "um_per_px": 4.0,                   # 「each pixel representing 4 µm」
         "sphere_radius_mm": 2.5}            # 樹脂の 3D プリント球の公称半径(figshare の説明)。校正された球ではない

#: 2026-10-15 の実測(ネットの無い CI ではこれを印字して章を飛ばす。門には使わない)。
REAL_RECORDED = {"px_per_mm": 252.13, "vs_K1_pct": 0.05, "rings": 8, "tilt_deg": 29.5,
                 "beta_px_per_mm2": 0.0035, "beta_se": 0.0034, "pupil_min_mm": 10500.0,
                 "sphere_r_mm": (2.400, 2.452)}


def _real_cache_dir() -> str:
    base = os.environ.get("FULLSEYE_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".cache", "fullseye")
    d = os.path.join(base, "poc_telecentric_metrology")
    os.makedirs(d, exist_ok=True)
    return d


def _sha256(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def real_fetch():
    """3 枚をキャッシュから(無ければ取得して)返す。``(paths, None)`` か ``(None, 飛ばす理由)``。

    ★CI(環境変数 ``CI``)と ``FULLSEYE_OFFLINE=1`` ではネットに出ない。取得したファイルは sha256 を
    確かめてから使い、合わなければ捨てて飛ばす(黙って別の画像で測らない)。repo には入れない。
    """
    d = _real_cache_dir()
    offline = bool(os.environ.get("CI")) or os.environ.get("FULLSEYE_OFFLINE", "") == "1"
    paths = {}
    for key, (url, name, size, sha) in REAL_FILES.items():
        p = os.path.join(d, name)
        if not os.path.exists(p):
            if offline:
                return None, "ネットに出ない設定(CI / FULLSEYE_OFFLINE)で、キャッシュ %s が無い" % p
            try:
                import urllib.request
                with urllib.request.urlopen(url, timeout=120) as r:      # noqa: S310 - 固定の https の URL
                    data = r.read()
            except Exception as exc:                                      # noqa: BLE001 - 取れなければ飛ばす
                return None, "取得できない(%s: %s)" % (type(exc).__name__, str(exc)[:80])
            if len(data) != size:
                return None, "%s の大きさが %d(期待 %d)" % (name, len(data), size)
            with open(p + ".part", "wb") as f:
                f.write(data)
            os.replace(p + ".part", p)
        got = _sha256(p)
        if got != sha:
            os.remove(p)
            return None, "%s の sha256 が合わない(%s…)ので捨てた" % (name, got[:12])
        paths[key] = p
    return paths, None


def _ring_points(g, cy, cx, length=2000.0, step_deg=1.0, amp_min=0.3):
    """中心から放射状に測定線を張り、明るい線(リング)の中心を取る(``measuring1d.measure_pos``)。

    外向きの測定線の上で、強い立ち下がり(|振幅| ≥ *amp_min*)ごとに、その手前 80 px 以内で最後の強い立ち上がりと
    組にして中点を取る。返り値 (M, 3): (行, 列, 線の幅 px)。

    ★2026-10-15 に直した: 以前は ``measure_pairs``(閾値 0.15)の組をそのまま使っていた。``measure_pairs`` は隣り合う
    極性違いのエッジを前から順に組むので、(1) 中央の穴の縁の黒い粒の 1 本で組の位相がずれると、後ろのリングが
    「暗い隙間」の組になって丸ごと落ち、(2) 線の中の粒の弱いエッジ(振幅 0.15〜0.3)と組んで、中点が線の内側の縁へ
    寄った(元の解像度で見ると、外側のリングの点が白い線の内側の縁に並んでいた)。(3) 傾いた板の奥の側は
    ぼけて線が太り(45 px 超)、幅の上限で落ちていた。
    """
    import measuring1d as M1
    out = []
    for a in np.deg2rad(np.arange(0.0, 360.0, step_deg)):
        meas = M1.gen_measure_rectangle2(cy + 0.5 * length * math.sin(a), cx + 0.5 * length * math.cos(a), a,
                                         length / 2, 3, g.shape)
        edges = [e for e in M1.measure_pos(g, meas, sigma=2.0, threshold=amp_min)]
        for i, e in enumerate(edges):
            if e["polarity"] != "negative":
                continue
            rise = [q for q in edges[:i] if q["polarity"] == "positive" and 0 < e["dist"] - q["dist"] < 80]
            if not rise:
                continue
            q = rise[-1]
            r = np.array([0.5 * (q["row"] + e["row"]), 0.5 * (q["col"] + e["col"])])
            if 0 <= r[0] < g.shape[0] and 0 <= r[1] < g.shape[1]:
                out.append((r[0], r[1], e["dist"] - q["dist"]))
    return np.array(out, float)


def _perspective_beta(rk_mm, tilt, L_mm, px_per_mm):
    """傾いた板の同心円を入射瞳の距離 L のピンホールで写したとき、楕円の中心が短軸方向に r² に比例してずれる
    係数 β [px/mm²](閉形式 x' = X·L/(L − Z) で写し、同じ ``fit_ellipse`` で中心を取る)。"""
    import measure as ME
    cen = []
    t = np.linspace(0.0, 2 * np.pi, 720, endpoint=False)
    for r in rk_mm:
        X, Y, Z = r * np.cos(t), r * np.sin(t) * math.cos(tilt), r * np.sin(t) * math.sin(tilt)
        s = L_mm / (L_mm - Z)
        f = ME.fit_ellipse(np.c_[Y * s * px_per_mm, X * s * px_per_mm])
        cen.append(f["cy"])
    A = np.c_[np.asarray(rk_mm) ** 2, np.ones(len(rk_mm))]
    return float(np.linalg.lstsq(A, np.array(cen), rcond=None)[0][0])


def _rho_of(P_, c_, phi_, q_):
    """楕円の族の「半径」: 中心 c_ から見た点を向き phi_ の軸へ回し、短軸を縦横比 q_ で割って伸ばした距離。"""
    dy, dx = P_[:, 0] - c_[0], P_[:, 1] - c_[1]
    u = dx * np.cos(phi_) + dy * np.sin(phi_)
    v = -dx * np.sin(phi_) + dy * np.cos(phi_)
    return np.sqrt(u * u + (v / q_) ** 2)


def plate_ring_points(g):
    """アライメント板の画像 *g*(0〜1)から、中央の穴の中心と、リングの中心線の点・リングの番号を取る。

    ``chapter_real`` と ``poc_simcal_telecentric`` が同じ読み方を使う(2026-10-15 に ``chapter_real`` から切り出した。
    中身は切り出す前と同じ)。返り値: ``cy, cx, hole``(穴の中心と metrology の円)・``pts``(全点)・``phi, q, s, ph``
    (族の向き・縦横比・間隔・位相の当たり)・``P``(使う点 (行, 列))・``idx``(``ks`` の中の位置)・``ks``(リングの番号)。
    """
    from scipy import ndimage
    rho_of = _rho_of
    # (a) 中心: 中央の穴(暗い円板)を距離変換で当たりを付け、metrology の円 → 楕円で縁に当て直す
    dark = ndimage.gaussian_filter(g, 3) < 0.03
    dt = ndimage.distance_transform_edt(dark)
    # 穴は板の中ほどにある。明るい線の勾配の法線が集まる点(最小二乗)を窓の中心にする
    s4 = ndimage.gaussian_filter(g, 4)
    gy, gx = np.gradient(s4)
    mag = np.hypot(gy, gx)
    yy, xx = np.nonzero(mag > np.percentile(mag, 99))
    sel = np.random.default_rng(0).choice(len(yy), min(40000, len(yy)), replace=False)
    P = np.c_[yy[sel], xx[sel]].astype(float)
    Nn = np.c_[gy[yy[sel], xx[sel]], gx[yy[sel], xx[sel]]]
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    w = np.ones(len(P))
    c = np.array(g.shape, float) / 2
    for _ in range(10):
        Pm = np.eye(2)[None] - Nn[:, :, None] * Nn[:, None, :]
        c = np.linalg.solve((w[:, None, None] * Pm).sum(0), (w[:, None, None] * Pm @ P[:, :, None])[:, :, 0].sum(0))
        dd = P - c
        dist = np.abs(dd[:, 0] * Nn[:, 1] - dd[:, 1] * Nn[:, 0])
        w = (dist < max(30.0, float(np.percentile(dist, 50)))).astype(float)
    r0, c0 = int(c[0]), int(c[1])
    win = np.zeros_like(dark)
    win[max(0, r0 - 350):r0 + 350, max(0, c0 - 350):c0 + 350] = True
    dtw = np.where(win, dt, 0.0)
    hy, hx = np.unravel_index(int(np.argmax(dtw)), dt.shape)
    mod = metrology.create_metrology_model()
    metrology.add_metrology_object_circle_measure(mod, float(hy), float(hx), float(dtw.max()), n=90)
    hole = metrology.apply_metrology_model(mod, g, measure_length=15, sigma=2, threshold=0.1)[0]["params"]
    cy, cx = hole["row"], hole["col"]
    # (b) リングの中心線の点 → 同心の相似な楕円の族(共通の中心・向き・縦横比 + リングごとの長半径)を当てる
    #   ★リングごとに自由な楕円(5 自由度)を当てると、影で弧が 90〜180° しか見えない外側のリングは長半径が外挿で
    #   膨らむ・縮む(2026-10-15 に元の解像度で見て分かった: 外側のリングで楕円が白い線から外れ、間隔が 246〜257 px/mm と
    #   ばらついた)。テレセン(正射影)なら傾いた板の同心円は「中心と形を共有する楕円の族」に写るので、族ごと当てる。
    #   族の仮定そのもの(中心の共有)は (c) でリングごとに中心を解き直して確かめる。
    from scipy.optimize import least_squares
    pts = _ring_points(g, cy, cx)
    pts = pts[(pts[:, 2] > 15) & (pts[:, 2] < 80) & (np.hypot(pts[:, 0] - cy, pts[:, 1] - cx) > 200)]


    best = None
    for phi in np.deg2rad(np.arange(-90.0, 90.0, 2.0)):
        for q in np.arange(0.70, 1.0005, 0.01):
            rr = rho_of(pts, (cy, cx), phi, q)
            for s in np.arange(200.0, 300.0, 0.5):
                R = abs(np.mean(np.exp(2j * np.pi * rr / s)))
                if best is None or R > best[0]:
                    best = (R, phi, q, s)
    _, phi, q, s = best
    rr = rho_of(pts, (cy, cx), phi, q)
    ph = float(np.angle(np.mean(np.exp(2j * np.pi * rr / s)))) / (2 * np.pi) * s
    k = np.round((rr - ph) / s).astype(int)
    keep = np.abs(rr - (k * s + ph)) < 25
    P, K = pts[keep, :2], k[keep]
    cnt = {int(kk): int((K == kk).sum()) for kk in np.unique(K)}
    ks = np.array([kk for kk in sorted(cnt) if cnt[kk] >= 30])
    sel = np.isin(K, ks)
    P, idx = P[sel], np.searchsorted(ks, K[sel])
    return {"cy": cy, "cx": cx, "hole": hole, "pts": pts, "phi": phi, "q": q, "s": s, "ph": ph,
            "P": P, "idx": idx, "ks": ks}


def chapter_real(L):
    """実画像の章: 論文の生画像(アライメント板・樹脂の球)を Fullseye の計測 op で測り、論文の値と突き合わせる。"""
    print("\n0. 実画像 —— Stark ほか(Sci. Rep. 2025)のテレセン生画像を測る(%s)" % REAL_SOURCE_SHORT)
    paths, why = real_fetch()
    if paths is None:
        r = REAL_RECORDED
        print("   [skip] %s。2026-10-15 の実測: 円の間隔 %.2f px/mm(論文の K1 252.0 と %+.2f %%)、リング %d 本、"
              "板の傾き %.1f°、楕円の中心のずれ β = %.3f ± %.3f px/mm²(入射瞳は %.0f mm より遠い)、"
              "樹脂の球の輪郭の半径 %.3f / %.3f mm(公称 2.5 mm)" % (why, r["px_per_mm"], r["vs_K1_pct"], r["rings"],
                                                         r["tilt_deg"], r["beta_px_per_mm2"], r["beta_se"],
                                                         r["pupil_min_mm"], *r["sphere_r_mm"]))
        return None
    import measure as ME
    from scipy import ndimage
    g = np.asarray(fs_read(paths["plate"]), float)
    g = g / g.max()
    rp = plate_ring_points(g)
    cy, cx, hole = rp["cy"], rp["cx"], rp["hole"]
    print("   中央の穴: 中心 (%.1f, %.1f) px、半径 %.1f px(metrology の円)" % (cy, cx, hole["radius"]))
    from scipy.optimize import least_squares
    rho_of = _rho_of
    phi, q, s, ph, P, idx, ks = (rp[k] for k in ("phi", "q", "s", "ph", "P", "idx", "ks"))

    def fam_resid(x_, P_, i_):
        return rho_of(P_, x_[:2], x_[2], x_[3]) - x_[4:][i_]

    x = np.r_[cy, cx, phi, q, s * ks + ph]
    inl = np.ones(len(P), bool)
    for _ in range(3):                                   # 外れ点(十字線の交点など)は MAD の 4 倍で落として解き直す
        fit = least_squares(fam_resid, x, args=(P[inl], idx[inl]))
        x = fit.x
        r_all = fam_resid(x, P, idx)
        inl = np.abs(r_all) < 4 * 1.4826 * np.median(np.abs(r_all)) + 1e-9
    dof = max(1, int(fit.fun.size) - len(x))
    cov = np.linalg.inv(fit.jac.T @ fit.jac) * float(np.sum(fit.fun ** 2)) / dof
    ccy, ccx, phi, q = (float(v) for v in x[:4])
    ra = x[4:]
    se_ra = np.sqrt(np.diag(cov)[4:])
    w = 1.0 / se_ra
    A = np.c_[ks, np.ones(len(ks))]
    sol_a, *_ = np.linalg.lstsq(A * w[:, None], ra * w, rcond=None)
    resid_a = ra - A @ sol_a
    cva = np.linalg.inv((A * w[:, None]).T @ (A * w[:, None]))
    chi2 = float(np.sum((resid_a * w) ** 2)) / max(1, len(ks) - 2)
    pxmm = float(sol_a[0])
    se_a = float(math.sqrt(cva[0, 0] * max(1.0, chi2)))
    tilt = math.acos(q)
    rings = []
    for j, kk in enumerate(ks):
        m = (idx == j) & inl
        rj = r_all[m]
        ang = np.degrees(np.arctan2(P[m, 0] - ccy, P[m, 1] - ccx)) % 360.0
        a_s = np.sort(ang)
        span = 360.0 - float(np.diff(np.r_[a_s, a_s[0] + 360.0]).max())
        free = ME.fit_ellipse(P[m])                     # 比較: リングごとに自由な楕円を当てた長半径
        rings.append({"k": int(kk), "n": int(m.sum()), "arc_deg": span, "rms_px": float(np.sqrt(np.mean(rj ** 2))),
                      "max_px": float(np.abs(rj).max()), "free_ra": float(free["ra"]), "pts": P[m],
                      "f": {"cy": ccy, "cx": ccx, "angle_deg": math.degrees(phi), "ra": float(ra[j]),
                            "rb": float(ra[j] * q)}})
    for r in rings:
        print("   リング %d: 点 %3d、弧 %3.0f°、長半径 %.1f px(= %.3f mm、自由な楕円なら %.1f px)、族への残差 RMS %.2f / 最大 %.2f px"
              % (r["k"], r["n"], r["arc_deg"], r["f"]["ra"], r["f"]["ra"] / pxmm, r["free_ra"], r["rms_px"], r["max_px"]))
    worst = max(r["rms_px"] for r in rings)
    gate("実画像: 中心から放射状の測定線(measure_pos の立ち上がりと立ち下がりの中点)でリング %d 本を拾い、同心の相似な"
         "楕円の族への残差は RMS 最大 %.2f px(外れ点 %d / %d 点を落とした)" % (len(rings), worst, int((~inl).sum()), len(inl)),
         len(rings) >= 5 and worst < 3.0)
    free_d = np.diff([r["free_ra"] for r in rings])
    vs = 100.0 * (pxmm / PAPER["K1_px_per_mm"] - 1)
    NUMBERS.update({"real_px_per_mm": pxmm, "real_vs_K1_pct": vs, "real_um_per_px": 1000.0 / pxmm})
    gate("実画像: 円の間隔 1 mm のアライメント板の長軸の伸び = %.2f ± %.2f px/mm(%.3f µm/px)—— 論文の K1 = 252.0 px/mm"
         "(K2 = 251.8 / 253.0)と %+.2f %%(1 %% 以内)" % (pxmm, se_a, 1000.0 / pxmm, vs), abs(vs) < 1.0,
         "論文の「1 画素 = 4 µm」(丸めた値)とは %+.1f %%。★%+.2f %% の一致を精度と読まない —— 論文自身の K1 と K2 が "
         "251.8〜253.0 px/mm(±0.25 %%)で散っている。★リングごとに自由な楕円を当てると間隔が %.0f〜%.0f px と散る"
         "(影で弧が短いリングの外挿)" % (100.0 * (1000.0 / pxmm / PAPER["um_per_px"] - 1), vs, free_d.min(),
                                        free_d.max()))
    gate("実画像: 長半径は間隔の整数 + 1/2 に並ぶ(リングの半径 %s mm、直線からの残差 最大 %.2f px = %.1f µm)"
         % (" / ".join("%.2f" % v for v in ra / pxmm), np.abs(resid_a).max(), 1000.0 * np.abs(resid_a).max() / pxmm),
         np.abs(resid_a).max() < 2.0)
    # (c) テレセンの性質: 傾いた板の同心円の中心は 1 点に集まる —— リングごとに形(向き・縦横比・長半径)を固定して
    #   中心だけを解き直し、短軸方向のずれが r² に比例するか(通常のレンズなら比例する)を見る
    NUMBERS["real_tilt_deg"] = math.degrees(tilt)
    mn = np.array([math.cos(phi), -math.sin(phi)])        # 短軸の向き (行, 列)
    off, se_off = [], []
    for j in range(len(ks)):
        Pj = P[(idx == j) & inl]
        fj = least_squares(lambda c, Pj=Pj, j=j: rho_of(Pj, c, phi, q) - ra[j], np.array([ccy, ccx]))
        cj = np.linalg.inv(fj.jac.T @ fj.jac) * float(np.sum(fj.fun ** 2)) / max(1, len(Pj) - 2)
        off.append(float((fj.x - np.array([ccy, ccx])) @ mn))
        se_off.append(float(math.sqrt(mn @ cj @ mn)))
    proj, se_off = np.array(off), np.array(se_off)
    rk = ra / pxmm
    wb = 1.0 / se_off
    Ab = np.c_[rk ** 2, np.ones(len(rk))]
    sb, *_ = np.linalg.lstsq(Ab * wb[:, None], proj * wb, rcond=None)
    cvb = np.linalg.inv((Ab * wb[:, None]).T @ (Ab * wb[:, None]))
    chi2b = float(np.sum(((proj - Ab @ sb) * wb) ** 2)) / max(1, len(rk) - 2)
    beta, se_b = float(sb[0]), float(math.sqrt(cvb[0, 0] * max(1.0, chi2b)))
    print("   板の傾き %.1f°(縦横比 %.4f)。リングごとの中心の短軸方向のずれ [px]: %s(± %s)"
          % (math.degrees(tilt), q, " / ".join("%+.2f" % v for v in proj), " / ".join("%.2f" % v for v in se_off)))
    Lfa = TC.chief_ray_angle(L["fa25"], 4.0)["pupil_distance_mm"]
    Len = TC.chief_ray_angle(L["ento"], 4.0)["pupil_distance_mm"]
    b_fa = _perspective_beta(rk, tilt, Lfa, pxmm)
    b_en = _perspective_beta(rk, tilt, Len, pxmm)
    b1 = _perspective_beta(rk, tilt, 1000.0, pxmm) * 1000.0      # β·L は L によらずほぼ一定
    lmin = b1 / (abs(beta) + 2 * se_b)
    edge_deg = math.degrees(math.atan(rk.max() / lmin))
    NUMBERS.update({"real_beta": beta, "real_beta_se": se_b, "real_pupil_min_mm": lmin, "real_beta_fa25": b_fa,
                    "real_beta_ento": b_en, "real_shift_fa25_px": b_fa * rk.max() ** 2, "real_edge_deg": edge_deg})
    print("   同じ板を入射瞳 %.1f mm の通常 f=25(2 章)で写すと β = %.2f px/mm²(外側のリングで中心が %.0f px ずれる)、"
          "通常 f=100(入射瞳 %.0f mm)で %.2f" % (Lfa, b_fa, b_fa * rk.max() ** 2, Len, b_en))
    gate("★テレセンの証拠(実画像): 傾いた板の同心円の中心は r² に比例してずれない(β = %.4f ± %.4f px/mm²)。"
         "通常 f=25 なら %.2f、f=100 でも %.2f px/mm² —— 測った β の 2σ の上限 %.3f は f=100 の 1/10 未満"
         % (beta, se_b, b_fa, b_en, abs(beta) + 2 * se_b), abs(beta) + 2 * se_b < 0.1 * abs(b_en),
         "入射瞳は %.1f m より遠い(2σ)= 視野の端 %.1f mm の主光線の傾き < %.3f°" % (lmin / 1000.0, rk.max(), edge_deg))
    proj_all, rk_all, full = proj, rk, np.ones(len(rk), bool)
    # (d) 樹脂の球(公称半径 2.5 mm、3D プリント)—— 輪郭の円の半径
    sph = {}
    for key in ("sphere_cam1", "sphere_cam2"):
        gi = np.asarray(fs_read(paths[key]), float)
        sm = ndimage.gaussian_filter(gi, 3)
        rows = []
        for thr in (0.015, 0.03, 0.06):
            blob = sm > thr
            lab, n = ndimage.label(blob)
            sz = ndimage.sum(blob, lab, range(1, n + 1))
            blob = ndimage.binary_fill_holes(lab == int(np.argmax(sz)) + 1)
            edge = blob ^ ndimage.binary_erosion(blob)
            er, ec = np.nonzero(edge)
            keep = (er < er.min() + 900) & (er > 2) & (ec > 2) & (ec < gi.shape[1] - 3)   # 下の台に触れる側を除く
            f = ME.fit_circle(np.c_[er[keep], ec[keep]])
            rows.append((thr, f["r"] / pxmm, f["rms"], f))
        sph[key] = rows
        print("   球 %s: 輪郭の半径 %s(閾値 0.015 / 0.03 / 0.06、残差 %s px)" % (
            key[-4:], " / ".join("%.3f mm" % r[1] for r in rows), " / ".join("%.1f" % r[2] for r in rows)))
    r1, r2 = sph["sphere_cam1"][0][1], sph["sphere_cam2"][0][1]
    span = max(abs(sph[k][0][1] / sph[k][2][1] - 1) for k in sph)
    NUMBERS.update({"real_sphere_cam1": r1, "real_sphere_cam2": r2, "real_sphere_thr_span": span})
    gate("★樹脂の球は真値にならない: 輪郭の半径は閾値 0.015 → 0.06 で %.1f %% 動き(陰で縁が暗い)、残差 %.1f px"
         "(3D プリントの面の角)。最も低い閾値で %.3f / %.3f mm(公称 2.5 mm と %+.1f / %+.1f %%)"
         % (100 * span, sph["sphere_cam1"][0][2], r1, r2, 100 * (r1 / 2.5 - 1), 100 * (r2 / 2.5 - 1)),
         span > 0.05, "論文の計量級の球(半径 5 mm ±1.6 µm)の生画像は公開データに入っていない")
    return {"g": g, "rings": rings, "hole": (cy, cx), "pxmm": pxmm, "proj": proj, "rk": rk, "rk_all": rk_all, "proj_all": proj_all, "full": full, "beta": beta,
            "se_b": se_b, "b_fa": b_fa, "b_en": b_en, "Lfa": Lfa, "Len": Len, "tilt": tilt, "phi": phi,
            "sph": sph, "paths": paths}


def fs_read(path):
    import fullseye as fs
    return fs.read_image(path)


def make_real_figures(real):
    """実画像の図(既存の図の番号を動かさないよう、最後に足す)。"""
    import fullseye as fs
    g = real["g"]
    rgb = np.repeat(g[..., None], 3, -1) ** (1 / 1.6)
    ov = rgb.copy()
    pal = [(0.90, 0.62, 0.0), (0.34, 0.71, 0.91), (0.0, 0.62, 0.45), (0.94, 0.89, 0.26), (0.0, 0.45, 0.70),
           (0.84, 0.37, 0.0), (0.80, 0.47, 0.65)]
    t = np.linspace(0, 2 * np.pi, 400)
    for i, r in enumerate(real["rings"]):
        f = r["f"]
        phi = math.radians(f["angle_deg"])
        x = f["cx"] + f["ra"] * np.cos(t) * math.cos(phi) - f["rb"] * np.sin(t) * math.sin(phi)
        y = f["cy"] + f["ra"] * np.cos(t) * math.sin(phi) + f["rb"] * np.sin(t) * math.cos(phi)
        ov = np.asarray(fs.draw_polyline(ov, np.c_[x, y], color=pal[i % len(pal)], width=4, closed=True))
        ov = np.asarray(fs.draw_markers(ov, np.array([[f["cx"], f["cy"]]]), color=pal[i % len(pal)], size=14,
                                        shape="cross", width=3))
    half = ov[::2, ::2]
    half = np.asarray(fs.annotate_scale_bar(half, 2.0 * 1000.0 / real["pxmm"], unit="µm"))
    half = np.asarray(fs.text_box(half, "楕円 = 同心の相似な楕円の族(+ = 中心)。1/2 に縮小", (10, 10), font_size=22))
    figs.save("real_alignment_plate", half,
              "【実画像】テレセンで撮ったアライメント板(円の間隔 1 mm)の生画像に、中心から放射状の測定線(measure_pos)で"
              "取ったリングの中心線へ当てた、同心の相似な楕円の族を重ねた(1/2 に縮小。検分は次の等倍の図で)。板は %.1f° 傾いて"
              "楕円に写り、右上は影でリングが見えない。長軸の伸びは %.2f px/mm で、論文の K1 = 252.0 px/mm と %+.2f %%。"
              % (NUMBERS["real_tilt_deg"], real["pxmm"], NUMBERS["real_vs_K1_pct"]) + REAL_SOURCE, source=REAL_SOURCE)
    # 等倍の切り出し: 外側のリングの見えている弧の中ほど(影の境に近く、外挿が効く所)
    ro = real["rings"][-1]
    pp = ro["pts"]
    ang = np.arctan2(pp[:, 0] - ro["f"]["cy"], pp[:, 1] - ro["f"]["cx"])
    j = int(np.argmin(np.abs(ang - np.median(ang))))
    H, W = rgb.shape[:2]
    y0 = int(min(max(0, pp[j, 0] - 250), H - 500))
    x0 = int(min(max(0, pp[j, 1] - 350), W - 700))
    crop = rgb[y0:y0 + 500, x0:x0 + 700].copy()
    tt = np.linspace(0, 2 * np.pi, 4000)
    for i, rr_ in enumerate(real["rings"]):
        f = rr_["f"]
        phi = math.radians(f["angle_deg"])
        x = f["cx"] + f["ra"] * np.cos(tt) * math.cos(phi) - f["rb"] * np.sin(tt) * math.sin(phi) - x0
        y = f["cy"] + f["ra"] * np.cos(tt) * math.sin(phi) + f["rb"] * np.sin(tt) * math.cos(phi) - y0
        ok = (x > -5) & (x < 705) & (y > -5) & (y < 505)
        if ok.sum() > 2:
            crop = np.asarray(fs.draw_polyline(crop, np.c_[x[ok], y[ok]], color=pal[i % len(pal)], width=1))
        q_ = rr_["pts"]
        mm = (q_[:, 0] >= y0) & (q_[:, 0] < y0 + 500) & (q_[:, 1] >= x0) & (q_[:, 1] < x0 + 700)
        if mm.any():
            crop = np.asarray(fs.draw_markers(crop, np.c_[q_[mm, 1] - x0, q_[mm, 0] - y0], color=pal[i % len(pal)],
                                              size=7, shape="cross", width=1))
    figs.save("real_plate_crop_1to1", crop,
              "【実画像】等倍の切り出し(700 × 500 画素、外側のリングの見えている弧の中ほど)。+ は測定線 1 本ごとの線の中心"
              "(強い立ち上がりと次の強い立ち下がりの中点)、細い線は当てた楕円の族。リングごとの点の数・弧の角度・族への残差は"
              "PoC の出力に印字する。" + REAL_SOURCE_SHORT, source=REAL_SOURCE)
    rk = real["rk"]
    xs = np.linspace(0, rk.max() * 1.05, 50)
    pa = real["proj"]
    ser = [("実画像(リングごとの中心。形は族で共通)", rk ** 2, pa),
           ("通常 f=25(入射瞳 %.0f mm)" % real["Lfa"], xs ** 2, real["b_fa"] * (xs ** 2 - np.mean(rk ** 2))),
           ("通常 f=100(入射瞳 %.0f mm)" % real["Len"], xs ** 2, real["b_en"] * (xs ** 2 - np.mean(rk ** 2)))]
    figs.save_plot("real_ring_centres", ser, xlabel="リングの半径² [mm²]", ylabel="中心の短軸方向のずれ [px]",
                   kinds=["scatter", "line", "line"], styles=[None, "dashed", "dashed"],
                   colors=["emphasis", "wrong", "reference"],
                   title="傾いた板の同心円: 実画像の中心はずれない(β = %.4f ± %.4f px/mm²)" % (real["beta"], real["se_b"]),
                   caption="【実画像】リングごとに形(向き・縦横比・長半径)を族の値に固定して中心だけを解き直し、短軸方向のずれを"
                           "取った。破線は同じ傾き・同じ倍率の板を 2 章のレンズの入射瞳の位置に置いたピンホールで写したときの中心の"
                           "ずれ(閉形式 x' = X·L/(L − Z) で写して fit_ellipse で中心を取った)。入射瞳は %.1f m より遠い"
                           "(主光線の傾きは視野の端で %.3f° 未満)。"
                           % (NUMBERS["real_pupil_min_mm"] / 1000.0, NUMBERS["real_edge_deg"]) + REAL_SOURCE_SHORT,
                   source=REAL_SOURCE)
    tiles = []
    for key in ("sphere_cam1", "sphere_cam2"):
        gi = np.asarray(fs_read(real["paths"][key]), float)
        im = np.repeat(np.clip(gi / max(gi.max(), 1e-9), 0, 1)[..., None], 3, -1) ** (1 / 1.8)
        for (thr, rmm, rms, f), col in zip(real["sph"][key], [(0.0, 0.62, 0.45), (0.94, 0.89, 0.26), (0.84, 0.37, 0.0)]):
            im = np.asarray(fs.draw_circle(im, (f["cx"], f["cy"]), f["r"], color=col, width=5))
        im = im[::2, ::2]
        im = np.asarray(fs.text_box(im, "%s  r = %s mm" % ("カメラ 1" if key.endswith("1") else "カメラ 2",
                                                          " / ".join("%.3f" % v[1] for v in real["sph"][key])),
                                    (10, 10), font_size=22))
        tiles += [im, np.ones((im.shape[0], 8, 3))]
    figs.save("real_resin_sphere", np.concatenate(tiles[:-1], 1),
              "【実画像】樹脂の 3D プリント球(公称半径 2.5 mm)を 2 台のテレセンで撮った生画像(1/2 に縮小)。円は輪郭を"
              "閾値 0.015(緑)/ 0.03(黄)/ 0.06(橙)で取って当てたもの。陰の側の縁が暗く、閾値で半径が 8 %% 動くので、"
              "この球は寸法の真値にならない(論文の計量級の球の生画像は公開データに無い)。" + REAL_SOURCE_SHORT, source=REAL_SOURCE)


def main():
    t0 = time.time()
    print("PoC テレセントリックレンズと寸法計測(予算 %s)" % ("reduced" if REDUCED else "full"))
    L = lenses()
    real = chapter_real(L)
    chief = chapter_chief(L)
    depth = chapter_depth(L)
    rend = chapter_render(L)
    sweep = chapter_residual(L)
    field = chapter_field(L)
    dof = chapter_dof(L)
    chapter_second(L)
    if not REDUCED and figs.target_dir() is not None:
        make_figures(L, chief, depth, rend, sweep, field, dof)
        if real is not None:
            make_real_figures(real)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
