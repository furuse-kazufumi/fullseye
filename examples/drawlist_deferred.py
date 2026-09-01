# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""drawlist_deferred — 描画を「ためてから流す」と何ができるようになるか。

    py -3.11 examples/drawlist_deferred.py
    py -3.11 examples/drawlist_deferred.py --save out/drawlist

【用途(分かりやすく)】
``imagedraw`` は呼んだ瞬間に絵にする(即時描画)。``drawlist`` は同じ描画を
**コマンドの列**として持ち、``flush()`` で初めて絵にする(蓄積描画)。絵になる前の
「列」の段階では、まだ検査も差分も変換もできる ―― それが本例の主題。

【この例で示すこと】
1. 蓄積描画の結果が即時描画と **画素完全一致**する(= 蓄積は「足すだけ」)。
2. 文字のはみ出しを **描く前に** 捕まえる(画素からは判定できない不具合)。
3. 図の差分が「なぜ違うか」で取れる(SHA-256 は「変わった」しか言わない)。
4. 同じ列をサムネイル解像度へ流せる。

【グラウンドトゥルース(beat-the-null)】
* 即時 vs 蓄積の最大画素差 == 0(厳密一致)。
* 収まらない文字を積むと必ず例外になり、収まる文字では例外にならない。
* 文字列を 1 つ変えた列の差分がちょうど 1 件で、その場所を指している。
* 2 回流すと SHA-256 が一致する(決定的)。
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import drawlist                            # noqa: E402  (蓄積 → フラッシュ)
import imagedraw as D                      # noqa: E402  (即時のラスタ描画)
from drawlist import DrawList, DrawListError  # noqa: E402

H, W = 180, 260
POLY = [[24, 24], [232, 40], [206, 150], [40, 132]]
MARKS = [[40, 40], [120, 70], [210, 130]]


def _sha(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float64).tobytes()).hexdigest()


def build(dl: DrawList) -> DrawList:
    """展示に使う場面を列として組む(z で重ね順を明示する)。"""
    dl.circle((130, 88), 52, color="reference", fill=True, z=0.0)
    dl.polyline(POLY, color="emphasis", width=2, closed=True, z=1.0)
    dl.line((24, 24), (232, 150), color="wrong", width=2, z=2.0)
    dl.markers(MARKS, color="right", size=6, shape="cross", z=3.0)
    return dl


def immediate() -> np.ndarray:
    """同じ場面を即時描画で(1 行ずつその場で絵にする)。"""
    img = D.new_canvas((H, W, 3))
    img = D.draw_circle(img, (130, 88), 52, color="reference", fill=True)
    img = D.draw_polyline(img, POLY, color="emphasis", width=2, closed=True)
    img = D.draw_line(img, (24, 24), (232, 150), color="wrong", width=2)
    img = D.draw_markers(img, MARKS, color="right", size=6, shape="cross")
    return img


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--save", metavar="PREFIX", help="PNG を <PREFIX>_full.png などへ保存")
    args = ap.parse_args()
    ok = True

    # --- 1. 蓄積は足すだけ ------------------------------------------------- #
    now = immediate()
    later = build(DrawList((H, W, 3))).flush()
    max_diff = float(np.abs(now - later).max())
    same = max_diff == 0.0 and _sha(now) == _sha(later)
    ok &= same
    print(f"1. 即時 vs 蓄積: max|diff| = {max_diff:g}  sha一致 = {_sha(now) == _sha(later)}")

    twice = build(DrawList((H, W, 3))).flush()
    det = _sha(twice) == _sha(later)
    ok &= det
    print(f"   組み直して流し直しても同じバイト列: {det}  sha = {_sha(later)[:16]}…")

    # --- 2. 絵になる前に検査する ------------------------------------------- #
    # 文字の下敷きを描く層(annotate)はまだ無くてよい ―― 検査は列の上で行われるので、
    # ラスタ化に到達する前に落ちる。
    bad = build(DrawList((H, W, 3)))
    bad.text_box((12, 160), "この注記は画像の幅にはどうやっても収まらない長さの文字列です",
                 size=14, z=4.0)
    caught = None
    try:
        bad.flush()
    except DrawListError as exc:
        caught = exc
    ok &= caught is not None and caught.code == "text_does_not_fit"
    print(f"2. はみ出す注記を描く前に捕捉: {caught}")

    fits = build(DrawList((H, W, 3), handlers={"text_box": lambda img, **kw: img}))
    fits.text_box((12, 160), "ok", size=12, z=4.0)
    issues = fits.inspect()
    ok &= issues == []
    print(f"   収まる注記は素通し: 指摘 {len(issues)} 件")

    # --- 3. 図の差分を「なぜ違うか」で取る ---------------------------------- #
    before = build(DrawList((H, W, 3), handlers={"text_box": lambda img, **kw: img}))
    before.text_box((12, 160), "before", size=12, z=4.0)
    after = DrawList.from_json(before.to_json(),
                              handlers={"text_box": lambda img, **kw: img})
    round_trip_exact = after.commands == before.commands
    ok &= round_trip_exact
    after._cmds[4]["args"]["text"] = "after"
    recs = drawlist.diff_command_lists(before, after)
    ok &= len(recs) == 1
    print(f"3. JSON 往復でコマンド列が完全一致: {round_trip_exact}")
    for line in drawlist.format_diff(recs):
        print(f"   構造差分: {line}")

    # --- 4. 同じ列を別解像度へ --------------------------------------------- #
    thumb = build(DrawList((H, W, 3))).scale(0.5).flush()
    big = build(DrawList((H, W, 3))).scale(2.0).flush()
    shapes_ok = thumb.shape == (H // 2, W // 2, 3) and big.shape == (2 * H, 2 * W, 3)
    ok &= shapes_ok
    up = np.repeat(np.repeat(later, 2, axis=0), 2, axis=1)
    mean_abs = float(np.abs(up - big).mean())
    frac = float((np.abs(up - big).max(axis=2) > 1e-9).mean())
    print(f"4. 同じ列から {thumb.shape[:2]} と {big.shape[:2]} を生成: {shapes_ok}")
    print(f"   2倍描画 vs 2倍拡大: mean|diff| = {mean_abs:.5f} / 差のある画素 {frac*100:.2f} %")

    if args.save:
        from imgio import write_image
        for name, arr in (("full", later), ("thumb", thumb), ("big", big)):
            p = Path(f"{args.save}_{name}.png")
            p.parent.mkdir(parents=True, exist_ok=True)
            write_image(str(p), arr)
            print(f"   saved {p}")

    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
