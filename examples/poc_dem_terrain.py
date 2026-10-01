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


# ───────────────────── 動画(図を出すときだけ組む) ─────────────────────
# 3-D は render3d.render_mesh(z-buffer)で描き、色は頂点の値を重心座標で補間する。
# ★座標の約束: 格子の行 0 を**北(画像の上)**とし、世界座標は (x = 東, Y = 北 = -行方向, z = 上)。
#   行方向をそのまま +Y にすると左手系になり、絵が鏡像になる(上から見た静止図と左右が食い違う)。
def _v_mesh(Z, xs, ys, step=1):
    """標高格子 ``Z[行, 列]`` → 三角形メッシュ ``(V, F)``。``xs`` = 列の座標 [m]、``ys`` = 行の座標 [m]
    (行方向 = 南向き)。世界座標は ``(x, -y, z)``。NaN の頂点に触れる三角形は捨てる。"""
    Zs = np.asarray(Z, np.float64)[::step, ::step]
    h, w = Zs.shape
    gx, gy = np.meshgrid(np.asarray(xs, np.float64)[::step], np.asarray(ys, np.float64)[::step])
    ok = np.isfinite(Zs).ravel()
    V = np.column_stack([gx.ravel(), -gy.ravel(), np.where(np.isfinite(Zs), Zs, 0.0).ravel()])
    idx = np.arange(h * w).reshape(h, w)
    a, b = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel()
    c, d = idx[1:, :-1].ravel(), idx[1:, 1:].ravel()
    F = np.concatenate([np.column_stack([a, b, d]), np.column_stack([a, d, c])])
    F = F[ok[F].all(axis=1)]
    return V, F


def _v_render(V, F, vcol, pose, K, w, h, light=None, ambient=0.35, bg=(0.07, 0.08, 0.10)):
    """頂点色 ``vcol (nv,3)`` のメッシュを描く → ``(rgb (h,w,3), depth (h,w))``。
    ``light`` = 世界座標の光の向き(None なら頂点色そのまま = 陰影は呼び手が色に焼き込み済み)。"""
    import render3d as R3

    r = R3.render_mesh(V, F, pose=pose, intrinsics=K, width=w, height=h, attributes=True)
    img = np.empty((h, w, 3), np.float64)
    img[:] = bg
    m = r["face"] >= 0
    if m.any():
        fi = r["face"][m]
        col = np.einsum("nk,nkc->nc", r["bary"][m], np.asarray(vcol, np.float64)[F[fi]])
        if light is not None:
            L = pose[:3, :3] @ (np.asarray(light, np.float64) / np.linalg.norm(light))
            col = col * (ambient + (1.0 - ambient) * np.clip(r["normals"][m] @ L, 0.0, 1.0))[:, None]
        img[m] = col
    return np.clip(img, 0.0, 1.0), r["depth"]


def _v_project(P, pose, K):
    """世界座標の点 → ``(列 u, 行 v, 奥行き)``。render_mesh と同じ約束(カメラは -Z を見る)。"""
    P = np.atleast_2d(np.asarray(P, np.float64))
    Vc = P @ pose[:3, :3].T + pose[:3, 3]
    dep = -Vc[:, 2]
    s = np.where(dep > 1e-9, dep, np.nan)
    return K[0, 0] * Vc[:, 0] / s + K[0, 2], K[1, 2] - K[1, 1] * Vc[:, 1] / s, dep


def _v_disk(img, u, v, r, color):
    """画面上の (u, v) に半径 r の円を塗る(はみ出しは切る)。"""
    if not (np.isfinite(u) and np.isfinite(v)):
        return img
    h, w = img.shape[:2]
    r0, r1 = max(0, int(v - r - 1)), min(h, int(v + r + 2))
    c0, c1 = max(0, int(u - r - 1)), min(w, int(u + r + 2))
    if r0 >= r1 or c0 >= c1:
        return img
    yy, xx = np.mgrid[r0:r1, c0:c1]
    m = (yy - v) ** 2 + (xx - u) ** 2 <= r * r
    img[r0:r1, c0:c1][m] = color
    return img


def _v_line(img, p0, p1, color, width=2.0):
    """画面上の線分 (u0,v0)-(u1,v1)。"""
    (u0, v0), (u1, v1) = p0, p1
    if not all(np.isfinite([u0, v0, u1, v1])):
        return img
    n = int(max(abs(u1 - u0), abs(v1 - v0)) * 1.5) + 2
    for t in np.linspace(0.0, 1.0, n):
        _v_disk(img, u0 + t * (u1 - u0), v0 + t * (v1 - v0), width * 0.5, color)
    return img


def _v_txt(img, s, xy, anchor="lt", fs=13):
    import annotate as AN

    return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=fs), dtype=np.float64)


def _v_cbar(img, lut, rect, vmin, vmax, unit, fs=11):
    import annotate as AN

    return np.asarray(AN.color_bar(img, lut, rect, vmin=vmin, vmax=vmax, unit=unit, font_size=fs,
                                   label_fmt="{:.2f}" if abs(vmax - vmin) < 5 else "{:.0f}"),
                      dtype=np.float64)


def _v_cmap(vals, name, vmin, vmax):
    """値の並び → RGB(尺度は vmin..vmax で固定)。"""
    import imgio

    a = np.asarray(vals, np.float64)
    return np.asarray(imgio.apply_cmap(a.reshape(1, -1), name, vmin=vmin, vmax=vmax),
                      np.float64).reshape(a.shape + (3,))


#: 動画の地形(800 m 四方、セル 5 m)。山 2 つ + 南西へ下る 3 度の平面 + 尾根のうねり。
#: 解析曲面ではない —— 動画は「op の出力がどう見えるか」を見せるためのもので、検算は §1〜6 がしている。
def _flight_terrain(n=161, cell=5.0):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) * cell
    z = (95.0 * np.exp(-((xx - 300.0) ** 2 + (yy - 330.0) ** 2) / (2 * 110.0 ** 2))
         + 60.0 * np.exp(-((xx - 590.0) ** 2 + (yy - 540.0) ** 2) / (2 * 80.0 ** 2))
         + 7.0 * np.sin(xx / 41.0) * np.cos(yy / 57.0)
         + plane(n, n, cell, 3.0, 225.0) + 40.0)
    return z


def fig_terrain_flight(cell=5.0, W=640, H=360, fps=30.0):
    """主図(動画): 地形の上を回り込み(前半)、止まって太陽を一周させる(後半)。

    陰影は描画器の光ではなく **``dem_hillshade`` の出力そのもの**で塗る(コマごとに太陽の方位を
    変えて呼び直す)。青い筋は ``dem_flow_accumulation`` の集水量 ≥ 150 セルの流路。北・南向き斜面
    (``dem_aspect`` で 315〜45 度 / 135〜225 度)の陰影の平均を毎コマ印字する。
    """
    import render3d as R3

    z = _flight_terrain(cell=cell)
    n = z.shape[0]
    xs = np.arange(n) * cell
    V, F = _v_mesh(z, xs, xs)
    ex = 2.5                                            # 高さの強調(画面上だけ。数字は実寸)
    V[:, 2] = (V[:, 2] - z.min()) * ex
    acc = np.asarray(demops.dem_flow_accumulation(z, cell), np.float64)
    asp = np.asarray(demops.dem_aspect(z, cell), np.float64)
    slope = np.asarray(demops.dem_slope(z, cell), np.float64)
    north = ((asp >= 315.0) | (asp < 45.0)) & (slope > 2.0)
    south = (asp >= 135.0) & (asp < 225.0) & (slope > 2.0)
    stream = (acc >= 150.0).ravel()
    zlo, zhi = float(z.min()), float(z.max())
    clo = zlo - 0.3 * (zhi - zlo)                       # terrain の下端(海の青)を使わない —— 青は流路に取っておく
    base = _v_cmap(z.ravel(), "terrain", clo, zhi)
    K = R3.intrinsics_from_fov(38.0, W, H)
    ctr = np.array([xs[-1] / 2, -xs[-1] / 2, 0.25 * (zhi - zlo) * ex])
    lut = _v_cmap(np.linspace(zlo, zhi, 256), "terrain", clo, zhi)
    n1, n2 = 150, 180                                   # 回り込み 5 s + 太陽を一周 6 s
    frames, rec = [], []
    for k in range(n1 + n2):
        if k < n1:
            cam_az = 200.0 + 160.0 * k / (n1 - 1)       # 南南西から回って北東の上空へ
            sun_az = 135.0
        else:
            cam_az = 360.0
            sun_az = (135.0 + 360.0 * (k - n1 + 1) / n2) % 360.0   # +1: 前半の最後のコマと同じ絵を作らない
        alt = 35.0
        hs = np.asarray(demops.dem_hillshade(z, cell, azimuth_deg=sun_az, altitude_deg=alt), np.float64)
        col = base * (0.18 + 0.82 * hs.ravel())[:, None]
        col[stream] = col[stream] * 0.3 + 0.7 * np.array([0.15, 0.45, 1.0])
        a = np.radians(cam_az)                          # 方位: 北 0 度・東回り(dem_aspect と同じ)
        eye = ctr + np.array([980.0 * np.sin(a), 980.0 * np.cos(a), 620.0])
        pose = R3.look_at(eye, ctr, up=(0.0, 0.0, 1.0))
        img, _ = _v_render(V, F, col, pose, K, W, H)
        # 方位の目印: 北の縁の中央に「北」、太陽の方向に「太陽」
        u, v, d = _v_project([[xs[-1] / 2, 0.0, (zhi - zlo) * ex * 0.15]], pose, K)
        if d[0] > 0 and 8 < u[0] < W - 30 and 20 < v[0] < H - 10:
            img = _v_disk(img, u[0], v[0], 4, (1.0, 1.0, 1.0))
            img = _v_txt(img, "北", (u[0], v[0] - 6), anchor="cb", fs=12)
        sa = np.radians(sun_az)
        su, sv, sd = _v_project([ctr + np.array([900.0 * np.sin(sa), 900.0 * np.cos(sa),
                                                 900.0 * np.tan(np.radians(alt))])], pose, K)
        if sd[0] > 0 and 14 < su[0] < W - 40 and 14 < sv[0] < H - 30:
            img = _v_disk(img, su[0], sv[0], 7, (1.0, 0.85, 0.2))
            img = _v_txt(img, "太陽", (su[0], sv[0] + 10), anchor="ct", fs=11)
        mn, ms = float(hs[north].mean()), float(hs[south].mean())
        rec.append((sun_az, mn, ms))
        img = _v_txt(img, "太陽 方位 %3.0f 度・仰角 %.0f 度(dem_hillshade で塗る)\n"
                          "陰影の平均  北向き斜面 %.3f / 南向き斜面 %.3f\n"
                          "青 = 集水量 150 セル以上(dem_flow_accumulation)" % (sun_az, alt, mn, ms),
                     (6, 6), fs=12)
        img = _v_cbar(img, lut, (W - 64, 64, 14, H - 120), zlo, zhi, "m")
        img = _v_txt(img, "高さ 2.5 倍強調", (W - 6, H - 6), anchor="rb", fs=10)
        frames.append(img)
    i_s = int(np.argmax([r[2] for r in rec[n1:]])) + n1
    i_n = int(np.argmax([r[1] for r in rec[n1:]])) + n1
    figs.save_video("terrain_flight", frames, fps=fps, gif_every=3, gif_width=480,
                    caption="主図(動画、%d × %d・%.0f fps・%.0f 秒): 800 m 四方の地形(セル 5 m)を南南西から北へ回り込み、"
                            "止まって太陽を一周させる。陰影は描画の光でなく dem_hillshade(仰角 35 度)の出力で塗り、"
                            "青は dem_flow_accumulation の集水量 150 セル以上。南向き斜面の陰影の平均は太陽方位 %.0f 度で"
                            "最大 %.3f、北向き斜面は %.0f 度で最大 %.3f —— 日当たりは斜面の向きで決まる(§6 の平面と同じ結論)。"
                            "高さは画面上だけ 2.5 倍。"
                            % (W, H, fps, len(frames) / fps, rec[i_s][0], rec[i_s][2], rec[i_n][0], rec[i_n][1]))
    return rec


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
        shade_names.append("%s %.3f" % (name, float(np.mean(sh[5:-5, 5:-5]))))
    # 4 枚を**同じ塗り分け**で並べる(パネルごとに自動伸長されると、明るさの
    # 差そのものが消えてしまう)ため、4 面を 1 枚の配列に連結してから渡す。
    figs.save_grid("hillshade_aspect",
                   [_big(np.concatenate([np.concatenate(shades[:2], axis=1),
                                         np.concatenate(shades[2:], axis=1)], axis=0), 2)],
                   ["左上=北 右上=東 左下=南 右下=西"], ncols=1,
                   title="日当たりは斜面の向きで決まる(南東の光、仰角 40 度)",
                   caption="陰影の平均は " + " / ".join(shade_names)
                           + "。南東を向いた面がいちばん明るい。")
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

    # 動画は図を出すときだけ組む(図なしの実行の所要時間と出力を変えない)
    if figs.enabled():
        fig_terrain_flight()

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
