# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: RLE 領域 — HALCON region の「効率の正体」を voxel 界に持ち込む.

現実の問題(平たく):
    HALCON が 1000 万画素の画像から抜いた領域を何千個もメモリに置けるのは、
    region がビットマップでなく run-length(行ごとの水平線分のリスト)だから。
    Fullseye の 3D 側はこれまで全マスクが dense 配列で、部品 1 個のマスクに
    数十 MB を払っていた。成分ごとの領域を貯める・時系列で持つ・undo に積む、
    といった「多数の領域を保持する」用途で効いてくる表現がなかった。

方法(volregion の rle_region ファミリ):
    1) vol_rle_encode   : dense 二値ボリューム → x 方向 run のリスト(VolRLE)
    2) vol_rle_volume   : run のまま voxel 数(decode 不要)
    3) vol_rle_bbox     : run のまま AABB(decode 不要、volops と厳密一致)
    4) vol_rle_centroid : run のまま重心(spacing で物理 mm、dense と一致)
    5) vol_rle_decode   : dense へ復元(往復 bit 一致)
    6) vol_tiled_map    : z スラブ streaming(局所 op はメモリ有界で厳密一致)

Ground truth(検証):
    - メモリ: 192^3 の現実的な部品(球+軸円柱)で dense bool の 1/73(実測)。
      run 数に比例するので、大きい部品ほど得(384^3 実測は 1/145)
    - 正確性: volume/bbox/centroid が dense 計算・volops.vol_bounding_box と
      厳密一致、encode→decode の往復が bit 一致
    - 速度: bbox は dense 走査に対し decode 不要の直接演算(この規模で実測
      数十倍。モジュール docstring の 384^3 実測は ~1000x)
    - fail-closed: 改竄した RLE(範囲外 run)は decode が書き込む前に拒否
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scipy import ndimage

import volops
from volregion import (
    VolRLE,
    vol_rle_bbox,
    vol_rle_centroid,
    vol_rle_components,
    vol_rle_decode,
    vol_rle_difference,
    vol_rle_encode,
    vol_rle_intersect,
    vol_rle_union,
    vol_rle_volume,
)


def build_part(n=192):
    """現実的な部品マスク: 球 + 軸円柱(遊びでなく CT でよく見る形)。"""
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(np.float32)
    c = n / 2.0
    part = (((z - c) ** 2 + (y - c) ** 2 + (x - c) ** 2) <= (n * 0.22) ** 2)
    part |= (((y - c) ** 2 + (x - c) ** 2) <= (n * 0.06) ** 2)
    return part.astype(np.float64)


def main():
    mask = build_part()

    # 1) encode: メモリが run 比例に落ちる
    region = vol_rle_encode(mask)
    dense_bytes = mask.astype(bool).nbytes
    ratio = dense_bytes / region.nbytes
    print("[encode]")
    print(f"  {mask.shape} 前景 {int(mask.sum()):,} voxel → run {len(region):,} 本")
    print(f"  メモリ: dense bool {dense_bytes / 1e6:.1f} MB → RLE"
          f" {region.nbytes / 1e6:.2f} MB = 1/{ratio:.0f}")
    assert ratio > 49.0, f"RLE の圧縮率が実測想定未満: {ratio}"

    # 2)-4) run のままの直接演算 = dense 計算と厳密一致
    t0 = time.perf_counter()
    vol_direct = vol_rle_volume(region)
    bbox_direct = vol_rle_bbox(region)
    cen_direct = vol_rle_centroid(region)
    t_direct = time.perf_counter() - t0
    t0 = time.perf_counter()
    vol_dense = int(mask.sum())
    bbox_dense = volops.vol_bounding_box(mask)
    cen_dense = tuple(np.argwhere(mask > 0.5).mean(axis=0))
    t_dense = time.perf_counter() - t0
    print("[direct queries]")
    print(f"  volume {vol_direct:,} / bbox {bbox_direct} / centroid"
          f" ({cen_direct[0]:.2f}, {cen_direct[1]:.2f}, {cen_direct[2]:.2f})")
    print(f"  RLE 直接 {t_direct * 1e3:.2f} ms vs dense {t_dense * 1e3:.0f} ms"
          f"(decode せず {t_dense / max(t_direct, 1e-9):.0f}x)")
    assert vol_direct == vol_dense
    assert bbox_direct == bbox_dense
    assert np.allclose(cen_direct, cen_dense)
    # spacing 付き重心は物理 mm(dense 重心 × spacing と一致)
    cen_mm = vol_rle_centroid(region, spacing=(2.0, 0.5, 0.5))
    assert np.allclose(cen_mm, np.asarray(cen_dense) * [2.0, 0.5, 0.5])

    # 5) decode: 往復 bit 一致
    back = vol_rle_decode(region)
    assert np.array_equal(back, mask)
    print("[decode] 往復 bit 一致")

    # 6) run のままの集合演算(voxel 数に一切触れない = HALCON region 演算の本体)。
    #    球だけ・円柱だけの 2 領域を作り、和/積/差が dense の論理演算と厳密一致
    z, y, x = np.mgrid[0:192, 0:192, 0:192].astype(np.float32)
    c = 96.0
    sph = (((z - c) ** 2 + (y - c) ** 2 + (x - c) ** 2) <= (192 * 0.22) ** 2)
    cyl = (((y - c) ** 2 + (x - c) ** 2) <= (192 * 0.06) ** 2)
    del z, y, x
    rs, rc_ = vol_rle_encode(sph), vol_rle_encode(cyl)
    t0 = time.perf_counter()
    union = vol_rle_union(rs, rc_)
    inter = vol_rle_intersect(rs, rc_)
    diff = vol_rle_difference(rs, rc_)
    t_set = time.perf_counter() - t0
    assert np.array_equal(vol_rle_decode(union) > 0.5, sph | cyl)
    assert np.array_equal(vol_rle_decode(inter) > 0.5, sph & cyl)
    assert np.array_equal(vol_rle_decode(diff) > 0.5, sph & ~cyl)
    assert vol_rle_volume(union) == int((sph | cyl).sum())
    print(f"[set algebra] 和/積/差 3 演算 {t_set * 1e3:.1f} ms(run のみ、"
          f"decode 検算で dense 論理演算と厳密一致)")

    # 7) 成分分解: 球と(球に刺さらない)独立小片 → 成分ごとの VolRLE
    frag = np.zeros(mask.shape, np.float64)
    frag[5:15, 5:15, 5:15] = 1.0
    two = vol_rle_decode(vol_rle_union(vol_rle_encode(mask), vol_rle_encode(frag)))
    comps = vol_rle_components(two, connectivity=6)
    print(f"[components] 2 物体 → {len(comps)} 成分(体積 "
          + ", ".join(f"{vol_rle_volume(cp):,}" for cp in comps) + ")")
    assert len(comps) == 2
    assert sum(vol_rle_volume(cp) for cp in comps) == int(two.sum())

    # 8) 三本目の脚 vol_tiled_map: 「一度に RAM に載る量」を有界化。
    #    局所 op(gaussian σ=2 → z footprint = round(4σ) = 8)は overlap=8 で
    #    全量計算と厳密一致(この契約が破れる overlap では一致しない=正直な限界)
    tiled = volops.vol_tiled_map(
        mask, lambda s: ndimage.gaussian_filter(s, 2.0), tile=48, overlap=8)
    full = ndimage.gaussian_filter(mask, 2.0)
    err = float(np.abs(tiled - full).max())
    print(f"[tiled_map] 48 スラブ streaming vs 全量 gaussian: 最大差 {err:.1e}")
    assert err < 1e-14, f"タイル処理が全量計算と一致しない: {err}"

    # fail-closed: 改竄 RLE は書き込む前に拒否される
    hostile = VolRLE(np.array([10 ** 9], np.int32), np.array([0], np.int32),
                     np.array([4], np.int32), region.shape)
    try:
        vol_rle_decode(hostile)
        raise AssertionError("改竄 RLE が通ってしまった")
    except ValueError:
        print("[fail-closed] 範囲外 run の改竄 RLE を decode 前に拒否")

    print(
        f"\nPASS: RLE がメモリ 1/{ratio:.0f}(run {len(region):,} 本)、"
        f"volume/bbox/centroid は run 直接で dense と厳密一致"
        f"({t_dense / max(t_direct, 1e-9):.0f}x 速)、往復 bit 一致、改竄は拒否。"
    )


if __name__ == "__main__":
    main()
