# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""記事図: 外観検査 AI の学習画像ジェネレータ(良品 + 不良 5 種)。

ユーザー要望(2026-09-05)「主に外観検査の際の AI 学習で使う画像生成器だと思って下さい」
「良品画像と数種類の不良品画像は見たいですね」への答え。

題材は**画像生成**であって検出ではない。見せたいのは「何を指定すると、どんな画像が
出てくるか」の 3 点:
  1. **欠陥の種類・深さ・寸法・位置を指定して作れる**(上段。良品も同じ手順で出る)。
  2. **同じ欠陥を、照明条件を変えて作り分けられる**(中段)。凹凸だけの欠陥は拡散照明
     では出ず低角照明では出る ―― 学習データには両方の見え方が要る。
  3. **画素完全な真値が生成と同時に出る**(下段)。人手のラベル付けが要らない。

すべて optscene の op だけで作る(私物のレンダラは持たない):
  scene_cylinder / scene_material / random_defects / optical_camera /
  render_optscene / sensor_capture / optscene_mask / optscene_defect_mask。
照明は illumdesign.light_source をそのまま食う。

Run: py -3.11 tools/gen_inspection_gallery.py
出力: docs/articles/assets/inspection_gallery.png
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import illumdesign  # noqa: E402
import optscene as OS  # noqa: E402

OUT = ROOT / "docs" / "articles" / "assets" / "inspection_gallery.png"
FONT = "C:/Windows/Fonts/YuGothB.ttc"
RES = 260

# 部品: ⌀20 mm・厚さ 6 mm のアルミ円盤(旋盤仕上げ)。ステージは黒い樹脂
# 実部品には必ず加工目がある。旋盤の送り 120 um / 谷 1.2 um の同心目を刻む ――
# 加工目こそ検査を難しくしている当人で(旋盤目と細い傷は暗視野で同じように光る)、
# つるつるの面で学習させたモデルは実機で加工目を全部欠陥と呼ぶ
PART = OS.surface_finish(
    OS.scene_cylinder((0.0, 0.0, 3.0), 10.0, 3.0,
                      OS.scene_material("conductor", metal="al", finish="circular")),
    kind="turned", pitch_um=320.0, depth_um=1.8, uv_size_mm=(19.0, 19.0), seed=1)
STAGE = OS.scene_plane(0.0, OS.scene_material("lambert", 0.08))

COLUMNS = [
    ("良品", None),
    ("傷(scratch)", "scratch"),
    ("割れ(crack)", "crack"),
    ("ピット(pits)", "pits"),
    ("しみ(stain)", "stain"),
    ("異物(foreign)", "foreign"),
]
LIGHTS = [
    ("ドーム照明(拡散)", illumdesign.light_source(kind="dome", radius_mm=85.0,
                                                  height_mm=70.0, n=96)),
    ("暗視野(低角リング)", illumdesign.light_source(kind="ring", radius_mm=95.0,
                                                    height_mm=7.0, n=64)),
]


def build(kind, seed):
    """良品(kind=None)か、その種類の欠陥を 1 件だけ持つ不良品を作る。"""
    if kind is None:
        return [PART, STAGE], []
    made = OS.random_defects(PART, count=1, kinds=(kind,), seed=seed,
                             uv_size_mm=(19.0, 19.0), height_um=(20.0, 45.0),
                             albedo_defects=kind != "pits")   # ピットは凹凸だけにする
    return [made["part"]] + made["objects"] + [STAGE], made["labels"]


def spec_text(name, labels, seed):
    """キャプション = **生成の指定内容**。検出の成否ではない。"""
    if not labels:
        return name
    lab = labels[0]
    if lab["kind"] == "foreign":
        return f"{name}  φ{lab['size_mm']:.2f}mm"
    return f"{name}  深さ{lab['height_um']:.0f}µm"


SS = 2          # 画素は面積を積分する。1 画素 1 光線だと縁も加工目も階段状になる


def shot(scene, cam, light, exposure_ms):
    rad = OS.render_optscene(scene, cam, [light], depth=1, supersample=SS)
    return OS.sensor_capture(rad, exposure_ms=exposure_ms, gain_e_per_unit=5.0e4,
                             read_noise_e=2.0, full_well_e=1.0e4, bit_depth=8, seed=7)


def contrast(img, defect, part):
    good = part & ~defect
    if not defect.any() or not good.any():
        return None
    a, b = float(img[defect].mean()), float(img[good].mean())
    return (a - b) / max(b, 1e-9)


def to_rgb(img8):
    return np.repeat(np.asarray(img8, np.uint8).mean(-1, keepdims=True).astype(np.uint8), 3, -1)


def label_overlay(img8, defect, part):
    """真値の重ね描き: 欠陥 = 橙、部品の外形 = 青の輪郭。"""
    out = to_rgb(img8).astype(np.float64) * 0.55
    edge = part ^ np.roll(part, 1, 0) | (part ^ np.roll(part, 1, 1))
    out[edge] = np.array([70, 140, 255])
    out[defect] = np.array([255, 150, 40])
    return np.clip(out, 0, 255).astype(np.uint8)


def auto_exposure(scene, cam, light, target=0.45):
    """良品面の平均が target になる露光 [ms] を求める。

    照明ごとに合わせる。暗視野は原理的に暗いので、ドームと同じ露光にすると段が
    まるごと黒く潰れ、「暗視野では何も見えない」という**逆の結論**が出てしまう。
    実機でも照明を替えたら露光を取り直すので、そちらに合わせる。
    """
    rad = OS.render_optscene(scene, cam, [light], depth=1, supersample=SS).mean(-1)
    part = OS.optscene_mask(scene, cam, 0)
    lvl = float(rad[part].mean())
    return float(np.clip(target * 1.0e4 * 1000.0 / max(lvl * 5.0e4, 1e-30), 0.01, 1e7))


def main() -> int:
    t0 = time.time()
    cam = OS.optical_camera(focal_mm=8.0, pixel_um=3.45, resolution=(RES, RES),
                            working_distance_mm=300.0)
    good, _ = build(None, 0)
    exposures = [auto_exposure(good, cam, light) for _lname, light in LIGHTS]
    ratio = exposures[1] / max(exposures[0], 1e-30)
    print(f"[expose] dome {exposures[0]:.1f} ms / dark-field {exposures[1]:.1f} ms "
          f"({ratio:.0f}x)", flush=True)

    cells, caps = [], []
    for row, (lname, light) in enumerate(LIGHTS):
        for col, (cname, kind) in enumerate(COLUMNS):
            scene, labels = build(kind, seed=100 + col)
            img = shot(scene, cam, light, exposures[row])
            cells.append(to_rgb(img))
            caps.append(spec_text(cname, labels, 100 + col))
    # 3 段目: 真値ラベル(暗視野の絵に重ねる)
    for col, (cname, kind) in enumerate(COLUMNS):
        scene, _labels = build(kind, seed=100 + col)
        img = shot(scene, cam, LIGHTS[1][1], exposures[1])
        part = OS.optscene_mask(scene, cam, 0)
        defect = OS.optscene_defect_mask(scene, cam)
        cells.append(label_overlay(img, defect, part))
        caps.append("真値: 欠陥 0 画素" if not defect.any()
                    else f"真値: 欠陥 {int(defect.sum())} 画素")
    print(f"[render] {len(cells)} cells {time.time() - t0:.0f}s", flush=True)

    # 大量生成が通常運用なので、この設定での実測スループットを測って図に載せる
    bench = OS.inspection_dataset([PART, STAGE], cam, [LIGHTS[0][1]], n=6, seed=1,
                                  jitter_mm=1.0, intensity_jitter=0.2, depth=1,
                                  supersample=SS,
                                  defects=dict(count=2, uv_size_mm=(19.0, 19.0),
                                               kinds=("scratch", "pits", "blob",
                                                      "stain", "foreign")))
    tp = OS.dataset_throughput(bench)
    speed = (f"実測スループット {RES}x{RES} px: {tp['seconds_per_image']:.2f} 秒/枚 = "
             f"{tp['images_per_hour']:,.0f} 枚/時(うちレンダ {tp['render_fraction'] * 100:.0f}%、"
             f"残りは真値 3 枚)")
    print("[bench] " + speed, flush=True)

    T, pad, cap, head = 200, 10, 24, 92
    rows = ["1) 欠陥の種類・深さ・寸法・位置を指定して生成(照明 = ドーム)",
            "2) 同じ欠陥を照明条件だけ変えて生成(照明 = 低角リング)",
            "3) 生成と同時に出る真値ラベル(人手のラベル付けは不要)"]
    title = ImageFont.truetype(FONT, 21)
    sub = ImageFont.truetype(FONT, 14)
    small = ImageFont.truetype(FONT, 14)
    rowf = ImageFont.truetype(FONT, 15)
    RH = T + cap + 26
    cv = Image.new("RGB", (pad + 6 * (T + pad), head + 3 * RH + pad), (17, 19, 23))
    dr = ImageDraw.Draw(cv)
    dr.text((pad, 9), "外観検査 AI の学習画像ジェネレータ — 良品と不良 5 種を、真値つきで作る",
            font=title, fill=(242, 242, 242))
    dr.text((pad, 38), "部品 = 直径 20mm の旋盤仕上げアルミ円盤(送り 320µm/1.8µm)。カメラ f8mm・画素 3.45µm・"
                       f"WD 300mm。露光は照明ごとに取り直す(低角はドームの {ratio:.0f} 倍)。"
                       "キャプションは生成の指定内容",
            font=sub, fill=(196, 198, 205))
    dr.text((pad, 56), speed, font=sub, fill=(150, 200, 255))
    for i, (im, c) in enumerate(zip(cells, caps)):
        r, k = divmod(i, 6)
        y = head + r * RH
        if k == 0:
            dr.text((pad, y - 20), rows[r], font=rowf, fill=(150, 200, 255))
        cv.paste(Image.fromarray(im).resize((T, T), Image.LANCZOS), (pad + k * (T + pad), y))
        dr.text((pad + k * (T + pad), y + T + 4), c, font=small, fill=(228, 228, 230))
    cv.save(OUT, optimize=True)
    print(f"[fig] {OUT} {cv.size} ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
