# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 接触した 2 つの物体を分水嶺(watershed)で 1 個ずつに割る (touching object separation).

実世界の問題:
    CT / 粉体 / 細胞 / 封入物では、独立した物体どうしが**接触したり僅かに重なったり**する。
    このとき連結成分ラベリング(regionprops3d.label_components)は「背景で分断された塊」しか
    分けられず、接触した 2 物体を 1 個に融合してしまう。個数(2)も間違うし、融合した塊の
    単一重心は**どちらの物体の中心でもない中間点**に落ち、個々の体積も測れない。

原理:
    前景の距離変換(background から最も遠い=物体の芯)を取ると、凸物体では中心付近が極大に
    なる。その極大を(最小間隔 min_distance の非最大抑制で 1 物体 1 個に間引いて)シードにし、
    反転距離場 −dist の上でシードから分水嶺を流すと、接触面(距離の谷)が自然な切断面になり
    2 物体へ分離できる。fullseye watershed3d の
      - distance_peaks(binary, min_distance)         -> シード(int マーカ配列)
      - separate_touching(binary, min_distance=...)  -> 分離ラベル(1 呼び出し)
      - watershed_vol(binary, markers=None, ...)      -> 分離ラベル(汎用・外部シード可)
    を使う。バックエンドは skimage 分水嶺と純 scipy(最近傍マーカ = ボロノイ分割)の 2 系統で、
    凸物体の接触分離では両者ほぼ一致する(本例で両方を検証する)。座標系は numpy 軸順 (z,y,x)。

検証(GT):
    半径 r の 2 球を、中心間隔 < 2r で**僅かに重ねて**配置する(→ 1 連結成分に融合)。真値は
      1) 個数 = 2
      2) 各球の中心(z,y,x)は解析的に既知 → 分離ラベルの重心がそれに一致(< 1 voxel)
      3) 前景を過不足なく被覆(全ラベル体積の和 = 前景ボクセル数)
      4) 各ラベル体積が単体球(孤立時のボクセル数)に一致(重なり lens を分水嶺線で折半する
         ぶんだけ目減りするので、相対誤差数 % 以内)
    を確認する。skimage / scipy 両バックエンドで assert する。

beat-the-null(下駄を履かせない基準):
    素朴な連結成分ラベリング(label_components)は接触 2 球を count=1 に融合する。その単一重心は
    2 球の中間点(=どちらの真の中心からも ~r voxel 離れる)。watershed が count=2 かつ各真の
    中心へ ~0 voxel で当てて、この基準線を**個数でも重心でも判別的に上回る**ことを assert する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
# この例のファイル名 (watershed3d.py) はモジュール watershed3d.py と同名のため、
# リポジトリルートを sys.path の**先頭**に必ず置き、スクリプトディレクトリ
# (examples_3d/) より優先させる。さもないと `import watershed3d` が自分自身を
# 拾って循環 import になる(PYTHONPATH に repo が入っていても位置が後ろだと負ける)。
sys.path.insert(0, str(_REPO_ROOT))

from regionprops3d import label_components  # noqa: E402  (null 基準線)
from watershed3d import (  # noqa: E402  (sys.path 調整後に import)
    distance_peaks,
    separate_touching,
    watershed_vol,
)


def add_sphere(vol: np.ndarray, center: tuple[int, int, int], radius: int) -> None:
    """vol(bool)に solid な球を OR で描き込む(既存前景と融合し得る)。"""
    zz, yy, xx = np.ogrid[: vol.shape[0], : vol.shape[1], : vol.shape[2]]
    d2 = (zz - center[0]) ** 2 + (yy - center[1]) ** 2 + (xx - center[2]) ** 2
    vol |= d2 <= radius * radius


def isolated_sphere_voxels(radius: int) -> int:
    """半径 radius の孤立球のボクセル数(体積 GT の基準)。"""
    n = 4 * radius + 4
    v = np.zeros((n, n, n), dtype=bool)
    add_sphere(v, (2 * radius + 2, 2 * radius + 2, 2 * radius + 2), radius)
    return int(v.sum())


def build_scene(radius: int = 12, overlap: int = 4):
    """z 軸に沿って僅かに重ねた 2 球を合成し、(vol, 真の中心リスト) を返す。

    中心間隔 = 2r - overlap(< 2r なので必ず連結して 1 成分に融合する)。
    """
    sep = 2 * radius - overlap
    shape = (sep + 2 * radius + 8, 4 * radius + 4, 4 * radius + 4)
    cz0 = radius + 4
    cy = cx = 2 * radius + 2
    centers = [(cz0, cy, cx), (cz0 + sep, cy, cx)]
    vol = np.zeros(shape, dtype=bool)
    for c in centers:
        add_sphere(vol, c, radius)
    return vol, centers


def measure_labels(labels: np.ndarray) -> list[dict]:
    """ラベル配列 → 各ラベルの {label, volume, centroid(z,y,x)} 一覧(背景 0 は除く)。"""
    out = []
    for L in range(1, int(labels.max()) + 1):
        m = labels == L
        vox = int(m.sum())
        if vox == 0:
            continue
        c = np.argwhere(m).mean(axis=0)
        out.append({"label": L, "volume": vox, "centroid": (float(c[0]), float(c[1]), float(c[2]))})
    return out


def match_to_centers(measured: list[dict], centers: list[tuple]) -> list[tuple[dict, tuple]]:
    """測定ラベルを最近傍重心で真の中心へ一対一対応(ラベル順に依存しない)。"""
    if len(measured) != len(centers):
        raise ValueError(f"測定ラベル数 {len(measured)} と真値中心数 {len(centers)} が不一致。")
    used = [False] * len(centers)
    pairs = []
    for m in measured:
        mc = np.asarray(m["centroid"])
        best_j, best_d = -1, np.inf
        for j, g in enumerate(centers):
            if used[j]:
                continue
            d = float(np.linalg.norm(mc - np.asarray(g, dtype=np.float64)))
            if d < best_d:
                best_d, best_j = d, j
        if best_j < 0:
            raise ValueError("対応づけできない測定ラベルがある(真値が枯渇)。")
        used[best_j] = True
        pairs.append((m, centers[best_j]))
    return pairs


def evaluate(labels: np.ndarray, centers: list[tuple], fg: int,
             single_vox: int) -> tuple[int, float, float]:
    """分離結果を真値と突き合わせ (count, max_centroid_err, max_vol_rel_err) を返す。"""
    props = measure_labels(labels)
    count = len(props)
    total = sum(p["volume"] for p in props)
    if total != fg:
        raise ValueError(f"ラベルが前景を被覆していない: 総ラベル体積 {total} != 前景 {fg}")
    if count != len(centers):
        return count, float("inf"), float("inf")
    pairs = match_to_centers(props, centers)
    max_cen = max(
        float(np.linalg.norm(np.asarray(m["centroid"]) - np.asarray(g))) for m, g in pairs
    )
    max_vol = max(abs(m["volume"] - single_vox) / single_vox for m, _ in pairs)
    return count, max_cen, max_vol


def render_png(vol, dist_mip, markers, ws_labels, centers, out_path) -> bool:
    """接触2球の MIP を「入力(連結成分=1色)→距離+シード→分水嶺(2色)」で並置し PNG 保存。

    matplotlib が無ければ False を返す(GT アサートは呼び出し側で別途必須)。
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        import matplotlib.font_manager as fm
    except ImportError:
        return False

    # 日本語ラベルが tofu(□)にならないよう、環境にある日本語対応フォントを先頭に置く。
    installed = {f.name for f in fm.fontManager.ttflist}
    for jp in ("Yu Gothic", "Meiryo", "Noto Sans JP", "MS Gothic", "BIZ UDGothic"):
        if jp in installed:
            plt.rcParams["font.family"] = jp
            break
    plt.rcParams["axes.unicode_minus"] = False

    # x 軸を投影(axis=2)→ (z,y) 断面 MIP。2 球は z 方向に並ぶので両方写る。
    bin_mip = vol.max(axis=2)
    ws_mip = ws_labels.max(axis=2)                      # 各 (z,y) の代表ラベル
    seed_zy = np.argwhere(markers.max(axis=2) > 0)      # 投影後のシード位置

    fig, axes = plt.subplots(1, 3, figsize=(12, 5.2))
    fig.suptitle("接触2球の分離: 連結成分は1個に融合 → 距離変換シードの分水嶺で2個へ",
                 fontsize=12)

    # (a) 入力 = 連結成分(count=1)。全前景を単色で。
    axes[0].imshow(bin_mip, cmap="gray", origin="lower", interpolation="nearest")
    axes[0].set_title("(a) 入力 MIP  連結成分 = 1(融合)")

    # (b) 距離変換 + 抽出シード。
    axes[1].imshow(dist_mip, cmap="viridis", origin="lower", interpolation="nearest")
    if len(seed_zy):
        axes[1].scatter(seed_zy[:, 1], seed_zy[:, 0], c="red", marker="x", s=120,
                        linewidths=2.5, label="シード(距離極大)")
        axes[1].legend(loc="upper right", fontsize=8)
    axes[1].set_title("(b) 距離変換 + シード(芯)")

    # (c) 分水嶺ラベル(2色)+ 真の中心。
    lab_cmap = ListedColormap([(0.06, 0.06, 0.09),   # 0: 背景
                               (0.90, 0.36, 0.22),   # 1
                               (0.20, 0.55, 0.90)])  # 2
    axes[2].imshow(ws_mip, cmap=lab_cmap, vmin=0, vmax=2, origin="lower",
                   interpolation="nearest")
    cy = [c[1] for c in centers]
    cz = [c[0] for c in centers]
    axes[2].scatter(cy, cz, facecolors="none", edgecolors="white", marker="o",
                    s=160, linewidths=2.0, label="真の中心")
    axes[2].legend(loc="upper right", fontsize=8)
    axes[2].set_title("(c) 分水嶺で分離 = 2(重心一致)")

    for ax in axes:
        ax.set_xlabel("y"); ax.set_ylabel("z")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    return True


def main() -> int:
    radius = 12
    overlap = 4
    min_distance = 8.0
    vol, centers = build_scene(radius=radius, overlap=overlap)

    # --- 入力の健全性チェック(退化入力で偽の成功を出さない) ---
    if vol.ndim != 3:
        raise ValueError(f"3D ボリュームが必要 (ndim={vol.ndim})。")
    if not vol.any():
        raise ValueError("前景ボクセルが 0 個(退化入力)。")
    if len(centers) < 2:
        raise ValueError("beat-the-null が意味を持つには物体数 >= 2 が必要。")

    fg = int(vol.sum())
    single_vox = isolated_sphere_voxels(radius)
    print(f"[GT] shape={vol.shape}, 前景={fg} voxel, 物体数(true)={len(centers)}, "
          f"孤立球 r={radius} = {single_vox} voxel")
    for i, c in enumerate(centers):
        print(f"[GT] sphere {i}: center(z,y,x) = ({c[0]}, {c[1]}, {c[2]})")

    # --- beat-the-null 基準線: 連結成分ラベリング ---
    null_labels, null_n = label_components(vol, connectivity=26)
    null_centroid = np.argwhere(null_labels > 0).mean(axis=0)
    null_min_dist = min(
        float(np.linalg.norm(null_centroid - np.asarray(c, dtype=np.float64))) for c in centers
    )
    print(f"[null]  label_components -> count = {null_n} (融合), "
          f"single-centroid(z,y,x) = ({null_centroid[0]:.2f}, {null_centroid[1]:.2f}, "
          f"{null_centroid[2]:.2f}), min dist to any true center = {null_min_dist:.2f} voxel")

    # --- シード抽出(距離変換の極大)---
    markers = distance_peaks(vol, min_distance=min_distance)
    n_seeds = int(markers.max())
    print(f"[seed]  distance_peaks(min_distance={min_distance}) -> {n_seeds} 個 "
          f"@ {np.argwhere(markers > 0).tolist()}")

    # --- watershed(skimage / scipy 両バックエンドを検証)---
    results = {}
    for method in ("skimage", "scipy"):
        labels = separate_touching(vol, min_distance=min_distance, method=method)
        count, cen_err, vol_err = evaluate(labels, centers, fg, single_vox)
        results[method] = (labels, count, cen_err, vol_err)
        print(f"[watershed:{method}] count = {count}, max centroid err = {cen_err:.4f} voxel, "
              f"max volume rel-err = {vol_err * 100:.2f}%")

    # 外部シード経路(watershed_vol に markers を直接渡す)も一貫することを確認。
    lab_ext = watershed_vol(vol, markers=markers, method="auto")
    ext_count, ext_cen, _ = evaluate(lab_ext, centers, fg, single_vox)
    print(f"[watershed:auto+markers] count = {ext_count}, max centroid err = {ext_cen:.4f} voxel")

    # --- GT アサーション(両バックエンド)---
    assert null_n == 1, f"null(連結成分)が 1 でない: {null_n}(シーン設計を見直す)"
    assert n_seeds == len(centers), f"シード数が物体数と不一致: {n_seeds} vs {len(centers)}"

    best_cen_err = min(r[2] for r in results.values())
    for method, (labels, count, cen_err, vol_err) in results.items():
        assert count == len(centers), \
            f"[{method}] 分離数が真値と不一致: {count} vs {len(centers)}"
        assert cen_err < 1.0, f"[{method}] 重心誤差が 1 voxel 以上: {cen_err:.4f}"
        assert vol_err < 0.05, f"[{method}] 体積相対誤差が 5% 以上: {vol_err * 100:.2f}%"
        # beat-the-null: 個数でも重心でも判別的に上回る
        assert count != null_n, f"[{method}] 個数が null と同じ(分離できていない)"
        assert cen_err < null_min_dist, \
            (f"[{method}] 重心誤差 {cen_err:.4f} が null の距離 {null_min_dist:.4f} "
             f"を下回れていない(beat-the-null 失敗)")

    assert ext_count == len(centers), f"外部シード経路の分離数が不一致: {ext_count}"
    assert ext_cen < 1.0, f"外部シード経路の重心誤差が大きい: {ext_cen:.4f}"
    # null が判別に足る余地(単一重心が真の中心から十分離れている)を持つこと
    assert null_min_dist > 1.0, f"null の単一重心が真の中心に近すぎて判別にならない: {null_min_dist:.4f}"

    # --- デモ PNG(結果を描画)---
    dist_mip = None
    try:
        from scipy.ndimage import distance_transform_edt as _edt
        dist_mip = _edt(vol).max(axis=2)
    except ImportError:
        pass
    out_png = _REPO_ROOT / "examples_3d" / "_gallery" / "watershed3d.png"
    png_ok = False
    if dist_mip is not None:
        png_ok = render_png(vol, dist_mip, markers, results["skimage"][0], centers, out_png)
    if png_ok:
        print(f"[png]   saved -> {out_png}")
    else:
        print("[png]   matplotlib 不在のため画像はスキップ(GT アサートは実施済み)")

    print(f"PASS: 接触2球を watershed で {results['skimage'][1]} 個に分離。"
          f"skimage/scipy 両バックエンドで各重心を真の中心へ最大 {best_cen_err:.3f} voxel、"
          f"各体積を単体比 <5% 誤差で復元。連結成分(null)は count=1 に融合しその単一重心は"
          f"真の中心から {null_min_dist:.2f} voxel ずれる — 個数(2 vs 1)でも重心でも判別的に上回った")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
