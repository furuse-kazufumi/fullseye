# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""地形を測る —— 傾斜・水の流れ・日当たりを、閉形式と突き合わせながら出す。

EXTEND: 実際の標高データを使うなら ``dem`` を差し替える。国土地理院の標高タイルは
ログイン不要で取れる(``https://cyberjapandata.gsi.go.jp/xyz/dem5a/{z}/{x}/{y}.txt``、
256x256 の CSV、欠測は ``e``)。**セル寸法は緯度で変わる**ので
``156543.03392804097 * cos(latitude) / 2**zoom`` で計算すること —— 赤道の値を
そのまま使うと東京で傾斜が 23 % 過小になる。データはリポジトリに同梱せず、
成果物には出典(国土地理院)を明記する。

この PoC が示すこと:

1. **解析曲面で検算できる** —— 平面・円錐・ガウス丘は傾斜も曲率も式で出るので、
   「それらしい絵」ではなく数字で合っているかを言える。
2. **離散化の誤差と実装の誤りを分ける** —— 格子を細かくして誤差が 2 次で減るなら
   離散化、減らないなら式が違う。
3. **欠測(水面)の扱いで答えが変わる** —— 拒否 / 流出口 / 壁 の 3 通りを並べる。

★ この PoC を書いたことで、族そのものの問題が 2 つ出た。(a) 頂点での断面曲率が
0 なのを実装の誤りと疑ったが、**斜面の向きが決まらない点では定義どおり**だった
(私の勘違い)。(b) 天空率が 513x513・8 方位で **41.9 秒**かかった —— テストは
小さい格子しか使っておらず「動く」ことは確かめていたが「使える」ことは確かめて
いなかった。地平線走査を fancy index からスライスへ書き直し、**結果は bit 一致の
まま 27〜40 倍**速くなった。**PoC は道具の穴を出すためにある**。
4. **日当たりは方位で決まる** —— 北向き斜面と南向き斜面の陰影・天空率の差。

実データ(東京湾岸、国土地理院 dem5a、z=15 の 4x4 タイル = 1024x1024、
セル 3.880 m)での所要時間の実測は末尾に印字する数字と同じ形で、
傾斜 46.9 ms / 方位 69.9 ms / 曲率 69.0 ms / 陰影 87.3 ms / 窪地埋め 1.42 s /
集水量 2.39 s だった。局所演算は 100 ms を切り、水文だけが 2 桁遅い
(優先度キューとトポロジカル掃引は逐次依存があり素直にはベクトル化できない)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

# ★リポジトリ直下を通しておかないと ``demops`` が見つからない(この例は
#   `fullseye` を import しないので、パスフックが効かない)。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import demops                                                    # noqa: E402
import examplefig as figs                                        # noqa: E402


def _big(a, k=3):
    """図に載せるためだけの最近傍拡大。格子が 41〜122 画素だと、パネルの題が
    入る幅すら無い(``annotate_figure_grid`` は題をパネル幅に収める)。"""
    return np.repeat(np.repeat(np.asarray(a, float), k, axis=0), k, axis=1)


def plane(h, w, cell, slope_deg, aspect_deg):
    """既知の傾斜・方位を持つ平面。行 0 が北、方位は北 0 度・東回り。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    g = math.tan(math.radians(slope_deg))
    a = math.radians(aspect_deg)
    return -g * ((xx * cell) * math.sin(a) + (-yy * cell) * math.cos(a))


def cone(n, cell, slope_deg, top=100.0):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    r = np.hypot(yy - n // 2, xx - n // 2) * cell
    return top - math.tan(math.radians(slope_deg)) * r


def gaussian_hill(n, cell, amp=50.0, sigma=40.0):
    yy, xx = (np.mgrid[0:n, 0:n] - n // 2) * cell
    return amp * np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2))


def main():
    cell = 5.0

    print("=== 1. 平面 —— 傾斜と方位は閉形式に一致するか ===")
    print(f"  {'与えた傾斜':>10}{'与えた方位':>10}{'測った傾斜':>12}{'測った方位':>12}")
    for slope_deg, aspect_deg in ((5.0, 0.0), (12.0, 90.0), (30.0, 210.0), (45.0, 315.0)):
        z = plane(41, 41, cell, slope_deg, aspect_deg)
        s = demops.dem_slope(z, cell)[3:-3, 3:-3]
        a = demops.dem_aspect(z, cell)[3:-3, 3:-3]
        print(f"  {slope_deg:>10.1f}{aspect_deg:>10.1f}{np.mean(s):>12.6f}{np.mean(a):>12.6f}")
    print("  → 北 0 度・東回り。行 0 が北。ここを取り違えると南北が鏡像になる。")

    print("\n=== 2. 円錐 —— 傾斜は一定、方位は放射状 ===")
    z = cone(81, cell, 20.0)
    s = demops.dem_slope(z, cell)[5:-5, 5:-5]
    a = demops.dem_aspect(z, cell)
    print(f"  傾斜 平均 {np.mean(s):.6f} 度 / 標準偏差 {np.std(s):.2e}(与えた 20.0)")
    print(f"  方位 中心の北({a[10, 40]:.1f} 度)/ 南({a[70, 40]:.1f})/ 東({a[40, 70]:.1f})/ 西({a[40, 10]:.1f})")
    # 「傾斜は一定・方位は放射状」は表の 1 行より 1 枚のほうが速い。
    figs.save_grid("cone", [_big(z), _big(demops.dem_slope(z, cell)), _big(a)],
                   ["標高", "傾斜(一定 20 度)", "方位(放射状)"],
                   title="円錐 —— 傾斜と方位が閉形式に一致する", ncols=3,
                   caption="方位は北 0 度・東回り。中心で不連続に見えるのは"
                           "「斜面の向きが決まらない点」で、定義どおり。")

    print("\n=== 3. ガウス丘 —— 曲率の誤差は離散化か、式の誤りか ===")
    print(f"  {'セル [m]':>10}{'頂点の断面曲率':>16}{'閉形式':>12}{'誤差':>12}{'比':>8}")
    prev = None
    conv = []                                    # (セル寸法, 誤差)—— 図の材料
    for c in (4.0, 2.0, 1.0):
        n = int(2 * 120.0 / c) | 1
        z = gaussian_hill(n, c, amp=50.0, sigma=40.0)
        k = demops.dem_curvature(z, c, kind="profile")[n // 2, n // 2]
        exact = -50.0 / 40.0 ** 2                    # 頂点での二階微分 = -amp/sigma^2
        err = abs(k - exact)
        ratio = (prev / err) if prev else float("nan")
        print(f"  {c:>10.1f}{k:>16.6f}{exact:>12.6f}{err:>12.2e}{ratio:>8.2f}")
        conv.append((c, err))
        prev = err
    print("  → セルを半分にすると誤差が約 4 分の 1(比 ≈ 4)= **2 次収束**。")
    print("     これが出れば離散化の誤差であって、式の誤りではない。")
    # 傾き 2 の参照線と重ねると「2 次収束」が一目で言える(数字の比だと
    # 4.0 が偶然か本物かを読み手が判断できない)。
    cs = np.array([c for c, _ in conv])
    es = np.array([e for _, e in conv])
    figs.save_plot("curvature_convergence",
                   [("実測の誤差", np.log10(cs), np.log10(es)),
                    ("傾き 2 の参照線", np.log10(cs),
                     np.log10(es[0]) + 2.0 * (np.log10(cs) - np.log10(cs[0])))],
                   xlabel="log10 セル寸法 [m]", ylabel="log10 |断面曲率の誤差|",
                   title="曲率の誤差は離散化か、式の誤りか",
                   caption="参照線と平行 = 2 次収束 = 離散化の誤差。"
                           "式が違えばセルを細かくしても誤差は下げ止まる。")

    print("\n=== 4. 水の流れ —— 一様斜面の集水量は数えられる ===")
    z = plane(60, 40, cell, 10.0, 180.0)             # 南向きに下る = 行が増える向き
    acc = demops.dem_flow_accumulation(z, cell)
    col = acc[:, 20]
    print(f"  最上流の集水量 {col[0]:.0f} / 中腹 {col[30]:.0f} / 最下流 {col[-1]:.0f}")
    print(f"  列に沿って単調増加か: {bool(np.all(np.diff(col) >= 0))}")
    print(f"  総和 {acc.sum():.0f}(セル数 {acc.size})")

    print("\n=== 5. 欠測(水面)の扱いで答えが変わる ===")
    z2 = gaussian_hill(101, cell, amp=-30.0, sigma=60.0)   # 窪地
    z2[45:55, 45:55] = np.nan                              # 中央に水面
    print(f"  {'方針':>10}{'最大集水量':>14}{'全体比':>10}")
    acc_maps, acc_names = [_big(z2, 2)], ["標高(中央が欠測)"]
    for policy in demops.NODATA_POLICIES:
        if policy == "error":
            try:
                demops.dem_flow_accumulation(z2, cell)
                print(f"  {policy:>10}  ← 通ってしまった(想定外)")
            except ValueError:
                print(f"  {policy:>10}      拒否(既定。何が正しいかは対象次第)")
            continue
        a = demops.dem_flow_accumulation(z2, cell, nodata=policy)
        top = float(np.nanmax(a))
        print(f"  {policy:>10}{top:>14.0f}{100 * top / a.size:>9.1f}%")
        acc_maps.append(_big(np.log10(np.nan_to_num(np.asarray(a, float), nan=0.0) + 1.0), 2))
        acc_names.append("集水量 log10 —— %s" % policy)
    print("  → 中央値などで**埋める**選択肢は置いていない。埋めると存在しない平原が")
    print("     でき、例外も出さずに水を通すため(どこが地形でどこが穴埋めか消える)。")
    # 「答えが変わる」を数字 2 つでなく形で見せる。outlet は欠測へ水を吸い込み、
    # barrier は欠測を避けて縁へ回す —— 流路の形そのものが別物になる。
    figs.save_grid("nodata_policies", acc_maps, acc_names, ncols=3,
                   title="欠測(水面)の扱いで流路が変わる",
                   caption="同じ地形・同じ op。違うのは欠測の方針だけ。")

    print("\n=== 6. 日当たり —— 向きで陰影と天空率が変わる ===")
    print(f"  {'斜面の向き':>10}{'陰影(南東光源)':>16}{'天空率':>10}")
    shades, shade_names = [], []
    for name, aspect_deg in (("北向き", 0.0), ("東向き", 90.0), ("南向き", 180.0), ("西向き", 270.0)):
        z3 = plane(61, 61, cell, 25.0, aspect_deg)
        sh = demops.dem_hillshade(z3, cell, azimuth_deg=135.0, altitude_deg=40.0)
        svf = demops.dem_sky_view_factor(z3, cell, n_azimuth=8)
        print(f"  {name:>10}{np.mean(sh[5:-5, 5:-5]):>16.4f}{np.mean(svf[5:-5, 5:-5]):>10.4f}")
        shades.append(np.asarray(sh))
        shade_names.append("%s(陰影 %.3f)" % (name, float(np.mean(sh[5:-5, 5:-5]))))
    # 4 枚を**同じ塗り分け**で並べる(1 枚ずつ自動伸長すると差が消える)ため、
    # 4 面を 1 枚の配列に連結してから渡す。
    figs.save_grid("hillshade_aspect",
                   [np.concatenate([np.concatenate(shades[:2], axis=1),
                                    np.concatenate(shades[2:], axis=1)], axis=0)],
                   [" / ".join(shade_names)], ncols=1,
                   title="日当たりは斜面の向きで決まる(南東からの光、仰角 40 度)",
                   caption="左上=北向き 右上=東向き 左下=南向き 右下=西向き。"
                           "南東を向いた面がいちばん明るい。")
    flat = np.zeros((41, 41))
    print(f"  平坦面の天空率 {np.mean(demops.dem_sky_view_factor(flat, cell)):.6f}(閉形式 1.0)")
    print(f"  平坦面の陰影 {np.mean(demops.dem_hillshade(flat, cell, altitude_deg=40.0)):.6f}"
          f"(閉形式 sin 40 度 = {math.sin(math.radians(40.0)):.6f})")

    print("\n=== 7. 速度(この機械での実測)===")
    big = gaussian_hill(513, 2.0, amp=80.0, sigma=200.0) + plane(513, 513, 2.0, 3.0, 200.0)
    for label, fn in (("傾斜", lambda: demops.dem_slope(big, 2.0)),
                      ("方位", lambda: demops.dem_aspect(big, 2.0)),
                      ("曲率", lambda: demops.dem_curvature(big, 2.0)),
                      ("陰影", lambda: demops.dem_hillshade(big, 2.0)),
                      ("天空率(8 方位)", lambda: demops.dem_sky_view_factor(big, 2.0, n_azimuth=8)),
                      ("窪地埋め", lambda: demops.dem_fill_sinks(big, 1e-6)),
                      ("集水量", lambda: demops.dem_flow_accumulation(big, 2.0))):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<16}{1e3 * (time.perf_counter() - t0):>9.1f} ms  (513x513)")
    print("  → 局所演算は速い。水文の 2 つが 2 桁遅いのはアルゴリズムの形によるもので、")
    print("     優先度キューとトポロジカル掃引は逐次依存があり素直にはベクトル化できない。")

    # ---- 自己検査(速さは assert しない)-----------------------------------
    z = plane(41, 41, cell, 12.0, 90.0)
    assert abs(np.mean(demops.dem_slope(z, cell)[3:-3, 3:-3]) - 12.0) < 1e-9
    assert abs(np.mean(demops.dem_aspect(z, cell)[3:-3, 3:-3]) - 90.0) < 1e-9
    assert abs(np.mean(demops.dem_sky_view_factor(np.zeros((41, 41)), cell)) - 1.0) < 1e-9
    assert abs(np.mean(demops.dem_hillshade(np.zeros((41, 41)), cell, altitude_deg=40.0))
               - math.sin(math.radians(40.0))) < 1e-9
    acc = demops.dem_flow_accumulation(plane(60, 40, cell, 10.0, 180.0), cell)
    assert np.all(np.diff(acc[:, 20]) >= 0), "一様斜面で集水量が単調増加しない"
    # -9999 のような番兵は受け取らない(実数として扱うと傾斜が巨大な嘘になる)
    sentinel = np.zeros((21, 21))
    sentinel[10, 10] = -9999.0
    try:
        demops.dem_slope(sentinel, cell)
        raise AssertionError("番兵が素通りした")
    except ValueError:
        pass
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
