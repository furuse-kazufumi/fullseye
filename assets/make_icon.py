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
    py -3.11 C:\\dev\\projects\\imgevolve\\assets\\make_icon.py
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


if __name__ == "__main__":
    main()
