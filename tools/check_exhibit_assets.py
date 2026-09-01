# -*- coding: utf-8 -*-
"""check_exhibit_assets — 機械が作った展示画像を、公開前に点検する。

自動生成した図は**それらしく見えるのが致命的に簡単**なので、目視だけに頼らない。
このツールは記事が参照している画像を全部開いて、次を報告する。

* 寸法・ファイルサイズ・GIF のフレーム数
* **真っ黒/真っ白に潰れていないか**(飽和画素の割合)
* **実質的に単色でないか**(固有色数)― 生成が失敗して塗り潰しになった典型
* **別名で同じ画像を出していないか**(SHA-256 の重複)― 生成器のコピペ事故
* サムネイルの欠落、サムネイルが原寸より大きい、といった取り違え
* 幅が極端(記事で読めない/無駄に重い)

`--strict` を付けると、警告のうち**公開してはいけない類**(単色・全飽和・重複・
サムネ欠落)で exit 1 になる。サイズや幅は環境依存なので既定では警告どまり。

    py -3.11 tools/check_exhibit_assets.py
    py -3.11 tools/check_exhibit_assets.py --strict --prefix wing3d_
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "articles" / "assets"
ARTICLES = [ROOT / "docs" / "articles" / f"fullseye_overview_qiita_{lang}.md"
            for lang in ("ja", "en")]
BASE = "https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/"

_IMG_RE = re.compile(r"!\[[^\]]*\]\((?P<url>[^)\s]+)\)|\]\((?P<href>" + re.escape(BASE) + r"[^)\s]+)\)")

MAX_GIF_BYTES = 3 * 1024 * 1024
MAX_PNG_BYTES = 6 * 1024 * 1024
MIN_WIDTH, MAX_WIDTH = 320, 2600
SATURATED_FRAC = 0.98
MIN_UNIQUE_COLORS = 4


def referenced() -> list[str]:
    """記事が参照している assets 配下の相対パスを、重複なく集める。"""
    rels: set[str] = set()
    for article in ARTICLES:
        if not article.exists():
            continue
        for m in _IMG_RE.finditer(article.read_text(encoding="utf-8")):
            url = m.group("url") or m.group("href") or ""
            if not url.startswith(BASE):
                continue
            rels.add(url[len(BASE):].split("?", 1)[0].split("#", 1)[0])
    return sorted(rels)


def inspect(path: Path) -> dict:
    from PIL import Image, ImageSequence

    info: dict = {"rel": str(path.relative_to(ASSETS)).replace("\\", "/"),
                  "bytes": path.stat().st_size, "notes": [], "hard": []}
    info["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    with Image.open(path) as im:
        info["size"] = (im.width, im.height)
        info["format"] = im.format
        frames = 1
        if getattr(im, "is_animated", False):
            frames = sum(1 for _ in ImageSequence.Iterator(im))
            im.seek(0)
        info["frames"] = frames
        arr = np.asarray(im.convert("RGB"), np.uint8)

    flat = arr.reshape(-1, 3)
    uniq = len(np.unique(flat[:: max(1, len(flat) // 200000)], axis=0))
    info["unique_colors"] = uniq
    dark = float(np.mean(np.all(arr <= 2, axis=-1)))
    light = float(np.mean(np.all(arr >= 253, axis=-1)))
    info["dark_frac"], info["light_frac"] = dark, light

    if uniq < MIN_UNIQUE_COLORS:
        info["hard"].append(f"実質単色({uniq} 色)― 生成が失敗している可能性")
    if dark > SATURATED_FRAC:
        info["hard"].append(f"ほぼ真っ黒({dark:.1%})")
    if light > SATURATED_FRAC:
        info["hard"].append(f"ほぼ真っ白({light:.1%})")
    if info["format"] == "GIF" and info["bytes"] > MAX_GIF_BYTES:
        info["notes"].append(f"GIF が重い({info['bytes']/1e6:.1f} MB)")
    if info["format"] == "PNG" and info["bytes"] > MAX_PNG_BYTES:
        info["notes"].append(f"PNG が重い({info['bytes']/1e6:.1f} MB)")
    if not (MIN_WIDTH <= info["size"][0] <= MAX_WIDTH):
        info["notes"].append(f"幅が極端({info['size'][0]} px)")
    if info["format"] == "GIF" and frames < 2:
        info["notes"].append("GIF なのに 1 フレーム(静止画なら PNG にする)")
    return info


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prefix", default="", help="この接頭辞の画像だけ点検する")
    ap.add_argument("--strict", action="store_true", help="公開不可の警告で exit 1")
    ap.add_argument("--all", action="store_true",
                    help="記事から参照されていない assets も点検する")
    args = ap.parse_args(argv)

    if args.all:
        rels = sorted(str(p.relative_to(ASSETS)).replace("\\", "/")
                      for p in ASSETS.rglob("*")
                      if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif"})
    else:
        rels = referenced()
    rels = [r for r in rels if Path(r).name.startswith(args.prefix)]

    missing: list[str] = []
    infos: list[dict] = []
    for rel in rels:
        path = ASSETS / rel
        if not path.exists():
            missing.append(rel)
            continue
        infos.append(inspect(path))

    by_hash: dict[str, list[str]] = defaultdict(list)
    for i in infos:
        by_hash[i["sha256"]].append(i["rel"])
    dupes = {h: names for h, names in by_hash.items() if len(names) > 1}

    # サムネイルの命名は 2 系統ある(`<stem>_thumb.jpg` と `thumbs/<stem>_720.jpg`)。
    # どちらでも「原寸より小さい派生が同名前置で存在する」ことを見る。
    stems = {Path(i["rel"]).stem for i in infos}
    no_thumb = sorted(
        Path(i["rel"]).stem for i in infos
        if i["rel"].endswith(".png") and not i["rel"].startswith("media/")
        and not Path(i["rel"]).stem.endswith(("_thumb", "_720"))
        and not any(s != Path(i["rel"]).stem and s.startswith(Path(i["rel"]).stem)
                    for s in stems))

    print(f"点検 {len(infos)} 枚(参照 {len(rels)} / 欠落 {len(missing)})\n")
    print(f"{'file':52} {'size':>11} {'MB':>6} {'fr':>3} {'colors':>7}  notes")
    for i in sorted(infos, key=lambda x: x["rel"]):
        flags = "; ".join(i["hard"] + i["notes"])
        print(f"{i['rel'][:52]:52} {i['size'][0]:5}x{i['size'][1]:<5} "
              f"{i['bytes']/1e6:6.2f} {i['frames']:3} {i['unique_colors']:7}  {flags}")

    hard = 0
    if missing:
        hard += len(missing)
        print("\n[公開不可] 記事が参照しているのに存在しない:")
        for rel in missing:
            print(f"  - {rel}")
    if dupes:
        hard += len(dupes)
        print("\n[公開不可] 同じ画像が別名で出ている(生成器のコピペ事故):")
        for names in dupes.values():
            print(f"  - {' == '.join(names)}")
    if no_thumb:
        print("\n[要確認] 原寸 PNG にサムネイルが無い(記事は必ずサムネ + クリックで原寸):")
        for stem in no_thumb:
            print(f"  - {stem}.png")
    broken = [i for i in infos if i["hard"]]
    if broken:
        hard += len(broken)
        print("\n[公開不可] 絵が壊れている可能性:")
        for i in broken:
            print(f"  - {i['rel']}: {'; '.join(i['hard'])}")

    print(f"\n公開不可 {hard} 件 / 要確認 {len(no_thumb)} 件")
    print("※ この点検は「壊れていない」ことしか言えない。**中身が正しいかは目で見ること**。")
    return 1 if (args.strict and hard) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
