# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC の結果を「触って見る」ための、1 枚の HTML ビューアを作る(公開 API。標準ライブラリ + numpy だけ)。

    import fullseye as fs
    spec = fs.viewer_spec("my_poc", title=..., subtitle=..., hint=..., tabs=[fs.viewer_points_tab(...), ...])
    fs.write_viewer(spec, "out/my_poc.html")

    py -3.11 pocviewer.py spec.json out.html     # JSON の仕様から(配列は入れ子の list)

出力は **自己完結した 1 ファイル**(暗色、素の WebGL と 2-D canvas、ライブラリ無し、外部 URL 読み込み
無し)。``file://`` でも iPhone の Safari でも動く。見た目と操作は ``walk_series_viewer.html``
(歩行の系譜)に倣う:

* **タブ** —— 同じ課題を違う方法で試した記録。各タブに **正直なバッジ**・短い説明・実測の数字。
* **3-D** —— ドラッグで回す / ホイールとピンチで拡大 / 視点ボタン / 再生(ターンテーブル)/ 時間つまみ / 速度。
* **2-D 動画** —— コマ送り、重ねた枠(真値と推定)、時系列グラフ(しきい値の線つき)。
* **動く 3-D** —— 物体ごとの剛体姿勢をコマごとに再生(残像の軌跡・点群の時系列・段の区切り・
  同じ時間軸で並ぶ 2-D の画像列と時系列)。再生 / コマ送り・戻し / 段へのジャンプ / 速度 0.25〜4 倍 /
  ループ / カメラの追従(平滑化して揺らさない)。
* **ja / en の切り替え**(既定は ja)。すべての文字列は仕様側が両言語で渡す。

バッジは 3 種に固定する(Fullseye の流儀: 成功だけを並べない):

* ``passed`` 「門を通った」 —— その方法が、自分の門(合否の検査)を通った。
* ``limit`` 「限界を見せる」 —— 壊れ方を正直に見せるための回。
* ``null``  「何もしない場合」 —— 比べるための零点(何もしない/素朴にやる)。

仕様 (spec) の形
----------------
::

    spec = {
      "id": "poc_xxx",
      "title": {"ja": ..., "en": ...}, "subtitle": {...}, "hint": {...},
      "credit": {...},                         # 任意。出典・謝辞・改変の記述(ページ下部)
      "tabs": [{
        "id": "a", "label": {...}, "badge": "passed" | "limit" | "null",
        "text": {...},                         # 短い正直な説明
        "numbers": [{"label": {...}, "value": "81.7 µm" | {"ja":..., "en":...}}, ...],
        "kind": "mesh" | "points" | "frames" | "split" | "anim3d",
        ...ペイロード(下)...
      }]
    }

ペイロード
~~~~~~~~~~
``mesh`` 三角形メッシュ + 頂点ごとの値の色 + カラーバー
    ``pos`` (N,3) / ``faces`` (M,3) int / ``val`` (N,) / ``cbar`` ``{lo, hi, unit, cmap, label}``
``points`` 点群(点ごとの値の色 + カラーバー、または点ごとの RGB)
    ``pos`` (N,3) / ``val`` (N,) + ``cbar``、または ``rgb`` (N,3) uint8。
    任意: ``ghost`` (K,3)(灰色の参照点群。位置合わせのずれを見せる)/ ``point_size``(世界単位)
``frames`` 2-D の画像列 + 重ねる枠 + 時系列
    ``frames`` (T,H,W) か (T,H,W,3)(uint8、または 0..1 の float)/ ``dt``(秒)/
    ``boxes`` ``[{label, color, xy (T,2), size [w,h], flag (T,) 任意, flag_color, flag_text}]`` /
    ``series`` ``[{label, color, values (T,), lo, hi, unit, threshold, decimals}]``
    任意: ``png=True`` でコマを無損失の PNG にして埋める(生の u8 より小さいことが多い。間引かない)。
``split`` 前後の画像 + ドラッグで動く分割線
    ``before`` / ``after`` (H,W) か (H,W,3) uint8 / ``label_before`` / ``label_after``
``anim3d`` 動く 3-D(物体ごとのメッシュは 1 回だけ、コマごとには剛体姿勢だけを持つ)
    ``t`` (T,) 狭義の増加(秒)/
    ``bodies`` ``[{name, pos (N,3) 物体のローカル座標, faces (M,3), rgb (3,)|(N,3) か val (N,)(+タブの cbar), label 任意}]`` /
    ``xyz`` (T,B,3) 位置 / ``quat`` (T,B,4) 姿勢の四元数 **(w, x, y, z)**(正規化して w>=0 に揃える)/
    任意: ``trails`` ``[{body, offset (3,) | xyz (T,3), color "#rrggbb", tail 秒(0 = 全履歴), label}]`` /
    ``clouds`` ``[{k コマ, pos (N,3), rgb (N,3) | color, point_size}]``(k から次の雲まで出す)/
    ``events`` ``[{t, label}]``(段の区切り。ジャンプのボタンになる)/ ``series``(frames と同じ形、長さ T)/
    ``panes`` ``[{label, frames (T,H,W[,3]), boxes, png=True}]``(同じ時間軸で並べる 2-D)/
    ``follow``(追従する物体の name。無ければ全物体の重心)/ ``cbar``

共通の任意項目: ``view`` ``{az, el, dist}``(3-D の初期視点。dist は既定距離の倍率)。

データの詰め方 —— **間引かない、量子化する**
--------------------------------------------
位置は軸ごとに uint16(最小値と範囲から等間隔。刻み = 範囲 / 65535)、値は uint16(カラーバーの
範囲でクリップ。色が飽和するのと同じ範囲)、四元数は int16(刻み 1/32767)、画像と索引は無損失の整数
(画像は無損失の PNG も選べる)。点を減らすことはしない
(見せたい欠陥を消さないため)。同じ配列は内容のハッシュで 1 本にまとめる(タブ間で位置を共有)。
:func:`_decode_array` が Python 側の逆変換で、テストは「戻した値が量子化の刻みの半分以内」を確かめる。

★fail-closed: NaN / inf、両言語がそろわない文字列、未知のバッジ・種類、範囲外の索引、
ノルム 0 の四元数、コマ数 T の不一致、未知の色指定は、黙って通さず ``ValueError`` で止める。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import struct
import sys
import zlib
from pathlib import Path
from typing import Any

import numpy as np

#: 対応する言語(この順)。``write_viewer(lang=...)`` に渡せるのはこの中だけ。
LANGS = ("ja", "en", "zh", "tw", "ko", "de", "hi", "fr")
#: 言語の自称(切り替えの選択肢に出す)。
LANG_NAMES = {"ja": "日本語", "en": "English", "zh": "简体中文", "tw": "繁體中文", "ko": "한국어",
              "de": "Deutsch", "hi": "हिन्दी", "fr": "Français"}
KINDS = ("mesh", "points", "frames", "split", "anim3d")


def _t(ja, en, zh, tw, ko, de, hi, fr):
    return dict(zip(LANGS, (ja, en, zh, tw, ko, de, hi, fr)))


#: タブのバッジ(8 言語)。
BADGES: dict[str, dict[str, str]] = {
    "passed": _t("門を通った", "Passed its gates", "通过了检验", "通過了檢驗", "검증을 통과",
                 "Prüfung bestanden", "जाँच पास की", "Contrôles réussis"),
    "limit": _t("限界を見せる", "Shows the limit", "展示极限", "展示極限", "한계를 보여줌",
                "Zeigt die Grenze", "सीमा दिखाता है", "Montre la limite"),
    "null": _t("何もしない場合", "Doing nothing", "什么都不做时", "什麼都不做時", "아무것도 안 할 때",
               "Ohne Maßnahme", "कुछ न करने पर", "Sans rien faire"),
}

#: ページの固定文字列(8 言語)。仕様のものではなく、ビューアの操作系。
UI: dict[str, dict[str, str]] = {
    "front": _t("正面", "Front", "正面", "正面", "정면", "Vorne", "सामने", "Face"),
    "side": _t("真横", "Side", "侧面", "側面", "측면", "Seite", "बगल", "Côté"),
    "iso": _t("斜め", "Oblique", "斜视", "斜視", "사선", "Schräg", "तिरछा", "Oblique"),
    "top": _t("俯瞰", "Top", "俯视", "俯視", "위에서", "Oben", "ऊपर से", "Dessus"),
    "play": _t("▶ 再生", "▶ Play", "▶ 播放", "▶ 播放", "▶ 재생", "▶ Abspielen", "▶ चलाएँ", "▶ Lecture"),
    "pause": _t("⏸ 一時停止", "⏸ Pause", "⏸ 暂停", "⏸ 暫停", "⏸ 일시정지", "⏸ Pause", "⏸ रोकें", "⏸ Pause"),
    "speed": _t("速度", "Speed", "速度", "速度", "속도", "Tempo", "गति", "Vitesse"),
    "loop": _t("ループ", "Loop", "循环", "循環", "반복", "Schleife", "दोहराएँ", "Boucle"),
    "nogl": _t("この環境では WebGL を初期化できませんでした。別のブラウザ(Chrome / Edge / Safari の最新版)でお試しください。",
               "WebGL could not be initialised here. Please try a recent Chrome, Edge or Safari.",
               "当前环境无法初始化 WebGL。请使用最新版 Chrome、Edge 或 Safari 重试。",
               "目前環境無法初始化 WebGL。請改用最新版 Chrome、Edge 或 Safari 再試。",
               "이 환경에서는 WebGL을 초기화할 수 없습니다. 최신 Chrome, Edge 또는 Safari로 다시 시도해 주세요.",
               "WebGL konnte hier nicht initialisiert werden. Bitte einen aktuellen Browser (Chrome, Edge oder Safari) verwenden.",
               "यहाँ WebGL शुरू नहीं हो सका। कृपया Chrome, Edge या Safari का नया संस्करण आज़माएँ।",
               "WebGL n'a pas pu être initialisé ici. Essayez une version récente de Chrome, Edge ou Safari."),
    "frame": _t("コマ", "frame", "帧", "影格", "프레임", "Bild", "फ़्रेम", "image"),
    "points": _t("点", "points", "个点", "個點", "개 점", "Punkte", "बिंदु", "points"),
    "verts": _t("頂点", "vertices", "个顶点", "個頂點", "개 꼭짓점", "Eckpunkte", "शीर्ष", "sommets"),
    "drag": _t("ドラッグで回す・ホイール/ピンチで拡大", "Drag to orbit, wheel / pinch to zoom",
               "拖动旋转,滚轮/双指缩放", "拖曳旋轉,滾輪/雙指縮放", "드래그로 회전, 휠/핀치로 확대",
               "Ziehen zum Drehen, Mausrad/Pinch zum Zoomen",
               "खींचकर घुमाएँ, व्हील/पिंच से ज़ूम करें", "Glisser pour tourner, molette/pincement pour zoomer"),
    "split": _t("左右にドラッグして前後を比べる", "Drag left/right to compare", "左右拖动以对比前后",
                "左右拖曳以比較前後", "좌우로 드래그해 전후를 비교", "Nach links/rechts ziehen zum Vergleichen",
                "बाएँ-दाएँ खींचकर पहले-बाद की तुलना करें", "Glisser à gauche ou à droite pour comparer"),
    "above": _t("しきい値以上", "at/above threshold", "不低于阈值", "不低於閾值", "임계값 이상",
                "ab Schwelle", "सीमा या उससे ऊपर", "au-dessus du seuil"),
    "below": _t("しきい値未満", "below threshold", "低于阈值", "低於閾值", "임계값 미만",
                "unter Schwelle", "सीमा से नीचे", "sous le seuil"),
    "azimuth": _t("方位", "azimuth", "方位角", "方位角", "방위각", "Azimut", "दिगंश", "azimut"),
    "back1": _t("◀ 1 コマ戻す", "◀ 1 frame back", "◀ 后退 1 帧", "◀ 倒退 1 格", "◀ 1 프레임 뒤로",
                "◀ 1 Bild zurück", "◀ 1 फ़्रेम पीछे", "◀ 1 image en arrière"),
    "fwd1": _t("1 コマ進める ▶", "1 frame forward ▶", "前进 1 帧 ▶", "前進 1 格 ▶", "1 프레임 앞으로 ▶",
               "1 Bild vor ▶", "1 फ़्रेम आगे ▶", "1 image en avant ▶"),
    "evprev": _t("⏮ 前の段", "⏮ Previous stage", "⏮ 上一阶段", "⏮ 上一階段", "⏮ 이전 단계",
                 "⏮ Vorherige Phase", "⏮ पिछला चरण", "⏮ Étape précédente"),
    "evnext": _t("次の段 ⏭", "Next stage ⏭", "下一阶段 ⏭", "下一階段 ⏭", "다음 단계 ⏭",
                 "Nächste Phase ⏭", "अगला चरण ⏭", "Étape suivante ⏭"),
    "follow": _t("カメラを追従させる", "Camera follows", "镜头跟随物体", "鏡頭跟隨物體", "카메라가 따라감",
                 "Kamera folgt", "कैमरा साथ चले", "Caméra qui suit"),
    "stage": _t("段", "stage", "阶段", "階段", "단계", "Phase", "चरण", "étape"),
    "bodies": _t("物体", "bodies", "个物体", "個物體", "개 물체", "Körper", "वस्तुएँ", "objets"),
}

_MAXV = {"q8": 255, "q16": 65535}


# --------------------------------------------------------------------------- #
# 配列の詰め方                                                                  #
# --------------------------------------------------------------------------- #
def _finite(a: np.ndarray, what: str) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    if not np.isfinite(a).all():
        raise ValueError("%s に NaN / inf がある(黙って通さない)" % what)
    return a


def _encode_array(a, t: str = "q16", lo=None, hi=None, per_axis: bool = False) -> dict:
    """配列を ``{t, shape, lo, hi, b64}`` に詰める。

    ``t``:
      * ``"q16"`` / ``"q8"`` —— 浮動小数を uint16 / uint8 へ等間隔に量子化。``lo`` / ``hi`` を渡せば
        その範囲でクリップ(渡さなければ最小・最大)。``per_axis=True`` なら最後の軸ごとに範囲を持つ。
        復元の誤差は **刻み (hi-lo)/最大値 の半分以内**(クリップした値を除く)。
      * ``"u8"`` / ``"u16"`` / ``"u32"`` —— 整数を無損失で。
      * ``"f32"`` —— float32 のまま。
      * ``"s16"`` —— -1..1 の浮動小数を int16 へ(``rint(x * 32767)``)。四元数の成分用。刻みは 1/32767。
      * ``"png"`` —— (T,H,W) / (T,H,W,3) の uint8 をコマごとの無損失 PNG(base64 の列)に。
    """
    a = np.asarray(a)
    shape = list(a.shape)
    if t in _MAXV:
        x = _finite(a, "量子化する配列")
        maxv = _MAXV[t]
        if per_axis:
            if x.ndim < 1:
                raise ValueError("per_axis には 1 次元以上が要る")
            flat = x.reshape(-1, x.shape[-1])
            los = flat.min(axis=0) if lo is None else np.broadcast_to(np.asarray(lo, float), (flat.shape[1],)).copy()
            his = flat.max(axis=0) if hi is None else np.broadcast_to(np.asarray(hi, float), (flat.shape[1],)).copy()
        else:
            los = np.array([x.min() if lo is None else float(lo)])
            his = np.array([x.max() if hi is None else float(hi)])
        span = np.where(his > los, his - los, 1.0)
        his = np.where(his > los, his, los + 1.0)         # 幅 0 の軸は幅 1 の箱にする(割り算を避ける)
        nax = len(los)
        y = x.reshape(-1, nax) if nax > 1 else x.reshape(-1, 1)
        q = np.rint(np.clip((y - los) / span, 0.0, 1.0) * maxv)
        q = q.astype(np.uint8 if t == "q8" else np.uint16)
        raw = q.tobytes()
        rec = {"t": t, "shape": shape, "lo": [float(v) for v in los], "hi": [float(v) for v in his]}
    elif t in ("u8", "u16", "u32"):
        dt = {"u8": np.uint8, "u16": np.uint16, "u32": np.uint32}[t]
        info = np.iinfo(dt)
        if a.dtype.kind == "f":
            if not np.isfinite(a).all() or not np.array_equal(a, np.rint(a)):
                raise ValueError("整数として詰める配列が整数でない")
        if a.size and (a.min() < info.min or a.max() > info.max):
            raise ValueError("%s に収まらない値がある(最小 %s / 最大 %s)" % (t, a.min(), a.max()))
        raw = np.ascontiguousarray(a.astype(dt)).tobytes()
        rec = {"t": t, "shape": shape}
    elif t == "f32":
        raw = np.ascontiguousarray(_finite(a, "float32 の配列").astype(np.float32)).tobytes()
        rec = {"t": t, "shape": shape}
    elif t == "s16":
        x = _finite(a, "s16 で詰める配列")
        if x.size and np.abs(x).max() > 1.0 + 1e-9:
            raise ValueError("s16 で詰めるのは -1..1 の値だけ(最大 %r)" % float(np.abs(x).max()))
        raw = np.rint(np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        rec = {"t": t, "shape": shape}
    elif t == "png":
        u = np.asarray(a)
        if u.dtype != np.uint8 or u.ndim not in (3, 4) or (u.ndim == 4 and u.shape[3] != 3) or len(u) == 0:
            raise ValueError("png で詰めるのは (T,H,W) か (T,H,W,3) の uint8")
        return {"t": t, "shape": shape,
                "png": [base64.b64encode(_png_encode(f)).decode("ascii") for f in u]}
    else:
        raise ValueError("未知の詰め方: %r" % t)
    rec["b64"] = base64.b64encode(raw).decode("ascii")
    return rec


def _decode_array(rec: dict) -> np.ndarray:
    """:func:`_encode_array` の逆。量子化した配列は float64 で返る(JS 側と同じ式)。"""
    t = rec["t"]
    shape = tuple(rec["shape"])
    if t == "png":
        return np.stack([_png_decode(base64.b64decode(x)) for x in rec["png"]]).reshape(shape)
    raw = base64.b64decode(rec["b64"])
    if t == "s16":
        return (np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32767.0).reshape(shape)
    if t in _MAXV:
        q = np.frombuffer(raw, dtype=np.uint8 if t == "q8" else np.dtype("<u2")).astype(np.float64)
        lo = np.asarray(rec["lo"], float)
        hi = np.asarray(rec["hi"], float)
        nax = len(lo)
        q = q.reshape(-1, nax)
        out = lo + q * (hi - lo) / _MAXV[t]
        return out.reshape(shape)
    dt = {"u8": np.dtype("u1"), "u16": np.dtype("<u2"), "u32": np.dtype("<u4"), "f32": np.dtype("<f4")}[t]
    return np.frombuffer(raw, dtype=dt).reshape(shape).copy()


def _quant_step(rec: dict) -> np.ndarray:
    """量子化した配列の刻み(軸ごと)。復元誤差の上限は刻みの半分。"""
    if rec["t"] == "s16":
        return np.array([1.0 / 32767.0])
    maxv = _MAXV[rec["t"]]
    return (np.asarray(rec["hi"], float) - np.asarray(rec["lo"], float)) / maxv


# --------------------------------------------------------------------------- #
# 無損失 PNG(標準ライブラリの zlib だけ。間引かない・色を減らさない)            #
# --------------------------------------------------------------------------- #
_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _png_chunk(tag: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)


def _png_encode(img) -> bytes:
    """(H,W) か (H,W,3) の uint8 を無損失の PNG のバイト列にする。

    行ごとのフィルタは None / Sub / Up から「符号つきの大きさの和が最小」のものを選ぶ(PNG 仕様の
    推奨ヒューリスティク)。3 種に絞るのは、Python 側の逆変換(:func:`_png_decode`)を numpy で
    素直に書けるようにするため(ブラウザはどのフィルタでも読む)。
    """
    a = np.asarray(img)
    if a.dtype != np.uint8 or a.ndim not in (2, 3) or (a.ndim == 3 and a.shape[2] != 3) or a.size == 0:
        raise ValueError("PNG にする画像は (H,W) か (H,W,3) の uint8")
    H, W = a.shape[:2]
    ch = 1 if a.ndim == 2 else 3
    rows = a.reshape(H, W * ch).astype(np.int16)
    sub = rows.copy()
    sub[:, ch:] -= rows[:, :-ch]
    up = rows.copy()
    up[1:] -= rows[:-1]
    cand = np.stack([rows, sub, up]) & 0xFF                          # (3,H,W*ch) 0..255
    cost = np.minimum(cand, 256 - cand).sum(axis=2)                  # (3,H)
    pick = cost.argmin(axis=0)
    chosen = cand[pick, np.arange(H)]
    raw = np.concatenate([pick.astype(np.uint8)[:, None], chosen.astype(np.uint8)], axis=1).tobytes()
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 0 if ch == 1 else 2, 0, 0, 0)
    return (_PNG_SIG + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(raw, 9))
            + _png_chunk(b"IEND", b""))


def _png_decode(data: bytes) -> np.ndarray:
    """:func:`_png_encode` の逆(8 bit のグレー / RGB、フィルタ 0/1/2、CRC を検査)。"""
    if data[:8] != _PNG_SIG:
        raise ValueError("PNG の署名が無い")
    pos, ihdr, idat = 8, None, []
    while pos + 12 <= len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        tag, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + n]
        if struct.unpack(">I", data[pos + 8 + n:pos + 12 + n])[0] != zlib.crc32(tag + body) & 0xFFFFFFFF:
            raise ValueError("PNG の CRC が合わない(%r)" % tag)
        if tag == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat.append(body)
        elif tag == b"IEND":
            break
        pos += 12 + n
    if ihdr is None:
        raise ValueError("PNG に IHDR が無い")
    W, H, depth, ctype, _c, _f, inter = ihdr
    if depth != 8 or ctype not in (0, 2) or inter:
        raise ValueError("この復号器は 8 bit のグレー / RGB、インタレース無しだけ")
    ch = 1 if ctype == 0 else 3
    raw = np.frombuffer(zlib.decompress(b"".join(idat)), np.uint8).reshape(H, 1 + W * ch)
    out = np.zeros((H, W * ch), np.uint8)
    prev = np.zeros(W * ch, np.int64)
    for y in range(H):
        f, row = int(raw[y, 0]), raw[y, 1:].astype(np.int64)
        if f == 0:
            cur = row
        elif f == 1:
            cur = np.cumsum(row.reshape(W, ch), axis=0).ravel() % 256
        elif f == 2:
            cur = (row + prev) % 256
        else:
            raise ValueError("この復号器はフィルタ 0/1/2 だけ(書く側と同じ): %d" % f)
        out[y] = cur
        prev = cur
    return out.reshape(H, W) if ch == 1 else out.reshape(H, W, 3)


class _Store:
    """配列を内容のハッシュで 1 本にまとめる入れ物(タブ間で同じ位置配列を共有する)。"""

    def __init__(self) -> None:
        self.arrays: dict[str, dict] = {}

    def put(self, a, t: str = "q16", **kw) -> str:
        rec = _encode_array(a, t, **kw)
        h = hashlib.sha1(json.dumps({k: v for k, v in rec.items()}, sort_keys=True).encode()).hexdigest()[:12]
        self.arrays.setdefault(h, rec)
        return h


# --------------------------------------------------------------------------- #
# 仕様の検査と詰め替え                                                          #
# --------------------------------------------------------------------------- #
def _norm_langs(lang) -> tuple:
    """``"ja"`` か ``["ja", "en", ...]`` を検査して tuple に(先頭が既定の言語)。"""
    seq = [lang] if isinstance(lang, str) else list(lang)
    if not seq:
        raise ValueError("lang が空")
    bad = [l for l in seq if l not in LANGS]
    if bad:
        raise ValueError("未対応の言語 %s(対応: %s)" % (bad, ", ".join(LANGS)))
    if len(set(seq)) != len(seq):
        raise ValueError("lang に重複がある: %s" % seq)
    return tuple(seq)


class _Ctx:
    """要求された言語と、足りない訳の集計(最後にまとめて ``ValueError``)。"""

    def __init__(self, langs: tuple) -> None:
        self.langs = langs
        self.missing: list[str] = []


def _bi(x: Any, where: str, ctx: _Ctx) -> dict:
    """要求した言語がそろった文字列にする(``str`` は不可 —— 言語を黙って補わない)。

    足りない鍵は ``ctx.missing`` に溜める(1 回の失敗で全部の欠けを名指しするため)。
    要求していない言語の訳は捨てる(単言語のページに他言語の文字を残さない)。
    """
    out = {}
    for l in ctx.langs:
        v = x.get(l) if isinstance(x, dict) else None
        if v is None or not str(v).strip():
            ctx.missing.append("%s.%s" % (where, l))
        else:
            out[l] = str(v)
    return out


def _num_value(v: Any, where: str, ctx: _Ctx) -> Any:
    if isinstance(v, str):
        if not v.strip():
            raise ValueError("%s: 空の値" % where)
        return v
    return _bi(v, where, ctx)


def _clean_list(v, dec: int = 4) -> list:
    """JSON 用の数のリスト。NaN は null(グラフで途切れる)。"""
    out = []
    for x in np.asarray(v, dtype=np.float64).ravel():
        out.append(None if not np.isfinite(x) else round(float(x), dec))
    return out


def _cbar(c: Any, where: str, ctx: _Ctx) -> dict:
    if not isinstance(c, dict) or "lo" not in c or "hi" not in c:
        raise ValueError("%s: cbar に lo / hi が要る" % where)
    lo, hi = float(c["lo"]), float(c["hi"])
    if not (np.isfinite(lo) and np.isfinite(hi) and hi > lo):
        raise ValueError("%s: cbar の範囲が不正 (%r, %r)" % (where, lo, hi))
    cmap = c.get("cmap", "div")
    if cmap not in ("div", "seq"):
        raise ValueError("%s: cmap は div / seq" % where)
    out = {"lo": lo, "hi": hi, "unit": str(c.get("unit", "")), "cmap": cmap}
    if c.get("label") is not None:
        out["label"] = _bi(c["label"], where + ".cbar.label", ctx)
    return out


def _as_u8(a, where: str) -> np.ndarray:
    a = np.asarray(a)
    if a.dtype == np.uint8:
        return a
    if a.dtype.kind in "iu":                       # JSON 経由の整数の画像は 0..255 とみなす
        if a.size and (a.min() < 0 or a.max() > 255):
            raise ValueError("%s: 整数の画像は 0..255 でなければならない" % where)
        return a.astype(np.uint8)
    x = _finite(a, where)
    if x.min() < -1e-9 or x.max() > 1.0 + 1e-9:
        raise ValueError("%s: float の画像は 0..1 でなければならない" % where)
    return np.rint(np.clip(x, 0.0, 1.0) * 255.0).astype(np.uint8)


def _pack_boxes(raw, T: int, where: str, ctx: _Ctx) -> list:
    """2-D の画像列に重ねる枠(``xy`` (T,2)・任意の ``flag`` (T,))を検査して詰める。"""
    boxes = []
    for j, b in enumerate(raw or []):
        xy = _finite(b.get("xy"), where + ".boxes.xy")
        if xy.shape != (T, 2):
            raise ValueError("%s: boxes[%d].xy は (T,2)" % (where, j))
        box = {"label": _bi(b.get("label"), where + ".boxes.label", ctx), "color": str(b.get("color", "#4fc3f7")),
               "xy": [[round(float(x), 3), round(float(y), 3)] for x, y in xy],
               "size": [float(b["size"][0]), float(b["size"][1])]}
        if b.get("flag") is not None:
            fl = np.asarray(b["flag"]).astype(bool)
            if fl.shape != (T,):
                raise ValueError("%s: boxes[%d].flag は (T,)" % (where, j))
            box["flag"] = [bool(x) for x in fl]
            box["flag_color"] = str(b.get("flag_color", "#ff5252"))
            if b.get("flag_text") is not None:
                box["flag_text"] = _bi(b["flag_text"], where + ".boxes.flag_text", ctx)
        boxes.append(box)
    return boxes


def _pack_series(raw, T: int, where: str, ctx: _Ctx) -> list:
    """時系列グラフ(``values`` (T,)・``lo`` < ``hi``・任意の ``threshold``)を検査して詰める。"""
    series = []
    for j, s in enumerate(raw or []):

        v = np.asarray(s.get("values"), dtype=np.float64)
        if v.shape != (T,):
            raise ValueError("%s: series[%d].values は (T,)" % (where, j))
        se = {"label": _bi(s.get("label"), where + ".series.label", ctx), "color": str(s.get("color", "#ffb74d")),
              "values": _clean_list(v), "lo": float(s.get("lo", 0.0)), "hi": float(s.get("hi", 1.0)),
              "unit": str(s.get("unit", "")), "decimals": int(s.get("decimals", 3))}
        if not se["hi"] > se["lo"]:
            raise ValueError("%s: series[%d] の lo < hi" % (where, j))
        if s.get("threshold") is not None:
            se["threshold"] = float(s["threshold"])
        series.append(se)
    return series


_HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")
_BODY_KEYS = frozenset({"name", "label", "pos", "faces", "rgb", "val", "alpha"})
_TRAIL_KEYS = frozenset({"body", "offset", "xyz", "color", "tail", "label"})
_CLOUD_KEYS = frozenset({"k", "pos", "rgb", "color", "point_size"})
_PANE_KEYS = frozenset({"label", "frames", "boxes", "png"})
_EVENT_KEYS = frozenset({"t", "label"})


def _hexcolor(c, where: str) -> str:
    if not isinstance(c, str) or not _HEX.match(c):
        raise ValueError("%s: 色は '#rrggbb'(未知の色指定は通さない): %r" % (where, c))
    return c


def _keys(d, allowed, where: str) -> dict:
    if not isinstance(d, dict):
        raise ValueError("%s: dict でなければならない(%s)" % (where, type(d).__name__))
    extra = sorted(set(d) - allowed)
    if extra:
        raise ValueError("%s: 未知の鍵 %s(使えるのは %s)" % (where, extra, sorted(allowed)))
    return d


def _real(x, where: str) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float, np.integer, np.floating)) or not np.isfinite(x):
        raise ValueError("%s: 有限の数でなければならない: %r" % (where, x))
    return float(x)


def _alpha(x, where: str) -> float:
    """物体の不透明度。0 < alpha <= 1 の有限の実数だけを通す(bool・文字列・NaN・範囲外は ValueError)。"""
    if isinstance(x, bool) or not isinstance(x, (int, float, np.integer, np.floating)):
        raise ValueError("%s: alpha は 0 < alpha <= 1 の数(%s は通さない): %r" % (where, type(x).__name__, x))
    a = float(x)
    if not np.isfinite(a) or not (0.0 < a <= 1.0):
        raise ValueError("%s: alpha は 0 < alpha <= 1(0 は見えない物体、1 が不透明): %r" % (where, x))
    return a


def _faces(raw, n: int, where: str) -> np.ndarray:
    f = np.asarray(raw)
    if f.ndim != 2 or f.shape[1] != 3 or len(f) == 0 or f.dtype.kind not in "iuf":
        raise ValueError("%s: faces は (M,3) の整数" % where)
    if f.dtype.kind == "f" and (not np.isfinite(f).all() or not np.array_equal(f, np.rint(f))):
        raise ValueError("%s: faces が整数でない" % where)
    if f.min() < 0 or f.max() >= n:
        raise ValueError("%s: faces の索引が範囲外(頂点 %d 個)" % (where, n))
    return f.astype(np.int64)


def _quat_canon(raw, where: str) -> np.ndarray:
    """四元数 (…,4) = (w,x,y,z) を正規化し、符号を揃える(w>0、w=0 なら最初の非零成分を正)。

    q と -q は同じ回転なので、符号を揃えても姿勢は変わらない(量子化の前に揃えると、同じ姿勢が
    同じ整数になる)。ノルムが 0 の四元数は回転を表さないので ``ValueError``。
    """
    q = _finite(raw, where)
    n = np.linalg.norm(q, axis=-1)
    bad = np.argwhere(~(n > 1e-12))
    if bad.size:
        raise ValueError("%s: 四元数のノルムが 0(位置 %s)—— 回転を表さない" % (where, tuple(int(v) for v in bad[0])))
    q = q / n[..., None]
    sg = np.sign(q[..., 0])
    for k in (1, 2, 3):
        sg = np.where(sg == 0, np.sign(q[..., k]), sg)
    return q * sg[..., None]


def _quat_matrix(q: np.ndarray) -> np.ndarray:
    """単位四元数 (…,4) = (w,x,y,z) → 回転行列 (…,3,3)(JS の quatMat と同じ式)。"""
    w, x, y, z = np.moveaxis(np.asarray(q, float), -1, 0)
    m = np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y),
                  2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x),
                  2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], axis=-1)
    return m.reshape(np.shape(q)[:-1] + (3, 3))


def _pack_anim3d(tab: dict, out: dict, store: _Store, where: str, ctx: _Ctx) -> None:
    """kind "anim3d" を検査して詰める(物体のメッシュは 1 回、コマごとは姿勢だけ)。"""
    t = _finite(tab.get("t"), where + ".t")
    if t.ndim != 1 or len(t) < 1:
        raise ValueError("%s: t は (T,)" % where)
    if len(t) > 1 and not (np.diff(t) > 0).all():
        raise ValueError("%s: t は狭義の増加でなければならない" % where)
    T = len(t)
    out["t"] = [float(v) for v in t]
    bodies = tab.get("bodies")
    if not isinstance(bodies, (list, tuple)) or not bodies:
        raise ValueError("%s: bodies が空" % where)
    cb = _cbar(tab["cbar"], where, ctx) if tab.get("cbar") is not None else None
    if cb is not None:
        out["cbar"] = cb
    names: list = []
    packed = []
    for j, b in enumerate(bodies):
        wb = "%s.bodies[%d]" % (where, j)
        _keys(b, _BODY_KEYS, wb)
        name = b.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("%s: name(文字列)が要る" % wb)
        if name in names:
            raise ValueError("%s: name が重複: %r" % (wb, name))
        names.append(name)
        if b.get("pos") is None:
            raise ValueError("%s: pos が要る" % wb)
        pos = _finite(b["pos"], wb + ".pos")
        if pos.ndim != 2 or pos.shape[1] != 3 or len(pos) == 0:
            raise ValueError("%s: pos は (N,3)" % wb)
        faces = _faces(b.get("faces"), len(pos), wb)
        pb: dict[str, Any] = {"name": name, "n": int(len(pos)), "nf": int(len(faces)),
                              "pos": store.put(pos, "q16", per_axis=True),
                              "faces": store.put(faces, "u32" if len(pos) > 65535 else "u16")}
        if b.get("label") is not None:
            pb["label"] = _bi(b["label"], wb + ".label", ctx)
        if "alpha" in b:
            alpha = _alpha(b["alpha"], wb + ".alpha")
            if alpha < 1.0:                              # 1 は既定(不透明)。載せないので出力は今と同じ
                pb["alpha"] = alpha
        has_rgb, has_val = b.get("rgb") is not None, b.get("val") is not None
        if has_rgb == has_val:
            raise ValueError("%s: 色は rgb か val(+タブの cbar)のどちらか 1 つ" % wb)
        if has_rgb:
            rgb = np.asarray(b["rgb"])
            if rgb.shape == (3,):
                pb["rgb1"] = [int(v) for v in _as_u8(rgb, wb + ".rgb")]
            elif rgb.shape == pos.shape:
                pb["rgb"] = store.put(_as_u8(rgb, wb + ".rgb"), "u8")
            else:
                raise ValueError("%s: rgb は (3,) か (N,3)" % wb)
        else:
            if cb is None:
                raise ValueError("%s: val を使うならタブに cbar が要る" % wb)
            val = _finite(b["val"], wb + ".val")
            if val.shape != (len(pos),):
                raise ValueError("%s: val は (N,)" % wb)
            pb["val"] = store.put(val, "q16", lo=cb["lo"], hi=cb["hi"])
        packed.append(pb)
    out["bodies"] = packed
    B = len(packed)
    xyz = _finite(tab.get("xyz"), where + ".xyz")
    if xyz.shape != (T, B, 3):
        raise ValueError("%s: xyz は (T,B,3) = (%d,%d,3) でなければならない(実際 %s)—— T の不一致"
                         % (where, T, B, xyz.shape))
    qraw = np.asarray(tab.get("quat"), dtype=np.float64)
    if qraw.shape != (T, B, 4):
        raise ValueError("%s: quat は (T,B,4) = (%d,%d,4) でなければならない(実際 %s)—— T の不一致"
                         % (where, T, B, qraw.shape))
    quat = _quat_canon(qraw, where + ".quat")
    out["xyz"] = store.put(xyz, "q16", per_axis=True)
    out["quat"] = store.put(quat, "s16")
    if tab.get("follow") is not None:
        if tab["follow"] not in names:
            raise ValueError("%s: follow の物体 %r が bodies に無い" % (where, tab["follow"]))
        out["follow"] = names.index(tab["follow"])
    trails, R = [], None
    for j, tr in enumerate(tab.get("trails") or []):
        wt = "%s.trails[%d]" % (where, j)
        _keys(tr, _TRAIL_KEYS, wt)
        if (tr.get("body") is None) == (tr.get("xyz") is None):
            raise ValueError("%s: body(+offset)か xyz のどちらか 1 つ" % wt)
        if tr.get("body") is not None:
            if tr["body"] not in names:
                raise ValueError("%s: 物体 %r が bodies に無い" % (wt, tr["body"]))
            k = names.index(tr["body"])
            off = _finite(tr.get("offset", (0.0, 0.0, 0.0)), wt + ".offset")
            if off.shape != (3,):
                raise ValueError("%s: offset は (3,)" % wt)
            if R is None:
                R = _quat_matrix(quat)
            p = xyz[:, k] + R[:, k] @ off
        else:
            p = _finite(tr["xyz"], wt + ".xyz")
            if p.shape != (T, 3):
                raise ValueError("%s: xyz は (T,3) = (%d,3)—— T の不一致" % (wt, T))
        tail = _real(tr.get("tail", 0.0), wt + ".tail")
        if tail < 0:
            raise ValueError("%s: tail は 0 以上(0 = 全履歴)" % wt)
        e = {"xyz": store.put(p, "q16", per_axis=True), "color": _hexcolor(tr.get("color", "#ffd54f"), wt),
             "tail": tail}
        if tr.get("label") is not None:
            e["label"] = _bi(tr["label"], wt + ".label", ctx)
        trails.append(e)
    out["trails"] = trails
    clouds, lastk = [], -1
    for j, c in enumerate(tab.get("clouds") or []):
        wc = "%s.clouds[%d]" % (where, j)
        _keys(c, _CLOUD_KEYS, wc)
        k = c.get("k")
        if isinstance(k, bool) or not isinstance(k, (int, np.integer)) or not (0 <= int(k) < T):
            raise ValueError("%s: k はコマの番号 0..%d の整数: %r" % (wc, T - 1, k))
        if int(k) <= lastk:
            raise ValueError("%s: k は狭義の増加(雲は時刻順)" % wc)
        lastk = int(k)
        if c.get("pos") is None:
            raise ValueError("%s: pos が要る" % wc)
        pos = _finite(c["pos"], wc + ".pos")
        if pos.ndim != 2 or pos.shape[1] != 3 or len(pos) == 0:
            raise ValueError("%s: pos は (N,3)" % wc)
        e = {"k": int(k), "n": int(len(pos)), "pos": store.put(pos, "q16", per_axis=True)}
        if c.get("rgb") is not None and c.get("color") is not None:
            raise ValueError("%s: rgb と color は片方だけ" % wc)
        if c.get("rgb") is not None:
            rgb = np.asarray(c["rgb"])
            if rgb.shape != pos.shape:
                raise ValueError("%s: rgb は pos と同じ形" % wc)
            e["rgb"] = store.put(_as_u8(rgb, wc + ".rgb"), "u8")
        else:
            e["color"] = _hexcolor(c.get("color", "#80cbc4"), wc)
        if c.get("point_size") is not None:
            ps = _real(c["point_size"], wc + ".point_size")
            if ps <= 0:
                raise ValueError("%s: point_size は正" % wc)
            e["point_size"] = ps
        clouds.append(e)
    out["clouds"] = clouds
    evs = []
    span_eps = 1e-9 * max(1.0, float(np.abs(t).max()))
    for j, e in enumerate(tab.get("events") or []):
        we = "%s.events[%d]" % (where, j)
        _keys(e, _EVENT_KEYS, we)
        et = _real(e.get("t"), we + ".t")
        if et < t[0] - span_eps or et > t[-1] + span_eps:
            raise ValueError("%s: 段の時刻 %r が t の範囲 [%r, %r] の外" % (we, et, float(t[0]), float(t[-1])))
        k = min(T - 1, int(np.searchsorted(t, et - span_eps, side="left")))
        evs.append({"t": et, "k": k, "label": _bi(e.get("label"), we + ".label", ctx)})
    evs.sort(key=lambda x: x["t"])
    out["events"] = evs
    out["series"] = _pack_series(tab.get("series") or [], T, where, ctx)
    panes = []
    for j, p in enumerate(tab.get("panes") or []):
        wp = "%s.panes[%d]" % (where, j)
        _keys(p, _PANE_KEYS, wp)
        if p.get("frames") is None:
            raise ValueError("%s: frames が要る" % wp)
        fr = _as_u8(p["frames"], wp + ".frames")
        if fr.ndim not in (3, 4) or (fr.ndim == 4 and fr.shape[3] != 3):
            raise ValueError("%s: frames は (T,H,W) か (T,H,W,3)" % wp)
        if len(fr) != T:
            raise ValueError("%s: frames のコマ数 %d が t の %d と違う—— T の不一致" % (wp, len(fr), T))
        panes.append({"label": _bi(p.get("label"), wp + ".label", ctx),
                      "frames": store.put(fr, "png" if p.get("png", True) else "u8"),
                      "boxes": _pack_boxes(p.get("boxes") or [], T, wp, ctx)})
    out["panes"] = panes


def _pack_tab(tab: dict, store: _Store, idx: int, ctx: _Ctx) -> dict:
    where = "tabs[%d]" % idx
    tid = str(tab.get("id", ""))
    if not tid or not all(ch.isalnum() or ch in "_-" for ch in tid):
        raise ValueError("%s: id は英数字と _ - だけ: %r" % (where, tid))
    where = "tab %s" % tid
    if tab.get("badge") not in BADGES:
        raise ValueError("%s: badge は %s のどれか: %r" % (where, sorted(BADGES), tab.get("badge")))
    kind = tab.get("kind")
    if kind not in KINDS:
        raise ValueError("%s: kind は %s のどれか: %r" % (where, KINDS, kind))
    out: dict[str, Any] = {
        "id": tid, "kind": kind, "badge": tab["badge"],
        "label": _bi(tab.get("label"), where + ".label", ctx),
        "text": _bi(tab.get("text"), where + ".text", ctx),
        "numbers": [{"label": _bi(n.get("label"), where + ".numbers.label", ctx),
                     "value": _num_value(n.get("value"), where + ".numbers.value", ctx)}
                    for n in tab.get("numbers", [])],
    }
    if tab.get("view"):
        out["view"] = {k: float(v) for k, v in tab["view"].items() if k in ("az", "el", "dist")}

    if kind in ("mesh", "points"):
        pos = _finite(tab.get("pos"), where + ".pos")
        if pos.ndim != 2 or pos.shape[1] != 3 or len(pos) == 0:
            raise ValueError("%s: pos は (N,3)" % where)
        out["pos"] = store.put(pos, "q16", per_axis=True)
        out["n"] = int(len(pos))
        if kind == "mesh":
            faces = np.asarray(tab.get("faces"))
            if faces.ndim != 2 or faces.shape[1] != 3 or len(faces) == 0:
                raise ValueError("%s: faces は (M,3)" % where)
            if faces.min() < 0 or faces.max() >= len(pos):
                raise ValueError("%s: faces の索引が範囲外" % where)
            out["faces"] = store.put(faces, "u32" if len(pos) > 65535 else "u16")
            out["nf"] = int(len(faces))
        if tab.get("val") is not None:
            cb = _cbar(tab.get("cbar"), where, ctx)
            val = _finite(tab["val"], where + ".val")
            if val.shape != (len(pos),):
                raise ValueError("%s: val は (N,)" % where)
            out["cbar"] = cb
            out["val"] = store.put(val, "q16", lo=cb["lo"], hi=cb["hi"])
        elif kind == "points" and tab.get("rgb") is not None:
            rgb = np.asarray(tab["rgb"])
            if rgb.shape != pos.shape:
                raise ValueError("%s: rgb は pos と同じ形" % where)
            out["rgb"] = store.put(_as_u8(rgb, where + ".rgb"), "u8")
        else:
            raise ValueError("%s: val(+cbar)か rgb が要る" % where)
        if kind == "points":
            if tab.get("ghost") is not None:
                g = _finite(tab["ghost"], where + ".ghost")
                if g.ndim != 2 or g.shape[1] != 3:
                    raise ValueError("%s: ghost は (K,3)" % where)
                out["ghost"] = store.put(g, "q16", per_axis=True)
            if tab.get("point_size") is not None:
                out["point_size"] = float(tab["point_size"])
    elif kind == "frames":
        fr = _as_u8(tab.get("frames"), where + ".frames")
        if fr.ndim not in (3, 4) or (fr.ndim == 4 and fr.shape[3] != 3) or len(fr) < 1:
            raise ValueError("%s: frames は (T,H,W) か (T,H,W,3)" % where)
        T = len(fr)
        out["frames"] = store.put(fr, "png" if tab.get("png") else "u8")
        out["dt"] = float(tab.get("dt", 0.2))
        out["boxes"] = _pack_boxes(tab.get("boxes", []), T, where, ctx)
        out["series"] = _pack_series(tab.get("series", []), T, where, ctx)
    elif kind == "anim3d":
        _pack_anim3d(tab, out, store, where, ctx)
    else:  # split
        b, a = _as_u8(tab.get("before"), where + ".before"), _as_u8(tab.get("after"), where + ".after")
        if b.shape != a.shape or b.ndim not in (2, 3) or (b.ndim == 3 and b.shape[2] != 3):
            raise ValueError("%s: before / after は同じ形の (H,W) か (H,W,3)" % where)
        out["before"] = store.put(b, "u8")
        out["after"] = store.put(a, "u8")
        out["label_before"] = _bi(tab.get("label_before"), where + ".label_before", ctx)
        out["label_after"] = _bi(tab.get("label_after"), where + ".label_after", ctx)
    return out


def _pack_spec(spec: dict, lang="ja") -> dict:
    """仕様を検査して、ページに埋める ``DATA``(JSON にできる dict)にする。

    ``lang`` は ``"ja"`` か ``["ja", "en", ...]``(先頭が既定)。要求した言語が 1 つでも欠けた文字列があれば、
    欠けた鍵を全部並べて ``ValueError``(日本語などへ黙って補わない)。
    """
    langs = _norm_langs(lang)
    ctx = _Ctx(langs)
    tabs = spec.get("tabs")
    if not tabs:
        raise ValueError("tabs が空")
    ids = [t.get("id") for t in tabs]
    if len(ids) != len(set(ids)):
        raise ValueError("タブの id が重複している: %s" % ids)
    store = _Store()
    data: dict[str, Any] = {
        "id": str(spec.get("id", "viewer")), "langs": list(langs),
        "langnames": {l: LANG_NAMES[l] for l in langs},
        "title": _bi(spec.get("title"), "title", ctx),
        "subtitle": _bi(spec.get("subtitle"), "subtitle", ctx),
        "hint": _bi(spec.get("hint"), "hint", ctx),
        "tabs": [_pack_tab(t, store, i, ctx) for i, t in enumerate(tabs)],
    }
    if spec.get("credit") is not None:
        data["credit"] = _bi(spec["credit"], "credit", ctx)
    if ctx.missing:
        raise ValueError("訳が足りない(要求した言語 %s): %s" % (list(langs), ", ".join(ctx.missing)))
    data["badges"] = {k: {l: v[l] for l in langs} for k, v in BADGES.items()}
    data["ui"] = {k: {l: v[l] for l in langs} for k, v in UI.items()}
    data["arrays"] = store.arrays
    return data


# --------------------------------------------------------------------------- #
# ページ                                                                        #
# --------------------------------------------------------------------------- #
_CSS = """
  :root { --bg:#11161c; --panel:#182029; --line:#2a3540; --fg:#e8edf2; --dim:#93a2b1; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font-family:"Segoe UI","Hiragino Sans",Meiryo,sans-serif; -webkit-text-size-adjust:100%; }
  header { padding:16px 18px 8px; display:flex; gap:12px; align-items:flex-start; justify-content:space-between; }
  h1 { font-size:18px; margin:0 0 4px; }
  .sub { font-size:13px; color:var(--dim); line-height:1.6; }
  #lang { flex:none; padding:5px 8px; font-size:13px; background:var(--panel); color:var(--fg); border:1px solid var(--line); border-radius:8px; }
  .tabs { display:flex; flex-wrap:wrap; gap:8px; padding:10px 18px 4px; }
  .tab { padding:8px 13px; border-radius:8px; border:1px solid var(--line);
         background:var(--panel); color:#c8d4df; cursor:pointer; font-size:14px; text-align:left; }
  .tab.on { background:#2c6fb5; border-color:#2c6fb5; color:#fff; font-weight:600; }
  .tab i { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:7px; vertical-align:baseline; }
  .card { margin:8px 18px; padding:10px 14px; background:var(--panel);
          border:1px solid var(--line); border-radius:8px; font-size:13.5px; line-height:1.75; }
  .badge { display:inline-block; padding:2px 9px; border-radius:999px; font-size:12px;
           margin-right:8px; font-weight:600; }
  .passed { background:#1d4e7a; color:#dbeafe; } .passed-dot { background:#5aa9f0; }
  .limit { background:#7a4a1d; color:#fde9d0; } .limit-dot { background:#f0a45a; }
  .null { background:#444c55; color:#e3e8ed; } .null-dot { background:#9aa6b2; }
  .nums { display:flex; flex-wrap:wrap; gap:6px 16px; margin-top:6px; }
  .num { font-variant-numeric:tabular-nums; } .num i { font-style:normal; color:var(--dim); margin-right:6px; }
  #wrap { position:relative; margin:6px 18px; height:min(64vh,560px); }
  #wrap.two { height:auto; }
  canvas { display:block; background:#0d1116; border:1px solid var(--line); border-radius:8px; touch-action:none; }
  #gl { width:100%; height:100%; cursor:grab; }
  #c2d { width:100%; height:auto; image-rendering:pixelated; max-height:56vh; object-fit:contain; margin:0 auto; }
  #err { display:none; position:absolute; inset:0; align-items:center; justify-content:center;
         padding:20px; text-align:center; color:#f6dede; background:#5c2f2f; border-radius:8px; }
  #hud { position:absolute; left:12px; top:10px; font-size:13px; color:#c3ced9; line-height:1.55;
         font-variant-numeric:tabular-nums; pointer-events:none; text-shadow:0 1px 3px #000; }
  #hud b.flag { color:#ff8a80; }
  .cb { display:flex; align-items:center; gap:10px; flex-wrap:wrap; padding:2px 18px 4px; font-size:12.5px; color:var(--dim); }
  .cb .bar { width:min(260px,60vw); height:12px; border-radius:3px; border:1px solid var(--line); }
  .cb .ticks { display:flex; justify-content:space-between; width:min(260px,60vw); font-size:11.5px; margin-top:2px; }
  .ctl { display:flex; align-items:center; gap:10px; flex-wrap:wrap; padding:10px 18px 6px; }
  button { padding:7px 13px; border-radius:8px; border:1px solid var(--line);
           background:var(--panel); color:var(--fg); cursor:pointer; font-size:14px; }
  button.pri { background:#2c6fb5; border-color:#2c6fb5; color:#fff; }
  input[type=range] { flex:1; min-width:160px; }
  .read { color:var(--dim); font-size:13px; font-variant-numeric:tabular-nums; }
  .views { padding:0 18px 8px; display:flex; gap:8px; flex-wrap:wrap; }
  #plot { width:calc(100% - 36px); margin:4px 18px; height:150px; }
  .hint { padding:2px 18px 10px; color:#7d8b99; font-size:12.5px; line-height:1.8; }
  .credit { padding:0 18px 26px; color:#6b7886; font-size:12px; line-height:1.7; }
  #wrap.a3w { height:min(52vh,480px); }
  #rate { padding:3px 6px; font-size:13px; background:var(--panel); color:var(--fg); border:1px solid var(--line); border-radius:6px; }
  .evs { display:flex; flex-wrap:wrap; gap:6px; padding:0 18px 6px; }
  .evs button { padding:4px 10px; font-size:12.5px; }
  .evs button.on { background:#2c6fb5; border-color:#2c6fb5; color:#fff; }
  .panes { display:flex; flex-wrap:wrap; gap:10px; margin:6px 18px; }
  .pane { flex:1 1 220px; min-width:0; }
  .pane .pl { font-size:12.5px; color:var(--dim); margin-bottom:3px; }
  .pane canvas { width:100%; height:auto; max-height:36vh; object-fit:contain; image-rendering:pixelated; }
"""

_BODY = """
<header>
  <div><h1 id="h1"></h1><div class="sub" id="sub"></div></div>
  <select id="lang"></select>
</header>
<div class="tabs" id="tabs"></div>
<div class="card" id="meta"></div>
<div id="wrap"><canvas id="gl"></canvas><canvas id="c2d" style="display:none"></canvas><div id="hud"></div>
  <div id="err"></div></div>
<div class="cb" id="cb" style="display:none"></div>
<div class="views" id="views">
  <button data-v="front"></button><button data-v="side"></button>
  <button data-v="iso"></button><button data-v="top"></button>
</div>
<div class="ctl" id="ctl">
  <button id="play" class="pri"></button>
  <button id="b1" class="a3" style="display:none"></button><button id="f1" class="a3" style="display:none"></button>
  <button id="evp" class="a3" style="display:none"></button><button id="evn" class="a3" style="display:none"></button>
  <input type="range" id="scrub" min="0" max="1000" value="0">
  <span class="read" id="tlabel"></span>
  <label class="read" id="spl"><span id="spd"></span> <input type="range" id="speed" min="10" max="300" value="100" style="width:80px;vertical-align:middle"></label>
  <label class="read a3" id="rtl" style="display:none"><span id="rtt"></span> <select id="rate"><option value="0.25">&times;0.25</option><option value="0.5">&times;0.5</option><option value="1" selected>&times;1</option><option value="2">&times;2</option><option value="4">&times;4</option></select></label>
  <label class="read" id="lpl"><input type="checkbox" id="loop" checked> <span id="lpt"></span></label>
  <label class="read a3" id="fwl" style="display:none"><input type="checkbox" id="follow"> <span id="fwt"></span></label>
</div>
<div class="evs" id="evs" style="display:none"></div>
<div class="panes" id="panes" style="display:none"></div>
<canvas id="plot" style="display:none"></canvas>
<div class="hint" id="hint"></div>
<div class="credit" id="credit"></div>
"""

_JS = r"""
(function(){
'use strict';
const D = __DATA__;
const $ = id => document.getElementById(id);
const qs = new URLSearchParams(location.search);
let L = D.langs.indexOf(qs.get('lang')) >= 0 ? qs.get('lang') : D.langs[0];
const T = o => o == null ? '' : (typeof o === 'string' ? o : (o[L] || ''));
const U = k => T(D.ui[k]);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tabs = D.tabs;
let cur = tabs.some(t => t.id === qs.get('tab')) ? qs.get('tab') : tabs[0].id;
const get = () => tabs.find(t => t.id === cur);

/* ---------- 配列の復元(Python の decode_array と同じ式) ---------- */
const cache = {};
function arr(key){
  if (cache[key]) return cache[key];
  const rec = D.arrays[key];
  if (rec.t === 'png') return cache[key] = {a: null, shape: rec.shape, png: rec.png};   /* コマごとの PNG は pngImg で読む */
  const b = atob(rec.b64), u = new Uint8Array(b.length);
  for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i);
  let r;
  switch (rec.t) {
    case 'u8': case 'q8': r = u; break;
    case 'u16': case 'q16': r = new Uint16Array(u.buffer); break;
    case 'u32': r = new Uint32Array(u.buffer); break;
    case 's16': r = new Int16Array(u.buffer); break;
    default: r = new Float32Array(u.buffer);
  }
  let out = r;
  if (rec.t === 'q8' || rec.t === 'q16') {
    const maxv = rec.t === 'q8' ? 255 : 65535, nax = rec.lo.length;
    out = new Float64Array(r.length);
    for (let i = 0; i < r.length; i++) { const a = i % nax; out[i] = rec.lo[a] + r[i] * (rec.hi[a] - rec.lo[a]) / maxv; }
  }
  if (rec.t === 's16') { out = new Float64Array(r.length); for (let i = 0; i < r.length; i++) out[i] = r[i] / 32767; }
  return cache[key] = {a: out, shape: rec.shape};
}

/* ---------- 色 ---------- */
const STOPS = {
  div: ['#e66101','#fdb863','#e6ebef','#7fb0e6','#2f7fd6'],
  seq: ['#30409a','#2a9fb5','#7fcf8a','#f2e05a','#f2863c']
};
const hex = h => [parseInt(h.slice(1,3),16), parseInt(h.slice(3,5),16), parseInt(h.slice(5,7),16)];
function cmapRGB(name, t){
  const s = STOPS[name].map(hex); t = Math.min(1, Math.max(0, t));
  const x = t * (s.length - 1), i = Math.min(s.length - 2, Math.floor(x)), f = x - i;
  return [0,1,2].map(k => s[i][k] + (s[i+1][k] - s[i][k]) * f);
}
function colorsOf(tab){
  const n = tab.n, c = new Uint8Array(n * 3);
  if (tab.val != null) {
    const V = arr(tab.val).a, cb = tab.cbar, sp = cb.hi - cb.lo;
    for (let i = 0; i < n; i++) { const r = cmapRGB(cb.cmap, (V[i] - cb.lo) / sp); c[i*3] = r[0]; c[i*3+1] = r[1]; c[i*3+2] = r[2]; }
  } else { c.set(arr(tab.rgb).a); }
  return c;
}

/* ---------- 行列 ---------- */
function mul(a,b){const o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++){let s=0;for(let k=0;k<4;k++)s+=a[k*4+r]*b[c*4+k];o[c*4+r]=s;}return o;}
function persp(fy,as,n,f){const t=1/Math.tan(fy/2),nf=1/(n-f);return new Float32Array([t/as,0,0,0, 0,t,0,0, 0,0,(f+n)*nf,-1, 0,0,2*f*n*nf,0]);}
function look(e,c,u){let z=[e[0]-c[0],e[1]-c[1],e[2]-c[2]];const zl=Math.hypot(z[0],z[1],z[2]);z=[z[0]/zl,z[1]/zl,z[2]/zl];
  let x=[u[1]*z[2]-u[2]*z[1],u[2]*z[0]-u[0]*z[2],u[0]*z[1]-u[1]*z[0]];const xl=Math.hypot(x[0],x[1],x[2])||1;x=[x[0]/xl,x[1]/xl,x[2]/xl];
  const y=[z[1]*x[2]-z[2]*x[1],z[2]*x[0]-z[0]*x[2],z[0]*x[1]-z[1]*x[0]];
  return new Float32Array([x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0,
    -(x[0]*e[0]+x[1]*e[1]+x[2]*e[2]),-(y[0]*e[0]+y[1]*e[1]+y[2]*e[2]),-(z[0]*e[0]+z[1]*e[1]+z[2]*e[2]),1]);}

/* ---------- WebGL ---------- */
const cv = $('gl'), c2 = $('c2d'), ctx = c2.getContext('2d');
const gl = cv.getContext('webgl', {antialias:true}) || cv.getContext('experimental-webgl');
const u32ext = gl ? gl.getExtension('OES_element_index_uint') : null;
function sh(t, src){ const o = gl.createShader(t); gl.shaderSource(o, src); gl.compileShader(o);
  if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) console.error(gl.getShaderInfoLog(o)); return o; }
function prog(vs, fs){ const p = gl.createProgram(); gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(p); if (!gl.getProgramParameter(p, gl.LINK_STATUS)) { console.error(gl.getProgramInfoLog(p)); return null; } return p; }
let PP = null, MP = null;
if (gl) {
  PP = prog('attribute vec3 a_p;attribute vec3 a_c;uniform mat4 u_vp;uniform float u_ps;varying vec3 v_c;'+
    'void main(){gl_Position=u_vp*vec4(a_p,1.0);v_c=a_c;gl_PointSize=clamp(u_ps/gl_Position.w,1.5,28.0);}',
    'precision mediump float;varying vec3 v_c;void main(){vec2 d=gl_PointCoord-0.5;if(dot(d,d)>0.25)discard;gl_FragColor=vec4(v_c,1.0);}');
  MP = prog('attribute vec3 a_p;attribute vec3 a_n;attribute vec3 a_c;uniform mat4 u_vp;varying vec3 v_n;varying vec3 v_c;'+
    'void main(){gl_Position=u_vp*vec4(a_p,1.0);v_n=a_n;v_c=a_c;}',
    'precision mediump float;varying vec3 v_n;varying vec3 v_c;uniform vec3 u_l;'+
    'void main(){float d=abs(dot(normalize(v_n),u_l))*0.65+0.38;gl_FragColor=vec4(v_c*d,1.0);}');
}
function buf(data, target){ const b = gl.createBuffer(); gl.bindBuffer(target || gl.ARRAY_BUFFER, b); gl.bufferData(target || gl.ARRAY_BUFFER, data, gl.STATIC_DRAW); return b; }

const scenes = {};
function bbox(P){
  const lo = [Infinity,Infinity,Infinity], hi = [-Infinity,-Infinity,-Infinity];
  for (let i = 0; i < P.length; i += 3) for (let k = 0; k < 3; k++) { const v = P[i+k]; if (v < lo[k]) lo[k] = v; if (v > hi[k]) hi[k] = v; }
  return {lo, hi, ctr: [0,1,2].map(k => (lo[k] + hi[k]) / 2)};
}
function centred(P, ctr){ const o = new Float32Array(P.length); for (let i = 0; i < P.length; i++) o[i] = P[i] - ctr[i % 3]; return o; }
function scene3d(tab){
  if (tab.kind === 'anim3d') return sceneAnim(tab);
  if (scenes[tab.id]) return scenes[tab.id];
  const P = arr(tab.pos).a, bb = bbox(P), n = tab.n;
  const rad = 0.5 * Math.hypot(bb.hi[0]-bb.lo[0], bb.hi[1]-bb.lo[1], bb.hi[2]-bb.lo[2]) || 1;
  const S = {rad, n, cbufC: null};
  S.pos = buf(centred(P, bb.ctr)); S.col = buf(colorsOf(tab));
  if (tab.kind === 'points') {
    S.ps = tab.point_size || (3.2 * rad / Math.sqrt(n));
    if (tab.ghost != null) {
      const G = arr(tab.ghost).a, gc = new Uint8Array(G.length); gc.fill(110);
      S.gpos = buf(centred(G, bb.ctr)); S.gcol = buf(gc); S.gn = G.length / 3;
    }
  } else {
    const F = arr(tab.faces).a, nv = n;
    if (nv > 65535 && !u32ext) { S.fail = true; return scenes[tab.id] = S; }
    const idx = nv > 65535 ? new Uint32Array(F) : new Uint16Array(F);
    const N = new Float32Array(P.length);
    for (let f = 0; f < F.length; f += 3) {
      const a = F[f]*3, b = F[f+1]*3, c = F[f+2]*3;
      const ux = P[b]-P[a], uy = P[b+1]-P[a+1], uz = P[b+2]-P[a+2], vx = P[c]-P[a], vy = P[c+1]-P[a+1], vz = P[c+2]-P[a+2];
      const nx = uy*vz-uz*vy, ny = uz*vx-ux*vz, nz = ux*vy-uy*vx;
      for (const q of [a,b,c]) { N[q] += nx; N[q+1] += ny; N[q+2] += nz; }
    }
    for (let i = 0; i < N.length; i += 3) { const l = Math.hypot(N[i],N[i+1],N[i+2]) || 1; N[i]/=l; N[i+1]/=l; N[i+2]/=l; }
    S.nrm = buf(N); S.idx = buf(idx, gl.ELEMENT_ARRAY_BUFFER); S.count = idx.length; S.itype = nv > 65535 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT;
  }
  return scenes[tab.id] = S;
}

/* ---------- 状態 ---------- */
let az = -1.0, el = 0.5, dist = 3, playing = false, frame = 0, last = performance.now(), dirty = true;
let atime = 0;   /* anim3d の再生時刻(秒、t と同じ尺度) */
let splitX = 0.5;
const PRESETS = {front:[-Math.PI/2, 0.08, 1], side:[0, 0.08, 1], iso:[-1.0, 0.5, 1], top:[-Math.PI/2, 1.5, 1]};
function dist0(S){ return S.rad * 2.0; }
function applyView(tab, S){
  const v = tab.view || {};
  az = v.az != null ? v.az : -1.0; el = v.el != null ? v.el : 0.5; dist = dist0(S) * (v.dist != null ? v.dist : 1);
}
function isTwoD(tab){ return tab.kind === 'frames' || tab.kind === 'split'; }

function resize3d(){
  const r = cv.getBoundingClientRect(), d = Math.min(2, window.devicePixelRatio || 1);
  const w = Math.max(1, Math.round(r.width * d)), h = Math.max(1, Math.round(r.height * d));
  if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
  gl.viewport(0, 0, cv.width, cv.height);
}
function draw3d(tab){
  if (tab.kind === 'anim3d') { drawAnim(tab); return; }
  const S = scene3d(tab);
  if (S.fail || !PP) { showErr(U('nogl')); return; }
  resize3d();
  const cd = Math.cos(el), sd = Math.sin(el), ca = Math.cos(az), sa = Math.sin(az);
  const eye = [dist*cd*ca, dist*cd*sa, dist*sd];
  const fy = 0.9, vp = mul(persp(fy, cv.width/cv.height, S.rad*0.02, S.rad*40), look(eye, [0,0,0], [0,0,1]));
  gl.enable(gl.DEPTH_TEST); gl.clearColor(0.051, 0.067, 0.086, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  if (tab.kind === 'points') {
    gl.useProgram(PP);
    const lp = gl.getAttribLocation(PP, 'a_p'), lc = gl.getAttribLocation(PP, 'a_c');
    gl.uniformMatrix4fv(gl.getUniformLocation(PP, 'u_vp'), false, vp);
    const px = S.ps * cv.height / (2 * Math.tan(fy / 2));
    gl.uniform1f(gl.getUniformLocation(PP, 'u_ps'), px);
    const run = (pb, cb, cnt) => {
      gl.bindBuffer(gl.ARRAY_BUFFER, pb); gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, cb); gl.enableVertexAttribArray(lc); gl.vertexAttribPointer(lc, 3, gl.UNSIGNED_BYTE, true, 0, 0);
      gl.drawArrays(gl.POINTS, 0, cnt);
    };
    if (S.gpos) run(S.gpos, S.gcol, S.gn);
    run(S.pos, S.col, S.n);
  } else {
    gl.useProgram(MP);
    const lp = gl.getAttribLocation(MP, 'a_p'), ln = gl.getAttribLocation(MP, 'a_n'), lc = gl.getAttribLocation(MP, 'a_c');
    gl.bindBuffer(gl.ARRAY_BUFFER, S.pos); gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, S.nrm); gl.enableVertexAttribArray(ln); gl.vertexAttribPointer(ln, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, S.col); gl.enableVertexAttribArray(lc); gl.vertexAttribPointer(lc, 3, gl.UNSIGNED_BYTE, true, 0, 0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, S.idx);
    let l = [eye[0]/dist*0.5, eye[1]/dist*0.5, eye[2]/dist*0.5 + 0.5]; const ll = Math.hypot(l[0], l[1], l[2]); l = l.map(v => v/ll);
    gl.uniform3f(gl.getUniformLocation(MP, 'u_l'), l[0], l[1], l[2]);
    gl.uniformMatrix4fv(gl.getUniformLocation(MP, 'u_vp'), false, vp);
    gl.drawElements(gl.TRIANGLES, S.count, S.itype, 0);
  }
  const deg = ((az * 180 / Math.PI) % 360 + 360) % 360;
  $('hud').innerHTML = esc(tab.n.toLocaleString() + ' ' + (tab.kind === 'points' ? U('points') : U('verts'))) + '<br>' + esc(U('drag'));
  $('tlabel').textContent = U('azimuth') + ' ' + deg.toFixed(0) + '°';
  $('scrub').value = String(Math.round(deg / 360 * 1000));
}

/* ---------- 動く 3-D(anim3d)。物体の頂点は GPU に 1 回だけ上げ、コマごとには姿勢(model 行列)だけを渡す ---------- */
let AP = null, LP = null;
if (gl) {
  AP = prog('attribute vec3 a_p;attribute vec3 a_n;attribute vec3 a_c;uniform mat4 u_vp;uniform mat4 u_m;varying vec3 v_n;varying vec3 v_c;'+
    'void main(){gl_Position=u_vp*u_m*vec4(a_p,1.0);v_n=(u_m*vec4(a_n,0.0)).xyz;v_c=a_c;}',
    'precision mediump float;varying vec3 v_n;varying vec3 v_c;uniform vec3 u_l;'+
    'void main(){float d=abs(dot(normalize(v_n),u_l))*0.65+0.38;gl_FragColor=vec4(v_c*d,1.0);}');
  LP = prog('attribute vec3 a_p;attribute float a_s;uniform mat4 u_vp;uniform float u_tc;uniform float u_tail;varying float v_a;'+
    'void main(){gl_Position=u_vp*vec4(a_p,1.0);v_a=u_tail>0.0?clamp(1.0-(u_tc-a_s)/u_tail,0.0,1.0):1.0;}',
    'precision mediump float;uniform vec3 u_col;varying float v_a;void main(){gl_FragColor=vec4(u_col,v_a);}');
}
const anims = {};
function attrsOff(){ if (!gl) return; const n = gl.getParameter(gl.MAX_VERTEX_ATTRIBS); for (let i = 0; i < Math.min(n, 8); i++) gl.disableVertexAttribArray(i); }
function normalsOf(P, F){
  const N = new Float32Array(P.length);
  for (let f = 0; f < F.length; f += 3) {
    const a = F[f]*3, b = F[f+1]*3, c = F[f+2]*3;
    const ux = P[b]-P[a], uy = P[b+1]-P[a+1], uz = P[b+2]-P[a+2], vx = P[c]-P[a], vy = P[c+1]-P[a+1], vz = P[c+2]-P[a+2];
    const nx = uy*vz-uz*vy, ny = uz*vx-ux*vz, nz = ux*vy-uy*vx;
    for (const q of [a,b,c]) { N[q] += nx; N[q+1] += ny; N[q+2] += nz; }
  }
  for (let i = 0; i < N.length; i += 3) { const l = Math.hypot(N[i],N[i+1],N[i+2]) || 1; N[i]/=l; N[i+1]/=l; N[i+2]/=l; }
  return N;
}
/* 単位四元数 (w,x,y,z) + 位置 → 列優先の 4x4(Python の _quat_matrix と同じ式) */
function quatMat(w, x, y, z, px, py, pz){
  const n = Math.hypot(w, x, y, z) || 1; w /= n; x /= n; y /= n; z /= n;
  return new Float32Array([1-2*(y*y+z*z), 2*(x*y+w*z), 2*(x*z-w*y), 0,
                           2*(x*y-w*z), 1-2*(x*x+z*z), 2*(y*z+w*x), 0,
                           2*(x*z+w*y), 2*(y*z-w*x), 1-2*(x*x+y*y), 0,
                           px, py, pz, 1]);
}
function frameAt(tab, tt){
  const t = tab.t; let a = 0, b = t.length - 1;
  if (tt <= t[0]) return 0; if (tt >= t[b]) return b;
  while (b - a > 1) { const m = (a + b) >> 1; if (t[m] <= tt) a = m; else b = m; }
  return a;
}
function seekFrame(tab, k){
  if (tab.kind !== 'anim3d') return;
  k = Math.max(0, Math.min(tab.t.length - 1, k)); atime = tab.t[k]; frame = k; dirty = true;
}
function animStep(tab, dt){
  const n = tab.t.length, t0 = tab.t[0], tN = tab.t[n-1], step = n > 1 ? (tN - t0) / (n - 1) : 0;
  atime += dt * (+$('rate').value || 1);
  if (atime >= tN + step) {                       /* 最後のコマも 1 コマぶん見せてから */
    if ($('loop').checked && n > 1) atime = t0 + (atime - t0) % (tN - t0 + step);
    else { atime = tN; playing = false; setBtn(); }
  }
  frame = frameAt(tab, atime);
}
function sceneAnim(tab){
  if (anims[tab.id]) return anims[tab.id];
  if (!gl) return anims[tab.id] = {fail: true, rad: 1, ctr: [0,0,0], tgt: [0,0,0]};
  const X = arr(tab.xyz).a, Q = arr(tab.quat).a, B = tab.bodies.length, T_ = tab.t.length, t0 = tab.t[0];
  const S = {B, T: T_, X, Q, bodies: [], trails: [], clouds: []};
  const lo = [Infinity,Infinity,Infinity], hi = [-Infinity,-Infinity,-Infinity];
  const grow = (x, y, z, r) => { const v = [x, y, z]; for (let k = 0; k < 3; k++) { if (v[k]-r < lo[k]) lo[k] = v[k]-r; if (v[k]+r > hi[k]) hi[k] = v[k]+r; } };
  for (let j = 0; j < B; j++) {
    const b = tab.bodies[j], P = arr(b.pos).a, F = arr(b.faces).a;
    if (b.n > 65535 && !u32ext) { S.fail = true; return anims[tab.id] = Object.assign(S, {rad: 1, ctr: [0,0,0], tgt: [0,0,0]}); }
    const blo = [Infinity,Infinity,Infinity], bhi = [-Infinity,-Infinity,-Infinity];   /* 物体の局所 AABB */
    for (let i = 0; i < P.length; i += 3) for (let k = 0; k < 3; k++) { blo[k] = Math.min(blo[k], P[i+k]); bhi[k] = Math.max(bhi[k], P[i+k]); }
    const corners = [];
    for (const x of [blo[0], bhi[0]]) for (const y of [blo[1], bhi[1]]) for (const z of [blo[2], bhi[2]]) corners.push([x, y, z]);
    const col = new Uint8Array(b.n * 3);
    if (b.rgb1) { for (let i = 0; i < b.n; i++) col.set(b.rgb1, i*3); }
    else if (b.rgb != null) col.set(arr(b.rgb).a);
    else { const V = arr(b.val).a, cb = tab.cbar, sp = cb.hi - cb.lo;
      for (let i = 0; i < b.n; i++) { const c = cmapRGB(cb.cmap, (V[i] - cb.lo) / sp); col[i*3] = c[0]; col[i*3+1] = c[1]; col[i*3+2] = c[2]; } }
    const idx = b.n > 65535 ? new Uint32Array(F) : new Uint16Array(F);
    S.bodies.push({pos: buf(new Float32Array(P)), nrm: buf(normalsOf(P, F)), col: buf(col),
      idx: buf(idx, gl.ELEMENT_ARRAY_BUFFER), count: idx.length, itype: b.n > 65535 ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT});
    for (let f = 0; f < T_; f++) {                  /* 場面の大きさ = 全コマで動かした AABB の角 */
      const o = f*B + j, m = quatMat(Q[o*4], Q[o*4+1], Q[o*4+2], Q[o*4+3], X[o*3], X[o*3+1], X[o*3+2]);
      for (const c of corners) grow(m[0]*c[0]+m[4]*c[1]+m[8]*c[2]+m[12], m[1]*c[0]+m[5]*c[1]+m[9]*c[2]+m[13], m[2]*c[0]+m[6]*c[1]+m[10]*c[2]+m[14], 0);
    }
  }
  for (const tr of tab.trails) {
    const P = arr(tr.xyz).a, s = new Float32Array(T_);
    for (let f = 0; f < T_; f++) { s[f] = tab.t[f] - t0; grow(P[f*3], P[f*3+1], P[f*3+2], 0); }
    S.trails.push({pos: buf(new Float32Array(P)), s: buf(s), col: hex(tr.color).map(v => v / 255), tail: tr.tail});
  }
  for (const c of tab.clouds) {
    const P = arr(c.pos).a; let col;
    if (c.rgb != null) col = new Uint8Array(arr(c.rgb).a);
    else { col = new Uint8Array(c.n * 3); const h = hex(c.color); for (let i = 0; i < c.n; i++) col.set(h, i*3); }
    for (let i = 0; i < P.length; i += 3) grow(P[i], P[i+1], P[i+2], 0);
    S.clouds.push({k: c.k, n: c.n, pos: buf(new Float32Array(P)), col: buf(col), ps: c.point_size || 0});
  }
  S.ctr = [0,1,2].map(k => (lo[k] + hi[k]) / 2);
  S.rad = 0.5 * Math.hypot(hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2]) || 1;
  for (const c of S.clouds) if (!c.ps) c.ps = 3.2 * S.rad / Math.sqrt(c.n) * 0.5;
  S.tgt = S.ctr.slice();                          /* 追従の注視点(平滑化して動かす) */
  return anims[tab.id] = S;
}
function followPoint(tab, S, f){
  if (tab.follow != null) { const o = (f*S.B + tab.follow)*3; return [S.X[o], S.X[o+1], S.X[o+2]]; }
  const c = [0, 0, 0];
  for (let j = 0; j < S.B; j++) { const o = (f*S.B + j)*3; c[0] += S.X[o]; c[1] += S.X[o+1]; c[2] += S.X[o+2]; }
  return c.map(v => v / S.B);
}
/* 追従: 目標へ指数で寄せる(時定数 0.35 s)。コマごとの小さな揺れはならされ、カメラは跳ばない */
function followTick(tab, dt){
  const S = sceneAnim(tab); if (S.fail) return false;
  const p = followPoint(tab, S, Math.floor(frame)), a = 1 - Math.exp(-Math.max(dt, 1e-3) / 0.35);
  let moved = 0;
  for (let k = 0; k < 3; k++) { const d = p[k] - S.tgt[k]; S.tgt[k] += d * a; moved = Math.max(moved, Math.abs(d)); }
  return moved > S.rad * 1e-4;
}
function curEvent(tab, f){ let e = -1; tab.events.forEach((ev, j) => { if (ev.k <= f) e = j; }); return e; }
function drawAnimHud(tab, f){
  const T_ = tab.t.length, ei = curEvent(tab, f);
  let hud = U('frame') + ' ' + f + ' / ' + (T_-1) + '  (' + (tab.t[f] - tab.t[0]).toFixed(2) + ' s)';
  if (ei >= 0) hud += '<br>' + esc(U('stage')) + ': <b>' + esc(T(tab.events[ei].label)) + '</b>';
  for (const s of tab.series) {
    const v = s.values[f]; let line = esc(T(s.label)) + ': ' + (v == null ? '—' : v.toFixed(s.decimals) + (s.unit ? ' ' + esc(s.unit) : ''));
    if (s.threshold != null && v != null) line += ' (' + esc(v >= s.threshold ? U('above') : U('below')) + ' ' + s.threshold.toFixed(s.decimals) + ')';
    hud += '<br><span style="color:' + esc(s.color) + '">■</span> ' + line;
  }
  hud += '<br>' + esc(tab.bodies.length + ' ' + U('bodies') + ' · ' + U('drag'));
  $('hud').innerHTML = hud;
  $('tlabel').textContent = (tab.t[f] - tab.t[0]).toFixed(2) + ' s';
  $('scrub').value = String(Math.round(f / Math.max(1, T_-1) * 1000));
  document.querySelectorAll('#evs [data-ev]').forEach(b => b.classList.toggle('on', +b.dataset.ev === ei));
}
function drawAnim(tab){
  const S = sceneAnim(tab), f = Math.max(0, Math.min(tab.t.length - 1, Math.floor(frame)));
  if (S.fail || !AP || !LP || !PP) { showErr(U('nogl')); drawAnimHud(tab, f); return; }
  resize3d();
  const tg = $('follow').checked ? S.tgt : S.ctr;
  const cd = Math.cos(el), sd = Math.sin(el), ca = Math.cos(az), sa = Math.sin(az);
  const eye = [tg[0] + dist*cd*ca, tg[1] + dist*cd*sa, tg[2] + dist*sd];
  const fy = 0.9, vp = mul(persp(fy, cv.width/cv.height, S.rad*0.02, S.rad*40), look(eye, tg, [0,0,1]));
  gl.enable(gl.DEPTH_TEST); gl.disable(gl.BLEND); gl.clearColor(0.051, 0.067, 0.086, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  attrsOff();
  /* 物体 */
  gl.useProgram(AP);
  const lp = gl.getAttribLocation(AP, 'a_p'), ln = gl.getAttribLocation(AP, 'a_n'), lc = gl.getAttribLocation(AP, 'a_c');
  const um = gl.getUniformLocation(AP, 'u_m');
  let l = [ca*cd*0.5, sa*cd*0.5, sd*0.5 + 0.5]; const ll = Math.hypot(l[0], l[1], l[2]); l = l.map(v => v/ll);
  gl.uniform3f(gl.getUniformLocation(AP, 'u_l'), l[0], l[1], l[2]);
  gl.uniformMatrix4fv(gl.getUniformLocation(AP, 'u_vp'), false, vp);
  gl.enableVertexAttribArray(lp); gl.enableVertexAttribArray(ln); gl.enableVertexAttribArray(lc);
  S.bodies.forEach((b, j) => {
    const o = f*S.B + j;
    gl.bindBuffer(gl.ARRAY_BUFFER, b.pos); gl.vertexAttribPointer(lp, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, b.nrm); gl.vertexAttribPointer(ln, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, b.col); gl.vertexAttribPointer(lc, 3, gl.UNSIGNED_BYTE, true, 0, 0);
    gl.uniformMatrix4fv(um, false, quatMat(S.Q[o*4], S.Q[o*4+1], S.Q[o*4+2], S.Q[o*4+3], S.X[o*3], S.X[o*3+1], S.X[o*3+2]));
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b.idx);
    gl.drawElements(gl.TRIANGLES, b.count, b.itype, 0);
  });
  attrsOff();
  /* 軌跡(残像: tail 秒より古い部分は薄く消える) */
  if (S.trails.length) {
    gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    gl.useProgram(LP);
    const pl = gl.getAttribLocation(LP, 'a_p'), sl = gl.getAttribLocation(LP, 'a_s');
    gl.uniformMatrix4fv(gl.getUniformLocation(LP, 'u_vp'), false, vp);
    gl.uniform1f(gl.getUniformLocation(LP, 'u_tc'), tab.t[f] - tab.t[0]);
    gl.enableVertexAttribArray(pl); gl.enableVertexAttribArray(sl);
    tab.trails.forEach((tr, j) => {
      const R = S.trails[j], start = R.tail > 0 ? frameAt(tab, tab.t[f] - R.tail) : 0, cnt = f - start + 1;
      if (cnt < 2) return;
      gl.bindBuffer(gl.ARRAY_BUFFER, R.pos); gl.vertexAttribPointer(pl, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, R.s); gl.vertexAttribPointer(sl, 1, gl.FLOAT, false, 0, 0);
      gl.uniform1f(gl.getUniformLocation(LP, 'u_tail'), R.tail);
      gl.uniform3f(gl.getUniformLocation(LP, 'u_col'), R.col[0], R.col[1], R.col[2]);
      gl.drawArrays(gl.LINE_STRIP, start, cnt);
    });
    attrsOff(); gl.disable(gl.BLEND);
  }
  /* 点群: k が今のコマ以下で最も新しい雲を、次の雲まで出す */
  let cl = null; for (const c of S.clouds) if (c.k <= f) cl = c;
  if (cl) {
    gl.useProgram(PP);
    const pl = gl.getAttribLocation(PP, 'a_p'), cc = gl.getAttribLocation(PP, 'a_c');
    gl.uniformMatrix4fv(gl.getUniformLocation(PP, 'u_vp'), false, vp);
    gl.uniform1f(gl.getUniformLocation(PP, 'u_ps'), cl.ps * cv.height / (2 * Math.tan(fy / 2)));
    gl.enableVertexAttribArray(pl); gl.enableVertexAttribArray(cc);
    gl.bindBuffer(gl.ARRAY_BUFFER, cl.pos); gl.vertexAttribPointer(pl, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, cl.col); gl.vertexAttribPointer(cc, 3, gl.UNSIGNED_BYTE, true, 0, 0);
    gl.drawArrays(gl.POINTS, 0, cl.n);
    attrsOff();
  }
  drawAnimHud(tab, f);
}
/* 同じ時間軸の 2-D(センサー画像・op の結果)。PNG はブラウザが無損失で復号する */
const imgs = {}, pimgs = {};
function pngImg(key, t){
  const id = key + ':' + t; let im = pimgs[id];
  if (!im) { im = new Image(); im.onload = () => { dirty = true; }; im.src = 'data:image/png;base64,' + D.arrays[key].png[t]; pimgs[id] = im; }
  return im.complete && im.naturalWidth > 0 ? im : null;
}
function paneImage(key, t){
  if (D.arrays[key].t === 'png') return pngImg(key, t);
  const id = key + ':' + t; if (imgs[id]) return imgs[id];
  const A = arr(key), sh_ = A.shape, H = sh_[1], W = sh_[2], ch = sh_.length === 4 ? 3 : 1, base = t * H * W * ch;
  const o = document.createElement('canvas'); o.width = W; o.height = H;
  const im = o.getContext('2d').createImageData(W, H), d = im.data;
  for (let i = 0; i < W * H; i++) {
    if (ch === 3) { d[i*4] = A.a[base+i*3]; d[i*4+1] = A.a[base+i*3+1]; d[i*4+2] = A.a[base+i*3+2]; }
    else { const g = A.a[base+i]; d[i*4] = g; d[i*4+1] = g; d[i*4+2] = g; }
    d[i*4+3] = 255;
  }
  o.getContext('2d').putImageData(im, 0, 0);
  return imgs[id] = o;
}
function buildPanes(tab){
  const box = $('panes');
  if (tab.kind !== 'anim3d' || !tab.panes.length) { box.style.display = 'none'; box.innerHTML = ''; return; }
  box.style.display = 'flex';
  box.innerHTML = tab.panes.map((p, j) => '<div class="pane"><div class="pl">' + esc(T(p.label)) + '</div><canvas id="pane' + j + '"></canvas></div>').join('');
}
function buildEvents(tab){
  const box = $('evs');
  if (tab.kind !== 'anim3d' || !tab.events.length) { box.style.display = 'none'; box.innerHTML = ''; return; }
  box.style.display = 'flex';
  box.innerHTML = tab.events.map((e, j) => '<button data-ev="' + j + '">' + esc(T(e.label)) + ' · ' + (e.t - tab.t[0]).toFixed(2) + ' s</button>').join('');
  box.querySelectorAll('[data-ev]').forEach(b => { b.onclick = () => seekFrame(tab, tab.events[+b.dataset.ev].k); });
}
function drawPanes(tab, f){
  tab.panes.forEach((p, j) => {
    const c = $('pane' + j); if (!c) return;
    const rec = D.arrays[p.frames], sh_ = rec.shape, H = sh_[1], W = sh_[2], k = Math.max(1, Math.round(320 / W));
    if (c.width !== W*k || c.height !== H*k) { c.width = W*k; c.height = H*k; }
    if (rec.t === 'png') for (let i = 1; i <= 6 && f + i < sh_[0]; i++) pngImg(p.frames, f + i);   /* 先読み */
    const im = paneImage(p.frames, f); if (!im) return;                                          /* 読めるまで前のコマを残す */
    const g = c.getContext('2d'); g.imageSmoothingEnabled = false; g.clearRect(0, 0, c.width, c.height);
    g.drawImage(im, 0, 0, W*k, H*k);
    g.font = (12 * Math.max(1, k/2)) + 'px sans-serif'; g.textBaseline = 'bottom';
    for (const b of p.boxes) {
      const fl = b.flag ? b.flag[f] : false, [x, y] = b.xy[f], w = b.size[0]*k, h = b.size[1]*k;
      g.strokeStyle = fl ? b.flag_color : b.color; g.lineWidth = Math.max(2, k * 0.8);
      g.strokeRect((x + 0.5)*k - w/2, (y + 0.5)*k - h/2, w, h);
      g.fillStyle = fl ? b.flag_color : b.color;
      g.fillText(T(b.label) + (fl && b.flag_text ? ' ' + T(b.flag_text) : ''), (x + 0.5)*k - w/2, (y + 0.5)*k - h/2 - 2);
    }
  });
}

/* ---------- 2-D(動画・分割) ---------- */
function frameCanvas(tab, key, t){
  if (tab.kind === 'frames') return paneImage(tab.frames, t);
  const id = tab.id + ':' + key + ':' + t;
  if (imgs[id]) return imgs[id];
  const A = arr(tab[key] || tab.frames), sh_ = A.shape;
  const H = tab.kind === 'frames' ? sh_[1] : sh_[0], W = tab.kind === 'frames' ? sh_[2] : sh_[1];
  const ch = sh_.length === (tab.kind === 'frames' ? 4 : 3) ? 3 : 1;
  const base = tab.kind === 'frames' ? t * H * W * ch : 0;
  const o = document.createElement('canvas'); o.width = W; o.height = H;
  const im = o.getContext('2d').createImageData(W, H), d = im.data;
  for (let i = 0; i < W * H; i++) {
    if (ch === 3) { d[i*4] = A.a[base+i*3]; d[i*4+1] = A.a[base+i*3+1]; d[i*4+2] = A.a[base+i*3+2]; }
    else { const g = A.a[base+i]; d[i*4] = g; d[i*4+1] = g; d[i*4+2] = g; }
    d[i*4+3] = 255;
  }
  o.getContext('2d').putImageData(im, 0, 0);
  return imgs[id] = o;
}
function dims(tab){ const s = arr(tab.kind === 'frames' ? tab.frames : tab.before).shape; return tab.kind === 'frames' ? [s[2], s[1]] : [s[1], s[0]]; }
function fit2d(tab){
  const [W, H] = dims(tab), k = Math.max(1, Math.round(640 / W));
  if (c2.width !== W * k || c2.height !== H * k) { c2.width = W * k; c2.height = H * k; }
  return k;
}
function draw2d(tab){
  const k = fit2d(tab), [W, H] = dims(tab);
  let fimg = null;
  if (tab.kind === 'frames') {                   /* PNG がまだ読めていなければ前のコマを残す(ちらつかせない) */
    const T0 = arr(tab.frames).shape[0], f0 = Math.min(T0 - 1, Math.max(0, Math.floor(frame)));
    if (D.arrays[tab.frames].t === 'png') for (let j = 1; j <= 6 && f0 + j < T0; j++) pngImg(tab.frames, f0 + j);
    fimg = frameCanvas(tab, 'frames', f0); if (!fimg) return;
  }
  ctx.imageSmoothingEnabled = false; ctx.clearRect(0, 0, c2.width, c2.height);
  if (tab.kind === 'split') {
    ctx.drawImage(frameCanvas(tab, 'after', 0), 0, 0, W*k, H*k);
    const sx = Math.round(splitX * W * k);
    ctx.save(); ctx.beginPath(); ctx.rect(0, 0, sx, H*k); ctx.clip();
    ctx.drawImage(frameCanvas(tab, 'before', 0), 0, 0, W*k, H*k); ctx.restore();
    ctx.fillStyle = '#ffffff'; ctx.fillRect(sx - 1, 0, 2, H*k);
    ctx.beginPath(); ctx.arc(sx, H*k/2, 14, 0, 6.2832); ctx.fillStyle = '#2c6fb5'; ctx.fill(); ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = '#fff'; ctx.font = (13*Math.max(1,k/2))+'px sans-serif'; ctx.textBaseline = 'top';
    ctx.textAlign = 'left'; ctx.fillText(T(tab.label_before), 8, 6); ctx.textAlign = 'right'; ctx.fillText(T(tab.label_after), W*k-8, 6);
    $('hud').innerHTML = esc(U('split'));
    return;
  }
  const T_ = arr(tab.frames).shape[0], f = Math.min(T_-1, Math.max(0, Math.floor(frame)));
  ctx.drawImage(fimg, 0, 0, W*k, H*k);
  let hud = U('frame') + ' ' + f + ' / ' + (T_-1) + '  (' + (f * tab.dt).toFixed(2) + ' s)';
  for (const b of tab.boxes) {
    const fl = b.flag ? b.flag[f] : false, [x, y] = b.xy[f], w = b.size[0]*k, h = b.size[1]*k;
    ctx.strokeStyle = fl ? b.flag_color : b.color; ctx.lineWidth = Math.max(2, k * 0.8);
    ctx.strokeRect((x + 0.5)*k - w/2, (y + 0.5)*k - h/2, w, h);
    hud += '<br><span style="color:' + esc(b.color) + '">■</span> ' + esc(T(b.label)) + (fl && b.flag_text ? ' <b class="flag">' + esc(T(b.flag_text)) + '</b>' : '');
  }
  for (const s of tab.series) {
    const v = s.values[f]; let line = esc(T(s.label)) + ': ' + (v == null ? '—' : v.toFixed(s.decimals) + (s.unit ? ' ' + esc(s.unit) : ''));
    if (s.threshold != null && v != null) line += ' (' + esc(v >= s.threshold ? U('above') : U('below')) + ' ' + s.threshold.toFixed(s.decimals) + ')';
    hud += '<br><span style="color:' + esc(s.color) + '">■</span> ' + line;
  }
  $('hud').innerHTML = hud;
  $('tlabel').textContent = (f * tab.dt).toFixed(2) + ' s';
  $('scrub').value = String(Math.round(f / Math.max(1, T_-1) * 1000));
  drawPlot(tab, f);
}
function drawPlot(tab, f){
  const p = $('plot'); if (!tab.series.length) { p.style.display = 'none'; return; }
  p.style.display = 'block';
  const r = p.getBoundingClientRect(), d = Math.min(2, window.devicePixelRatio || 1);
  p.width = Math.max(1, Math.round(r.width * d)); p.height = Math.max(1, Math.round(r.height * d));
  const g = p.getContext('2d'); g.setTransform(d, 0, 0, d, 0, 0);
  const w = r.width, h = r.height, ml = 8, mr = 8, mt = 8, mb = 22, n = tab.series[0].values.length;
  g.fillStyle = '#0d1116'; g.fillRect(0, 0, w, h);
  const X = i => ml + (w - ml - mr) * i / Math.max(1, n - 1), Y = (s, v) => mt + (h - mt - mb) * (1 - (v - s.lo) / (s.hi - s.lo));
  g.strokeStyle = '#26313c'; g.lineWidth = 1; g.strokeRect(ml, mt, w - ml - mr, h - mt - mb);
  g.font = '11px sans-serif'; g.textBaseline = 'alphabetic';
  let lx = ml + 4;
  for (const s of tab.series) {
    if (s.threshold != null) { g.setLineDash([4, 4]); g.strokeStyle = s.color; g.globalAlpha = 0.6; g.beginPath(); g.moveTo(ml, Y(s, s.threshold)); g.lineTo(w - mr, Y(s, s.threshold)); g.stroke(); g.setLineDash([]); g.globalAlpha = 1; }
    for (const pass of [0, 1]) {
      g.strokeStyle = s.color; g.lineWidth = pass ? 2 : 1; g.globalAlpha = pass ? 1 : 0.28; g.beginPath(); let pen = false;
      const a = pass ? 0 : f, b = pass ? f : n - 1;
      for (let i = a; i <= b; i++) { const v = s.values[i]; if (v == null) { pen = false; continue; } if (!pen) { g.moveTo(X(i), Y(s, v)); pen = true; } else g.lineTo(X(i), Y(s, v)); }
      g.stroke();
    }
    g.globalAlpha = 1; g.fillStyle = s.color;
    const lab = T(s.label) + ' [' + s.lo + '–' + s.hi + (s.unit ? ' ' + s.unit : '') + ']'; g.fillText(lab, lx, h - 6); lx += g.measureText(lab).width + 16;
  }
  if (tab.events) { g.strokeStyle = '#93a2b1'; g.globalAlpha = 0.55; g.setLineDash([2, 3]);
    for (const e of tab.events) { g.beginPath(); g.moveTo(X(e.k), mt); g.lineTo(X(e.k), h - mb); g.stroke(); }
    g.setLineDash([]); g.globalAlpha = 1; }
  g.strokeStyle = '#ffffff'; g.globalAlpha = 0.7; g.beginPath(); g.moveTo(X(f), mt); g.lineTo(X(f), h - mb); g.stroke(); g.globalAlpha = 1;
}

/* ---------- ページ ---------- */
function showErr(msg){ const e = $('err'); e.textContent = msg; e.style.display = 'flex'; }
function colorbar(tab){
  const cb = $('cb');
  if (isTwoD(tab) || !tab.cbar) { cb.style.display = 'none'; return; }
  const c = tab.cbar, st = STOPS[c.cmap];
  cb.style.display = 'flex';
  const f = v => Math.abs(v) >= 100 ? v.toFixed(0) : (Math.abs(v) >= 1 ? v.toFixed(1) : v.toFixed(2));
  cb.innerHTML = '<span>' + esc(c.label ? T(c.label) : '') + '</span><div><div class="bar" style="background:linear-gradient(90deg,' + st.join(',') + ')"></div>' +
    '<div class="ticks"><span>' + f(c.lo) + '</span><span>' + f((c.lo + c.hi) / 2) + '</span><span>' + f(c.hi) + ' ' + esc(c.unit) + '</span></div></div>';
}
function renderTabs(){
  $('tabs').innerHTML = tabs.map(t => '<button class="tab ' + (t.id === cur ? 'on' : '') + '" data-id="' + esc(t.id) + '"><i class="' + t.badge + '-dot"></i>' + esc(T(t.label)) + '</button>').join('');
  document.querySelectorAll('.tab').forEach(b => b.onclick = () => select(b.dataset.id));
}
function renderMeta(){
  const t = get();
  const nums = t.numbers.map(n => '<span class="num"><i>' + esc(T(n.label)) + '</i><b>' + esc(T(n.value)) + '</b></span>').join('');
  $('meta').innerHTML = '<span class="badge ' + t.badge + '">' + esc(T(D.badges[t.badge])) + '</span><b>' + esc(T(t.label)) + '</b><br>' + esc(T(t.text)) +
    (nums ? '<div class="nums">' + nums + '</div>' : '');
}
function renderText(){
  document.documentElement.lang = L;
  $('h1').textContent = T(D.title); document.title = T(D.title);
  $('sub').textContent = T(D.subtitle); $('hint').textContent = T(D.hint); $('credit').textContent = T(D.credit);
  const sel = $('lang'); sel.style.display = D.langs.length > 1 ? 'block' : 'none';
  sel.innerHTML = D.langs.map(l => '<option value="' + l + '"' + (l === L ? ' selected' : '') + '>' + esc(D.langnames[l]) + '</option>').join('');
  document.querySelectorAll('[data-v]').forEach(b => b.textContent = U(b.dataset.v));
  $('spd').textContent = U('speed'); $('lpt').textContent = U('loop'); $('err').textContent = U('nogl');
  $('b1').textContent = U('back1'); $('f1').textContent = U('fwd1'); $('evp').textContent = U('evprev'); $('evn').textContent = U('evnext');
  $('rtt').textContent = U('speed'); $('fwt').textContent = U('follow');
  setBtn(); renderTabs(); renderMeta(); colorbar(get()); buildPanes(get()); buildEvents(get());
}
function setBtn(){ $('play').textContent = playing ? U('pause') : U('play'); }
function select(id){
  cur = id; frame = 0; splitX = 0.5; const t = get();
  try { const u = new URL(location.href); u.searchParams.set('tab', cur); history.replaceState(null, '', u); } catch (e) {}
  $('err').style.display = 'none';
  const two = isTwoD(t);
  const an = t.kind === 'anim3d';
  $('wrap').className = two ? 'two' : (an && t.panes.length ? 'a3w' : ''); cv.style.display = two ? 'none' : 'block'; c2.style.display = two ? 'block' : 'none';
  document.querySelectorAll('.a3').forEach(e => { e.style.display = an ? '' : 'none'; });
  $('spl').style.display = an ? 'none' : '';
  if (an) { atime = t.t[0]; $('follow').checked = false; }
  $('views').style.display = two ? 'none' : 'flex';
  $('ctl').style.display = t.kind === 'split' ? 'none' : 'flex';
  $('lpl').style.display = t.kind === 'frames' || an ? 'inline' : 'none';
  $('plot').style.display = (t.kind === 'frames' || an) && t.series.length ? 'block' : 'none';
  playing = t.kind === 'frames' || an; last = performance.now();
  if (!two) { if (!gl) showErr(U('nogl')); else { const S = scene3d(t); applyView(t, S); } }
  renderTabs(); renderMeta(); colorbar(t); setBtn(); buildPanes(t); buildEvents(t); dirty = true;
}
function render(){
  const t = get();
  if (t.kind === 'anim3d') { const f = Math.floor(frame); if (gl) draw3d(t); else drawAnimHud(t, f); drawPanes(t, f); drawPlot(t, f); return; }
  if (isTwoD(t)) draw2d(t); else if (gl) draw3d(t);
}
function tick(now){
  const t = get(), dt = Math.min(0.1, (now - last) / 1000); last = now;
  const sp = $('speed').value / 100;
  if (playing) {
    if (t.kind === 'frames') {
      const n = arr(t.frames).shape[0]; frame += dt * sp / t.dt;
      if (frame >= n - 1) { if ($('loop').checked) frame = frame % (n - 1 || 1); else { frame = n - 1; playing = false; setBtn(); } }
    } else if (t.kind === 'anim3d') { animStep(t, dt); } else if (!isTwoD(t)) { az += dt * sp * 0.6; }
    dirty = true;
  }
  if (t.kind === 'anim3d' && gl && $('follow').checked && followTick(t, dt)) dirty = true;
  if (dirty) { dirty = false; render(); }
  requestAnimationFrame(tick);
}

/* ---------- 入力 ---------- */
$('play').onclick = () => {
  const t = get();
  if (!playing && t.kind === 'anim3d' && Math.floor(frame) >= t.t.length - 1) { atime = t.t[0]; frame = 0; }   /* 終わりからは頭へ */
  playing = !playing; setBtn(); last = performance.now(); dirty = true; };
$('b1').onclick = () => { playing = false; setBtn(); seekFrame(get(), Math.floor(frame) - 1); };
$('f1').onclick = () => { playing = false; setBtn(); seekFrame(get(), Math.floor(frame) + 1); };
$('evp').onclick = () => { const t = get(), f = Math.floor(frame); let k = 0; for (const e of t.events) if (e.k < f) k = e.k; seekFrame(t, k); };
$('evn').onclick = () => { const t = get(), f = Math.floor(frame), e = t.events.find(e => e.k > f); if (e) seekFrame(t, e.k); };
$('follow').onchange = () => { const t = get(); if (t.kind === 'anim3d' && gl) { const S = sceneAnim(t); if (!$('follow').checked) S.tgt = S.ctr.slice(); } dirty = true; };
document.addEventListener('keydown', e => {
  const t = get(); if (t.kind !== 'anim3d' || /^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName)) return;
  if (e.key === ' ') { e.preventDefault(); $('play').onclick(); }
  else if (e.key === 'ArrowLeft') { e.preventDefault(); $('b1').onclick(); }
  else if (e.key === 'ArrowRight') { e.preventDefault(); $('f1').onclick(); }
});
$('lang').onchange = e => { L = e.target.value; try { const u = new URL(location.href); u.searchParams.set('lang', L); history.replaceState(null, '', u); } catch (e) {} renderText(); dirty = true; };
$('scrub').oninput = e => {
  const t = get(); playing = false; setBtn();
  if (t.kind === 'anim3d') { seekFrame(t, Math.round(e.target.value / 1000 * (t.t.length - 1))); return; }
  if (t.kind === 'frames') frame = e.target.value / 1000 * (arr(t.frames).shape[0] - 1); else az = e.target.value / 1000 * 2 * Math.PI;
  dirty = true;
};
document.querySelectorAll('[data-v]').forEach(b => b.onclick = () => { const t = get(), S = scene3d(t), v = PRESETS[b.dataset.v]; az = v[0]; el = v[1]; dist = dist0(S); dirty = true; });
const pts = new Map(); let pinch = 0;
function target(){ return isTwoD(get()) ? c2 : cv; }
function splitMove(e){ const r = c2.getBoundingClientRect(); splitX = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)); dirty = true; }
[cv, c2].forEach(el_ => {
  el_.addEventListener('pointerdown', e => { el_.setPointerCapture(e.pointerId); pts.set(e.pointerId, {x: e.clientX, y: e.clientY});
    if (pts.size === 2) { const a = [...pts.values()]; pinch = Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y); }
    if (get().kind === 'split' && el_ === c2) splitMove(e); });
  el_.addEventListener('pointermove', e => {
    const p = pts.get(e.pointerId); if (!p) return;
    if (get().kind === 'split' && el_ === c2) { splitMove(e); return; }
    if (isTwoD(get())) return;
    if (pts.size === 2) { p.x = e.clientX; p.y = e.clientY; const a = [...pts.values()], d = Math.hypot(a[0].x - a[1].x, a[0].y - a[1].y);
      if (pinch > 0) { dist = Math.min(dist0(scene3d(get())) * 8, Math.max(dist0(scene3d(get())) * 0.05, dist * pinch / d)); } pinch = d; dirty = true; return; }
    az -= (e.clientX - p.x) * 0.008; el = Math.max(-1.5, Math.min(1.5, el + (e.clientY - p.y) * 0.008));
    p.x = e.clientX; p.y = e.clientY; dirty = true; });
  const up = e => { pts.delete(e.pointerId); pinch = 0; };
  el_.addEventListener('pointerup', up); el_.addEventListener('pointercancel', up);
});
cv.addEventListener('wheel', e => { e.preventDefault(); const S = scene3d(get());
  dist = Math.min(dist0(S) * 8, Math.max(dist0(S) * 0.05, dist * Math.exp(e.deltaY * 0.0012))); dirty = true; }, {passive: false});
window.addEventListener('resize', () => { dirty = true; });

renderText(); select(cur); requestAnimationFrame(tick);
})();
"""


# 半透明の物体(bodies[*]["alpha"] < 1)がある場面だけ、_JS の _JS_ALPHA_ANCHOR の直前に差し込む塊。
# 半透明の物体の無い場面では差し込まないので、ページは alpha を足す前とバイト単位で同じになる
# (公開済みのビューア docs/view2026/viewers/*.html に drift を出さない)。
_JS_ALPHA_ANCHOR = "/* 同じ時間軸の 2-D(センサー画像・op の結果)。PNG はブラウザが無損失で復号する */\n"
_JS_ALPHA = r"""/* ---------- 半透明の物体(alpha < 1)。この塊は半透明の物体がある場面だけページに入る ----------
   描く順: 不透明の物体 → 軌跡 → 点群(ここまで drawAnimOpaque)→ 半透明の物体。軌跡と点群が深度を書いた後に、
   半透明の物体を BLEND・depthMask(false)・深度テスト有効のまま重ねるので、レンズの中や後ろの光線が透けて見え、
   不透明の物の後ろにある部分は隠れる。半透明どうしは毎コマ、カメラから遠い順(物体の世界 AABB の中心)に並べ、
   1 物体の中は CULL_FACE で 裏面 → 表面 の 2 パス(凸形状の裏面が表面に被らない)。巻き順は物体ごとに符号付き体積で
   確かめ、内向き(体積 < 0)なら 2 パスの順を入れ替える。陰影は不透明と同じ |n·l|(両面ライティング = 法線の向きに依らない)。
   縁はフレネル風に濃く・明るく(視線と面が寝るほど alpha を 1 へ寄せる)して、薄い alpha でも輪郭が見えるようにする。 */
let TP = null;
if (gl) {
  TP = prog('attribute vec3 a_p;attribute vec3 a_n;attribute vec3 a_c;uniform mat4 u_vp;uniform mat4 u_m;varying vec3 v_n;varying vec3 v_c;varying vec3 v_w;'+
    'void main(){vec4 w=u_m*vec4(a_p,1.0);gl_Position=u_vp*w;v_w=w.xyz;v_n=(u_m*vec4(a_n,0.0)).xyz;v_c=a_c;}',
    'precision mediump float;varying vec3 v_n;varying vec3 v_c;varying vec3 v_w;uniform vec3 u_l;uniform vec3 u_eye;uniform float u_a;'+
    'void main(){vec3 n=normalize(v_n);float c=abs(dot(n,normalize(u_eye-v_w)));float r=pow(1.0-c,3.0);'+
    'float d=abs(dot(n,u_l))*0.65+0.38;float a=clamp(u_a+(1.0-u_a)*0.75*r,0.0,1.0);'+
    'gl_FragColor=vec4(min(v_c*d+0.3*r,vec3(1.0)),a);}');
}
const transl = {};
/* 半透明の物体の一覧(場面ごとに 1 回): 番号・alpha・局所 AABB の中心・巻き順が内向きか */
function translOf(tab){
  if (transl[tab.id]) return transl[tab.id];
  const L = [];
  tab.bodies.forEach((b, j) => {
    if (b.alpha == null || !(b.alpha < 1)) return;
    const P = arr(b.pos).a, F = arr(b.faces).a, lo = [Infinity,Infinity,Infinity], hi = [-Infinity,-Infinity,-Infinity];
    for (let i = 0; i < P.length; i += 3) for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], P[i+k]); hi[k] = Math.max(hi[k], P[i+k]); }
    const c = [0,1,2].map(k => (lo[k] + hi[k]) / 2);
    let vol = 0;                                    /* 6 × 符号付き体積(中心からの四面体の和)。外向き = 正 */
    for (let f = 0; f < F.length; f += 3) {
      const a = F[f]*3, q = F[f+1]*3, r = F[f+2]*3;
      const ax = P[a]-c[0], ay = P[a+1]-c[1], az_ = P[a+2]-c[2], bx = P[q]-c[0], by = P[q+1]-c[1], bz = P[q+2]-c[2];
      const cx = P[r]-c[0], cy = P[r+1]-c[1], cz = P[r+2]-c[2];
      vol += ax*(by*cz-bz*cy) + ay*(bz*cx-bx*cz) + az_*(bx*cy-by*cx);
    }
    L.push({j, a: b.alpha, c, inward: vol < 0});
  });
  return transl[tab.id] = L;
}
const drawAnimOpaque = drawAnim;
drawAnim = function(tab){
  const S = sceneAnim(tab), L = S.fail || !TP ? [] : translOf(tab);
  if (!L.length) { drawAnimOpaque(tab); return; }
  const keep = L.map(e => S.bodies[e.j].count);
  L.forEach(e => { S.bodies[e.j].count = 0; });   /* 不透明のパスでは描かない(drawElements の 0 個は何も描かない) */
  try { drawAnimOpaque(tab); } finally { L.forEach((e, i) => { S.bodies[e.j].count = keep[i]; }); }
  if (AP && LP && PP) drawTranslucent(tab, S, L);
};
function drawTranslucent(tab, S, L){
  const f = Math.max(0, Math.min(tab.t.length - 1, Math.floor(frame)));
  /* カメラは drawAnim と同じ式(テストが両方の式の一致を見ている) */
  const tg = $('follow').checked ? S.tgt : S.ctr;
  const cd = Math.cos(el), sd = Math.sin(el), ca = Math.cos(az), sa = Math.sin(az);
  const eye = [tg[0] + dist*cd*ca, tg[1] + dist*cd*sa, tg[2] + dist*sd];
  const fy = 0.9, vp = mul(persp(fy, cv.width/cv.height, S.rad*0.02, S.rad*40), look(eye, tg, [0,0,1]));
  let l = [ca*cd*0.5, sa*cd*0.5, sd*0.5 + 0.5]; const ll = Math.hypot(l[0], l[1], l[2]); l = l.map(v => v/ll);
  const order = L.map(e => {
    const o = f*S.B + e.j, m = quatMat(S.Q[o*4], S.Q[o*4+1], S.Q[o*4+2], S.Q[o*4+3], S.X[o*3], S.X[o*3+1], S.X[o*3+2]), c = e.c;
    const w = [m[0]*c[0]+m[4]*c[1]+m[8]*c[2]+m[12], m[1]*c[0]+m[5]*c[1]+m[9]*c[2]+m[13], m[2]*c[0]+m[6]*c[1]+m[10]*c[2]+m[14]];
    return {e, m, d: Math.hypot(w[0]-eye[0], w[1]-eye[1], w[2]-eye[2])};
  }).sort((p, q) => q.d - p.d);                   /* 遠い順 */
  gl.useProgram(TP);
  const lp = gl.getAttribLocation(TP, 'a_p'), ln = gl.getAttribLocation(TP, 'a_n'), lc = gl.getAttribLocation(TP, 'a_c');
  const um = gl.getUniformLocation(TP, 'u_m'), ua = gl.getUniformLocation(TP, 'u_a');
  gl.uniform3f(gl.getUniformLocation(TP, 'u_l'), l[0], l[1], l[2]);
  gl.uniform3f(gl.getUniformLocation(TP, 'u_eye'), eye[0], eye[1], eye[2]);
  gl.uniformMatrix4fv(gl.getUniformLocation(TP, 'u_vp'), false, vp);
  gl.enableVertexAttribArray(lp); gl.enableVertexAttribArray(ln); gl.enableVertexAttribArray(lc);
  gl.enable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  gl.depthMask(false); gl.enable(gl.CULL_FACE);
  for (const it of order) {
    const b = S.bodies[it.e.j];
    gl.bindBuffer(gl.ARRAY_BUFFER, b.pos); gl.vertexAttribPointer(lp, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, b.nrm); gl.vertexAttribPointer(ln, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, b.col); gl.vertexAttribPointer(lc, 3, gl.UNSIGNED_BYTE, true, 0, 0);
    gl.uniformMatrix4fv(um, false, it.m);
    gl.uniform1f(ua, it.e.a);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b.idx);
    /* cullFace(FRONT) = 裏面だけ描く → cullFace(BACK) = 表面だけ描く。内向きの巻きなら逆 */
    for (const side of it.e.inward ? [gl.BACK, gl.FRONT] : [gl.FRONT, gl.BACK]) {
      gl.cullFace(side); gl.drawElements(gl.TRIANGLES, b.count, b.itype, 0);
    }
  }
  gl.disable(gl.CULL_FACE); gl.cullFace(gl.BACK); gl.depthMask(true); gl.disable(gl.BLEND);
  attrsOff();
}
"""


def _has_translucent(data: dict) -> bool:
    """詰めた仕様に alpha < 1 の物体があるか(あれば _JS_ALPHA を差し込む)。"""
    return any(t.get("kind") == "anim3d" and any("alpha" in b for b in t.get("bodies", ()))
               for t in data.get("tabs", ()))


def _build_html(spec: dict, lang="ja") -> str:
    """仕様から HTML 文字列を作る(検査はここで行う)。``lang`` は :func:`_pack_spec` と同じ。"""
    data = _pack_spec(spec, lang)
    blob = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    js = _JS
    if _has_translucent(data):                           # 半透明の物体がある場面だけ(無ければ今と同じページ)
        if js.count(_JS_ALPHA_ANCHOR) != 1:
            raise AssertionError("半透明の塊の差し込み位置が 1 回でない")
        js = js.replace(_JS_ALPHA_ANCHOR, _JS_ALPHA + _JS_ALPHA_ANCHOR)
    js = js.replace("__DATA__", blob)
    if js.count(blob) != 1:
        raise AssertionError("DATA の差し込みが 1 回でない")
    title = html.escape(data["title"][data["langs"][0]])
    return ("<!doctype html>\n<html lang=\"%s\">\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
            "<title>%s</title>\n<style>%s</style>\n%s\n<script>%s</script>\n</html>\n" % (data["langs"][0], title, _CSS, _BODY, js))


def write_viewer(spec: dict, path, lang="ja") -> str:
    """HTML を書いて、書いたパス(文字列)を返す。仕様が不正なら何も書かず ``ValueError``。

    ``lang="ja"`` は単言語のページ。``lang=["ja", "en", ...]`` は言語の切り替えつきで、先頭が既定。
    対応は ja / en / zh / tw / ko / de / hi / fr。URL の ``?lang=xx`` で開く言語を選べる。
    """
    text = _build_html(spec, lang)                      # 検査はここで終わる(書く前に落とす)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
    return str(p)


# --------------------------------------------------------------------------- #
# 仕様を組み立てる道具(辞書を手で書かなくてよいように)                            #
# --------------------------------------------------------------------------- #
def viewer_text(ja: str, en: str, **others: str) -> dict:
    """言語ごとの文字列の辞書。``viewer_text("日本語", "English", zh="中文", de="Deutsch")``。

    ``others`` のキーは ``LANGS``(zh / tw / ko / de / hi / fr)だけ。要求した言語に足りない訳は
    書き出し時に ``ValueError`` で止まる(黙って他言語で補わない)。
    """
    bad = [k for k in others if k not in LANGS]
    if bad:
        raise ValueError("未対応の言語 %s(対応: %s)" % (bad, ", ".join(LANGS)))
    return {"ja": ja, "en": en, **others}


def viewer_number(label: dict, value) -> dict:
    """カードに出す実測の数字 1 つ。``value`` は文字列(両言語共通)か :func:`viewer_text`。"""
    return {"label": label, "value": value}


def _tab(kind: str, tab_id: str, label: dict, badge: str, text: dict, numbers, extra: dict) -> dict:
    d = {"id": tab_id, "kind": kind, "label": label, "badge": badge, "text": text,
         "numbers": list(numbers or [])}
    d.update({k: v for k, v in extra.items() if v is not None})
    return d


def viewer_mesh_tab(tab_id, label, badge, text, pos, faces, val, cbar, numbers=None, view=None) -> dict:
    """三角形メッシュ + 頂点ごとの値(色)+ カラーバーのタブ。"""
    return _tab("mesh", tab_id, label, badge, text, numbers,
                {"pos": pos, "faces": faces, "val": val, "cbar": cbar, "view": view})


def viewer_points_tab(tab_id, label, badge, text, pos, val=None, cbar=None, rgb=None, ghost=None,
                      point_size=None, numbers=None, view=None) -> dict:
    """点群のタブ。``val`` + ``cbar``(値の色)か ``rgb``(点ごとの色)。``ghost`` は灰色の参照点群。"""
    return _tab("points", tab_id, label, badge, text, numbers,
                {"pos": pos, "val": val, "cbar": cbar, "rgb": rgb, "ghost": ghost,
                 "point_size": point_size, "view": view})


def viewer_frames_tab(tab_id, label, badge, text, frames, dt=0.2, boxes=None, series=None,
                      numbers=None, png=False) -> dict:
    """2-D の画像列のタブ。``boxes`` は重ねる枠(真値と推定)、``series`` は時系列グラフ。

    ``png=True`` ならコマを無損失の PNG で埋める(画素は 1 つも変えない。生の u8 より小さいことが多い)。
    """
    return _tab("frames", tab_id, label, badge, text, numbers,
                {"frames": frames, "dt": dt, "boxes": boxes or [], "series": series or [],
                 "png": True if png else None})


def viewer_split_tab(tab_id, label, badge, text, before, after, label_before, label_after,
                     numbers=None) -> dict:
    """前後の画像を、ドラッグで動く分割線で比べるタブ。"""
    return _tab("split", tab_id, label, badge, text, numbers,
                {"before": before, "after": after, "label_before": label_before,
                 "label_after": label_after})


def viewer_anim3d_tab(tab_id, label, badge, text, t, bodies, xyz, quat, trails=None, clouds=None,
                      events=None, series=None, panes=None, cbar=None, follow=None, numbers=None,
                      view=None) -> dict:
    """動く 3-D のタブ: 物体ごとの剛体姿勢をコマごとに再生する(2-D の画像列・時系列も同じ時間軸で)。

    物体のメッシュは **1 回だけ** 持ち、コマごとには姿勢(位置 + 四元数)だけを持つ。ページでは
    ドラッグで回す・ホイール/ピンチで拡大・視点ボタン・再生/一時停止・コマ送り/戻し・スライダ・
    速度(0.25〜4 倍)・ループ・段へのジャンプ・カメラの追従(平滑化して揺らさない)ができる。
    キーボードでは空白で再生/一時停止、← → でコマ送り。

    Parameters
    ----------
    t : (T,)
        各コマの時刻 [秒]。狭義の増加(等間隔でなくてよい。再生は t に従う)。
    bodies : list of dict
        ``{"name": str, "pos": (N,3) 物体のローカル座標, "faces": (M,3) int,
        "rgb": (3,) か (N,3)(uint8 か 0..1)| "val": (N,)(+ ``cbar``), "label": 文字列の辞書(任意)}``。
        色は rgb か val のどちらか 1 つ。未知の鍵(``"color": "red"`` など)は ``ValueError``。
        ``"alpha": float``(任意、0 < alpha <= 1、既定 1 = 不透明)で半透明にする(レンズ・ガラス板・
        ビームスプリッタなど)。半透明の物体は不透明の物体・軌跡・点群の **後に**、カメラから遠い順に重ねて
        描くので、中や後ろを通る軌跡(光線)が透けて見える。縁は少し濃く出る。目安は 0.25〜0.35。
        範囲外・NaN・bool・文字列は ``ValueError``。alpha が 1 だけの場面のページは alpha を使わない場面と同じ。
    xyz : (T,B,3)
        各コマの物体の位置(ローカル原点の世界座標)。B = ``len(bodies)``。
    quat : (T,B,4)
        各コマの物体の姿勢の四元数 **(w, x, y, z)**。正規化して w>=0 に揃えてから int16 にする
        (q と -q は同じ回転)。ノルム 0 は ``ValueError``。世界座標 = R(quat) @ pos + xyz。
    trails : list of dict, optional
        軌跡の線。``{"body": name, "offset": (3,) ローカル点}`` か ``{"xyz": (T,3)}``、
        ``"color": "#rrggbb"``、``"tail": 秒``(0 = 全履歴。正なら残像として古い部分が薄れる)。
    clouds : list of dict, optional
        点群の時系列(少数のコマ)。``{"k": コマ番号, "pos": (N,3) 世界座標, "rgb": (N,3) | "color": "#rrggbb",
        "point_size": 世界単位}``。k から次の雲の k まで表示する。k は狭義の増加。
    events : list of dict, optional
        段の区切り ``{"t": 秒, "label": 文字列の辞書}``。ジャンプのボタンとグラフの縦線になる。
    series : list of dict, optional
        時系列グラフ(:func:`viewer_frames_tab` と同じ形、``values`` は (T,))。
    panes : list of dict, optional
        同じ時間軸で並べる 2-D(センサー画像・op の結果)。``{"label": ..., "frames": (T,H,W[,3]),
        "boxes": [...](frames と同じ形), "png": True}``。既定は無損失の PNG で埋める(画素は変えない)。
    cbar : dict, optional
        ``val`` で色づけする物体があるときのカラーバー ``{lo, hi, unit, cmap, label}``。
    follow : str, optional
        追従するときに注視する物体の name(無ければ全物体の位置の平均)。追従は既定で切。

    容量: 位置は軸ごとの uint16(刻み = 範囲/65535)、四元数は int16(刻み 1/32767)、メッシュは 1 回だけ。
    コマ数 T が合わない(xyz / quat / series / panes / 軌跡)、NaN / inf、範囲外の索引、未知の色指定は
    ``ValueError``(黙って通さない)。

    Examples
    --------
    >>> import numpy as np, fullseye as fs
    >>> cube = np.array([[x, y, z] for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)])
    >>> tri = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
    ...        [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    >>> T = 60; t = np.arange(T) / 30.0; ang = np.pi * t
    >>> xyz = np.stack([np.cos(ang), np.sin(ang), 0 * t], -1)[:, None, :]          # (T,1,3)
    >>> quat = np.stack([np.cos(ang / 2), 0 * t, 0 * t, np.sin(ang / 2)], -1)[:, None, :]  # z 軸まわり
    >>> tab = fs.viewer_anim3d_tab(
    ...     "spin", fs.viewer_text("回る箱", "A spinning box"), "passed",
    ...     fs.viewer_text("円を描いて回る。", "It goes round."), t,
    ...     [{"name": "box", "pos": cube, "faces": tri, "rgb": [79, 195, 247]}], xyz, quat,
    ...     trails=[{"body": "box", "color": "#ffd54f", "tail": 0.5}],
    ...     events=[{"t": 1.0, "label": fs.viewer_text("半周", "Half a turn")}])
    >>> spec = fs.viewer_spec("spin", fs.viewer_text("見本", "Sample"), fs.viewer_text("副題", "Sub"),
    ...                       fs.viewer_text("操作", "Hint"), [tab])
    >>> html = fs.pocviewer._build_html(spec, ["ja", "en"])                         # write_viewer で書く
    """
    return _tab("anim3d", tab_id, label, badge, text, numbers,
                {"t": t, "bodies": list(bodies), "xyz": xyz, "quat": quat, "trails": list(trails or []),
                 "clouds": list(clouds or []), "events": list(events or []), "series": list(series or []),
                 "panes": list(panes or []), "cbar": cbar, "follow": follow, "view": view})


def viewer_spec(viewer_id: str, title: dict, subtitle: dict, hint: dict, tabs, credit=None) -> dict:
    """ビューア全体の仕様。``tabs`` は ``viewer_*_tab`` の戻り値の列(空は不可)。"""
    tabs = list(tabs)
    if not tabs:
        raise ValueError("tabs が空(タブが 1 つも無いビューアは作らない)")
    return {"id": viewer_id, "title": title, "subtitle": subtitle, "hint": hint, "tabs": tabs,
            "credit": credit}


__all__ = [
    "BADGES", "UI", "LANGS", "LANG_NAMES", "KINDS", "viewer_text", "viewer_number", "viewer_spec", "viewer_mesh_tab",
    "viewer_points_tab", "viewer_frames_tab", "viewer_split_tab", "viewer_anim3d_tab", "write_viewer",
]


def _main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec", help="JSON の仕様(配列は入れ子の list)")
    ap.add_argument("out", help="出力の HTML")
    ap.add_argument("--lang", default="ja", help="言語(カンマ区切りで複数。先頭が既定): " + ",".join(LANGS))
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    out = write_viewer(spec, a.out, a.lang.split(","))
    print("wrote %s (%d bytes)" % (out, Path(out).stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
