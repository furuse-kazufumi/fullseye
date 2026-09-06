# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""examplefig — 例(PoC)が **任意で**図を吐き、Studio がそれを拾うための細い層。

## なぜ要るか(2026-09-06、ユーザー「Studio 上で動くような PoC になってる?」)

PoC 30 本は Studio の 2-D Examples ギャラリーに載っていて Run も編集もできるが、
**出力がテキストの表だけ**だった。画像処理ツールキットの IDE で走らせているのに
絵が 1 枚も出ない。かといって PoC に描画を常時入れると、CLI で回したときに
遅くなり、CI でも無駄なファイルが出る。

そこで **環境変数 ``FULLSEYE_FIGURE_DIR`` があるときだけ書く**。

* 未設定(既定)—— :func:`save` は**何もせず ``None`` を返す**。数字も速度も
  1 ビットも変わらない。`py -3.11 examples/poc_*.py` の挙動は従来どおり。
* 設定あり —— そのディレクトリへ ``NN_<name>.png`` を書き、``figures.json`` に
  題と説明を積む。Studio の Figures タブがこれを読んで並べる。

## 使う側

```python
import examplefig as figs

figs.save("speckle", ref, "基準のスペックル(3000 斑点、1σ 1.6 px)")
figs.save("strain", exx, "ε_xx。±2000 µε で塗り分け", signed=True)
```

図は**すべて fullseye 自身の annotate 族で組む**(ユーザー 2026-09-06:
「表や図は Fullseye でも作れるはず」)。多パネルは
:func:`fullseye.annotate_figure_grid`、折れ線は :func:`fullseye.plot_series` +
:func:`fullseye.axes_transform`、表は :func:`fullseye.text_box`。
外部の作図ライブラリは使わない —— 使うと「この道具で何ができるか」を
示すという例の目的が薄れるし、任意依存も増える。

`save` は **(H,W) / (H,W,3) / (H,W,4) の float か uint8** を受ける。
(H,W) は :func:`fullseye.colorize_depth`(``signed=True`` なら発散 LUT)で
塗ってから書く。**書けなかったら黙って諦める**(例の本文は数値を出すのが
仕事で、図が出ないことで落としてはいけない)—— ただし理由は
:func:`errors` に残るので、Studio と門はそれを見られる。
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

#: 図を書き出すディレクトリを指す環境変数。未設定なら :func:`save` は無処理。
ENV_DIR = "FULLSEYE_FIGURE_DIR"

#: 1 回の実行で書く枚数の上限。暴走した例がディスクを埋めないための歯止め。
MAX_FIGURES = 64

_manifest: list[dict] = []
_errors: list[str] = []


def target_dir() -> Path | None:
    """図の出力先(``None`` = 出力しない)。"""
    d = os.environ.get(ENV_DIR, "").strip()
    if not d:
        return None
    try:
        p = Path(d)
        p.mkdir(parents=True, exist_ok=True)
        return p
    except OSError as exc:
        _errors.append("%s を作れない: %s" % (d, exc))
        return None


def enabled() -> bool:
    """図を出す設定になっているか。重い描画を組む前の分岐に使う。"""
    return target_dir() is not None


def errors() -> list[str]:
    """図を書こうとして失敗した理由(例の本文は落とさないので、ここに残す)。"""
    return list(_errors)


def _to_rgb8(v, signed: bool):
    """(H,W) か (H,W,3|4) → uint8 RGB。**値域の伸ばし方をここに 1 か所だけ持つ**。"""
    import fullseye as fs

    a = np.asarray(v)
    if a.dtype == np.uint8 and a.ndim == 3:
        return a[..., :3]
    a = np.asarray(a, np.float64)
    a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    if a.ndim == 3:
        lo, hi = float(a.min()), float(a.max())
        if hi > 1.0 or lo < 0.0:
            a = (a - lo) / (hi - lo) if hi - lo > 1e-12 else np.zeros_like(a)
        return (np.clip(a[..., :3], 0, 1) * 255).astype(np.uint8)
    if a.ndim != 2:
        raise ValueError("examplefig.save: (H,W) か (H,W,3|4) のみ。来たのは %r" % (a.shape,))
    if signed:
        m = float(np.max(np.abs(a))) or 1.0
        lut = np.asarray(fs.diverging_lut(256))
        idx = np.clip(((a / m) * 0.5 + 0.5) * 255.0, 0, 255).astype(np.int32)
        return (np.clip(lut[idx], 0, 1) * 255).astype(np.uint8)
    return np.asarray(fs.colorize_depth(a), np.uint8)[..., :3]


def save(name: str, image, caption: str = "", signed: bool = False) -> Path | None:
    """図を 1 枚書く。``FULLSEYE_FIGURE_DIR`` が無ければ**何もせず ``None``**。

    ``signed=True`` は 0 を中心に塗る(ひずみ・残差・位相差のような符号つきの量)。
    """
    d = target_dir()
    if d is None:
        return None
    if len(_manifest) >= MAX_FIGURES:
        _errors.append("上限 %d 枚に達したので %r は書かなかった" % (MAX_FIGURES, name))
        return None
    try:
        import fullseye as fs

        rgb = _to_rgb8(image, signed)
        path = d / ("%02d_%s.png" % (len(_manifest) + 1, name))
        fs.write_image(str(path), rgb)
        _manifest.append({"file": path.name, "name": name, "caption": caption,
                          "shape": list(np.shape(image))})
        (d / "figures.json").write_text(
            json.dumps(_manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        return path
    except Exception as exc:                            # noqa: BLE001
        # ★例の本文を落とさない。図が出ないのは残念だが、数字は出さねばならない。
        _errors.append("%s: %s: %s" % (name, type(exc).__name__, exc))
        return None


def manifest() -> list[dict]:
    """この実行で書いた図の一覧。"""
    return list(_manifest)


def reset() -> None:
    """状態を捨てる(試験用)。"""
    _manifest.clear()
    _errors.clear()


# --------------------------------------------------------------------------- #
# 図の組み立て —— すべて fullseye の annotate 族で作る                          #
# --------------------------------------------------------------------------- #
def _panel(v, signed=False, title=""):
    """1 枚のパネル(uint8 RGB)。題を左上に置く。"""
    import fullseye as fs

    rgb = _to_rgb8(v, signed).astype(np.float64) / 255.0
    if title:
        rgb = np.asarray(fs.text_box(rgb, title, (6, 6), anchor="lt", font_size=12))
    return rgb


def save_grid(name: str, panels, captions=None, title=None, ncols=2,
              signed=False, caption: str = "") -> Path | None:
    """複数の画像を 1 枚の多パネル図に組んで書く(:func:`annotate_figure_grid`)。

    ``signed`` は 1 個の bool でも、パネルごとの列でもよい。
    """
    if target_dir() is None:
        return None
    try:
        import fullseye as fs

        sg = signed if isinstance(signed, (list, tuple)) else [signed] * len(panels)
        imgs = [_panel(v, bool(s)) for v, s in zip(panels, sg)]
        fig = fs.annotate_figure_grid(imgs, captions=list(captions or []),
                                      ncols=ncols, title=title)
        return save(name, fig, caption)
    except Exception as exc:                            # noqa: BLE001
        _errors.append("%s(grid): %s: %s" % (name, type(exc).__name__, exc))
        return None


def save_plot(name: str, series, xlabel: str = "", ylabel: str = "", title: str = "",
              caption: str = "", size=(560, 360), xlim=None, ylim=None,
              kinds=None) -> Path | None:
    """折れ線・散布のグラフを書く。``series`` = ``[(ラベル, x, y), ...]``。

    軸・目盛り・格子・凡例はすべて fullseye の annotate 族が引く。
    """
    if target_dir() is None:
        return None
    try:
        import fullseye as fs

        w, h = size
        img = np.full((h, w, 3), 1.0)
        xs_all = np.concatenate([np.asarray(x, float).ravel() for _, x, _ in series])
        ys_all = np.concatenate([np.asarray(y, float).ravel() for _, _, y in series])
        xs_all = xs_all[np.isfinite(xs_all)]
        ys_all = ys_all[np.isfinite(ys_all)]
        xl = xlim or (float(xs_all.min()), float(xs_all.max()))
        yl = ylim or (float(ys_all.min()), float(ys_all.max()))
        if xl[1] - xl[0] < 1e-12:
            xl = (xl[0] - 0.5, xl[1] + 0.5)
        pad = 0.06 * (yl[1] - yl[0] or 1.0)
        yl = (yl[0] - pad, yl[1] + pad)
        rect = (72, 44, w - 96, h - 92)
        ax = fs.axes_transform(rect, xl, yl)
        xt, yt = fs.nice_ticks(xl[0], xl[1], 6), fs.nice_ticks(yl[0], yl[1], 5)
        img = np.asarray(fs.grid_lines(img, ax, xticks=xt, yticks=yt, alpha=0.25))
        img = np.asarray(fs.axes_frame(img, ax, width=1))
        img = np.asarray(fs.ticks(img, ax, xticks=xt, yticks=yt, tick_len=5, font_size=10))
        colours = ("reference", "emphasis", "accent", "neutral", "caution")
        legend = []
        for k, (label, x, y) in enumerate(series):
            c = colours[k % len(colours)]
            kind = (kinds[k] if kinds else "line")
            img = np.asarray(fs.plot_series(img, ax, np.asarray(x, float),
                                            np.asarray(y, float), kind=kind,
                                            color=c, width=2, marker_size=3))
            legend.append((c, label))
        if len(legend) > 1:
            img = np.asarray(fs.legend_box(img, legend, (w - 14, 50), anchor="rt",
                                           markers=True, font_size=11, swatch=11, pad=6))
        head = title or name
        img = np.asarray(fs.text_box(img, head, (10, 8), anchor="lt", font_size=13))
        foot = (xlabel + ("   |   " if xlabel and ylabel else "") + ylabel).strip()
        if foot:
            img = np.asarray(fs.text_box(img, foot, (10, h - 10), anchor="lb", font_size=11))
        return save(name, img, caption)
    except Exception as exc:                            # noqa: BLE001
        _errors.append("%s(plot): %s: %s" % (name, type(exc).__name__, exc))
        return None


def save_table(name: str, header, rows, title: str = "", caption: str = "",
               col_w=110, row_h=24) -> Path | None:
    """数表を**画像として**書く。桁を揃えて等幅に並べる。

    「表も Fullseye で作れる」——`text_box` を格子状に置くだけ。値の整形は
    呼び手の責任(``rows`` は文字列の列で渡す)。
    """
    if target_dir() is None:
        return None
    try:
        import fullseye as fs

        ncol = len(header)
        w = 24 + col_w * ncol
        h = 56 + row_h * (len(rows) + 1)
        img = np.full((h, w, 3), 1.0)
        if title:
            img = np.asarray(fs.text_box(img, title, (12, 8), anchor="lt", font_size=13))
        y0 = 40
        for j, cell in enumerate(header):
            img = np.asarray(fs.text_box(img, str(cell), (14 + col_w * j, y0),
                                         anchor="lt", font_size=11, color="emphasis"))
        for i, row in enumerate(rows):
            for j, cell in enumerate(row[:ncol]):
                img = np.asarray(fs.text_box(img, str(cell),
                                             (14 + col_w * j, y0 + row_h * (i + 1)),
                                             anchor="lt", font_size=11,
                                             box_alpha=0.0, border=0))
        return save(name, img, caption)
    except Exception as exc:                            # noqa: BLE001
        _errors.append("%s(table): %s: %s" % (name, type(exc).__name__, exc))
        return None
