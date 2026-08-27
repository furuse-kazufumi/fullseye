"""事例: 3D ボリューム内の複数ブロブを数えて一つずつ計測する (region properties).

実世界の問題:
    CT / ボリューメトリック検査では、1 枚のスキャンに「独立した物体」が複数写る
    ことがよくある(骨片が数個、部品が数個、封入物が数個…)。まずやりたい基本操作は
    「いくつあるか(個数)」と「それぞれどこにどれだけあるか(重心・体積)」を、
    塊ごとに分けて測ることだ。全部を一緒くたにした平均では、どの物体がどこにあるかも、
    何個あるかも復元できない。

原理:
    二値ボリューム(前景 True / 背景 False)を連結成分ラベリングで塊ごとに分け、
    塊ごとにボクセル数(=体積)と重心を測る。fullseye regionprops3d の
      - label_components(vol, connectivity=26) -> (labels, n)   個数を返す
      - region_props(vol, connectivity=26)     -> list[dict]    塊ごとの volume/centroid ほか
      - largest_component(vol, connectivity=26) -> bool マスク   最大塊だけ
      - filter_by_volume(vol, min_voxels, ...)  -> bool マスク   小さい塊を除去
    をこの順で連鎖させる。座標系は numpy の軸順 (z, y, x)。

検証(GT):
    既知の K 個の分離した直方体ブロブ(各ボクセル数・重心が解析的に既知)を合成し、
      1) ラベル数 n が K と一致するか
      2) 各ブロブの体積(ボクセル数)が真値と一致するか
      3) 各ブロブの重心が真値と一致するか(< 1 voxel)
      4) largest_component が最大ブロブ(既知)を厳密に返すか
      5) filter_by_volume が閾値未満の小ブロブだけ落とすか
    を確認する。beat-the-null: 「前景を 1 領域とみなす」素朴な基準線では個数は常に 1
    (≠ K)で、その単一重心はどの真の重心からも遠く、個数も重心も復元できない。
    実手法がこの基準線を判別的に上回ることを assert する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from regionprops3d import (  # noqa: E402  (sys.path 調整後に import)
    filter_by_volume,
    label_components,
    largest_component,
    region_props,
)


def add_box(vol: np.ndarray, z: tuple[int, int], y: tuple[int, int],
            x: tuple[int, int]) -> dict:
    """vol に solid な直方体ブロブを 1 個描き込み、その真値(体積・重心)を返す。

    z/y/x は (start, stop)(stop は排他的、numpy スライス規約)。
    solid box が占める整数座標 [a, b) の平均は (a + b - 1) / 2 なので重心は解析解。
    """
    (zs, ze), (ys, ye), (xs, xe) = z, y, x
    vol[zs:ze, ys:ye, xs:xe] = True
    volume = (ze - zs) * (ye - ys) * (xe - xs)
    centroid = ((zs + ze - 1) / 2.0, (ys + ye - 1) / 2.0, (xs + xe - 1) / 2.0)
    return {"volume": int(volume), "centroid": centroid}


def build_scene() -> tuple[np.ndarray, list[dict]]:
    """K=3 個の well-separated な直方体ブロブを持つ体積を合成し、真値リストを返す。

    ブロブ間は全軸で十分な空きを空けるので、最も緩い 26 連結でも融合しない
    (対角接触もしない)。体積を互いに異なる値にして「最大」を一意にする。
    """
    vol = np.zeros((40, 40, 40), dtype=bool)
    gt = [
        add_box(vol, (2, 5), (2, 5), (2, 5)),        # 小: 3*3*3   = 27
        add_box(vol, (20, 26), (10, 15), (30, 34)),  # 大: 6*5*4   = 120 (最大)
        add_box(vol, (10, 14), (30, 34), (5, 9)),    # 中: 4*4*4   = 64
    ]
    return vol, gt


def match_to_gt(measured: list[dict], gt: list[dict]) -> list[tuple[dict, dict]]:
    """測定リージョンを最近傍重心で真値ブロブへ一対一対応させる(ラベル順に依存しない)。

    各真値は高々 1 回しか使わせず、全真値が過不足なくマッチしなければ ValueError。
    """
    if len(measured) != len(gt):
        raise ValueError(
            f"測定リージョン数 {len(measured)} と真値ブロブ数 {len(gt)} が不一致。"
        )
    used = [False] * len(gt)
    pairs: list[tuple[dict, dict]] = []
    for m in measured:
        mc = np.asarray(m["centroid"], dtype=np.float64)
        best_j, best_d = -1, np.inf
        for j, g in enumerate(gt):
            if used[j]:
                continue
            d = float(np.linalg.norm(mc - np.asarray(g["centroid"])))
            if d < best_d:
                best_d, best_j = d, j
        if best_j < 0:
            raise ValueError("対応づけできない測定リージョンがある(真値が枯渇)。")
        used[best_j] = True
        pairs.append((m, gt[best_j]))
    return pairs


def main() -> int:
    vol, gt = build_scene()
    k_true = len(gt)

    # --- 入力の健全性チェック(退化入力で偽の成功を出さない) ---
    if vol.ndim != 3:
        raise ValueError(f"3D ボリュームが必要 (ndim={vol.ndim})。")
    if not vol.any():
        raise ValueError("前景ボクセルが 0 個。合成シーンが空(退化入力)。")
    if k_true < 2:
        raise ValueError("beat-the-null が意味を持つには K>=2 が必要。")

    total_fg = int(vol.sum())
    print(f"[GT] volume shape = {vol.shape}, foreground voxels = {total_fg}, K(true) = {k_true}")
    for i, g in enumerate(gt):
        cz, cy, cx = g["centroid"]
        print(f"[GT] blob {i}: volume = {g['volume']:4d}, centroid(z,y,x) = "
              f"({cz:.2f}, {cy:.2f}, {cx:.2f})")

    # --- (1) label_components: 個数を数える ---
    labels, n = label_components(vol, connectivity=26)
    if labels.shape != vol.shape:
        raise ValueError(f"labels 形状 {labels.shape} が入力 {vol.shape} と不一致。")
    print(f"[measure] label_components -> n = {n}")

    # --- beat-the-null 基準線: 「前景を 1 領域とみなす」 ---
    null_count = 1
    null_centroid = np.argwhere(vol).mean(axis=0)  # 全前景の単一重心
    null_min_dist = min(
        float(np.linalg.norm(null_centroid - np.asarray(g["centroid"]))) for g in gt
    )
    print(f"[null]  count = {null_count} (≠ K), single-centroid(z,y,x) = "
          f"({null_centroid[0]:.2f}, {null_centroid[1]:.2f}, {null_centroid[2]:.2f}), "
          f"min dist to any GT = {null_min_dist:.2f} voxel")

    # --- (2) region_props: 塊ごとに体積・重心を測る ---
    props = region_props(vol, connectivity=26)
    if len(props) != n:
        raise ValueError(f"region_props 件数 {len(props)} が label 数 {n} と不一致。")

    pairs = match_to_gt(props, gt)
    max_vol_err = 0
    max_centroid_err = 0.0
    for m, g in pairs:
        vol_err = abs(m["volume"] - g["volume"])
        cen_err = float(np.linalg.norm(
            np.asarray(m["centroid"]) - np.asarray(g["centroid"])
        ))
        max_vol_err = max(max_vol_err, vol_err)
        max_centroid_err = max(max_centroid_err, cen_err)
    print(f"[measure] region_props -> max volume error = {max_vol_err} voxel, "
          f"max centroid error = {max_centroid_err:.4f} voxel")

    # --- (3) largest_component: 最大塊(既知)を厳密に返すか ---
    gt_largest = max(range(k_true), key=lambda i: gt[i]["volume"])
    gt_largest_vol = gt[gt_largest]["volume"]
    lc_mask = largest_component(vol, connectivity=26)
    lc_vol = int(lc_mask.sum())
    lc_centroid = np.argwhere(lc_mask).mean(axis=0)
    lc_cen_err = float(np.linalg.norm(lc_centroid - np.asarray(gt[gt_largest]["centroid"])))
    print(f"[measure] largest_component -> volume = {lc_vol} "
          f"(GT largest = {gt_largest_vol}), centroid error = {lc_cen_err:.4f} voxel")

    # --- (4) filter_by_volume: 小ブロブだけ落とす(連鎖の締め) ---
    # 閾値を最小ブロブ超・次点以下に設定 -> 最小ブロブのみ除去されるはず。
    sizes = sorted(g["volume"] for g in gt)
    min_voxels = sizes[0] + 1          # 最小(27)は落とし、次点(64)以上は残す
    survivors_expected = sum(v for v in sizes if v >= min_voxels)
    fb_mask = filter_by_volume(vol, min_voxels=min_voxels, connectivity=26)
    fb_vol = int(fb_mask.sum())
    _, fb_n = label_components(fb_mask, connectivity=26)
    print(f"[measure] filter_by_volume(min_voxels={min_voxels}) -> "
          f"surviving voxels = {fb_vol} (expected {survivors_expected}), "
          f"surviving blobs = {fb_n} (expected {k_true - 1})")

    # --- GT アサーション ---
    # 実手法: 個数・体積・重心を厳密復元
    assert n == k_true, f"ラベル数が真値と不一致: n={n} vs K={k_true}"
    assert len(props) == k_true, f"region_props 件数が真値と不一致: {len(props)} vs {k_true}"
    assert max_vol_err == 0, f"体積(ボクセル数)に誤差: max {max_vol_err} voxel"
    assert max_centroid_err < 1.0, f"重心誤差が 1 voxel 以上: {max_centroid_err:.4f}"

    # largest_component: 最大塊を厳密に(体積一致 + 重心一致)
    assert lc_vol == gt_largest_vol, \
        f"largest_component 体積が最大塊と不一致: {lc_vol} vs {gt_largest_vol}"
    assert lc_cen_err < 1.0, f"largest_component 重心誤差が大きい: {lc_cen_err:.4f}"

    # filter_by_volume: 最小塊のみ除去(体積・個数とも一致)
    assert fb_vol == survivors_expected, \
        f"filter 後の体積が想定と不一致: {fb_vol} vs {survivors_expected}"
    assert fb_n == k_true - 1, f"filter 後の塊数が想定と不一致: {fb_n} vs {k_true - 1}"

    # beat-the-null: 素朴な単一領域では個数も重心も復元不能
    assert null_count != k_true, "null が偶然 K に一致(シーン設計を見直すこと)"
    assert null_min_dist > 1.0, \
        f"null の単一重心が真の重心に近すぎて判別にならない: {null_min_dist:.4f}"
    assert max_centroid_err < null_min_dist, \
        (f"実手法の重心誤差 {max_centroid_err:.4f} が null の距離 {null_min_dist:.4f} "
         f"を下回れていない(beat-the-null 失敗)")

    print(f"PASS: {n} 個の塊を分離し体積誤差 {max_vol_err} voxel・重心誤差 "
          f"{max_centroid_err:.4f} voxel で計測、largest={lc_vol}voxel を厳密特定、"
          f"filter で最小塊のみ除去。null(1 領域・重心ズレ {null_min_dist:.2f} voxel)を上回った")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
