# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 部品の直接刻印(DPM)の Data Matrix と、ラベルの QR —— 等級の閉形式と、読める限界の POD。

    PYTHONPATH=. py -3.11 examples/poc_symbol_part_dpm.py

自動車・電子部品のトレーサビリティで使う 2 種を**合成で**作る(真値 = 符号化した文字列):

  * 金属部品のドットピーン刻印の Data Matrix(点の直径 0.8 モジュール、地の反射率 0.65、
    刻印の凹み 0.30 = コントラストの低い DPM)
  * 段ボールのラベルに印字した QR(1-M)

見せたいこと(数字はすべてこの実行で測ったもの):

1. 往復: 生成 → モジュール格子の復号、任意の回転で撮像 → 位置決め・標本化・復号が全件戻る。
   独立な zxing-cpp(入っていれば)も同じ文字列を読む。
2. 印字品質の等級が**閉形式どおり**: 刻印のコントラスト SC = 0.65 − 0.30 = 0.35 → D
   (点の内側に収まる開口 0.4 X で。開口 0.8 X では点の縁が入って SC が下がる)、
   部品の傾き t(縦軸まわり、遠い視点)→ 軸の不均一 AN = 2(1 − cos t)/(1 + cos t)、
   k 語の欠け → 未使用の誤り訂正 UEC = 1 − 2k/n_ec。
3. ★読める限界を POD で言う: 低コントラストの刻印をデフォーカスで掃引し、Fullseye と
   zxing-cpp の d90 / d90/95 を同じ撮像で比べる。四角いモジュールの刻印では 2 つの
   独立な読み取り器が数 % で一致する(読み取りの鎖と POD の鎖の検算)。★ドットピーンでは
   zxing-cpp はくっきりした点を読めず、ぼけで点がつながると読める —— 読取率がぼけに対して
   **非単調**になり、POD の前提が破れる。op はそれを検出して旗を立てる。
4. ★★暗いライン(フルウェル 4000 e、読み出し雑音 25 e)で、読める最小のコントラスト
   (light − dark)を POD で出す —— 照明を明るくすれば何が変わるかを数字で言える。
5. d90 で撮った刻印の等級は低い(読めることと、どの読み取り器でも読める余裕は別)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

L = fs.ledger
FAIL = []
DPM = {"dot": 0.8, "dark": 0.30, "light": 0.65}


def check(ok, label, detail=""):
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))
    if not ok:
        FAIL.append(label)


def have_zxing():
    try:
        import zxingcpp  # noqa: F401
    except ImportError:
        return False
    return True


def main():
    t0 = time.time()
    zx = have_zxing()
    print("=" * 76)
    print("PoC: 部品の DPM Data Matrix とラベルの QR —— 等級の閉形式と読める限界の POD")
    print("=" * 76)
    dm = L.dm_encode("PN12345-LOT2611A")
    qr = L.qr_encode("PN12345-LOT2611A", ec_level="M")
    print("  Data Matrix %dx%d、ブロック %s / QR 型番 %d-%s、ブロック %s"
          % (dm["rows"], dm["cols"], dm["blocks"], qr["version"], qr["ec_level"], qr["blocks"]))

    print("\n[1] 往復(モジュール格子 / 画像)")
    check(L.dm_decode_modules(dm["modules"])["text"] == dm["text"], "DM の格子 → 文字列")
    check(L.qr_decode_modules(qr["modules"])["text"] == qr["text"], "QR の格子 → 文字列")
    rng = np.random.default_rng(3)
    ok_dm = ok_qr = 0
    for _ in range(6):
        ang = float(rng.uniform(0, 360))
        img = L.capture_degrade(L.render_symbol(dm, 5.0, rotate_deg=ang, **DPM),
                                gauss_px=0.7, full_well_e=20000.0, read_noise_e=10.0, bits=8,
                                seed=int(rng.integers(1 << 30)))
        loc = L.dm_locate(img)
        smp = L.dm_sample(img, loc)
        ok_dm += L.dm_decode_modules(smp["modules"])["text"] == dm["text"] and \
            L.dm_read(img)["text"] == dm["text"]
        img = L.capture_degrade(L.render_symbol(qr, 4.0, rotate_deg=ang), gauss_px=0.7,
                                full_well_e=20000.0, read_noise_e=10.0, bits=8,
                                seed=int(rng.integers(1 << 30)))
        loc = L.qr_locate(img)
        smp = L.qr_sample(img, loc)
        ok_qr += L.qr_decode_modules(smp["modules"])["text"] == qr["text"] and \
            L.qr_read(img)["text"] == qr["text"]
    check(ok_dm == 6, "刻印の DM を任意の回転で 6/6(位置決め → 標本化 → 復号)")
    check(ok_qr == 6, "ラベルの QR を任意の回転で 6/6")
    # 15° 刻みの 24 方向、雑音なしのくっきりした刻印 —— 2 つの読み取り器の読める数
    solid = {"dark": 0.30, "light": 0.65}
    n_fs_dot = sum(L.dm_read(L.render_symbol(dm, 5.0, rotate_deg=a, **DPM))["text"] == dm["text"]
                   for a in range(0, 360, 15))
    check(n_fs_dot == 24, "Fullseye: くっきりしたドットピーンの DM を 24 方向すべて読む")
    if zx:
        z_qr = L.read_symbols_zxing(L.render_symbol(qr, 4.0, rotate_deg=33.0), ["QRCode"])
        z_solid = sum(L.read_symbols_zxing(L.render_symbol(dm, 5.0, rotate_deg=a, **solid),
                                           ["DataMatrix"])["texts"] == [dm["text"]]
                      for a in range(0, 360, 15))
        z_dot = sum(L.read_symbols_zxing(L.render_symbol(dm, 5.0, rotate_deg=a, **DPM),
                                         ["DataMatrix"])["n"] > 0 for a in range(0, 360, 15))
        check(z_qr["texts"] == [qr["text"]] and z_solid == 24,
              "zxing-cpp: QR と四角いモジュール(レーザ刻印)の DM は同じ文字列(24/24)")
        print("  ★zxing-cpp はくっきりした**ドットピーン**の DM を %d / 24 方向しか読まない"
              "(L 字が点の列で途切れる。ぼけで点がつながると読める —— [3] の非単調)" % z_dot)

    print("\n[2] 印字品質の等級(開口 0.8 X、閉形式と照合)")
    g = L.grade_datacode2d(L.render_symbol(dm, 8.0))
    check(g["overall_grade"] == 4, "理想の印字の DM は A", g["limiting"])
    # 開口 0.4 X は直径 0.8 X の点の内側に収まる → 点の底の反射率がそのまま出る(閉形式)
    g = L.grade_datacode2d(L.render_symbol(dm, 8.0, **DPM), aperture_x=0.4,
                           expected_text=dm["text"])
    print("  刻印(0.30 / 0.65、点 0.8)、開口 0.4 X → 等級 %s、SC %.3f、制限 %s"
          % (g["letter"], g["symbol_contrast"], g["limiting"]))
    check(abs(g["symbol_contrast"] - 0.35) < 1e-4 and g["grades"]["symbol_contrast"] == 1,
          "刻印の SC = 0.65 − 0.30 = 0.35 → D")
    g8 = L.grade_datacode2d(L.render_symbol(dm, 8.0, **DPM), expected_text=dm["text"])
    print("  同じ刻印を開口 0.8 X で測ると SC %.3f —— 点の縁が開口に入る(DPM の測り方を"
          "別に定める理由。ISO/IEC 29158 は番号の参照のみ)" % g8["symbol_contrast"])
    check(g8["symbol_contrast"] < 0.35, "開口が点と同じ大きさだと SC は下がる")
    for t in (15.0, 24.0):
        an_true = 2 * (1 - np.cos(np.deg2rad(t))) / (1 + np.cos(np.deg2rad(t)))
        g = L.grade_datacode2d(L.render_symbol(dm, 8.0, tilt_deg=t, tilt_axis_deg=90.0,
                                               distance_ratio=300.0))
        print("  傾き %.0f° → AN %.4f(閉形式 %.4f)、等級 %s"
              % (t, g["axial_nonuniformity"], an_true, g["letter"]))
        check(abs(g["axial_nonuniformity"] - an_true) < 0.006, "傾き %.0f° の AN が閉形式" % t)
    n_ec = dm["blocks"][0][1]
    for k in (2, 4):
        m = np.asarray(dm["modules"]).astype(bool) ^ np.isin(np.asarray(dm["codeword_index"]),
                                                               np.arange(k))
        tbl = dict(dm)
        tbl["modules"] = m.astype(np.uint8)
        g = L.grade_datacode2d(L.render_symbol(tbl, 8.0))
        want = 1 - 2 * k / n_ec
        print("  %d 語の欠け → UEC %.3f(閉形式 %.3f)、等級 %s" % (k, g["unused_error_correction"], want,
                                                         g["letter"]))
        check(abs(g["unused_error_correction"] - want) < 1e-12, "%d 語の欠けの UEC が閉形式" % k)

    print("\n[3] デフォーカスの POD(モジュール 4 px、雑音 20000 e / 10 e、揺らぎ 5 %)")
    pods = {}
    for kind, rk in (("レーザ刻印(四角)", solid), ("ドットピーン", dict(DPM))):
        for rd in ["datamatrix"] + (["zxing"] if zx else []):
            tr = L.symbol_read_trials(dm, "defocus_px", np.linspace(2.0, 14.0, 7), trials=30,
                                      module_px=4.0, render=rk, refine=True, level_jitter=0.05,
                                      reader=rd, seed=11)
            q = L.symbol_read_pod(tr)
            pods[(kind, rd)] = q
            print("  %-14s %-10s d50 %.2f  d90 %.2f  d90/95 %.2f px  単調 %s(z %.1f)  誤読 %d / %d"
                  % (kind, rd, q["level50"] or np.nan, q["level90"] or np.nan,
                     q["level90_95"] or np.nan, q["monotone"], q["nonmonotone_z"],
                     q["misread_total"], q["decoded_total"]))
    p = pods[("ドットピーン", "datamatrix")]
    ps = pods[("レーザ刻印(四角)", "datamatrix")]
    check(p["method"] == ps["method"] == "hitmiss_glm" and p["level90_95"] < p["level90"]
          and p["monotone"] and ps["monotone"], "Fullseye の POD(両方の刻印で単調)")
    check(p["misread_total"] == 0 and ps["misread_total"] == 0, "誤読 0")
    if zx:
        z = pods[("レーザ刻印(四角)", "zxing")]
        r = z["level90"] / ps["level90"]
        print("  四角い刻印: zxing / Fullseye の d90 の比 %.3f" % r)
        check(0.8 < r < 1.25, "四角い刻印では 2 つの独立な読み取り器の d90 が 25 % 以内で一致")
        zd = pods[("ドットピーン", "zxing")]
        rates = [(round(d["level"], 1), round(d["read_rate"], 2)) for d in zd["per_level"][:4]]
        print("  ドットピーン: zxing の読取率 %s —— ぼけが**増えると読める**ので POD の前提"
              "(単調)が破れ、op は monotone = False の旗を立てる" % rates)
        check(not zd["monotone"], "非単調を検出して旗を立てる")
        # ★最初に書いた門「ドットピーンでも 2 つの読み取り器の d90 が 25 % 以内」は 0.789 で
        #   落ちた。原因を調べると zxing はくっきりした点の刻印を読まず、POD 曲線が非単調だった。

    print("\n[4] 暗いライン(4000 e、読み出し 25 e、ぼけ 1.2 px)で読める最小のコントラスト")
    tr = L.symbol_read_trials(dm, "contrast", np.linspace(0.02, 0.30, 8), trials=30, module_px=4.0,
                              render={"dot": 0.8, "light": 0.65},
                              capture={"full_well_e": 4000.0, "read_noise_e": 25.0, "gauss_px": 1.2},
                              refine=True, level_jitter=0.05, seed=12)
    pc = L.symbol_read_pod(tr)
    lo, hi = pc["separation_bracket"] if pc["method"] != "hitmiss_glm" else (None, None)
    print("  方法 %s  c50 %s  c90 %s  c90/95 %s(light − dark)"
          % (pc["method"], *("%.3f" % v if v is not None else "-" for v in
                             (pc["level50"], pc["level90"], pc["level90_95"]))))
    if pc["method"] == "hitmiss_glm":
        check(pc["level50"] < pc["level90"] < pc["level90_95"], "大きいほど良い因子: c50 < c90 < c90/95")
        # 雑音の閉形式: 暗部と明部の差 c·E·full_well(電子)を、両方の雑音 √(shot + read²) で割った
        # SNR が c90/95 のとき何倍か(参考値。読み取りは 1 モジュールの平均でなく全体で決まる)
        fw = 4000.0
        c = pc["level90_95"]
        e_l, e_d = 0.65 * fw, (0.65 - c) * fw
        snr = (e_l - e_d) / np.sqrt(0.5 * (e_l + e_d) + 25.0 ** 2)
        print("  c90/95 での 1 画素の SNR = %.1f(明暗の電子数の差 / 雑音)" % snr)
        check(0.65 - pc["level90_95"] > 0.3, "暗部の反射率は 0.35 より高くてよい(刻印の現実的な範囲)")
    else:
        print("  完全分離の括弧 (%s, %s)" % (lo, hi))

    print("\n[5] d90 で撮った刻印の等級")
    d90 = float(p["level90"])
    img = L.capture_degrade(L.render_symbol(dm, 4.0, **DPM), defocus_px=d90)
    g = L.grade_datacode2d(img)
    print("  d90 = %.2f px → 等級 %s(%s)、変調 %s"
          % (d90, g["letter"], g.get("limiting"), g.get("grades", {}).get("modulation")))
    check(g["overall_grade"] <= 1, "読み取り器が 90 % 読むぼけで、等級は D 以下")

    # 図: ドットピーンの DM(くっきり / d90 のぼけ)と 2 つの読み取り器の水準ごとの読取率
    if figs.enabled():
        sharp = L.render_symbol(dm, 4.0, rotate_deg=20.0, **DPM)
        blur = L.capture_degrade(L.render_symbol(dm, 4.0, rotate_deg=20.0, **DPM), defocus_px=d90,
                                 full_well_e=20000.0, read_noise_e=10.0, bits=8, seed=1)
        figs.save_grid("dpm_datamatrix", [sharp, blur],
                       ["ドットピーン(点 0.8、0.30 / 0.65)", "d90 = %.2f px のぼけ" % d90],
                       ncols=2, gray=True, vrange=(0.0, 1.0), title="部品の DPM Data Matrix",
                       caption="くっきりした点は zxing-cpp が読まず、ぼけると読む(非単調)。")
        rows = []
        for (kind, rd), q in pods.items():
            for d in q["per_level"]:
                rows.append([kind, rd, "%.2f" % d["level"], d["n"], "%.2f" % d["read_rate"]])
        figs.save_table("dpm_pod_levels", ["刻印", "読み取り器", "直径 [px]", "試行", "読取率"], rows,
                        title="デフォーカスの読取率(水準ごと)")
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\n%.0f 秒。" % (time.time() - t0))
    if FAIL:
        print("FAIL: %s" % FAIL)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
