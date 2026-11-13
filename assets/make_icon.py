"""Fullseye ブランドアイコン生成スクリプト (再生成可能).

デザイン
--------
モチーフ = bullseye (的) + 微妙なクロスヘア。
"full" (FullSense) + "bullseye" (的を射る = 正しいアルゴリズムを当てる) の
ブランド由来をそのまま図像化したもの。

配色 (フラット / モダン):
    濃紺  #0D2039  … 地 (基板・計測器の暗部)
    ティール #14B8A6 … 外周リング (画像処理・精度)
    アンバー #F5A524 … 内リング (ヒット/検出)
    ペール  #FFF3D6 … 中心アクセント (命中点)

小サイズ耐性
------------
- 各サイズを個別に 8x スーパーサンプリングで描画 → LANCZOS 縮小 (真のAA)。
- size < 32 では簡略ジオメトリ (太リング 3 バンド、クロスヘア無し) に切替え、
  16px でも潰れないようにする。
- クロスヘアは size >= 48 のみ (それ以下では線が 1px 未満になり濁るため)。

使い方:
    py -3.11 assets/make_icon.py

出力 (正本はこの道具。どの絵も手で差し替えない):
    assets/fullseye.ico / assets/fullseye_256.png
        … 従来の出力 (16〜256 px の ico と 256 px の png)。
    docs/favicon.ico (16/32/48 px)
        … 公開サイト https://furuse.work/ の /favicon.ico。ブラウザが既定で取りに来る場所なので、
          head に link の無い静的な HTML (docs/view2026/viewers など) にも効く。
    docs/apple-touch-icon.png (180 px、不透明)
        … iOS のホーム画面。iOS は透明な所を黒で埋めるので、外周と同じ濃紺の正方形に重ねる。
    docs/assets/img/fullseye_256.png
        … head の rel="icon" (256 px) と、サイトのトップ (docs/README*.md) の題の下のロゴ。
          assets/fullseye_256.png と同じ絵を同じ保存のしかたで書く (バイト一致)。
    サイトの head への配線は docs/_includes/head-custom.html (既定のテーマ primer の口)。
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw

# --- ブランドカラー -------------------------------------------------------
NAVY: Final = (13, 32, 57, 255)  # #0D2039
TEAL: Final = (20, 184, 166, 255)  # #14B8A6
AMBER: Final = (245, 165, 36, 255)  # #F5A524
CORE: Final = (255, 243, 214, 255)  # #FFF3D6

# --- 幾何 (キャンバス幅を 1.0 とした正規化半径) ---------------------------
# 標準 (size >= 32): 濃紺リム → ティール → 濃紺 → アンバー → 濃紺 → 中心
BANDS_STD: Final = [
    (0.500, NAVY),   # 濃紺リム (外周のごく薄い縁)
    (0.465, TEAL),   # ティール外リング
    (0.345, NAVY),
    (0.285, AMBER),  # アンバー内リング
    (0.175, NAVY),
    (0.115, CORE),   # 中心アクセント
]
# 簡略 (size < 32): 3 バンドのみ。16px でも各帯が >= 2px 確保される
BANDS_TINY: Final = [
    (0.500, TEAL),
    (0.330, NAVY),
    (0.210, AMBER),
]

CROSSHAIR_HALF_WIDTH: Final = 0.0225  # 幅 0.045 (キャンバス比)
CROSSHAIR_INNER: Final = 0.115        # 中心アクセントは削らない
CROSSHAIR_OUTER: Final = 0.52         # 外周まで貫通

ICON_SIZES: Final = (16, 32, 48, 64, 128, 256)
SUPERSAMPLE: Final = 8

ASSETS_DIR: Final = Path(__file__).resolve().parent
ICO_PATH: Final = ASSETS_DIR / "fullseye.ico"
PNG_PATH: Final = ASSETS_DIR / "fullseye_256.png"

# --- 公開サイト (GitHub Pages、元は docs/) に置く絵。名前はサイトの根からのパス ---------
SITE_DIR: Final = ASSETS_DIR.parent / "docs"
SITE_FAVICON: Final = "favicon.ico"                  # /favicon.ico
SITE_FAVICON_SIZES: Final = (16, 32, 48)
SITE_TOUCH: Final = "apple-touch-icon.png"           # /apple-touch-icon.png
SITE_TOUCH_SIZE: Final = 180                         # iOS のホーム画面の標準の大きさ
SITE_PNG: Final = "assets/img/fullseye_256.png"      # /assets/img/fullseye_256.png


def _disc(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, color) -> None:
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)


def render(size: int) -> Image.Image:
    """指定サイズのアイコンを 1 枚描画する (高解像度で描いて縮小)。"""
    ss = SUPERSAMPLE
    n = size * ss
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    c = n / 2.0

    tiny = size < 32
    bands = BANDS_TINY if tiny else BANDS_STD

    # 外側 → 内側の順に塗り重ねて同心リングを作る
    for radius, color in bands:
        _disc(draw, c, c, radius * n, color)

    # クロスヘア: 地の色で 4 方向を "切り欠く" reticle 表現 (大サイズのみ)
    if not tiny and size >= 48:
        hw = CROSSHAIR_HALF_WIDTH * n
        r_in = CROSSHAIR_INNER * n
        r_out = CROSSHAIR_OUTER * n
        # 水平 (左右) / 垂直 (上下)
        draw.rectangle([c - r_out, c - hw, c - r_in, c + hw], fill=NAVY)
        draw.rectangle([c + r_in, c - hw, c + r_out, c + hw], fill=NAVY)
        draw.rectangle([c - hw, c - r_out, c + hw, c - r_in], fill=NAVY)
        draw.rectangle([c - hw, c + r_in, c + hw, c + r_out], fill=NAVY)
        # 中心アクセントは切り欠きの影響を受けないよう再描画
        _disc(draw, c, c, BANDS_STD[-1][0] * n, CORE)

    return img.resize((size, size), Image.LANCZOS)


def read_ico_entries(path: Path) -> list[tuple[int, int]]:
    """ICONDIR を直接パースして格納サイズ一覧を返す (0 は 256 を意味する)。"""
    data = path.read_bytes()
    reserved, ico_type, count = struct.unpack_from("<HHH", data, 0)
    if reserved != 0 or ico_type != 1:
        raise ValueError(f"not a valid ICO header: reserved={reserved} type={ico_type}")
    entries: list[tuple[int, int]] = []
    for i in range(count):
        w, h = struct.unpack_from("<BB", data, 6 + i * 16)
        entries.append((w or 256, h or 256))
    return sorted(entries)


def render_touch_icon(size: int = SITE_TOUCH_SIZE) -> Image.Image:
    """apple-touch-icon を描く (不透明の RGB)。

    iOS はホーム画面のアイコンの透明な所を黒で埋めるので、外周の縁と同じ濃紺の正方形に
    重ねて四隅を塗る (角の丸めは iOS がする)。
    """
    bg = Image.new("RGBA", (size, size), NAVY)
    return Image.alpha_composite(bg, render(size)).convert("RGB")


def write_site_icons(images: dict[int, Image.Image], site_dir: Path = SITE_DIR) -> list[Path]:
    """公開サイトの絵 3 枚を ``site_dir`` (既定は docs/) に書き、書いたパスを返す。

    ``images`` は ``render`` で描いたサイズごとの絵 (main と同じ絵を使う)。
    16/32/48 と 256 が要る。
    """
    need = (*SITE_FAVICON_SIZES, 256)
    missing = [s for s in need if s not in images]
    if missing:
        raise ValueError(f"images にサイズが無い: {missing}")
    favicon = site_dir / SITE_FAVICON
    touch = site_dir / SITE_TOUCH
    png = site_dir / SITE_PNG
    png.parent.mkdir(parents=True, exist_ok=True)
    largest = max(SITE_FAVICON_SIZES)
    images[largest].save(
        favicon,
        format="ICO",
        sizes=[(s, s) for s in SITE_FAVICON_SIZES],
        append_images=[images[s] for s in SITE_FAVICON_SIZES if s != largest],
    )
    render_touch_icon().save(touch, format="PNG")
    # assets/fullseye_256.png と同じ絵・同じ保存のしかた (バイト一致)
    images[256].save(png, format="PNG")
    return [favicon, touch, png]


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    images = {s: render(s) for s in ICON_SIZES}
    base = images[max(ICON_SIZES)]
    others = [images[s] for s in ICON_SIZES if s != max(ICON_SIZES)]

    base.save(
        ICO_PATH,
        format="ICO",
        sizes=[(s, s) for s in ICON_SIZES],
        append_images=others,
    )
    base.save(PNG_PATH, format="PNG")

    print(f"ICO : {ICO_PATH}")
    print(f"PNG : {PNG_PATH}")
    print(f"ICO entries (parsed from ICONDIR): {read_ico_entries(ICO_PATH)}")
    with Image.open(ICO_PATH) as im:
        print(f"PIL  ico.sizes(): {sorted(im.ico.sizes())}")
        print(f"PIL  default size: {im.size} mode={im.mode}")

    for path in write_site_icons(images):
        print(f"SITE: {path}")
    print(f"SITE favicon entries (parsed from ICONDIR): {read_ico_entries(SITE_DIR / SITE_FAVICON)}")


if __name__ == "__main__":
    main()
