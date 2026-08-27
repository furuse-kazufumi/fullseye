# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 曲面(球)に沿った距離を測る — 測地距離 と 均等な代表点えらび (FPS).

解きたい問題(かんたんな言葉で):
    ボールの表面にアリが2匹いる。アリは表面を這うしかない(空中を突っ切れない)。
    2匹の「表面を歩く最短距離」を知りたい。これが測地距離(geodesic distance)。
    地図でいう「大円距離」(飛行機が地球の丸みに沿って飛ぶ距離)と同じもの。
    素朴に3D空間の直線距離(定規で刺した距離=弦)で測ると、丸みを無視して
    いつも短めに出てしまう。表面に沿う道のり(弧)は直線(弦)より必ず長いからだ。

方法:
    球面から点群をサンプルし、各点を近傍どうしつないだ kNN グラフを作る。
    そのグラフ上の最短路(Dijkstra)を測地距離の離散近似とする(Isomap 型)。
    さらに farthest_point_sampling で、表面上で互いに遠い代表点を均等に選ぶ。

検証(GT, 既知の正解):
    半径 R の球なので、2点の測地距離の真値は「大円距離 = R × 中心角」で解析的に分かる。
      (1) 測ったグラフ測地距離が 大円距離 と一致する(相対誤差 < 10%)。
      (2) 測地距離は 直線(ユークリッド弦)距離より常に長い(弦 < 弧)。
    beat-the-null(素朴案を上回る):
      直線ユークリッド距離を測地距離とみなす素朴案は、曲面上で系統的に過小評価する
      (遠い点ほどひどい)。本手法の相対誤差が、その素朴案の誤差より小さいことを示す。
      FPS も、ランダムに代表点を選ぶ素朴案より「最も近い代表点どうしの間隔」を広くする。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import geodesic3d as G  # noqa: E402


def fibonacci_sphere(n: int, radius: float = 1.0) -> np.ndarray:
    """黄金角らせんで球面上に(ほぼ)一様な n 点を作る。→ (n,3) float。

    一様に散らばるので kNN グラフの密度が偏らず、測地距離の近似が安定する。
    """
    i = np.arange(n)
    y = 1.0 - 2.0 * (i + 0.5) / n            # -1..1 を等間隔に(高さ)
    r = np.sqrt(np.clip(1.0 - y * y, 0.0, 1.0))
    phi = np.pi * (3.0 - np.sqrt(5.0))        # 黄金角
    theta = phi * i
    x = np.cos(theta) * r
    z = np.sin(theta) * r
    return radius * np.stack([x, y, z], axis=1)


def great_circle(points: np.ndarray, source: int, radius: float) -> np.ndarray:
    """球面上の真の測地(大円)距離 = R × 中心角。→ (N,) float。source から全点。"""
    p = np.asarray(points, dtype=float)
    ps = p[source]
    cos_ang = np.clip((p @ ps) / (radius * radius), -1.0, 1.0)
    return radius * np.arccos(cos_ang)


def main() -> int:
    radius = 2.0
    n_points = 2000
    k = 10

    # --- 1) 合成データ: 半径 R の球面上に一様点群(真値が解析式で分かる) ---
    pts = fibonacci_sphere(n_points, radius=radius)
    source = 0

    # --- 2) op を鎖にする: kNN グラフ上の測地距離(Dijkstra) ---
    geo = G.geodesic_distances(pts, source, k=k)          # (N,) 測地距離(近似)
    gc = great_circle(pts, source, radius)                # (N,) 大円距離(真値)
    chord = np.linalg.norm(pts - pts[source], axis=1)     # (N,) 直線(弦)= 素朴案

    reachable = np.isfinite(geo)
    assert reachable.all(), "kNN グラフが分断: 到達不能点あり(k を増やす)"

    # 一番遠い点(ほぼ対蹠点)を代表ペアにして数値を報告する。
    target = int(np.argmax(gc))
    rel_geo = abs(geo[target] - gc[target]) / gc[target]      # 本手法の相対誤差
    rel_null = abs(chord[target] - gc[target]) / gc[target]   # 素朴案(直線)の相対誤差

    print(f"球の半径 R                       : {radius:.3f}")
    print(f"点数 / kNN の k                   : {n_points} / {k}")
    print(f"代表ペア source->target          : {source} -> {target} (最遠)")
    print(f"大円距離(真値, R×中心角)        : {gc[target]:.4f}")
    print(f"測地距離(本手法, グラフ最短路)  : {geo[target]:.4f}  相対誤差 {rel_geo*100:.2f}%")
    print(f"直線距離(素朴案, 弦)            : {chord[target]:.4f}  相対誤差 {rel_null*100:.2f}%")

    # GT(1): 本手法の測地距離が大円距離と一致(相対誤差 < 10%)。
    assert rel_geo < 0.10, f"測地距離が大円距離と乖離: 相対誤差 {rel_geo*100:.2f}%"

    # GT(2): 弦 < 弧。測地距離は直線より常に長い(近い点の数値ノイズ用に微小許容)。
    tol = 1e-9
    assert np.all(geo[reachable] + tol >= chord[reachable]), "測地距離が直線より短い点がある(弦<弧に反する)"

    # beat-the-null(距離): 素朴な直線案は系統的に過小評価。真値との相対誤差を本手法が下回る。
    mean_rel_geo = float(np.mean(np.abs(geo[reachable] - gc[reachable]) / np.maximum(gc[reachable], 1e-9)))
    far = gc > 0.5 * gc.max()   # 遠い点(弦の過小評価が顕著な領域)で公平に比べる
    mean_rel_null = float(np.mean(np.abs(chord[far] - gc[far]) / gc[far]))
    print(f"平均相対誤差 本手法(全点)       : {mean_rel_geo*100:.2f}%")
    print(f"平均相対誤差 素朴案(遠方点, 直線): {mean_rel_null*100:.2f}%")
    assert mean_rel_geo < mean_rel_null, "本手法が素朴な直線案を上回れていない"
    # 直線案は「短い側」に偏る(系統的過小評価)ことも確認。
    assert np.mean(chord[far] - gc[far]) < 0, "素朴案が過小評価になっていない"

    # --- 3) op を鎖にする: FPS で均等な代表点を選ぶ ---
    m = 8
    sel = G.farthest_point_sampling(pts, m, k=k, start=source)   # (m,) 選択インデックス
    assert sel.shape == (m,) and len(np.unique(sel)) == m, "FPS の選択が不正(重複/個数)"

    # 均等さの指標: 選んだ代表点どうしの「最も近いペアの大円距離」(大きいほど均等)。
    def min_pairwise_gc(idx: np.ndarray) -> float:
        best = np.inf
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                cos_ang = np.clip((pts[idx[a]] @ pts[idx[b]]) / (radius * radius), -1.0, 1.0)
                best = min(best, radius * float(np.arccos(cos_ang)))
        return best

    fps_spread = min_pairwise_gc(sel)

    # beat-the-null(FPS): ランダムに m 点選ぶ素朴案の平均間隔を上回る。
    rng = np.random.default_rng(0)
    null_spreads = [min_pairwise_gc(rng.choice(n_points, size=m, replace=False)) for _ in range(200)]
    null_spread = float(np.mean(null_spreads))
    print(f"FPS 最近接ペア間隔(大円)        : {fps_spread:.4f}")
    print(f"ランダム選択の平均間隔(素朴案)   : {null_spread:.4f}")
    assert fps_spread > null_spread, "FPS がランダム選択より均等になっていない"

    print(
        f"PASS: 測地={geo[target]:.3f} が大円={gc[target]:.3f} と一致(誤差{rel_geo*100:.1f}%<10%)、"
        f"弦<弧を全点で満たし、素朴な直線案(遠方誤差{mean_rel_null*100:.0f}%)を上回る。"
        f"FPS 間隔 {fps_spread:.3f} > ランダム {null_spread:.3f}。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
