# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: ハイブリッド接合のボイドは、超音波の「明るさ」でなく「位相」で見つける

    py -3.11 examples/poc_sam_hybrid_bonding_voids.py

2 枚のダイを Cu のパッドと SiO2 の誘電体で直接貼り合わせる(ハイブリッド接合)と、貼り合わせの
面に**空洞(ボイド)**が残ることがあります。走査型音響顕微鏡(SAM)は水の中で集束した超音波を
上のダイ越しに当て、接合面から返るエコーを 1 点ずつ測って像(C スキャン)にします。

この PoC は、厚さ 100 µm の Si のダイの下の接合面(SiO2 1 µm + 1 µm、Cu パッド 1 µm + 1 µm、
直径 40 µm・ピッチ 80 µm)に、直径 5〜24 µm のボイドをパッドの上と誘電体の中に置き、次を
実測します。

1. **A スキャン**: 誘電体・パッド・ボイド・パッドの上のボイドの 4 種類のエコー。薄い SiO2 と Cu の
   層は接合面を中心に対称なので、エコーは表面エコーに対して **±90°(直交)**。ボイドは空気
   (Z が 4 万分の 1)なので **180°(反転)**。
2. **振幅の C スキャン vs 位相の C スキャン**: 振幅の像では、直径 16 µm 未満のボイドは
   パッドの上でも誘電体の中でも**良品の画素の明るさの範囲に隠れます**(12 個中 8 個)。直交の背景(−90°)に反転の
   ボイド(180°)が足されると、ベクトルが直角に足されるので**振幅は 2 次でしか変わらない**から。
   位相(同相成分)の像では、ボイドだけが負に光ります。
3. **従来の「極性」の読み方は当てにならない**: ゲートの中で |RF| が最大の 1 点の符号で反転を
   判定すると、無傷の Cu パッドが周波数によって「反転(剥離)」と読まれます(直交のエコーの
   1 点の符号に意味が無い)。位相反転による剥離判定が装置・探触子・操作者で変わるという
   報告(2013 年、15〜75 MHz)の、このモデルの中での一つの説明です。
4. **周波数の取引**: 横分解能は周波数に比例して良くなり(PSF の半値全幅 1.02 λ_w F#)、水の中の
   往復の減衰は f² で増えます。ボイドの信号を最大にする周波数は閉形式で出て、総当たりと一致。
   表面エコーの裾がゲートに入る下限(パルスが長すぎる)も同じ op が返します。
5. **POD**: ボイド(直径 4〜36 µm)を 3 枚の地図に 88 個置き、受信雑音を入れて 150 / 200 / 300 MHz で
   撮り、``pod_ahat_fit`` / ``pod_from_ahat``(MIL-HDBK-1823A の â vs a)で a90/95 を出します。
   位相を使う検出(良品の基準を引いて、ボイドの向きに射影)と振幅だけの検出(良品の基準からの
   振幅のずれの絶対値)を、同じ規則の閾値(良品の部位の平均 + 3.09σ)で比べます。
   結果: 150 MHz で 12.4 µm 対 16.6 µm(位相のほうが 25 % 小さい)、300 MHz では水の減衰で
   どちらも試した範囲の外へ逃げます。位相の利点は「何倍」ではなく、小さなボイドの信号が
   直交の背景に直角に足される領域で効く —— という大きさです(数字は合成のもの)。

真値: 地図(どこがボイドか)は自分で置いたもの。エコーは層の伝達行列(``tests/test_ultrasound.py``
が下から積み上げる Airy の再帰・時間領域の経路の和・光学の薄膜の式と 1e-12 で照合)。

★正直に書いておくこと(範囲と合成であること):
  * **1-D の平面波・垂直入射・縦波だけ**の層モデル + 周波数ごとの**ガウスの横 PSF**。モード変換
    (横波)、表面波、斜入射の角度スペクトル(V(z))、水/Si 界面での屈折による収差(焦点ずれ)、
    表面粗さ、層の厚さむらは入っていません。開口は Si の縦波の臨界角の内側(F# ≥ 2.8)に限ります。
  * ボイドは厚さ 0.1 µm の空気の層。部分的に接した界面(kissing bond、Baik & Thompson 1984 の
    ばねモデル)は入っていません —— それはボイドより見つけにくく、この PoC の数字は楽観側です。
  * 材料定数は ``acoustic_material_table`` の出典どおり(公開の資料から写したか、弾性定数から
    計算した値)。**Si の減衰は確かめた値が無いので 0** で、水の経路(1 mm)の減衰だけが周波数の
    取引を決めています。成膜した SiO2 は溶融石英の値で代用しています。
  * 位相は接合面の**期待時刻**で読みます(ダイの厚さが既知で一様)。ダイが 1 µm 厚いと、
    200 MHz で位相が 17° 回ります。厚さが場所で変わる部品では画素ごとに時刻を直す必要があります。
  * 検出の比較は、**設計(どこがパッドか)が分かっている**前提で、良品の基準をクラスごとに
    引いています(振幅の検出にも同じ前提を与えています)。
  * 公開文献と第一原理だけで組んだ合成です。実在の装置・製品の値は使っていません。
    「SAM のボイド検出に POD を当てた先行研究」は、私たちの検索(OpenAlex で "probability of
    detection" × "acoustic microscopy")では 0 件でした —— 新規性の主張ではありません。

走らせ方: ``py -3.11 examples/poc_sam_hybrid_bonding_voids.py``
(図は ``FULLSEYE_FIGURE_DIR`` を指定したときだけ書く)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402  (台帳の公開経路 fs.ledger を使う)

CHECKS = []

DIE = 100e-6              # 上のダイ(Si)の厚さ [m]
HALF = 1e-6               # 接合層の上下の半分(SiO2 / Cu)の厚さ [m]
GAP = 0.1e-6              # ボイド(空気の層)の厚さ [m]
WATER = 1.0e-3            # 水の経路 [m]
FNUM = 3.0                # 水側の F 数(Si の縦波の臨界角で F# ≥ 2.8)
PX = 2e-6                 # 画素 [m]
PITCH, PAD = 80e-6, 40e-6
NCELL = 6                 # 6 × 6 のパッド = 480 µm 角
NOISE = 1.5e-3            # 受信雑音(RF の RMS、焦点の完全反射体のエコー = 1)
GATE = 2                  # 接合面(上下の半分が出会う面)の界面の番号
F_SHOW = 150e6
F_POD = (150e6, 200e6, 300e6)
LABELS = ("誘電体", "Cu パッド", "ボイド(誘電体)", "ボイド(パッドの上)")


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))


def stacks():
    die = [("silicon", DIE)]
    L = fs.ledger.acoustic_layer_stack
    return {0: L(die + [("sio2", HALF), ("sio2", HALF)]),
            1: L(die + [("copper", HALF), ("copper", HALF)]),
            2: L(die + [("sio2", HALF), ("air", GAP), ("sio2", HALF)]),
            3: L(die + [("copper", HALF), ("air", GAP), ("copper", HALF)])}


def bond_map(voids):
    """パッドの格子(ラベル 1)の上にボイド(誘電体の中 = 2、パッドの上 = 3)を置く。"""
    n = int(round(NCELL * PITCH / PX))
    yy, xx = np.mgrid[:n, :n] * PX
    m = np.zeros((n, n), dtype=np.int64)
    for i in range(NCELL):
        for j in range(NCELL):
            m[(yy - (i + 0.5) * PITCH) ** 2 + (xx - (j + 0.5) * PITCH) ** 2 <= (PAD / 2) ** 2] = 1
    for cy, cx, d in voids:
        v = (yy - cy) ** 2 + (xx - cx) ** 2 <= (d / 2) ** 2
        m[v & (m == 1)] = 3
        m[v & (m == 0)] = 2
    return m


def showcase_voids():
    """直径 5〜24 µm を、パッドの上と誘電体(パッドの間の交点)に 1 つずつ。"""
    sizes = [5e-6, 7e-6, 9e-6, 12e-6, 16e-6, 24e-6]
    corners = [(4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (5, 3)]       # セルの角(4 つのパッドの間)
    out = []
    for k, d in enumerate(sizes):
        out.append(((1 + 0.5) * PITCH, (k + 0.5) * PITCH, d, "pad"))    # 2 行目のパッドの中心
        out.append((corners[k][0] * PITCH, corners[k][1] * PITCH, d, "diel"))
    return out


def pod_sites(rng):
    """POD 用: 各セルのパッドの中心と、セルの角(誘電体)に 5 割の確率でボイド。"""
    sites = []
    for i in range(NCELL):
        for j in range(NCELL):
            for kind, (y, x) in (("pad", ((i + 0.5) * PITCH, (j + 0.5) * PITCH)),
                                 ("diel", (i * PITCH, j * PITCH))):
                if kind == "diel" and (i == 0 or j == 0):
                    continue
                d = float(np.exp(rng.uniform(math.log(4e-6), math.log(36e-6)))) if rng.random() < 0.5 else 0.0
                sites.append((y, x, d, kind))
    return sites


def baselines(c, sites):
    """良品の基準: 同じ像の中の、ボイドの無い部位(パッドの中心 / 誘電体の角)の複素値の平均。

    ★一面に広がったときの値(``plane_phasor``)は基準にしない: 直径 40 µm のパッドは PSF
    (150 MHz で 30 µm)と同じくらいの大きさで、周りの誘電体(−90°)と混ざって中心の振幅が
    一面の値の半分になる。基準は設計どおりの良品を同じ条件で測った値(ゴールデン基準)。
    """
    a = c["amplitude_at_t"] * np.exp(1j * c["phase"])
    out = {}
    for kind in ("pad", "diel"):
        v = [a[int(round(y / PX)), int(round(x / PX))] for y, x, d, k in sites if k == kind and d == 0]
        out[kind] = complex(np.mean(v))
    return a, out


def detect_stats(c, sites):
    """部位ごとの 2 つの検出量。

    * 位相を使う: 良品の基準を引いて、ボイドの向き(一面のボイドと一面の良品の差の偏角)へ射影
      (片側。ボイドが足される向きだけを数える)
    * 振幅だけ: 良品の基準の振幅からのずれの絶対値(両側。パッドの上のボイドは暗くもなりうる)
    """
    P = c["plane_phasor"]
    a, base = baselines(c, sites)
    rows = []
    for y, x, d, kind in sites:
        yi, xi = int(round(y / PX)), int(round(x / PX))
        bg = 1 if kind == "pad" else 0
        vl = 3 if bg == 1 else 2
        u = (P[vl] - P[bg]) / abs(P[vl] - P[bg])
        coh = float(np.real((a[yi, xi] - base[kind]) * np.conj(u)))
        amp = float(abs(abs(a[yi, xi]) - abs(base[kind])))
        rows.append((d, kind, coh, amp))
    return rows


def main():
    t0 = time.time()
    S = stacks()
    mats = fs.ledger.acoustic_material_table()["materials"]
    used = ("water", "silicon", "sio2", "copper", "air")
    print("積層: Si %d µm / 接合層 %s %.0f + %.0f µm / Si、水の経路 %.1f mm、F# %.1f"
          % (DIE * 1e6, "SiO2 or Cu", HALF * 1e6, HALF * 1e6, WATER * 1e3, FNUM))
    for k in used:
        print("  %-8s Z = %6.3f MRayl  c = %5.0f m/s  (%s)" % (k, mats[k]["Z"] / 1e6, mats[k]["c"],
                                                              mats[k]["source"][:70]))
    check(all(mats[k]["verified"] is True and mats[k]["source"] for k in used),
          "使う材料はすべて出典つき・確かめた印つき")

    # ---- 1. 界面と伝達行列 ------------------------------------------------------- #
    co = fs.ledger.acoustic_interface_coefficients(S[2])
    check(np.max(np.abs(co["energy"] - 1)) < 1e-13, "界面のエネルギー保存 R² + (Z1/Z2)T² = 1",
          "最大のずれ %.1e" % np.max(np.abs(co["energy"] - 1)))
    check(bool(np.all((co["R"] < 0) == (co["z2"] < co["z1"]))), "反射の符号が負になるのは Z が下がる界面だけ",
          " / ".join("%s %+.3f" % (n, r) for n, r in zip(co["names"], co["R"])))

    # ---- 2. A スキャン ------------------------------------------------------------- #
    asc = {k: fs.ledger.pulse_echo_ascan(S[k], f0=F_SHOW, water_path=WATER) for k in S}
    pol = {k: fs.ledger.echo_phase_polarity(asc[k], interface=GATE) for k in S}
    for k in S:
        print("  %-14s 位相 %+7.1f°  振幅 %.4f  → %s(1 点の符号 %+d)"
              % (LABELS[k], pol[k]["phase_deg"], pol[k]["amplitude"], pol[k]["label"], pol[k]["signed_peak"]))
    check(pol[2]["polarity"] == -1 and pol[3]["polarity"] == -1, "ボイドは誘電体の中でもパッドの上でも反転",
          "%.0f° / %.0f°" % (pol[2]["phase_deg"], pol[3]["phase_deg"]))
    check(pol[0]["polarity"] == 0 and pol[1]["polarity"] == 0
          and abs(abs(pol[0]["phase_deg"]) - 90) < 15 and abs(abs(pol[1]["phase_deg"]) - 90) < 15,
          "無傷の誘電体と Cu パッドは直交(薄い層の微分形のエコー)",
          "%.0f° / %.0f°" % (pol[0]["phase_deg"], pol[1]["phase_deg"]))
    sp, phs = {}, {}
    for f in np.arange(140e6, 401e6, 20e6):
        r = fs.ledger.echo_phase_polarity(fs.ledger.pulse_echo_ascan(S[1], f0=float(f), water_path=WATER),
                                          interface=GATE)
        sp[f], phs[f] = r["signed_peak"], r["phase_deg"]
    flips = sum(1 for a_, b_ in zip(list(sp.values())[:-1], list(sp.values())[1:]) if a_ != b_)
    check(len(set(sp.values())) == 2 and all(60 < p_ < 120 for p_ in phs.values()),
          "従来の極性(|RF| 最大の 1 点の符号)は無傷の Cu パッドで 140〜400 MHz の間に %d 回転ぶ。位相は全部 +60〜+120°" % flips,
          "".join("+" if v > 0 else "−" for v in sp.values()))

    # ---- 3. 振幅の C スキャン vs 位相の C スキャン ------------------------------------ #
    show = showcase_voids()
    m_show = bond_map([(y, x, d) for y, x, d, _ in show])
    cs = fs.ledger.sam_cscan(m_show, S, pixel_size=PX, f0=F_SHOW, f_number=FNUM, water_path=WATER,
                             gate_interface=GATE, noise_rms=NOISE, seed=7)
    P = cs["plane_phasor"]
    amp = cs["amplitude_at_t"]
    print("  一面に広がったときの期待時刻の値: " + " / ".join(
        "%s %.4f∠%+.0f°" % (LABELS[k], abs(P[k]), math.degrees(math.atan2(P[k].imag, P[k].real))) for k in P))
    # 良品の部位(ボイドから十分離れたパッドの中心とセルの角)→ ゴールデン基準
    goods = ([((i + 0.5) * PITCH, (j + 0.5) * PITCH, 0.0, "pad") for i in (0, 2) for j in range(NCELL)]
             + [(3 * PITCH, j * PITCH, 0.0, "diel") for j in range(1, NCELL)])
    a_show, base = baselines(cs, goods)
    print("  良品の基準(同じ像の良品の部位の平均): パッド %.4f∠%+.0f° / 誘電体 %.4f∠%+.0f°"
          % (abs(base["pad"]), math.degrees(np.angle(base["pad"])), abs(base["diel"]),
             math.degrees(np.angle(base["diel"]))))
    # 良品の画素(どのボイドからも 2 FWHM 以上離れた点)
    yy, xx = np.mgrid[:m_show.shape[0], :m_show.shape[1]] * PX
    far = np.ones(m_show.shape, bool)
    for y, x, d, _ in show:
        far &= (yy - y) ** 2 + (xx - x) ** 2 > (d / 2 + 2 * cs["psf_fwhm_f0"]) ** 2
    good = far & ((m_show == 0) | (m_show == 1))
    lo, hi = np.percentile(amp[good], 0.1), np.percentile(amp[good], 99.9)
    hidden, rows_show = 0, []
    for y, x, d, kind in show:
        yi, xi = int(round(y / PX)), int(round(x / PX))
        bg = 1 if kind == "pad" else 0
        vl = 3 if bg == 1 else 2
        u = (P[vl] - P[bg]) / abs(P[vl] - P[bg])
        a_v, ph = amp[yi, xi], math.degrees(cs["phase"][yi, xi])
        in_range = lo <= a_v <= hi
        hidden += int(in_range)
        d_amp = (abs(a_show[yi, xi]) - abs(base[kind])) / NOISE
        d_coh = float(np.real((a_show[yi, xi] - base[kind]) * np.conj(u))) / NOISE
        rows_show.append((d, kind, a_v, ph, in_range, d_amp, d_coh))
        print("  ボイド %4.1f µm (%s): 振幅 %.4f%s  位相 %+5.0f°  基準からの変化: 振幅 %+5.1fσ / 位相を使う %+5.1fσ"
              % (d * 1e6, "パッド" if kind == "pad" else "誘電体", a_v, "(良品の範囲内)" if in_range else "",
                 ph, d_amp, d_coh))
    check(hidden >= 6, "振幅の像では、ボイドの半分以上が良品の画素の明るさの範囲(0.1〜99.9 %)に隠れる",
          "%d / %d 個(良品の範囲 %.4f〜%.4f)" % (hidden, len(show), lo, hi))
    mid = [r for r in rows_show if 9e-6 <= r[0] <= 16e-6]
    check(all(r[6] > 2.5 and r[6] >= 2 * abs(r[5]) for r in mid),
          "9〜16 µm のボイド 6 個: 位相を使う変化は 2.5σ 超で、どれも振幅の変化の 2 倍以上(直交の足し算)",
          " / ".join("%.0f%s %.1f vs %.1f" % (r[0] * 1e6, "p" if r[1] == "pad" else "d", r[6], r[5]) for r in mid))
    floor = 5.0 * NOISE
    call = (np.cos(cs["phase"]) < -0.7) & (amp > floor)
    fp = int((call & good).sum())
    hits = [r for r in rows_show if r[0] >= 16e-6]
    check(fp <= 2 and all(call[int(round(y / PX)), int(round(x / PX))] for y, x, d, _ in show if d >= 16e-6),
          "位相の像で反転(cos 位相 < −0.7、振幅 > 5σ)と読む画素: 16 µm 以上のボイドはすべて、良品はほぼ 0",
          "良品 %d 画素中 %d 画素、ボイド %d 個中 %d 個" % (int(good.sum()), fp, len(hits), len(hits)))

    # ---- 4. 周波数の取引 ------------------------------------------------------------ #
    sizes = (6e-6, 10e-6, 20e-6)
    trs = {a: fs.ledger.sam_frequency_tradeoff(S[0], a, water_path=WATER, f_number=FNUM, interface=GATE)
           for a in sizes}
    t10 = trs[10e-6]
    check(abs(t10["f_opt"] / t10["f_opt_closed"] - 1) < 1e-6,
          "最適周波数: 数値の最適化 = 閉形式 (k/a)·sqrt(log2(1 + a² ln2 / (β k²)))",
          "10 µm で %.2f MHz(閉形式 %.2f MHz)" % (t10["f_opt"] / 1e6, t10["f_opt_closed"] / 1e6))
    fg = np.geomspace(20e6, 1e9, 200001)
    sig = (1 - 2.0 ** (-(10e-6 * fg / t10["k"]) ** 2)) * np.exp(-t10["beta"] * fg ** 2)
    check(abs(fg[np.argmax(sig)] / t10["f_opt"] - 1) < 1e-4, "総当たりの最大とも一致",
          "%.2f MHz" % (fg[np.argmax(sig)] / 1e6))
    print("  表面エコーの裾がゲートに入らない下限 %.0f MHz(ダイ 100 µm、比帯域 0.6)、F# の下限 %.2f"
          % (t10["f_min_time"] / 1e6, t10["f_number_min"]))
    check(t10["f_number_min"] < FNUM, "F# は Si の縦波の臨界角の内側", "下限 %.2f < %.1f" % (t10["f_number_min"], FNUM))

    # ---- 5. POD(150 / 200 / 300 MHz、位相を使う検出 vs 振幅だけ) ---------------------- #
    import pod as _pod  # noqa: PLC0415  (fs.ledger にも同じ op がある。表の列名をそのまま使う)
    pods, prow = {}, []
    for f in F_POD:
        rows = []
        for seed in (1, 2, 3):
            sites = pod_sites(np.random.default_rng(seed))
            m = bond_map([(y, x, d) for y, x, d, _ in sites if d > 0])
            c = fs.ledger.sam_cscan(m, S, pixel_size=PX, f0=f, f_number=FNUM, water_path=WATER,
                                    gate_interface=GATE, noise_rms=NOISE, seed=seed)
            rows += detect_stats(c, sites)
        res = {}
        for col, name in ((2, "位相"), (3, "振幅")):
            goods = {k: np.array([r[col] for r in rows if r[0] == 0 and r[1] == k]) for k in ("pad", "diel")}
            a_dec = max(g.mean() + 3.09 * g.std() for g in goods.values())
            va = np.array([r[0] for r in rows if r[0] > 0]) * 1e6
            vh = np.array([r[col] for r in rows if r[0] > 0])
            fit = fs.ledger.pod_ahat_fit({"a": va, "ahat": vh}, log_size=True)
            pr = fs.ledger.pod_from_ahat(fit, a_dec)
            pfc = fs.ledger.pod_false_call(np.concatenate(list(goods.values())), a_dec)
            res[name] = (pr, a_dec, pfc, len(va))
        pods[f] = res
        rp, ra = res["位相"][0], res["振幅"][0]
        prow.append(("%d" % (f / 1e6), "%.1f" % rp["a90"], "%.1f%s" % (rp["a90_95"], "*" if rp["a90_95_beyond_data"] else ""),
                     "%.1f" % ra["a90"], "%.1f%s" % (ra["a90_95"], "*" if ra["a90_95_beyond_data"] else ""),
                     "%d" % res["位相"][3]))
        print("  %3d MHz: 位相 a90/95 = %5.1f µm(誤検出 %.2f %%)  振幅 a90/95 = %5.1f µm(誤検出 %.2f %%)  ボイド %d 個"
              % (f / 1e6, rp["a90_95"], 100 * res["位相"][2]["pfp_empirical"], ra["a90_95"],
                 100 * res["振幅"][2]["pfp_empirical"], res["位相"][3]))
    check(all(pods[f]["位相"][0]["a90_95"] < 0.8 * pods[f]["振幅"][0]["a90_95"] for f in F_POD),
          "どの周波数でも、位相を使う検出の a90/95 は振幅だけの 8 割未満(同じ基準・同じ閾値の規則)",
          " / ".join("%d MHz %.1f vs %.1f µm" % (f / 1e6, pods[f]["位相"][0]["a90_95"], pods[f]["振幅"][0]["a90_95"])
                     for f in F_POD))
    a9 = [pods[f]["位相"][0]["a90_95"] for f in F_POD]
    s_pred = [float(np.interp(f, t10["freqs"], t10["signal"])) for f in F_POD]
    check(t10["f_opt_usable"] <= F_POD[0] and a9[0] < a9[1] < a9[2] and s_pred[0] > s_pred[1] > s_pred[2],
          "最適周波数より上では、予測の信号の順と a90/95 の順が一致(低いほど良い)",
          "予測の最適 %.0f MHz、a90/95 %s µm" % (t10["f_opt_usable"] / 1e6, " < ".join("%.1f" % v for v in a9)))
    check(not pods[F_POD[0]]["位相"][0]["a90_95_beyond_data"], "150 MHz の a90/95 は試した大きさの範囲の内側")

    elapsed = time.time() - t0
    check(elapsed < 60.0, "所要時間(CI の上限に余裕を残す)", "%.1f 秒" % elapsed)

    if figs.enabled():
        _figures(S, asc, pol, m_show, cs, show, trs, pods)
    assert not figs.errors(), figs.errors()

    bad = [ck for ck in CHECKS if not ck[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(CHECKS), len(CHECKS) - len(bad), elapsed))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


def _figures(S, asc, pol, m_show, cs, show, trs, pods):
    a0 = asc[0]
    t_ns = (a0["t"] - a0["t_front"]) * 1e9
    sel = (t_ns > -15) & (t_ns < 45)
    tg = a0["t_interfaces"][GATE]
    hw = 2 * a0["sigma_t"]
    g = [((tg - hw - a0["t_front"]) * 1e9, (tg + hw - a0["t_front"]) * 1e9)]
    top = max(np.abs(asc[k]["rf"][sel]).max() for k in S)
    series = [(LABELS[k], t_ns[sel], asc[k]["rf"][sel] + 0.0) for k in S]
    for lo, hi in g:
        series.append(("ゲート(接合面 ± 2σ_t)", np.array([lo, lo, hi, hi]), np.array([-top, top, top, -top]) * 0.3))
    figs.save_plot("ascan", series, xlabel="表面エコーからの時間 [ns]", ylabel="RF",
                   title="A スキャン(150 MHz): 表面エコーと、%.1f ns 後の接合面のエコー" % ((tg - a0["t_front"]) * 1e9),
                   colors=["neutral", "emphasis", "wrong", "wrong", "reference"],
                   styles=[None, None, None, "dotted", "dashed"], size=(760, 360),
                   caption="接合面のエコーは表面エコーの 1 割未満。ボイドのエコーは反転、誘電体とパッドは直交(微分形)。")
    zoom = (t_ns > 12) & (t_ns < 36)
    figs.save_plot("ascan_gate", [(LABELS[k], t_ns[zoom], asc[k]["rf"][zoom]) for k in S],
                   xlabel="表面エコーからの時間 [ns]", ylabel="RF",
                   title="ゲートの中: ボイドは反転、パッドと誘電体は ±90°",
                   colors=["neutral", "emphasis", "wrong", "wrong"], styles=[None, None, None, "dotted"],
                   size=(760, 360), caption="期待時刻(%.1f ns)で読んだ位相は、%s。" % (
                       (tg - a0["t_front"]) * 1e9, "、".join("%s %+.0f°" % (LABELS[k], pol[k]["phase_deg"]) for k in S)))
    lab = m_show.astype(float)
    amp = cs["amplitude_at_t"]
    # 反転 = +1 に揃える(パネル d と同じ向き)。振幅が雑音の 5 倍に満たない画素は位相が雑音なので 0 に
    neg_cos = -np.cos(cs["phase"]) * np.clip(amp / (5.0 * NOISE), 0.0, 1.0)
    figs.save_grid("amplitude_vs_phase",
                   [lab, amp, neg_cos, -cs["inphase"]],
                   ["真値(0 誘電体 / 1 パッド / 2-3 ボイド)", "振幅の C スキャン", "−cos(位相): 反転 = +1",
                    "−同相成分(ボイドの向き)"],
                   title="振幅では小さなボイドが背景に埋もれる。位相ではボイドだけが光る", ncols=2,
                   signed=[False, False, True, True], gray=[False, True, False, False],
                   vrange=[(0, 3), (0, float(np.percentile(amp, 99.5))), (-1, 1), None],
                   caption="150 MHz、受信雑音 1.5e-3。誘電体の中の小さなボイドは振幅の像で背景と同じ明るさ(直交の背景に"
                           "反転のエコーが直角に足される)。位相の像ではボイドだけが +1 側に光り、無傷のパッドと誘電体は 0 付近"
                           "(±90°)。パッドの縁の逆向きの輪は、+80° のパッドと −90° の誘電体のエコーが PSF の中で打ち消し合って"
                           "位相が 0° 付近へ回ったもの(振幅の像でパッドの縁が暗い輪になるのも同じ理由)。")
    frames = []
    for f in (150e6, 200e6, 250e6, 300e6, 350e6):
        c = fs.ledger.sam_cscan(m_show, S, pixel_size=PX, f0=f, f_number=FNUM, water_path=WATER,
                                gate_interface=GATE, noise_rms=NOISE, seed=7)
        a_ = c["amplitude_at_t"] / max(float(np.percentile(c["amplitude_at_t"], 99.5)), 1e-12)
        frames.append(np.concatenate([2 * np.clip(a_, 0, 1) - 1, np.ones((m_show.shape[0], 4)),
                                      np.cos(c["phase"])], axis=1))
    figs.save_gif("frequency_sweep", frames, fps=1.5, signed=True,
                  caption="150 → 350 MHz。左 = 振幅(各コマで正規化)、右 = cos(位相)。周波数を上げると像は締まるが、"
                          "水の減衰で雑音に沈んでいく。")
    names = list(trs)
    win = (trs[names[0]]["freqs"] >= 40e6) & (trs[names[0]]["freqs"] <= 600e6)     # 描く範囲だけ渡す
    lg = lambda v: np.log10(np.maximum(v, 1e-12))
    ser = []
    for a in names:
        w_ = win & (trs[a]["signal"] >= 1e-4)                     # 描く範囲(log10 ≥ −4)だけ渡す
        ser.append(("ボイド %d µm" % (a * 1e6), trs[a]["freqs"][w_] / 1e6, lg(trs[a]["signal"][w_])))
    ser.append(("最適(閉形式)", np.array([trs[a]["f_opt_closed"] / 1e6 for a in names]),
                np.array([lg(np.interp(trs[a]["f_opt"], trs[a]["freqs"], trs[a]["signal"])) for a in names])))
    fmt = trs[names[0]]["f_min_time"] / 1e6
    ser.append(("表面エコーの裾の下限", np.array([fmt, fmt]), np.array([-4.0, 0.0])))
    figs.save_plot("tradeoff", ser,
                   xlabel="中心周波数 [MHz]", ylabel="log10 ボイドの信号",
                   title="最適周波数は水の減衰でほぼ決まる(小さいボイドの極限 1/√β = %.0f MHz)"
                         % (1e-6 / math.sqrt(trs[names[0]]["beta"])),
                   colors=["emphasis", "neutral", "reference", "wrong", "reference"],
                   kinds=["line", "line", "line", "scatter", "line"], styles=[None, None, None, None, "dashed"],
                   size=(700, 380), ylim=(-4.0, 0.0),
                   caption="S(f) = (1 − 2^−(a/w)²) exp(−β f²)。最適 %s MHz(閉形式)。表面エコーの裾がゲートに入らない下限は %.0f MHz。"
                           % (" / ".join("%.0f" % (trs[a]["f_opt"] / 1e6) for a in names), trs[names[0]]["f_min_time"] / 1e6))
    t = trs[10e-6]
    win2 = (t["freqs"] >= 60e6) & (t["freqs"] <= 600e6)
    figs.save_plot("resolution_and_loss",
                   [("横分解能 FWHM [µm]", t["freqs"][win2] / 1e6, t["fwhm"][win2] * 1e6),
                    ("水の往復減衰 [dB / 10]", t["freqs"][win2] / 1e6, t["loss_db"][win2] / 10)],
                   xlabel="中心周波数 [MHz]", ylabel="µm  /  dB÷10",
                   title="横分解能は 1/f で良くなり、減衰は f² で増える", colors=["emphasis", "wrong"],
                   size=(700, 360), caption="FWHM = 1.02 λ_w F#(F# 3)、水の経路 1 mm(2.17e-3 dB/(cm MHz²))。")
    series, cols, sty = [], [], []
    for f in F_POD:
        for name, st in (("位相", None), ("振幅", "dashed")):
            pr = pods[f][name][0]
            series.append(("%d MHz %s" % (f / 1e6, name), pr["a"], pr["pod"]))
            cols.append({150e6: "emphasis", 200e6: "neutral", 300e6: "wrong"}[f])
            sty.append(st)
    figs.save_plot("pod", series, xlabel="ボイドの直径 [µm]", ylabel="POD", xlim=(0, 60), ylim=(0, 1.02),
                   title="POD(â vs a、MIL-HDBK-1823A): 実線 = 位相を使う検出、破線 = 振幅だけ",
                   colors=cols, styles=sty, size=(760, 400),
                   caption="閾値は同じ規則(良品の部位の平均 + 3.09σ、パッドと誘電体の厳しい方)。")
    rows = []
    for f in F_POD:
        rp, ra = pods[f]["位相"][0], pods[f]["振幅"][0]
        rows.append(["%d" % (f / 1e6), "%.1f" % rp["a90_95"], "%.2f" % (100 * pods[f]["位相"][2]["pfp_empirical"]),
                     "%.1f%s" % (ra["a90_95"], "(外挿)" if ra["a90_95_beyond_data"] else ""),
                     "%.2f" % (100 * pods[f]["振幅"][2]["pfp_empirical"]), "%d" % pods[f]["位相"][3]])
    figs.save_table("pod_numbers", ["周波数 [MHz]", "位相 a90/95 [µm]", "位相 誤検出 [%]", "振幅 a90/95 [µm]",
                                    "振幅 誤検出 [%]", "ボイド数"], rows,
                    title="ボイドの a90/95(水 1 mm、F# 3、受信雑音 1.5e-3)",
                    caption="(外挿)= a90/95 が試した大きさ(4〜36 µm)の外。")


if __name__ == "__main__":
    main()
