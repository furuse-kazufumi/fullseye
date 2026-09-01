# -*- coding: utf-8 -*-
"""exhibit_tile — 展示をタイル(コンタクトシート)に束ねる共通部品。

## なぜ要るか

ありふれた静止画の処理結果を 1 枚ずつ原寸で並べると、記事が縦に伸びるだけで
**読む速度が落ちる**。「収縮/膨張/開/閉」のように**並べて比べたいもの**は、
1 枚のタイルにした方が速く伝わるし、スクロールも短くなる。

逆に、**その 1 枚が固有の主張や数字を背負っている展示**(λ/4 で位相シフト法が飛ぶ、
検出開始が光学限界の 1.41 倍、など)はタイルに埋めない。小さくすると読めなくなる
数値が焼き込んであるからで、そこは原寸で置く。

判断の目安 ― 束ね方は 3 つある:

* **タイル(`contact_sheet`)** ― 並べて**比べる**もの。同じ被写体にパラメータ違いを
  当てた比較、族の見本帳。3 枚以上あるとき。
* **フリップブック GIF(`flipbook`)** ― **同じ寸法の絵で工程が進む**もの。
  前処理 → 二値化 → 細線化 → 計測、のように順番に意味があるもの。
  並べるより「切り替わる」方が速く伝わる。
* **原寸で 1 枚** ― 図中の数値が主役、軸ラベル付きのグラフ、前後 2 枚だけの比較。
  小さくすると焼き込んだ数値が読めなくなるものは束ねない。

## 使い方

```python
from exhibit_tile import contact_sheet, save_exhibit

sheet = contact_sheet([img_a, img_b, img_c, img_d], ncols=2,
                      labels=["収縮 面積 -18.4%", "膨張 +21.7%", "開", "閉"],
                      title="形態学の 4 兄弟(同じ図形・同じ構造要素)")
save_exhibit(sheet, "wing2d_morphology_four")   # png + _thumb.jpg
```

決定的である(同じ入力から同じバイト列)。乱数もタイムスタンプも使わない。
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "articles" / "assets"
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\meiryo.ttc",
    r"C:\Windows\Fonts\YuGothM.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
)

BG = (12, 12, 20)
FG = (235, 235, 240)
MUTED = (150, 150, 165)


def _font(size: int):
    from PIL import ImageFont
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    """幅に収まるよう折り返す。**黙って切らない**のが要点。

    日本語には空白が無いので、単語境界ではなく 1 文字ずつ詰めて測る。
    1 文字すら入らない極端な幅のときだけ、そのまま 1 行として返す
    (無限ループにしない)。改行はそこで必ず折る。
    """
    if not text:
        return []
    lines: list[str] = []
    for para in str(text).split("\n"):
        if not para:
            lines.append("")
            continue
        cur = ""
        for ch in para:
            trial = cur + ch
            if draw.textlength(trial, font=font) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines


def _fit_label(draw, text: str, font_size: int, max_w: int) -> tuple[str, object]:
    """ラベルを幅に収める。**入り切らないなら文字を小さくする ―― 切らない。**

    パネルのラベルは 1 行で置きたい(2 行にすると格子が崩れる)ので、折り返す
    かわりにフォントを縮める。それでも入らないところまで来たら、**黙って切らずに
    例外**にする ―― 図の意味を説明する文字が消えるのは、絵が壊れているのと
    同じくらい悪い。実際、機械検査は文字切れを検出できない(壊れていない画像
    として通る)ので、ここで止めるしかない。
    """
    for size in range(font_size, max(9, font_size - 8) - 1, -1):
        font = _font(size)
        if draw.textlength(text, font=font) <= max_w:
            return text, font
    font = _font(max(9, font_size - 8))
    if draw.textlength(text, font=font) > max_w:
        raise ValueError(
            f"label does not fit in {max_w}px even at the smallest size: {text!r} "
            "— shorten it or widen the panel (truncating it silently is not an option)")
    return text, font


def _to_u8(a: np.ndarray) -> np.ndarray:
    """float [0,1] でも uint8 でも受け、RGB uint8 にそろえる。

    NaN を黙って 0 にしない ― 非有限が混ざったら例外にする。図の中で NaN が
    黒として出ると「暗い部分がある絵」に見えてしまい、誰も気づけない。
    """
    arr = np.asarray(a)
    if arr.dtype != np.uint8:
        if not np.all(np.isfinite(arr)):
            raise ValueError("panel contains NaN/Inf — fix the data, do not render it as black")
        arr = np.clip(arr, 0.0, 1.0)
        arr = np.round(arr * 255.0).astype(np.uint8)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    if arr.ndim != 3 or arr.shape[2] not in (3, 4):
        raise ValueError(f"panel must be (H,W), (H,W,3) or (H,W,4); got {arr.shape}")
    return arr[..., :3]


def contact_sheet(panels: list, labels: list | None = None, *, ncols: int = 3,
                  panel_px: int = 380, pad: int = 12, label_h: int = 34,
                  title: str | None = None, title_h: int = 44,
                  font_size: int = 18, title_font_size: int = 24) -> np.ndarray:
    """パネルを格子に並べ、各パネルの下にラベル、上に表題を置いたシートを返す。

    パネルは長辺 ``panel_px`` に合わせて等方に縮小する(拡大はしない ―
    小さい絵を引き伸ばすと、無い解像度があるように見える)。戻り値は float [0,1]。
    """
    from PIL import Image, ImageDraw

    if not panels:
        raise ValueError("contact_sheet needs at least one panel")
    if labels is not None and len(labels) != len(panels):
        raise ValueError(f"labels ({len(labels)}) must match panels ({len(panels)})")

    imgs = []
    for p in panels:
        im = Image.fromarray(_to_u8(p), "RGB")
        scale = min(1.0, panel_px / max(im.width, im.height))
        if scale < 1.0:
            im = im.resize((max(1, round(im.width * scale)),
                            max(1, round(im.height * scale))), Image.LANCZOS)
        imgs.append(im)

    n = len(imgs)
    ncols = max(1, min(ncols, n))
    nrows = (n + ncols - 1) // ncols
    cw = max(im.width for im in imgs)
    row_h = [max(im.height for im in imgs[r * ncols:(r + 1) * ncols]) for r in range(nrows)]
    lh = label_h if labels else 0
    width = ncols * cw + (ncols + 1) * pad

    # 表題は折り返して**必ず全部載せる**。以前はここで中央に 1 行描くだけだったので、
    # 幅を超えた表題が左右で黙って切れていた ―― 図の意味を説明する文字が消えるのは、
    # 絵が壊れているのと同じくらい悪い。
    tfont = _font(title_font_size)
    title_lines: list[str] = []
    if title:
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        title_lines = _wrap(probe, title, tfont, width - 2 * pad)
    line_h = round(title_font_size * 1.35)
    th = (max(title_h, len(title_lines) * line_h + pad) if title_lines else 0)

    height = th + sum(h + lh + pad for h in row_h) + pad
    canvas = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(canvas)

    for i, line in enumerate(title_lines):
        y = (th - len(title_lines) * line_h) // 2 + i * line_h + line_h // 2
        draw.text((width // 2, y), line, fill=FG, font=tfont, anchor="mm")

    font = _font(font_size)
    for i, im in enumerate(imgs):
        r, c = divmod(i, ncols)
        top = th + pad + sum(hh + lh + pad for hh in row_h[:r])
        x = pad + c * (cw + pad) + (cw - im.width) // 2
        y = top + (row_h[r] - im.height) // 2
        canvas.paste(im, (x, y))
        if labels and labels[i]:
            text, lfont = _fit_label(draw, str(labels[i]), font_size, cw)
            draw.text((pad + c * (cw + pad) + cw // 2, top + row_h[r] + lh // 2),
                      text, fill=MUTED, font=lfont, anchor="mm")

    return np.asarray(canvas, np.float64) / 255.0


def save_exhibit(image: np.ndarray, stem: str, *, assets: Path | None = None,
                 thumb_width: int = 720, quality: int = 88) -> dict:
    """``<stem>.png`` とサムネイル ``<stem>_thumb.jpg`` を書き、実測値を返す。

    記事は必ずサムネイルを表示し、クリックで原寸へ飛ばす ― 縦に伸びるのを抑えるため。
    """
    from PIL import Image

    out = Path(assets) if assets is not None else ASSETS
    out.mkdir(parents=True, exist_ok=True)
    im = Image.fromarray(_to_u8(image), "RGB")
    png = out / f"{stem}.png"
    im.save(png, optimize=True)

    scale = min(1.0, thumb_width / im.width)
    thumb_im = im if scale >= 1.0 else im.resize(
        (max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
    thumb = out / f"{stem}_thumb.jpg"
    thumb_im.save(thumb, quality=quality, optimize=True)

    return {
        "png": str(png), "thumb": str(thumb),
        "size": (im.width, im.height),
        "png_bytes": png.stat().st_size, "thumb_bytes": thumb.stat().st_size,
        "png_sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
    }


def flipbook(frames: list, labels: list | None = None, *, title: str | None = None,
             label_h: int = 40, title_h: int = 44, font_size: int = 20,
             title_font_size: int = 24, bar_h: int = 8) -> list[np.ndarray]:
    """**同じ寸法**のフレームを、工程が読めるコマ送りに仕立てて返す。

    各コマに「今どの工程か」のラベルと、``i/N`` を示す進捗バーを焼き込む。
    アニメーションは**止まった 1 コマだけ見ても意味が分かる**必要があるので、
    表題・工程名・進捗を常に画面に置く(GIF は必ず途中で止まって見られる)。

    寸法が揃っていない場合は例外にする ― 揃っていないものをコマ送りにすると、
    工程ではなく「別の絵の羅列」になってしまう。そういうものは ``contact_sheet``。
    """
    from PIL import Image, ImageDraw

    if len(frames) < 2:
        raise ValueError("flipbook needs at least 2 frames (1 frame is a still, not a process)")
    if labels is not None and len(labels) != len(frames):
        raise ValueError(f"labels ({len(labels)}) must match frames ({len(frames)})")

    panels = [_to_u8(f) for f in frames]
    shapes = {p.shape for p in panels}
    if len(shapes) != 1:
        raise ValueError(
            "flipbook needs frames of identical size; got "
            + ", ".join(str(s) for s in sorted(shapes))
            + " — use contact_sheet() for mixed sizes")

    h, w = panels[0].shape[:2]
    th = title_h if title else 0
    lh = label_h if labels else 0
    total_h = th + h + lh + bar_h
    font, tfont = _font(font_size), _font(title_font_size)

    out: list[np.ndarray] = []
    n = len(panels)
    for i, panel in enumerate(panels):
        canvas = Image.new("RGB", (w, total_h), BG)
        draw = ImageDraw.Draw(canvas)
        if title:
            draw.text((w // 2, th // 2), title, fill=FG, font=tfont, anchor="mm")
        canvas.paste(Image.fromarray(panel, "RGB"), (0, th))
        if labels:
            text, lfont = _fit_label(draw, f"{i + 1}/{n}  {labels[i]}", font_size, w - 8)
            draw.text((w // 2, th + h + lh // 2), text, fill=FG, font=lfont, anchor="mm")
        y = total_h - bar_h
        draw.rectangle([0, y, w - 1, total_h - 1], fill=(38, 38, 52))
        draw.rectangle([0, y, max(0, round(w * (i + 1) / n) - 1), total_h - 1], fill=(96, 168, 255))
        out.append(np.asarray(canvas, np.uint8))
    return out


def save_animation(frames: list, stem: str, *, assets: Path | None = None,
                   duration_ms: int = 700, hold_last_ms: int = 1400,
                   loop: int = 0, thumb_width: int = 720, quality: int = 88) -> dict:
    """コマ送りを GIF として書き、**読み戻してフレーム数を照合**した結果を返す。

    GIF は「それらしく書けてしまう」ので、書きっぱなしにしない。サムネイルは
    先頭フレームから作る(記事のサムネが静止画として意味を持つように)。
    """
    from PIL import Image, ImageSequence

    out = Path(assets) if assets is not None else ASSETS / "media"
    out.mkdir(parents=True, exist_ok=True)
    imgs = [Image.fromarray(_to_u8(f), "RGB") for f in frames]
    if len({im.size for im in imgs}) != 1:
        raise ValueError("all animation frames must share one size")

    gif = out / f"{stem}.gif"
    durations = [duration_ms] * len(imgs)
    durations[-1] = hold_last_ms
    imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=durations,
                 loop=loop, optimize=True, disposal=2)

    with Image.open(gif) as re_read:
        n_read = sum(1 for _ in ImageSequence.Iterator(re_read))
    if n_read != len(imgs):
        raise ValueError(f"{gif.name}: wrote {len(imgs)} frames but read back {n_read}")

    thumbs = (ASSETS / "thumbs") if assets is None else out
    thumbs.mkdir(parents=True, exist_ok=True)
    first = imgs[0]
    scale = min(1.0, thumb_width / first.width)
    thumb_im = first if scale >= 1.0 else first.resize(
        (max(1, round(first.width * scale)), max(1, round(first.height * scale))), Image.LANCZOS)
    thumb = thumbs / f"{stem}_thumb.jpg"
    thumb_im.save(thumb, quality=quality, optimize=True)

    return {"gif": str(gif), "thumb": str(thumb), "frames": n_read,
            "size": first.size, "gif_bytes": gif.stat().st_size,
            "gif_sha256": hashlib.sha256(gif.read_bytes()).hexdigest()}


def markdown_animation(stem: str, alt: str, caption: str, *,
                       base: str = "https://raw.githubusercontent.com/furuse-kazufumi/"
                                   "fullseye/master/docs/articles/") -> str:
    """GIF 1 点ぶんの Markdown。GIF は動いてこそなので、直接埋め込む。"""
    return f"![{alt}]({base}assets/media/{stem}.gif)\n\n*↑ {caption}*\n"


def markdown(stem: str, alt: str, caption: str, *,
             base: str = "https://raw.githubusercontent.com/furuse-kazufumi/"
                         "fullseye/master/docs/articles/assets/") -> str:
    """展示 1 点ぶんの Markdown(画像行 + キャプション行)を返す。"""
    return (f"[![{alt}]({base}{stem}_thumb.jpg)]({base}{stem}.png)\n\n"
            f"*↑ {caption}*\n")


def _selftest() -> int:
    """合成パネルでシートを組み、2 回作って決定的であることを確かめる。"""
    import tempfile

    rng = np.random.default_rng(0)
    panels = [np.clip(rng.random((120, 160)) * 0.4 + i * 0.15, 0, 1) for i in range(5)]
    labels = [f"panel {i}" for i in range(5)]
    sheet = contact_sheet(panels, labels, ncols=3, title="selftest")
    with tempfile.TemporaryDirectory() as td:
        a = save_exhibit(sheet, "selftest", assets=Path(td))
        b = save_exhibit(contact_sheet(panels, labels, ncols=3, title="selftest"),
                         "selftest", assets=Path(td))
        same = a["png_sha256"] == b["png_sha256"]
        print(f"size={a['size']} png={a['png_bytes']}B thumb={a['thumb_bytes']}B "
              f"deterministic={same}")
    steps = [np.clip(np.linspace(0, 1, 160)[None, :].repeat(120, 0) + k * 0.1, 0, 1)
             for k in range(4)]
    book = flipbook(steps, ["読み込み", "二値化", "細線化", "計測"], title="工程")
    with tempfile.TemporaryDirectory() as td:
        a = save_animation(book, "selftest", assets=Path(td))
        b = save_animation(flipbook(steps, ["読み込み", "二値化", "細線化", "計測"], title="工程"),
                           "selftest", assets=Path(td))
        anim_same = a["gif_sha256"] == b["gif_sha256"]
        print(f"gif frames={a['frames']} size={a['size']} bytes={a['gif_bytes']} "
              f"deterministic={anim_same}")

    multi = contact_sheet(panels[:2], ncols=2, title="改行を\n含む表題")
    print(f"multiline title: {multi.shape[1]}x{multi.shape[0]} (落ちずに 2 行で組めている)")
    wide = contact_sheet(panels[:2], ncols=2,
                         labels=["とても長いラベルを入れても切られない" * 2, "短い"])
    print(f"long label: {wide.shape[1]}x{wide.shape[0]} (縮小して収めた)")

    for label, call in (
        ("NaN panel", lambda: contact_sheet([np.full((8, 8), np.nan)])),
        ("mixed sizes", lambda: flipbook([np.zeros((4, 4)), np.zeros((4, 5))])),
        ("single frame", lambda: flipbook([np.zeros((4, 4))])),
        ("unfittable label", lambda: contact_sheet(
            [np.zeros((40, 40))], labels=["切られるくらいなら例外にする" * 8])),
    ):
        try:
            call()
        except ValueError as exc:
            print(f"fail-closed on {label}: {exc}")
        else:
            print(f"FAIL: {label} was accepted instead of raising")
            return 1
    return 0 if (same and anim_same) else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
