# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery_drive_world_io — 運転の世界へ外から持ち込むファイル(BVH・イベント列・3DGS)と、無限に続く区画の番号を往復で確かめる

    py -3.11 examples/gallery_drive_world_io.py

【平たく言うと】
運転の世界は外のデータを読む: 人の動き(BVH)、イベントカメラのイベント列、3D Gaussian Splatting の点群。
読み手が列や単位を取り違えると、世界は黙ってもっともらしく壊れる。ここでは**自分で中身の分かる小さな
ファイルを一時ディレクトリに書き**、op で読み戻して「書いたもの = 読んだもの」を確かめる(往復)。
あわせて、無限に続く区画世界(driveinf)の番号付けと乱数を、外の基準(SplitMix64 の公表されたテストベクトル)
と第 2 実装で確かめる。repo の中には何も書かず、ネットワークにも出ない。

【何を期待し、何と比べるか】
  * read_bvh         : 3 コマの手書き BVH。根の Zrotation 90° で子は (1−10, 2, 3)、子の Zrotation 90° も重なって
                       末端は (−9, −3, 3)(閉形式)。骨の長さ 10・5 は全コマで不変。
  * read_events      : 見出しつき .txt(x y t p)・見出しなし .csv(列順 t x y p、中身から列を推定)・名前つき .npz の
                       3 通りで、書いた x・y・t と極性(0 → −1)が一致。
  * events_to_frames : コマの総和 = 極性の総和、コマごとの和 = 時間を 4 等分した自前の数え上げ。
  * gs_read_file     : .splat(32 バイト/個)と INRIA 形式の .ply を書いて読む。位置・大きさは float32 で一致、
                       色 = 0.5 + C0·f_dc(C0 = 1/(2√π))、不透明度 = sigmoid、大きさ = exp、回転は単位四元数に正規化。
                       min_opacity で薄いガウスが落ちる。
  * tile_hash        : SplitMix64 を 4 回(種 → i → j → 塩)。自前の第 2 実装と一致し、その第 2 実装は
                       SplitMix64 の公表ベクトル(状態 0 の最初の 2 出力)で検算する。負の番号も扱う。
  * tile_uniform     : 上位 53 ビット / 2⁵³ —— [0, 1) に入り、2 万個の平均 ≈ 0.5、10 区間の χ² が自由度 9 の 99.9 % 点未満。
  * global_to_tile   : (X, Y) = i·tile + x の往復が厳密、負の座標は 1 つ前の区画へ。
"""
from __future__ import annotations

import math
import os
import struct
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import driveinf as DI  # noqa: E402
import gsplatnp as GS  # noqa: E402
import motionio as MI  # noqa: E402

_ROWS = []
_M64 = (1 << 64) - 1


def check(op, what, expected, got, ok):
    """1 行 = 何を期待し、何が出て、合ったか。"""
    _ROWS.append((op, bool(ok)))
    print("  %-17s %-50s 期待 %-24s 実測 %-24s %s" % (op, what, expected, got, "ok" if ok else "NG"))


_BVH = """HIERARCHY
ROOT Hips
{
  OFFSET 0 0 0
  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
  JOINT Spine
  {
    OFFSET 0 10 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    End Site
    {
      OFFSET 0 5 0
    }
  }
}
MOTION
Frames: 3
Frame Time: 0.0333333
0 0 0 0 0 0 0 0 0
1 2 3 90 0 0 90 0 0
0 0 0 0 90 0 0 0 0
"""


def part_bvh(tmp):
    print("== 1. BVH(人の動き)")
    p = os.path.join(tmp, "two_bones.bvh")
    with open(p, "w", encoding="utf-8") as f:
        f.write(_BVH)
    b = MI.read_bvh(p)
    check("read_bvh", "関節名と親(End Site は <親>_end)", "Hips/Spine/Spine_end −1,0,1",
          "%s %s" % ("/".join(b["names"]), ",".join(str(int(v)) for v in b["parents"])),
          b["names"] == ["Hips", "Spine", "Spine_end"] and b["parents"].tolist() == [-1, 0, 1])
    P = b["positions"]
    want = np.array([[[0, 0, 0], [0, 10, 0], [0, 15, 0]],
                     [[1, 2, 3], [-9, 2, 3], [-9, -3, 3]],
                     [[0, 0, 0], [0, 0, 10], [0, 0, 15]]], np.float64)
    err = float(np.abs(P - want).max())
    check("read_bvh", "3 コマの関節の世界座標(閉形式)", "差 < 1e-12", "%.1e" % err, P.shape == (3, 3, 3) and err < 1e-12)
    l1 = np.linalg.norm(P[:, 1] - P[:, 0], axis=1)
    l2 = np.linalg.norm(P[:, 2] - P[:, 1], axis=1)
    check("read_bvh", "骨の長さは全コマで 10 と 5", "10 / 5", "%s / %s" % (np.round(l1, 12).tolist(), np.round(l2, 12).tolist()),
          np.allclose(l1, 10.0) and np.allclose(l2, 5.0))
    check("read_bvh", "コマの時間", "0.0333333 s", "%g s" % b["frame_time"], b["frame_time"] == 0.0333333)
    bad = os.path.join(tmp, "broken.bvh")
    with open(bad, "w", encoding="utf-8") as f:
        f.write(_BVH.replace("0 0 0 0 90 0 0 0 0\n", "0 0 0 0 90 0 0 0\n"))
    rejected = False
    try:
        MI.read_bvh(bad)
    except ValueError:
        rejected = True
    check("read_bvh", "値が 1 個足りないコマは拒む", "ValueError", "ValueError" if rejected else "通った", rejected)


def part_events(tmp):
    print("== 2. イベントカメラのイベント列")
    rng = np.random.default_rng(20261012)
    n = 400
    x = rng.integers(0, 16, n)
    y = rng.integers(0, 12, n)
    t = np.sort(rng.uniform(0.0, 0.1, n)) + 1e-4           # 秒、整数でない単調列
    p01 = rng.integers(0, 2, n)
    pol = np.where(p01 > 0, 1, -1)
    txt = os.path.join(tmp, "events.txt")
    with open(txt, "w", encoding="utf-8") as f:
        f.write("x y t p\n")
        for a, b_, c, d in zip(x, y, t, p01):
            f.write("%d %d %.17g %d\n" % (a, b_, c, d))
    csv = os.path.join(tmp, "events_noheader.csv")
    with open(csv, "w", encoding="utf-8") as f:
        for a, b_, c, d in zip(x, y, t, p01):
            f.write("%.17g,%d,%d,%d\n" % (c, a, b_, d))
    npz = os.path.join(tmp, "events.npz")
    np.savez(npz, ts=t, col=x, row=y, polarity=p01)
    ev = None
    for path, how in ((txt, "見出しつき .txt"), (csv, "見出しなし .csv(列順 t x y p)"), (npz, "名前つき .npz")):
        e = MI.read_events(path)
        same = (np.array_equal(e["x"], x) and np.array_equal(e["y"], y) and np.array_equal(e["t"], t)
                and np.array_equal(e["p"], pol))
        check("read_events", "%s: x・y・t・極性が往復" % how, "%d 件一致" % n,
              "%d 件%s" % (len(e["x"]), "一致" if same else "不一致"), same)
        if path == csv:
            check("read_events", "見出しなし: 列は中身から推定", "t=0 x=1 y=2 p=3 推定",
                  "t=%d x=%d y=%d p=%d %s" % (e["columns"]["t"], e["columns"]["x"], e["columns"]["y"],
                                               e["columns"]["p"], "推定" if e["guessed"] else ""),
                  e["guessed"] and e["columns"] == {"x": 1, "y": 2, "t": 0, "p": 3})
        ev = e if ev is None else ev
    check("read_events", "像の大きさ = (y の最大 + 1, x の最大 + 1)", "(%d, %d)" % (y.max() + 1, x.max() + 1),
          str(ev["shape"]), ev["shape"] == (int(y.max()) + 1, int(x.max()) + 1))

    T = 4
    fr = MI.events_to_frames(ev, n_frames=T)
    check("events_to_frames", "コマの総和 = 極性の総和", str(int(pol.sum())), "%g" % fr.sum(), fr.sum() == pol.sum())
    edges = t.min() + (t.max() - t.min()) * np.arange(1, T) / T
    k = np.searchsorted(edges, t, side="right")             # 自前の数え上げ(最後の区間は右端を含む)
    want = np.array([pol[k == i].sum() for i in range(T)])
    got = fr.sum(axis=(1, 2))
    check("events_to_frames", "コマごとの和 = 時間を 4 等分した数え上げ", str(want.tolist()), str(got.astype(int).tolist()),
          np.array_equal(got, want) and fr.shape == (T, 12, 16))
    px = (y == 3) & (x == 5)
    check("events_to_frames", "画素 (3, 5) の全コマの和", str(int(pol[px].sum())), "%g" % fr[:, 3, 5].sum(),
          fr[:, 3, 5].sum() == pol[px].sum())


def part_gsplat(tmp):
    print("== 3. 3D Gaussian Splatting のファイル")
    sp = os.path.join(tmp, "two.splat")
    q90 = (math.cos(math.pi / 4), 0.0, 0.0, math.sin(math.pi / 4))      # z 軸まわり 90°(wxyz)
    recs = [((1.5, -2.25, 0.5), (0.01, 0.02, 0.04), (255, 128, 0, 200), (1.0, 0.0, 0.0, 0.0)),
            ((-3.0, 4.0, 1.25), (0.5, 0.25, 0.125), (10, 20, 30, 64), q90)]
    with open(sp, "wb") as f:
        for xyz, sc, rgba, q in recs:
            qb = [min(255, max(0, int(round(v * 128.0 + 128.0)))) for v in q]
            f.write(struct.pack("<3f3f4B4B", *xyz, *sc, *rgba, *qb))
    g = GS.gs_read_file(sp)
    want_xyz = np.array([r[0] for r in recs], np.float32).astype(np.float64)     # 書いたのは float32
    want_sc = np.array([r[1] for r in recs], np.float32).astype(np.float64)
    check("gs_read_file", ".splat: 位置と大きさ = 書いた float32", "厳密に一致",
          "差 %.1e / %.1e" % (np.abs(g["xyz"] - want_xyz).max(), np.abs(g["scale"] - want_sc).max()),
          np.array_equal(g["xyz"], want_xyz) and np.array_equal(g["scale"], want_sc))
    rgba = np.array([r[2] for r in recs], np.float64) / 255.0
    check("gs_read_file", ".splat: 色・不透明度 = u8 / 255", "(1, 0.502, 0) 0.784",
          "%s %.3f" % (np.round(g["rgb"][0], 3).tolist(), g["opacity"][0]),
          np.allclose(g["rgb"], rgba[:, :3]) and np.allclose(g["opacity"], rgba[:, 3]))
    qn = np.linalg.norm(g["rot"], axis=1)
    check("gs_read_file", ".splat: 回転は単位四元数(量子化 1/128 以内)", "(0.707, 0, 0, 0.707)",
          str(np.round(g["rot"][1], 3).tolist()), np.allclose(qn, 1.0) and np.abs(g["rot"][1] - q90).max() < 1.0 / 128
          and np.abs(g["rot"][0] - (1, 0, 0, 0)).max() < 1.0 / 128)
    thin = GS.gs_read_file(sp, min_opacity=0.5)
    check("gs_read_file", "min_opacity 0.5 で α 64/255 のガウスが落ちる", "1 / 2 個",
          "%d / %d 個" % (len(thin["xyz"]), thin["n_total"]), len(thin["xyz"]) == 1 and thin["n_total"] == 2)

    ply = os.path.join(tmp, "two.ply")
    C0 = 0.5 / math.sqrt(math.pi)                           # 0 次の球面調和 Y₀₀ = 1/(2√π)
    rgb = np.array([[0.25, 0.5, 0.75], [0.9, 0.1, 0.4]])
    op = np.array([0.8, 0.3])
    scale = np.array([[0.01, 0.02, 0.04], [0.3, 0.3, 0.3]])
    rot = np.array([[2.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 3.0]])  # わざと正規化していない
    xyz = np.array([[0.0, 1.0, 2.0], [-1.0, -2.0, 0.5]])
    props = (["x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity"] + ["scale_%d" % i for i in range(3)]
             + ["rot_%d" % i for i in range(4)])
    rows = np.column_stack([xyz, (rgb - 0.5) / C0, np.log(op / (1 - op)), np.log(scale), rot]).astype("<f4")
    head = "ply\nformat binary_little_endian 1.0\nelement vertex %d\n%send_header\n" % (
        len(rows), "".join("property float %s\n" % k for k in props))
    with open(ply, "wb") as f:
        f.write(head.encode("ascii"))
        f.write(rows.tobytes())
    h = GS.gs_read_file(ply)
    check("gs_read_file", ".ply: 色 = 0.5 + C0·f_dc", str(rgb[0].tolist()), str(np.round(h["rgb"][0], 6).tolist()),
          h["format"] == "ply" and np.abs(h["rgb"] - rgb).max() < 1e-6)
    check("gs_read_file", ".ply: 不透明度 = sigmoid(logit)", str(op.tolist()), str(np.round(h["opacity"], 6).tolist()),
          np.abs(h["opacity"] - op).max() < 1e-6)
    check("gs_read_file", ".ply: 大きさ = exp(log)", str(scale[0].tolist()), str(np.round(h["scale"][0], 6).tolist()),
          np.abs(h["scale"] - scale).max() < 1e-6)
    check("gs_read_file", ".ply: 回転を単位四元数に正規化", "(1,0,0,0) (0,0,0,1)",
          "%s %s" % (np.round(h["rot"][0], 6).tolist(), np.round(h["rot"][1], 6).tolist()),
          np.allclose(h["rot"], [[1, 0, 0, 0], [0, 0, 0, 1]]))


def _sm64(x):
    """SplitMix64 の 1 段(Steele・Lea・Flood 2014 / Vigna の参照実装と同じ定数)。第 2 実装。"""
    x = (x + 0x9E3779B97F4A7C15) & _M64
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _M64
    return z ^ (z >> 31)


def _tile_hash_ref(i, j, seed, salt):
    h = _sm64(seed & _M64)
    for v in (i, j, salt):
        h = _sm64(h ^ (v & _M64))
    return h


def part_tiles():
    print("== 4. 無限に続く区画(番号・乱数)")
    golden = 0x9E3779B97F4A7C15
    vec_ok = _sm64(0) == 0xE220A8397B1DCDAF and _sm64(golden) == 0x6E789E6AA1B965F4
    check("tile_hash", "第 2 実装の検算: SplitMix64 の公表ベクトル", "e220a839… 6e789e6a…",
          "%016x…" % _sm64(0), vec_ok)
    cases = [(0, 0, 0, 0), (3, -7, 20261001, 0), (-1, -1, 1, 5), (123456, 654321, 2 ** 40 + 7, 2), (-2 ** 40, 9, 42, 1)]
    same = all(DI.tile_hash(*c) == _tile_hash_ref(*c) for c in cases)
    check("tile_hash", "第 2 実装と一致(負の番号を含む 5 通り)", "5 / 5",
          "%d / 5" % sum(DI.tile_hash(*c) == _tile_hash_ref(*c) for c in cases), same)
    check("tile_hash", "塩が違えば別の値・同じ入力なら同じ値", "別 / 同",
          "%s / %s" % ("別" if DI.tile_hash(3, 4, 9, 0) != DI.tile_hash(3, 4, 9, 1) else "同",
                       "同" if DI.tile_hash(3, 4, 9, 0) == DI.tile_hash(3, 4, 9, 0) else "別"),
          DI.tile_hash(3, 4, 9, 0) != DI.tile_hash(3, 4, 9, 1) and DI.tile_hash(3, 4, 9, 0) == DI.tile_hash(3, 4, 9, 0))

    u = np.array([DI.tile_uniform(i, j, 7) for i in range(-100, 100) for j in range(-50, 50)])
    exact = DI.tile_uniform(3, -7, 20261001) == (_tile_hash_ref(3, -7, 20261001, 0) >> 11) / 2.0 ** 53
    check("tile_uniform", "上位 53 ビット / 2⁵³(第 2 実装と一致)", "一致", "一致" if exact else "不一致", exact)
    check("tile_uniform", "2 万個がすべて [0, 1)", "[0, 1)", "[%.4f, %.4f]" % (u.min(), u.max()),
          u.min() >= 0.0 and u.max() < 1.0 and u.size == 20000)
    cnt = np.histogram(u, bins=10, range=(0.0, 1.0))[0]
    chi2 = float(((cnt - u.size / 10) ** 2 / (u.size / 10)).sum())
    check("tile_uniform", "平均 ≈ 0.5・10 区間の χ² < 27.88(df 9 の 99.9 %)", "0.5 ± 0.01 / < 27.88",
          "%.4f / %.2f" % (u.mean(), chi2), abs(u.mean() - 0.5) < 0.01 and chi2 < 27.88)

    i, j, x, y = DI.global_to_tile(1234.5, -0.25, 200.0)
    check("global_to_tile", "(1234.5, −0.25) を 200 m の区画へ", "(6, −1, 34.5, 199.75)",
          "(%d, %d, %g, %g)" % (i, j, x, y), (i, j, x, y) == (6, -1, 34.5, 199.75))
    pts = [(0.0, 0.0), (199.75, 400.0), (-1e6 + 0.5, 3.25e5), (12345.125, -98765.5)]
    back = all(gi * 200.0 + gx == X and gj * 200.0 + gy == Y and 0 <= gx < 200 and 0 <= gy < 200
               for X, Y in pts for gi, gj, gx, gy in [DI.global_to_tile(X, Y, 200.0)])
    check("global_to_tile", "i·tile + x = X の往復(4 点、厳密)", "4 / 4", "一致" if back else "不一致", back)


def run():
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="fullseye_drive_io_") as tmp:
        part_bvh(tmp)
        part_events(tmp)
        part_gsplat(tmp)
    part_tiles()
    return time.perf_counter() - t0


if __name__ == "__main__":
    sec = run()
    ng = [op for op, ok in _ROWS if not ok]
    print("world io: %d op / %d 検査 / NG %d / %.2f s" % (len({op for op, _ in _ROWS}), len(_ROWS), len(ng), sec))
    if ng:
        print("FAILED:", sorted(set(ng)))
        raise SystemExit(1)
    print("PASS")
