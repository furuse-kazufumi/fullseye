# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""op の図に使う**テスト入力画像**を画像生成 AI に作らせる(1 回きりの取得スクリプト)。

    py -3.11 tools/gen_ai_inputs.py            # 生成して docs/ops/_fig/inputs/ に保存
    py -3.11 tools/gen_ai_inputs.py --dry-run  # プロンプトだけ表示

**なぜ**(ユーザー指示 2026-09-07「外部の画像生成 AI にテスト用の入力画像を作って
もらっても良い」): 合成シーン + skimage の写真 2 枚だけでは、産業検査で実際に出る
被写体(傷のある機械部品・基板・印字ラベル・粒状の食品)での挙動が図に出ない。
実写真は権利の確認が要るが、生成画像なら来歴を丸ごと記録できる。

**規律**:
- 生成は **このスクリプトを人が走らせたときだけ**(CI やテストからは呼ばない。
  網も課金も要る)。結果の PNG は repo に**コミット**し、以後は読むだけ。
- 来歴は ``docs/ops/_fig/inputs/PROVENANCE.json`` に **モデル名・日付・プロンプト・
  サイズ・SHA-256** を残す。図の生成器(``tools/gen_op_figures.py``)はこの JSON に
  載っている画像だけを使う(拾い食いしない)。
- 提供元は 2 つ: OpenAI(``OPENAI_API_KEY``、``gpt-image-1``)→ 使えなければ
  Google Gemini(``GEMINI_API_KEY``、``gemini-2.5-flash-image``)。どちらを使ったかは
  来歴に残る。キーは ``D:/api-keys.json`` / ``C:/dev/api-keys.json`` から読み、
  ログにも出力にも出さない。2026-09-07 の初回は OpenAI 側が残高切れ(429
  ``credit_balance_exhausted``)で Gemini を使った。
- 画像は 256×256 のグレー(``.png``)とカラー(``.color.png``)の 2 通りを保存する。
  図の側は 128 に縮めて使う。
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import hashlib
import io
import json
import os
import sys
import urllib.request

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(_ROOT, "docs", "ops", "_fig", "inputs")
PROVENANCE = os.path.join(OUT_DIR, "PROVENANCE.json")

#: 生成する被写体。名前は図のキャプションに出る(短い英語)。
PROMPTS = {
    "part": ("Top-down photograph of a machined aluminium part on a dark inspection table, "
             "one visible scratch and a small dent on the flat face, even diffuse lighting, "
             "sharp focus, no text, industrial machine-vision style"),
    "pcb": ("Close-up photograph of a green printed circuit board with SMD components, solder "
            "joints and silkscreen markings, straight-on view, even lighting, sharp focus, "
            "no watermark"),
    "label": ("Photograph of a printed product label with black alphanumeric text and a 1-D "
              "barcode on white paper, slightly tilted, even lighting, sharp focus"),
    "beans": ("Top-down photograph of dried coffee beans spread on a light grey conveyor belt, "
              "some beans touching, a few defective dark beans, even lighting, sharp focus"),
}

MODEL = "gpt-image-1"
SIZE = "1024x1024"
GEMINI_MODEL = "gemini-2.5-flash-image"


def _key(name: str = "OPENAI_API_KEY") -> str:
    for p in (r"D:/api-keys.json", r"C:/dev/api-keys.json"):
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                k = json.load(f).get(name)
            if k:
                return k
    raise SystemExit("%s が見つからない(D:/api-keys.json)" % name)


def _generate_gemini(prompt: str, key: str) -> bytes:
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"responseModalities": ["IMAGE"]}}).encode("utf-8")
    url = ("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s"
           % (GEMINI_MODEL, key))
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        res = json.loads(r.read().decode("utf-8"))
    for part in res["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    raise RuntimeError("Gemini の応答に画像が無い")


def _generate_any(prompt: str) -> tuple[bytes, str]:
    """OpenAI → 駄目なら Gemini。使ったモデル名を返す。"""
    try:
        return _generate(prompt, _key("OPENAI_API_KEY")), MODEL
    except (urllib.error.HTTPError, SystemExit) as e:
        print("[ai-inputs]   openai unavailable (%s) -> gemini" % getattr(e, "code", e), flush=True)
    return _generate_gemini(prompt, _key("GEMINI_API_KEY")), GEMINI_MODEL


def _generate(prompt: str, key: str) -> bytes:
    body = json.dumps({"model": MODEL, "prompt": prompt, "size": SIZE, "quality": "low",
                       "n": 1}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations", data=body, method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        res = json.loads(r.read().decode("utf-8"))
    d = res["data"][0]
    if "b64_json" in d:
        return base64.b64decode(d["b64_json"])
    with urllib.request.urlopen(d["url"], timeout=180) as r:      # 旧モデルは URL 返し
        return r.read()


def _save(name: str, png: bytes) -> dict:
    from PIL import Image
    import numpy as np

    im = Image.open(io.BytesIO(png)).convert("RGB").resize((256, 256), Image.LANCZOS)
    os.makedirs(OUT_DIR, exist_ok=True)
    p_color = os.path.join(OUT_DIR, name + ".color.png")
    p_gray = os.path.join(OUT_DIR, name + ".png")
    im.save(p_color, optimize=True)
    im.convert("L").save(p_gray, optimize=True)
    sha = hashlib.sha256(png).hexdigest()
    return {"gray": os.path.basename(p_gray), "color": os.path.basename(p_color),
            "sha256_original": sha, "size_saved": [256, 256]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    a = ap.parse_args()
    names = a.only or list(PROMPTS)
    if a.dry_run:
        for n in names:
            print(n, "->", PROMPTS[n])
        return 0
    prov = {}
    if os.path.exists(PROVENANCE):
        with open(PROVENANCE, encoding="utf-8") as f:
            prov = json.load(f)
    for n in names:
        print("[ai-inputs] generating", n, "...", flush=True)
        png, used = _generate_any(PROMPTS[n])
        rec = _save(n, png)
        rec.update({"model": used, "requested_size": SIZE if used == MODEL else "model default",
                    "quality": "low" if used == MODEL else "default",
                    "prompt": PROMPTS[n],
                    "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                    "license_note": "Generated with an image model (see 'model') by the repository "
                                    "author; used as a synthetic test input. Not a photograph of a real product."})
        prov[n] = rec
        print("[ai-inputs]   saved", rec["gray"], rec["color"])
    with open(PROVENANCE, "w", encoding="utf-8") as f:
        json.dump(prov, f, ensure_ascii=False, indent=1)
    print("[ai-inputs] provenance ->", PROVENANCE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
