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
    th = title_h if title else 0

    width = ncols * cw + (ncols + 1) * pad
    height = th + sum(h + lh + pad for h in row_h) + pad
    canvas = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(canvas)

    if title:
        draw.text((width // 2, th // 2), title, fill=FG, font=_font(title_font_size), anchor="mm")

    font = _font(font_size)
    for i, im in enumerate(imgs):
        r, c = divmod(i, ncols)
        top = th + pad + sum(h + lh + pad for h in row_h[:r])
        x = pad + c * (cw + pad) + (cw - im.width) // 2
        y = top + (row_h[r] - im.height) // 2
        canvas.paste(im, (x, y))
        if labels and labels[i]:
            draw.text((pad + c * (cw + pad) + cw // 2, top + row_h[r] + lh // 2),
                      labels[i], fill=MUTED, font=font, anchor="mm")

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
    try:
        contact_sheet([np.full((8, 8), np.nan)])
    except ValueError as exc:
        print(f"fail-closed on NaN: {exc}")
    else:
        print("FAIL: NaN panel was rendered instead of raising")
        return 1
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
