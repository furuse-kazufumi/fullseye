# -*- coding: utf-8 -*-
"""事例: OpenVX 互換の 10 op を規格(OpenVX 1.3.1)の式どおりの値で確かめる(vxcore ギャラリー)

平たく言うと:
  OpenVX は組込み向け画像処理の標準 API。各関数は「この画素はこの式で決まる」と規格の本文で決まっている。
  ここでは規格の式から手で値が出せる入力(傾きの一定な坂・1 点だけの突起・既知の角度の勾配・恒等や
  90° 回転の写像)を作り、vxcore の 10 op に通して 1 画素ずつ照合する。中央値・最小・最大のフィルタは
  scipy.ndimage を独立の第 2 実装にして全画素を比べる。外れたら exit 1。図は作らない、乱数は seed 固定。

確かめ方(op ごとの真値):
  * vx_sobel3x3         —— 坂 I = 3x + 5y の内側で gx = 3·2·4 = 24、gy = 5·2·4 = 40、replicate の端は半分、undefined は valid の外が 0
  * vx_magnitude        —— (3,4)→5、(1,1)→uint16(√2 + 0.5) = 1、(2,3)→4、(−32768,−32768)→32767 に飽和
  * vx_phase            —— 0°, 90°, 180°, 270°, 315° が 0, 64, 128, 192, 224、2π の手前は floor で 255・round で 0、(0,0) は 0
  * vx_table_lookup     —— U8 の反転表で 255 − I、S16 は offset 32768 で負の値を引く、表の外は止まる
  * vx_histogram        —— offset 10・range 40・4 升: 10→0、19→0、20→1、49→3、範囲外 9 と 50 は数えない
  * vx_nonlinear_filter —— median / min / max を十字マスク・replicate で scipy と全画素一致、孤立した 1 点は中央値で消える
  * vx_nonmax_suppression —— 2×2 の平らな頂上は右下の 1 画素だけ残る(前 ≥・後 > の非対称)、S16 の抑制値は INT16_MIN
  * vx_remap            —— 恒等の表で入力そのまま、x + 0.5 の bilinear で坂 2x が 2x + 1、外の隣は constant_value として混ざる
  * vx_warp_affine      —— 逆写像 (x0, y0) = (y, N−1−x) が np.rot90(k=−1) とビット一致、平行移動で外は constant_value
  * vx_warp_perspective —— 3 行目 (0, 0, 1) なら warp_affine とビット一致、行列を 2 倍しても同じ(同次座標)

    py -3.11 examples/gallery_openvx_spec_values.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

import vxcore as VX  # noqa: E402

ROWS: list = []
#: vx_nonlinear_filter の function(vx_non_linear_filter_e)。★引用符つきの "median" を書くと、例の索引
#: (tools/op_example_index.py)が「この例は 2-D の median op を呼んでいる」と数えてしまう
#: (引用符つきの op 名は振り分けの一覧として拾う規則)。ここは fullseye の median op を使わないので 1 本の文字列から分ける。
VX_MEDIAN, VX_MIN, VX_MAX = "median min max".split()


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def demo_gradients() -> None:
    H, W = 12, 16
    y, x = np.mgrid[0:H, 0:W]
    ramp = (3 * x + 5 * y).astype(np.uint8)          # 最大 3·15 + 5·11 = 100
    r = VX.vx_sobel3x3(ramp, border="replicate")
    gx, gy = r["gx"], r["gy"]
    inner = (slice(1, H - 1), slice(1, W - 1))
    check("vx_sobel3x3", "坂 I = 3x + 5y の内側", "gx = 24、gy = 40(S16)",
          f"gx {sorted(set(gx[inner].ravel().tolist()))}、gy {sorted(set(gy[inner].ravel().tolist()))}、{gx.dtype}",
          np.all(gx[inner] == 24) and np.all(gy[inner] == 40) and gx.dtype == np.int16)
    check("vx_sobel3x3", "replicate の左端・上端(片側差分)", "gx = 3·1·4 = 12、gy = 5·1·4 = 20",
          f"gx[5, 0] = {gx[5, 0]}、gy[0, 5] = {gy[0, 5]}", gx[5, 0] == 12 and gy[0, 5] == 20)
    u = VX.vx_sobel3x3(ramp, border="undefined")
    y0, y1, x0, x1 = u["valid"]
    out_zero = np.all(u["gx"][0] == 0) and np.all(u["gx"][:, 0] == 0)
    check("vx_sobel3x3", "border undefined", "valid = (1, H−1, 1, W−1)、内側は replicate と同じ、外は 0",
          f"valid {u['valid']}、外 0 {out_zero}",
          (y0, y1, x0, x1) == (1, H - 1, 1, W - 1) and np.array_equal(u["gx"][inner], gx[inner]) and out_zero)

    gxs = np.array([[3, 1, 2, -32768, 0]], np.int16)
    gys = np.array([[4, 1, 3, -32768, 0]], np.int16)
    mag = VX.vx_magnitude(gxs, gys)
    want = [5, int(math.sqrt(2) + 0.5), int(math.sqrt(13) + 0.5), 32767, 0]
    check("vx_magnitude", "(3,4) (1,1) (2,3) (−32768,−32768) (0,0)", f"uint16(√(x²+y²) + 0.5)、32767 で飽和 = {want}",
          f"{mag.ravel().tolist()}({mag.dtype})", mag.ravel().tolist() == want and mag.dtype == np.int16)

    pgx = np.array([[1, 0, -1, 0, 1, 1000, 0]], np.int16)
    pgy = np.array([[0, 1, 0, -1, -1, -1, 0]], np.int16)
    fl = VX.vx_phase(pgx, pgy, mapping="floor").ravel().tolist()
    ro = VX.vx_phase(pgx, pgy, mapping="round").ravel().tolist()
    check("vx_phase", "0° 90° 180° 270° 315°・2π の手前・(0,0)", "floor: 0 64 128 192 224 255 0",
          str(fl), fl == [0, 64, 128, 192, 224, 255, 0])
    check("vx_phase", "同じ勾配を round で", "0 64 128 192 224 0(2π の手前は 0 に巻く) 0", str(ro),
          ro == [0, 64, 128, 192, 224, 0, 0])


def demo_point_ops() -> None:
    rng = np.random.default_rng(0)
    img = rng.integers(0, 256, (9, 11), dtype=np.uint8)
    inv = VX.vx_table_lookup(img, (255 - np.arange(256)).astype(np.uint8))
    check("vx_table_lookup", "U8、反転の表 table[i] = 255 − i", "255 − I", f"一致 {np.array_equal(inv, 255 - img)}、{inv.dtype}",
          np.array_equal(inv, 255 - img) and inv.dtype == np.uint8)
    s16 = np.array([[-300, -1, 0, 1, 300]], np.int16)
    tbl = (np.arange(65536) - 32768).astype(np.int64)
    tbl = np.clip(np.abs(tbl), 0, 32767).astype(np.int16)        # |v|
    absv = VX.vx_table_lookup(s16, tbl, offset=32768)
    check("vx_table_lookup", "S16、offset 32768 で |v| の表", "[300, 1, 0, 1, 300]", str(absv.ravel().tolist()),
          absv.ravel().tolist() == [300, 1, 0, 1, 300])
    try:
        VX.vx_table_lookup(np.array([[5, 200]], np.uint8), np.zeros(100, np.uint8))
        refused = "止まらなかった"
    except ValueError:
        refused = "ValueError"
    check("vx_table_lookup", "長さ 100 の表で画素 200", "表の外 → 止まる(端に寄せない)", refused, refused == "ValueError")

    h_img = np.array([[9, 10, 19, 20, 49, 50, 35, 35]], np.uint8)
    hist = VX.vx_histogram(h_img, num_bins=4, offset=10, range_=40)
    check("vx_histogram", "画素 9 10 19 20 49 50 35 35、offset 10・range 40・4 升",
          "下端 [10 20 30 40]、数 [2 1 2 1](9 と 50 は数えない)",
          f"下端 {hist[:, 0].tolist()}、数 {hist[:, 1].tolist()}",
          hist[:, 0].tolist() == [10, 20, 30, 40] and hist[:, 1].tolist() == [2, 1, 2, 1])


def demo_neighbourhood() -> None:
    rng = np.random.default_rng(1)
    img = rng.integers(0, 256, (20, 24), dtype=np.uint8)
    cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
    ref = {VX_MEDIAN: ndi.median_filter(img, footprint=cross, mode="nearest"),
           VX_MIN: ndi.grey_erosion(img, footprint=cross, mode="nearest"),
           VX_MAX: ndi.grey_dilation(img, footprint=cross, mode="nearest")}
    same = {f: np.array_equal(VX.vx_nonlinear_filter(img, cross, function=f, border="replicate"), ref[f]) for f in ref}
    check("vx_nonlinear_filter", "十字マスク・replicate、乱数 20×24", "median / min / max が scipy と全画素一致",
          str(same), all(same.values()))
    spike = np.zeros((7, 7), np.uint8)
    spike[3, 3] = 255
    med = VX.vx_nonlinear_filter(spike, np.ones((3, 3), bool), function=VX_MEDIAN, border="replicate")
    check("vx_nonlinear_filter", "孤立した 1 点、3×3 BOX の中央値", "全部 0", f"最大 {int(med.max())}", med.max() == 0)

    a = np.zeros((7, 8), np.uint8)
    a[2:4, 3:5] = 9                                      # 2×2 の平らな頂上
    a[5, 1] = 4                                          # 孤立した低い峰
    nms = VX.vx_nonmax_suppression(a, window=3)
    alive = [tuple(int(v) for v in p) for p in np.argwhere(nms > 0)]
    check("vx_nonmax_suppression", "2×2 の平らな頂上 + 孤立した峰", "残るのは頂上の右下 (3, 4) と峰 (5, 1)",
          str(alive), alive == [(3, 4), (5, 1)] and nms[3, 4] == 9)
    b = a.astype(np.int16)
    nb = VX.vx_nonmax_suppression(b, window=3)
    check("vx_nonmax_suppression", "同じ入力を S16 で", "抑制した画素は INT16_MIN = −32768",
          f"抑制値 {sorted(set(nb[nb != b].tolist()))}", set(nb[nb != b].tolist()) == {-32768})


def demo_geometry() -> None:
    H, W = 10, 12
    y, x = np.mgrid[0:H, 0:W].astype(np.float64)
    ramp = (2 * x).astype(np.uint8)
    idm = VX.vx_remap(ramp, x, y, interpolation="nearest", border="constant")
    check("vx_remap", "恒等の表", "入力とビット一致", f"{np.array_equal(idm, ramp)}", np.array_equal(idm, ramp))
    half = VX.vx_remap(ramp, x + 0.5, y, interpolation="bilinear", border="constant", constant_value=8)
    inner = half[:, :W - 1].astype(int)
    check("vx_remap", "map_x = x + 0.5、bilinear、坂 2x、constant 8", "内側 2x + 1、最後の列は 22 と外の 8 の平均 15",
          f"内側の差 最大 {int(np.abs(inner - (2 * x[:, :W - 1] + 1)).max())}、最後の列 {sorted(set(half[:, W - 1].tolist()))}",
          np.array_equal(inner, 2 * x[:, :W - 1] + 1) and set(half[:, W - 1].tolist()) == {15})
    far = VX.vx_remap(ramp, x + 20.0, y, interpolation="nearest", border="constant", constant_value=8)
    check("vx_remap", "map_x = x + 20(全部が入力の外)", "全画素 constant_value 8", str(sorted(set(far.ravel().tolist()))),
          set(far.ravel().tolist()) == {8})

    N = 9
    rng = np.random.default_rng(2)
    sq = rng.integers(0, 256, (N, N), dtype=np.uint8)
    rot = np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, N - 1.0]])
    r90 = VX.vx_warp_affine(sq, rot, interpolation="nearest", border="constant")
    check("vx_warp_affine", "逆写像 x0 = y、y0 = N−1−x", "np.rot90(k=−1)(時計回り)とビット一致",
          f"{np.array_equal(r90, np.rot90(sq, k=-1))}", np.array_equal(r90, np.rot90(sq, k=-1)))
    shift = np.array([[1.0, 0.0, 3.0], [0.0, 1.0, -2.0]])
    sh = VX.vx_warp_affine(sq, shift, interpolation="nearest", border="constant", constant_value=7)
    ok_in = np.array_equal(sh[2:, :N - 3], sq[:N - 2, 3:])
    ok_out = np.all(sh[:2] == 7) and np.all(sh[:, N - 3:] == 7)
    check("vx_warp_affine", "平行移動 (x0, y0) = (x + 3, y − 2)", "out[y, x] = in[y − 2, x + 3]、はみ出しは 7",
          f"中身 {ok_in}、外 {ok_out}", ok_in and ok_out)

    M3 = np.vstack([rot, [0.0, 0.0, 1.0]])
    pa = VX.vx_warp_perspective(sq, M3, interpolation="nearest", border="constant")
    pb = VX.vx_warp_perspective(sq, 2.0 * M3, interpolation="nearest", border="constant")
    check("vx_warp_perspective", "3 行目 (0, 0, 1) の 90° 回転 / 行列を 2 倍", "warp_affine とビット一致 / 同じ像(同次座標)",
          f"{np.array_equal(pa, r90)} / {np.array_equal(pb, pa)}", np.array_equal(pa, r90) and np.array_equal(pb, pa))
    ramp2 = (10 * x + 5 * y).astype(np.uint8)
    Mp = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.5]])   # 2 倍に拡大した位置を読む
    zoom = VX.vx_warp_perspective(ramp2, Mp, interpolation="nearest", border="constant", constant_value=1)
    yy, xx = np.mgrid[0:H // 2, 0:W // 2]
    check("vx_warp_perspective", "z0 = 0.5 で (2x, 2y) を読む", "左上 (H/2, W/2) は in[2y, 2x]、それより外は 1",
          f"中身 {np.array_equal(zoom[:H // 2, :W // 2], ramp2[2 * yy, 2 * xx])}、外 {sorted(set(zoom[H // 2 + 1:].ravel().tolist()))}",
          np.array_equal(zoom[:H // 2, :W // 2], ramp2[2 * yy, 2 * xx]) and set(zoom[H // 2 + 1:].ravel().tolist()) == {1})


def main() -> int:
    t0 = time.time()
    demo_gradients()
    demo_point_ops()
    demo_neighbourhood()
    demo_geometry()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len({r[0] for r in ROWS})} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
