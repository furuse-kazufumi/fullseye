# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""3D Gaussian Splatting をブラウザで見せる 1 枚の HTML を書く(商品の閲覧・展示会場のオフライン端末向け)。

何をするか:
  * :func:`gs_viewer_html` —— 1 つの 3DGS(:func:`gsplatnp.gs_read_file` / :func:`gsplatnp.gs_from_world` の dict、
    または .ply / .splat のパス)を、外部読み込みの無い 1 枚の HTML にする。データは量子化して gzip → base64 で
    ページに埋め、ブラウザ標準の ``DecompressionStream('gzip')`` で伸ばす。WebGL2 でインスタンス化した四角形を描き、
    2-D 共分散は :func:`gsplatnp.gs_render` と同じ式 Σ' = J W Σ Wᵀ Jᵀ + 0.3 px²(Mip-Splatting の不透明度補正つき)、
    前後の並べ替えは Web Worker(視点が変わったときだけ)、α 合成は手前から C = Σ c_i α_i T_i。
  * :func:`gs_catalog_html` —— 複数の 3DGS をサムネイルの一覧から選んで見るカタログの 1 枚。サムネイルは Python 側で
    :func:`gsplatnp.gs_render` が描いた PNG。選んだ品だけを伸ばし、切り替えると前の品の GPU の資源を解放する。
  * 寸法: :func:`measure3d.smallest_box3`(最小体積の外形の箱)を不透明なガウシアンの中心に当て、上向きの軸に
    いちばん近い辺を H、残りを W ≥ D として mm で重ねる。

正直な注記:
  * 色は球面調和(SH)の 0 次だけを使う。視点で変わる成分(光沢・映り込み)は捨てる。捨てた次数は返り値と
    ページの両方に書く。
  * :func:`gsplatnp.gs_from_world` の 3DGS(メッシュから初期化)は、陰影を世界に固定した光で色へ焼き込む
    (``bake_light``)。写真から学習した 3DGS ではない —— ページの注記(``note``)で利用者に伝える。
  * 並べ替えはガウシアンの中心の深さを 16 bit の桶で数える(ブラウザ)。gs_render は画素ごとに厳密な深さ順。
    差はほぼ同じ深さのガウシアンの重なり順と、8 bit の表示の丸めだけ(門 tests/test_gsviewer.py が実測で見る)。
  * 容量の上限(既定 16 MB)を超えるときは、不透明度の小さい順(同じなら大きさの小さい順)に間引き、
    間引いた数を返り値の ``thinning`` とページの両方に出す。黙って減らさない。
"""
from __future__ import annotations

import base64
import gzip
import html as _html
import json
import os
from typing import Any

import numpy as np

__all__ = ["gs_viewer_html", "gs_catalog_html"]

#: 対応言語と自称は pocviewer と同じ(同じ切り替えの作法: ``?lang=xx`` → navigator.language → 先頭)。
from pocviewer import LANGS, LANG_NAMES, _JS_PICK_LANG  # noqa: E402

#: 既定の容量の上限(Artifact の上限と同じ 16 MB)。
DEFAULT_MAX_BYTES = 16 * 1024 * 1024
#: 1 ガウシアンあたりの埋め込みの大きさ(位置 3×u16 + log 大きさ 3×u16 + 四元数 4×u8 + RGBA 4×u8)。
BYTES_PER_SPLAT = 20
#: 背景の 3 色(ページの「白・灰・黒」)。gs_render の ``sky`` にもそのまま渡せる 0..1 の値。
BACKGROUNDS = {"white": (1.0, 1.0, 1.0), "gray": (0.5, 0.5, 0.5), "black": (0.0, 0.0, 0.0)}


def _t(ja, en, zh, tw, ko, de, hi, fr):
    return dict(zip(LANGS, (ja, en, zh, tw, ko, de, hi, fr)))


#: ページの固定文言(8 言語)。
UI: dict[str, dict[str, str]] = {
    "front": _t("正面", "Front", "正面", "正面", "정면", "Vorne", "सामने", "Face"),
    "side": _t("側面", "Side", "侧面", "側面", "측면", "Seite", "बगल", "Côté"),
    "top": _t("上", "Top", "顶部", "頂部", "위", "Oben", "ऊपर", "Dessus"),
    "iso": _t("斜め", "3/4 view", "斜视", "斜視", "비스듬히", "Schräg", "तिरछा", "3/4"),
    "spin": _t("回転台", "Turntable", "转台", "轉台", "회전대", "Drehteller", "घूमता मंच", "Plateau tournant"),
    "bg": _t("背景", "Background", "背景", "背景", "배경", "Hintergrund", "पृष्ठभूमि", "Fond"),
    "white": _t("白", "White", "白", "白", "흰색", "Weiß", "सफ़ेद", "Blanc"),
    "gray": _t("灰", "Grey", "灰", "灰", "회색", "Grau", "धूसर", "Gris"),
    "black": _t("黒", "Black", "黑", "黑", "검정", "Schwarz", "काला", "Noir"),
    "dims": _t("寸法", "Dimensions", "尺寸", "尺寸", "치수", "Maße", "माप", "Dimensions"),
    "opacity": _t("不透明度のしきい値", "Opacity threshold", "不透明度阈值", "不透明度閾值", "불투명도 임계값",
                  "Deckkraft-Schwelle", "अपारदर्शिता सीमा", "Seuil d’opacité"),
    "quality": _t("品質(ガウシアンの数)", "Quality (number of Gaussians)", "质量(高斯数量)", "品質(高斯數量)",
                  "품질(가우시안 수)", "Qualität (Anzahl der Gaußfunktionen)", "गुणवत्ता (गॉसियन की संख्या)",
                  "Qualité (nombre de gaussiennes)"),
    "shown": _t("表示中", "Showing", "显示中", "顯示中", "표시 중", "Angezeigt", "दिखाए जा रहे", "Affichées"),
    "about": _t("この表示について", "About this view", "关于此显示", "關於此顯示", "이 표시에 대해", "Über diese Ansicht",
                "इस दृश्य के बारे में", "À propos de cet affichage"),
    "close": _t("閉じる", "Close", "关闭", "關閉", "닫기", "Schließen", "बंद करें", "Fermer"),
    "back": _t("一覧に戻る", "Back to the list", "返回列表", "返回列表", "목록으로", "Zurück zur Liste", "सूची पर लौटें",
               "Retour à la liste"),
    "pick": _t("見たい品を選んでください", "Choose an item to view", "请选择要查看的物品", "請選擇要查看的物品",
               "보고 싶은 항목을 고르세요", "Wählen Sie ein Objekt", "देखने के लिए कोई वस्तु चुनें",
               "Choisissez un objet à afficher"),
    "help": _t("ドラッグで回転・ホイール / ピンチで拡大", "Drag to rotate · wheel / pinch to zoom", "拖动旋转 · 滚轮 / 双指缩放",
               "拖曳旋轉 · 滾輪 / 雙指縮放", "드래그로 회전 · 휠 / 핀치로 확대", "Ziehen zum Drehen · Rad / Zwei Finger zum Zoomen",
               "घुमाने के लिए खींचें · ज़ूम के लिए व्हील / पिंच", "Glisser pour tourner · molette / pincer pour zoomer"),
    "loading": _t("読み込み中…", "Loading…", "加载中…", "載入中…", "불러오는 중…", "Wird geladen…", "लोड हो रहा है…",
                  "Chargement…"),
    "nogl": _t("このブラウザでは WebGL2 が使えないため表示できません。", "This browser has no WebGL2, so the model cannot be shown.",
               "此浏览器不支持 WebGL2,无法显示。", "此瀏覽器不支援 WebGL2,無法顯示。", "이 브라우저는 WebGL2를 지원하지 않아 표시할 수 없습니다.",
               "Dieser Browser hat kein WebGL2; das Modell kann nicht angezeigt werden.",
               "इस ब्राउज़र में WebGL2 नहीं है, इसलिए मॉडल नहीं दिखाया जा सकता।",
               "Ce navigateur n’a pas WebGL2 : le modèle ne peut pas être affiché."),
    "sh": _t("色は球面調和の 0 次だけで描いています(視点で変わる光沢・映り込みは捨てています)。",
             "Colour uses only the 0th-order spherical harmonic (view-dependent gloss and reflections are dropped).",
             "颜色仅使用 0 阶球谐函数(舍弃了随视角变化的光泽与反射)。",
             "顏色僅使用 0 階球諧函數(捨棄了隨視角變化的光澤與反射)。",
             "색은 0차 구면 조화만 사용합니다(시점에 따라 달라지는 광택·반사는 버렸습니다).",
             "Die Farbe nutzt nur die Kugelflächenfunktion 0. Ordnung (blickabhängiger Glanz und Spiegelungen fehlen).",
             "रंग केवल 0वें क्रम के गोलीय हार्मोनिक से है (दृष्टि पर निर्भर चमक और प्रतिबिंब हटाए गए हैं)।",
             "La couleur n’utilise que l’harmonique sphérique d’ordre 0 (brillance et reflets dépendant de la vue omis)."),
    "thin": _t("容量の上限に収めるため、{k} 個のガウシアンを間引きました(元 {n} 個。不透明度・大きさの小さい順)。",
               "{k} Gaussians were removed to fit the size limit (of {n}; lowest opacity, then smallest, first).",
               "为符合容量上限,删减了 {k} 个高斯(原有 {n} 个;按不透明度、大小从小到大)。",
               "為符合容量上限,刪減了 {k} 個高斯(原有 {n} 個;按不透明度、大小由小到大)。",
               "용량 한도에 맞추려고 가우시안 {k}개를 줄였습니다(원래 {n}개, 불투명도·크기가 작은 순).",
               "{k} Gaußfunktionen wurden für die Größengrenze entfernt (von {n}; geringste Deckkraft, dann kleinste zuerst).",
               "आकार सीमा में लाने के लिए {k} गॉसियन हटाए गए ({n} में से; सबसे कम अपारदर्शिता, फिर सबसे छोटे पहले)।",
               "{k} gaussiennes ont été retirées pour tenir dans la limite ({n} au total ; opacité la plus faible, puis les plus petites)."),
    "dimnote": _t("寸法 = 不透明なガウシアンの中心に当てた最小体積の外形の箱(W × D × H、mm)。",
                  "Dimensions = minimum-volume box around the centres of the opaque Gaussians (W × D × H, mm).",
                  "尺寸 = 包围不透明高斯中心的最小体积外接盒(W × D × H,mm)。",
                  "尺寸 = 包圍不透明高斯中心的最小體積外接盒(W × D × H,mm)。",
                  "치수 = 불투명한 가우시안 중심을 감싸는 최소 부피 상자(W × D × H, mm).",
                  "Maße = Quader minimalen Volumens um die Zentren der deckenden Gaußfunktionen (B × T × H, mm).",
                  "माप = अपारदर्शी गॉसियन के केंद्रों के चारों ओर न्यूनतम आयतन का बक्सा (W × D × H, mm)।",
                  "Dimensions = boîte de volume minimal autour des centres des gaussiennes opaques (L × P × H, mm)."),
    "hotspots": _t("注記", "Notes", "注释", "註記", "주석", "Hinweise", "टिप्पणियाँ", "Annotations"),
    "lang": _t("言語", "Language", "语言", "語言", "언어", "Sprache", "भाषा", "Langue"),
}


# ───────────────────────────── 入力を 1 つの形にそろえる ───────────────────────────── #
def _quat_from_mat(R: np.ndarray) -> np.ndarray:
    """回転行列 (N,3,3) → 単位四元数 (N,4) wxyz(w ≥ 0)。Shepperd の分岐で数値的に安定。"""
    N = len(R)
    q = np.empty((N, 4))
    tr = R[:, 0, 0] + R[:, 1, 1] + R[:, 2, 2]
    d = np.stack([tr, R[:, 0, 0], R[:, 1, 1], R[:, 2, 2]], axis=1)
    k = np.argmax(d, axis=1)
    for case in range(4):
        m = k == case
        if not m.any():
            continue
        r = R[m]
        if case == 0:
            s = np.sqrt(1.0 + tr[m]) * 2.0
            q[m] = np.column_stack([0.25 * s, (r[:, 2, 1] - r[:, 1, 2]) / s, (r[:, 0, 2] - r[:, 2, 0]) / s,
                                    (r[:, 1, 0] - r[:, 0, 1]) / s])
        elif case == 1:
            s = np.sqrt(1.0 + r[:, 0, 0] - r[:, 1, 1] - r[:, 2, 2]) * 2.0
            q[m] = np.column_stack([(r[:, 2, 1] - r[:, 1, 2]) / s, 0.25 * s, (r[:, 0, 1] + r[:, 1, 0]) / s,
                                    (r[:, 0, 2] + r[:, 2, 0]) / s])
        elif case == 2:
            s = np.sqrt(1.0 + r[:, 1, 1] - r[:, 0, 0] - r[:, 2, 2]) * 2.0
            q[m] = np.column_stack([(r[:, 0, 2] - r[:, 2, 0]) / s, (r[:, 0, 1] + r[:, 1, 0]) / s, 0.25 * s,
                                    (r[:, 1, 2] + r[:, 2, 1]) / s])
        else:
            s = np.sqrt(1.0 + r[:, 2, 2] - r[:, 0, 0] - r[:, 1, 1]) * 2.0
            q[m] = np.column_stack([(r[:, 1, 0] - r[:, 0, 1]) / s, (r[:, 0, 2] + r[:, 2, 0]) / s,
                                    (r[:, 1, 2] + r[:, 2, 1]) / s, 0.25 * s])
    q /= np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-300)
    q[q[:, 0] < 0] *= -1.0
    return q


def _mat_from_quat(q: np.ndarray) -> np.ndarray:
    """単位四元数 (N,4) wxyz → 回転行列 (N,3,3)(ブラウザ側と同じ式)。"""
    q = q / np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-300)
    w, x, y, z = q.T
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)], axis=1),
        np.stack([2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)], axis=1),
        np.stack([2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)], axis=1)], axis=1)


def _ply_sh_degree(path) -> int:
    """3DGS の PLY のヘッダから球面調和の次数を数える(f_rest_* の数 = 3((L+1)² − 1))。読めなければ 0。"""
    try:
        with open(path, "rb") as f:
            head = f.read(65536)
    except OSError:
        return 0
    end = head.find(b"end_header")
    if end < 0:
        return 0
    n_rest = sum(1 for w in head[:end].decode("ascii", "replace").split() if w.startswith("f_rest_"))
    L = 0
    while 3 * ((L + 2) ** 2 - 1) <= n_rest:
        L += 1
    return L


def _canon(gs, *, bake_light=(0.3, -0.5, 0.8), ambient: float = 0.35, min_scale: float = 1e-7) -> dict:
    """どの入力も ``{mu (N,3), scale (N,3), rot (N,4) wxyz, rgb (N,3), opacity (N,), sh_degree_in, source}`` にそろえる。

    * パス(str / PathLike)→ :func:`gsplatnp.gs_read_file`(.ply の球面調和の次数はヘッダから数える)。
    * gs_read_file の dict(``xyz`` / ``scale`` / ``rot`` / ``rgb``)→ そのまま。
    * gs_from_world の dict(``mu`` / ``R`` / ``cov_t`` / ``sigma_n`` / ``color`` / ``normal``)→ 世界の共分散
      Σ = R diag(cov_t, σn²) Rᵀ を固有分解して大きさと向きに直す。色は ``bake_light``(世界の座標の光の向き)で
      gs_render と同じ Lambert ``ambient + (1 − ambient)|n·l|`` を焼き込む(``bake_light=None`` なら焼かない)。
    """
    import gsplatnp as _g
    sh_in, source = 0, "dict"
    if isinstance(gs, (str, os.PathLike)):
        p = os.fspath(gs)
        if p.lower().endswith(".ply"):
            sh_in = _ply_sh_degree(p)
        source = os.path.basename(p)
        gs = _g.gs_read_file(p)
    if not isinstance(gs, dict) or len(gs) == 0:
        raise ValueError("gs_viewer_html: gs must be a non-empty dict (gs_read_file / gs_from_world) or a .ply/.splat path")
    if "mu" in gs and "scale" in gs and "rot" in gs and "rgb" in gs:     # すでにそろえた形(_canon / _decode の返り値)
        mu = np.asarray(gs["mu"], np.float64)
        scale = np.asarray(gs["scale"], np.float64)
        rot = np.asarray(gs["rot"], np.float64)
        rgb = np.asarray(gs["rgb"], np.float64)
        op = np.asarray(gs["opacity"], np.float64)
        sh_in = max(sh_in, int(gs.get("sh_degree_in", 0) or 0))
        source = gs.get("source", source)
    elif "xyz" in gs:
        mu = np.asarray(gs["xyz"], np.float64)
        scale = np.asarray(gs.get("scale", np.zeros_like(mu)), np.float64)
        rot = np.asarray(gs.get("rot", np.tile([1.0, 0, 0, 0], (len(mu), 1))), np.float64)
        rgb = np.asarray(gs["rgb"], np.float64)
        op = np.asarray(gs["opacity"], np.float64)
        sh_in = max(sh_in, int(gs.get("sh_degree", 0) or 0))
    elif "mu" in gs and "R" in gs:
        mu = np.asarray(gs["mu"], np.float64)
        R = np.asarray(gs["R"], np.float64)
        N = len(mu)
        Sl = np.zeros((N, 3, 3))
        Sl[:, :2, :2] = np.asarray(gs["cov_t"], np.float64)
        Sl[:, 2, 2] = np.asarray(gs["sigma_n"], np.float64) ** 2
        Sw = np.einsum("nij,njk,nlk->nil", R, Sl, R)
        ev, V = np.linalg.eigh(Sw)
        V = np.where((np.linalg.det(V) < 0)[:, None, None], V * np.array([1.0, 1.0, -1.0]), V)
        scale = np.sqrt(np.clip(ev, 0.0, None))
        rot = _quat_from_mat(V)
        rgb = np.asarray(gs["color"], np.float64)
        if bake_light is not None:
            l = np.asarray(bake_light, np.float64)
            l = l / np.linalg.norm(l)
            n = np.asarray(gs["normal"], np.float64)
            rgb = np.clip(rgb * (ambient + (1.0 - ambient) * np.clip(np.abs(n @ l), 0.0, 1.0))[:, None], 0.0, 1.0)
        op = np.asarray(gs["opacity"], np.float64)
        source = "gs_from_world"
    else:
        raise ValueError("gs_viewer_html: unknown gs dict (need xyz/scale/rot/rgb/opacity or mu/R/cov_t/sigma_n/color)")
    N = len(mu)
    if N == 0:
        raise ValueError("gs_viewer_html: gs has no Gaussians")
    for name, a, shape in (("scale", scale, (N, 3)), ("rot", rot, (N, 4)), ("rgb", rgb, (N, 3)), ("opacity", op, (N,))):
        if a.shape != shape:
            raise ValueError("gs_viewer_html: %s has shape %s, expected %s" % (name, a.shape, shape))
    ok = np.isfinite(mu).all(1) & np.isfinite(scale).all(1) & np.isfinite(rot).all(1) & np.isfinite(rgb).all(1) & np.isfinite(op)
    if not ok.all():
        raise ValueError("gs_viewer_html: %d Gaussians have non-finite values" % int((~ok).sum()))
    ext = float(np.ptp(mu, axis=0).max()) if N > 1 else 1.0
    scale = np.maximum(scale, max(min_scale, 1e-7 * max(ext, 1e-12)))
    rot = rot / np.maximum(np.linalg.norm(rot, axis=1, keepdims=True), 1e-300)
    return {"mu": mu, "scale": scale, "rot": rot, "rgb": np.clip(rgb, 0, 1), "opacity": np.clip(op, 0, 1),
            "sh_degree_in": int(sh_in), "source": source}


def _renderable(c: dict) -> dict:
    """:func:`_canon` / :func:`_decode` の形を :func:`gsplatnp.gs_render` が描ける dict にする(門と サムネイル用)。

    R = 四元数の回転行列、``cov_t`` = diag(s0², s1²)、``sigma_n`` = s2(Σ = R diag(s²) Rᵀ と同じ)。色は焼き込み済みなので、
    gs_render には ``ambient=1.0`` を渡すと陰影が掛からない(ページと同じ色になる)。
    """
    R = _mat_from_quat(np.asarray(c["rot"], np.float64))
    s = np.asarray(c["scale"], np.float64)
    N = len(s)
    cov_t = np.zeros((N, 2, 2))
    cov_t[:, 0, 0] = s[:, 0] ** 2
    cov_t[:, 1, 1] = s[:, 1] ** 2
    return {"mu": np.asarray(c["mu"], np.float64), "R": R, "cov_t": cov_t, "sigma_n": s[:, 2], "normal": R[:, :, 2],
            "color": np.asarray(c["rgb"], np.float64), "opacity": np.asarray(c["opacity"], np.float64),
            "label": np.zeros(N, np.int64)}


# ───────────────────────────── 量子化と埋め込み ───────────────────────────── #
def _importance_order(c: dict) -> np.ndarray:
    """間引きと品質つまみの順: 不透明度の大きい順、同じなら大きさ(3 軸の積の立方根)の大きい順。先頭ほど残す。"""
    size = np.cbrt(np.prod(c["scale"], axis=1))
    return np.lexsort((-size, -c["opacity"]))


def _subset(c: dict, idx) -> dict:
    out = {k: (v[idx] if isinstance(v, np.ndarray) else v) for k, v in c.items()}
    return out


def _encode(c: dict) -> tuple[bytes, dict]:
    """列ごとの配置(位置 3×u16 → log 大きさ 3×u16 → 四元数 4×u8 → RGBA 4×u8)で量子化し gzip(mtime=0 で決定的)。

    位置は軸ごとの [lo, hi] を 65535 等分、大きさは log を [slo, shi] で 65535 等分、四元数は (q·127.5 + 127.5) を丸め、
    色と不透明度は 255 倍を丸める。返り値 = (gzip のバイト列, 復号に要る meta)。
    """
    N = len(c["mu"])
    lo = c["mu"].min(0)
    hi = c["mu"].max(0)
    span = np.where(hi - lo > 0, hi - lo, 1e-12)
    ls = np.log(c["scale"])
    slo, shi = float(ls.min()), float(ls.max())
    sspan = shi - slo if shi > slo else 1e-12
    P = np.rint((c["mu"] - lo) / span * 65535.0).clip(0, 65535).astype("<u2")
    S = np.rint((ls - slo) / sspan * 65535.0).clip(0, 65535).astype("<u2")
    Q = np.rint(c["rot"] * 127.5 + 127.5).clip(0, 255).astype(np.uint8)
    C = np.rint(np.column_stack([c["rgb"], c["opacity"]]) * 255.0).clip(0, 255).astype(np.uint8)
    raw = b"".join([P.T.tobytes(), S.T.tobytes(), Q.T.tobytes(), C.T.tobytes()])
    meta = {"n": int(N), "lo": [float(v) for v in lo], "span": [float(v) for v in span], "slo": slo, "sspan": float(sspan)}
    return gzip.compress(raw, compresslevel=9, mtime=0), meta


def _decode(blob: bytes, meta: dict) -> dict:
    """:func:`_encode` の逆(ブラウザの復号と同じ式)。門がページに埋めたデータを Python 側で戻すのに使う。"""
    raw = gzip.decompress(blob)
    N = int(meta["n"])
    if len(raw) != BYTES_PER_SPLAT * N:
        raise ValueError("gs viewer data: %d bytes for %d Gaussians (expected %d)" % (len(raw), N, BYTES_PER_SPLAT * N))
    o = 0
    P = np.frombuffer(raw, "<u2", 3 * N, o).reshape(3, N).T.astype(np.float64); o += 6 * N
    S = np.frombuffer(raw, "<u2", 3 * N, o).reshape(3, N).T.astype(np.float64); o += 6 * N
    Q = np.frombuffer(raw, np.uint8, 4 * N, o).reshape(4, N).T.astype(np.float64); o += 4 * N
    C = np.frombuffer(raw, np.uint8, 4 * N, o).reshape(4, N).T.astype(np.float64)
    mu = np.asarray(meta["lo"]) + P / 65535.0 * np.asarray(meta["span"])
    scale = np.exp(meta["slo"] + S / 65535.0 * meta["sspan"])
    rot = (Q - 127.5) / 127.5
    rot /= np.maximum(np.linalg.norm(rot, axis=1, keepdims=True), 1e-300)
    return {"mu": mu, "scale": scale, "rot": rot, "rgb": C[:, :3] / 255.0, "opacity": C[:, 3] / 255.0}


def _b64len(n: int) -> int:
    return 4 * ((n + 2) // 3)


def _fit_budget(c: dict, budget: int) -> tuple[dict, bytes, dict, dict]:
    """``budget`` バイト(base64 後)に収まるまで重要度の低い側から間引く。返り値 = (残した canon, blob, meta, 記録)。"""
    order = _importance_order(c)
    c = _subset(c, order)                       # 埋め込みは重要度の順(品質つまみ = 先頭の k 個)
    N = len(c["mu"])
    blob, meta = _encode(c)
    keep = N
    tries = 0
    while _b64len(len(blob)) > budget:
        tries += 1
        if keep <= 1 or tries > 40:
            raise ValueError("gs_viewer_html: cannot fit even one Gaussian into %d bytes (raise max_bytes)" % budget)
        keep = max(1, min(keep - 1, int(keep * budget / _b64len(len(blob)) * 0.98)))
        blob, meta = _encode(_subset(c, np.arange(keep)))
    rec = {"n_input": int(N), "n_kept": int(keep), "n_dropped": int(N - keep), "thinned": bool(keep < N),
           "order": "opacity ascending, then size ascending (dropped first)", "budget_bytes": int(budget)}
    return _subset(c, np.arange(keep)), blob, meta, rec


# ───────────────────────────── 寸法(Fullseye の op)───────────────────────────── #
def _farthest_points(P: np.ndarray, k: int) -> np.ndarray:
    """最遠点抽出で ``k`` 点の索引(決まった始点 = 重心から最も遠い点)。外形の端を残して点を減らす。"""
    n = len(P)
    if n <= k:
        return np.arange(n)
    idx = [int(np.argmax(np.linalg.norm(P - P.mean(0), axis=1)))]
    d = np.linalg.norm(P - P[idx[0]], axis=1)
    for _ in range(k - 1):
        j = int(np.argmax(d))
        idx.append(j)
        d = np.minimum(d, np.linalg.norm(P - P[j], axis=1))
    return np.asarray(idx)


def _dimensions(c: dict, up, *, unit_mm: float, mode: str = "upright", min_opacity: float = 0.5,
                n_hull: int = 72) -> dict | None:
    """外形の箱と W × D × H(mm)、箱の 8 隅を返す(点 = 不透明度 ≥ ``min_opacity`` のガウシアンの中心)。

    どちらのモードも向きは Fullseye の op :func:`measure3d.smallest_box3`(最小体積の向きつきの箱)が決め、
    大きさは全部の点をその向きに写して測る(箱は全部の点を必ず含む)。
    この op は凸包の面ごとに初期値を作って磨くので、滑らかな曲面(凸包の面が数千)をそのまま渡すと数分かかる
    (実測: 凸包 796 面で 12 s)。だから凸包の頂点を最遠点抽出で ``n_hull`` 点まで減らしてから渡す
    (向きが最適から少しずれると、箱が少し大きくなる側にだけ誤る)。

    * ``mode="upright"``(既定): 上向き ``up`` を H の軸に固定する(机に置いた商品の「幅 × 奥行 × 高さ」)。足跡
      (水平射影の凸包)を最低と最高の高さに置いた直角柱を smallest_box3 に渡す。返った軸が上向きから外れたら
      回転キャリパーで足跡の最小の長方形を直接求める(``op`` にどちらを使ったかを書く)。
    * ``mode="obb"``: 向きを自由にした最小体積の箱(L 字の物は斜めの箱になりうる)。
    H = 上向きにいちばん近い軸の辺、W ≥ D = 残り 2 辺。
    """
    from scipy.spatial import ConvexHull
    m = c["opacity"] >= min_opacity
    P = c["mu"][m] if m.sum() >= 4 else c["mu"]
    if len(P) < 4:
        return None
    u = np.asarray(up, np.float64)
    u = u / np.linalg.norm(u)
    try:
        hv = P[np.unique(ConvexHull(P).simplices)]
    except Exception:
        return None
    if mode == "obb":
        import measure3d
        sub = hv[_farthest_points(hv, n_hull)]
        try:
            box = measure3d.smallest_box3(sub)
        except ValueError:
            return None
        axes = np.asarray(box["axes"], np.float64)            # 行 = 単位ベクトル
        op_name = "measure3d.smallest_box3"
    elif mode == "upright":
        # 上向きを H に固定した箱 = 水平面の最小面積の長方形 × 高さ。その長方形も smallest_box3 に解かせる:
        # 足跡(凸包の頂点の水平射影の 2-D 凸包)を最低と最高の高さに置いた直角柱を渡すと、底面が凸包の面なので
        # 底に沿う向き(上向きの軸)が初期値に入り、最小体積 = 最小の足跡の長方形 × 高さになる。返った軸が上向きから
        # 外れたら(起きないはずだが)回転キャリパーで足跡の長方形を直接求める。
        import measure3d
        e1, e2, _ = _basis(u)
        q = np.column_stack([hv @ e1, hv @ e2])
        h2 = q[ConvexHull(q).vertices]
        h2 = h2[_farthest_points(h2, n_hull // 2)]
        h2 = h2[ConvexHull(h2).vertices]                        # 抽出で崩れた周回の順を戻す(回転キャリパー用)
        z = hv @ u
        prism = np.vstack([h2[:, :1] * e1 + h2[:, 1:] * e2 + z.min() * u, h2[:, :1] * e1 + h2[:, 1:] * e2 + z.max() * u])
        axes = None
        op_name = "measure3d.smallest_box3 (upright prism of the footprint)"
        try:
            box = measure3d.smallest_box3(prism)
            ax = np.asarray(box["axes"], np.float64)
            k = int(np.argmax(np.abs(ax @ u)))
            if abs(ax[k] @ u) > 1.0 - 1e-6:
                a1 = ax[(k + 1) % 3] - (ax[(k + 1) % 3] @ u) * u
                a1 /= np.linalg.norm(a1)
                axes = np.array([a1, np.cross(u, a1), u])
        except ValueError:
            pass
        if axes is None:
            best = (np.inf, 0.0)
            for i in range(len(h2)):                           # 回転キャリパー: 最小の長方形は凸包の辺に 1 辺が沿う
                d = h2[(i + 1) % len(h2)] - h2[i]
                th = np.arctan2(d[1], d[0])
                rr = np.array([[np.cos(th), np.sin(th)], [-np.sin(th), np.cos(th)]])
                r2 = h2 @ rr.T
                area = np.ptp(r2[:, 0]) * np.ptp(r2[:, 1])
                if area < best[0]:
                    best = (area, th)
            th = best[1]
            a1 = np.cos(th) * e1 + np.sin(th) * e2
            axes = np.array([a1, np.cross(u, a1), u])
            op_name = "upright (rotating calipers on the footprint)"
    else:
        raise ValueError("dims mode must be 'obb' or 'upright'")
    loc = P @ axes.T                                           # 大きさは全部の点で(箱は全点を含む)
    lo, hi = loc.min(0), loc.max(0)
    half = 0.5 * (hi - lo)
    center = (0.5 * (hi + lo)) @ axes
    ih = int(np.argmax(np.abs(axes @ u)))
    rest = [i for i in range(3) if i != ih]
    rest.sort(key=lambda i: -half[i])
    iw, idd = rest
    ax = {"W": axes[iw], "D": axes[idd], "H": axes[ih] * (1.0 if axes[ih] @ u >= 0 else -1.0)}
    hl = {"W": half[iw], "D": half[idd], "H": half[ih]}
    corners = []
    for sw in (-1, 1):
        for sd in (-1, 1):
            for sh in (-1, 1):
                corners.append(center + sw * hl["W"] * ax["W"] + sd * hl["D"] * ax["D"] + sh * hl["H"] * ax["H"])
    return {"mm": {k: float(2.0 * hl[k] * unit_mm) for k in ("W", "D", "H")},
            "corners": [[float(v) for v in p] for p in corners], "center": [float(v) for v in center],
            "n_points": int(len(P)), "n_hull": int(len(hv)), "op": op_name, "mode": mode}


# ───────────────────────────── カメラ ───────────────────────────── #
def _basis(up):
    u = np.asarray(up, np.float64)
    u = u / np.linalg.norm(u)
    ref = np.array([1.0, 0, 0]) if abs(u[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = ref - (ref @ u) * u
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    return e1, e2, u


def _orbit_pose(target, yaw_deg: float, pitch_deg: float, dist: float, up=(0, 0, 1)) -> np.ndarray:
    """ページと同じ回し方のカメラ(world → camera 4×4、render3d.look_at の規約)。

    目 = target + dist (cos p (cos y e1 + sin y e2) + sin p up)、e1 / e2 = up に直交する基底(up = z なら x / y)。
    yaw −90° = 正面(−e2 の側から見る)。
    """
    import render3d
    e1, e2, u = _basis(up)
    y, p = np.radians(yaw_deg), np.radians(pitch_deg)
    d = np.cos(p) * (np.cos(y) * e1 + np.sin(y) * e2) + np.sin(p) * u
    t = np.asarray(target, np.float64)
    return render3d.look_at(t + float(dist) * d, t, u)


def _intrinsics(fov_deg: float, width: int, height: int) -> np.ndarray:
    """縦の画角 ``fov_deg`` の K(ページと同じ: fy = (H/2)/tan(fov/2)、主点 = ((W−1)/2, (H−1)/2))。"""
    import render3d
    return render3d.intrinsics_from_fov(float(fov_deg), int(width), int(height))


def _default_camera(c: dict, up, fov_deg: float, dims: dict | None) -> dict:
    tgt = np.asarray(dims["center"]) if dims else 0.5 * (c["mu"].min(0) + c["mu"].max(0))
    r = np.linalg.norm(c["mu"] - tgt, axis=1)
    rad = float(np.quantile(r, 0.99)) if len(r) > 10 else float(r.max() if len(r) else 1.0)
    rad = max(rad, 1e-6)
    dist = rad / np.sin(np.radians(fov_deg) / 2.0) * 1.08
    return {"target": [float(v) for v in tgt], "dist": float(dist), "yaw": -60.0, "pitch": 22.0, "fov": float(fov_deg),
            "radius": rad}


# ───────────────────────────── 文言 ───────────────────────────── #
def _texts(v, what: str, langs) -> dict:
    """str(全言語に同じ)か {lang: str} を {lang: str} にする。辞書なら要求した言語が全部あること(黙って補わない)。"""
    if v is None:
        return {l: "" for l in langs}
    if isinstance(v, str):
        return {l: v for l in langs}
    if isinstance(v, dict):
        miss = [l for l in langs if l not in v]
        if miss:
            raise ValueError("%s: missing languages %s" % (what, ", ".join(miss)))
        return {l: str(v[l]) for l in langs}
    raise ValueError("%s: give a str or a {lang: str} dict" % what)


def _langs(lang) -> list:
    seq = [lang] if isinstance(lang, str) else list(lang)
    bad = [l for l in seq if l not in LANGS]
    if bad or not seq:
        raise ValueError("unsupported language %s (supported: %s)" % (bad, ", ".join(LANGS)))
    return seq


def _hotspots(hotspots, langs) -> list:
    out = []
    for i, h in enumerate(hotspots or ()):
        pos = np.asarray(h.get("pos"), np.float64).ravel()
        if pos.shape != (3,) or not np.isfinite(pos).all():
            raise ValueError("hotspot %d: pos must be 3 finite numbers" % i)
        out.append({"pos": [float(v) for v in pos], "label": _texts(h.get("label"), "hotspot %d label" % i, langs),
                    "desc": _texts(h.get("desc", ""), "hotspot %d desc" % i, langs)})
    return out


def _item_payload(gs, *, budget: int, up, unit_mm: float, fov_deg: float, bake_light, ambient: float,
                  dims: bool, hotspots, langs, name=None, desc=None, note=None, camera=None) -> tuple[dict, dict, dict]:
    """1 品ぶんの埋め込み(JSON にできる dict)と、返り値用の記録、量子化前の canon を作る。"""
    c0 = _canon(gs, bake_light=bake_light, ambient=ambient)
    c, blob, meta, rec = _fit_budget(c0, budget)
    dm = (_dimensions(c0, up, unit_mm=unit_mm, mode="upright" if dims is True else str(dims)) if dims else None)
    cam = _default_camera(c0, up, fov_deg, dm)
    if camera:
        cam.update({k: (list(map(float, v)) if k == "target" else float(v)) for k, v in camera.items()})
    payload = {"b64": base64.b64encode(blob).decode("ascii"), "meta": meta, "dims": dm, "camera": cam,
               "hotspots": _hotspots(hotspots, langs), "name": _texts(name, "name", langs),
               "desc": _texts(desc, "desc", langs), "note": _texts(note, "note", langs),
               "thinning": rec, "sh_in": c0["sh_degree_in"]}
    info = dict(rec)
    info.update({"embedded_bytes": len(payload["b64"]), "gzip_bytes": len(blob), "dims_mm": dm["mm"] if dm else None,
                 "dims": dm, "camera": cam, "sh_degree_in": c0["sh_degree_in"], "sh_degree_used": 0,
                 "sh_dropped": c0["sh_degree_in"] > 0, "source": c0["source"]})
    return payload, info, c


# ───────────────────────────── ページ ───────────────────────────── #
_CSS = r"""
:root{--bg:#7f7f7f;--fg:#f2f4f6;--dim:#aab4be;--panel:rgba(18,24,31,.86);--line:#33404d;--acc:#8ec5ff}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:#15191e;color:var(--fg);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;overflow:hidden}
#stage{position:fixed;inset:0;touch-action:none}
#gl{position:absolute;inset:0;width:100%;height:100%;display:block;cursor:grab}
#gl:active{cursor:grabbing}
#ov{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}
#ov line{stroke:#ff9f43;stroke-width:1.6}
#ov text{fill:#ff9f43;font:600 13px system-ui,sans-serif;paint-order:stroke;stroke:#15191e;stroke-width:3px}
.bar{position:absolute;left:0;right:0;display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:8px 12px;background:var(--panel);z-index:3}
#top{top:0}#bot{bottom:0}
#top h1{font-size:15px;margin:0 8px 0 0;font-weight:600;flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
button,select{font:inherit;color:var(--fg);background:#22303d;border:1px solid var(--line);border-radius:6px;padding:5px 9px;cursor:pointer;min-height:32px}
button[aria-pressed=true]{background:#2f5a85;border-color:var(--acc)}
button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--acc);outline-offset:1px}
.grp{display:flex;gap:4px;align-items:center;flex-wrap:wrap}
.grp label{color:var(--dim);font-size:12.5px}
input[type=range]{width:110px}
#count{color:var(--dim);font-size:12.5px;font-variant-numeric:tabular-nums}
.hs{position:absolute;z-index:2;transform:translate(-50%,-50%);width:28px;height:28px;min-height:0;padding:0;border-radius:50%;
  background:#ff6b6b;border:2px solid #fff;color:#fff;font-weight:700;box-shadow:0 1px 4px rgba(0,0,0,.5)}
.hs[hidden]{display:none}
#pop,#about{position:absolute;z-index:4;max-width:min(360px,calc(100vw - 32px));background:var(--panel);border:1px solid var(--line);
  border-radius:8px;padding:10px 12px}
#pop[hidden],#about[hidden]{display:none}
#pop h2,#about h2{margin:0 0 6px;font-size:15px}
#pop p,#about p{margin:0 0 6px;color:#d6dee6}
#about{right:12px;top:56px}
#msg{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;z-index:1;color:var(--dim);pointer-events:none}
#grid{position:fixed;inset:0;overflow:auto;padding:60px 16px 24px;z-index:5;background:#15191e}
#grid[hidden]{display:none}
#grid h1{font-size:18px;margin:0 0 4px}
#grid .sub{color:var(--dim);margin:0 0 14px}
#cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(220px,42vw),1fr));gap:12px}
.card{display:flex;flex-direction:column;gap:6px;padding:8px;border-radius:10px;background:#1d252e;border:1px solid var(--line);text-align:left;min-height:0}
.card img{width:100%;height:auto;aspect-ratio:1/1;object-fit:cover;border-radius:6px;background:#888}
.card b{font-size:14px}
.card span{color:var(--dim);font-size:12.5px}
.gate .bar,.gate #msg,.gate .hs,.gate #pop,.gate #about{display:none!important}
@media (max-width:600px){input[type=range]{width:84px}.bar{padding:6px 8px;gap:4px}button,select{padding:4px 7px}}
"""

#: 描画の部品(単体ビューアとカタログで共有)。GLSL ES 3.00 / WebGL2。
_JS_CORE = r"""
'use strict';
const GS = {};
GS.stats = {buffers: 0, textures: 0, programs: 0};
GS.inflate = async function(b64){
  const bin = atob(b64); const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  const ds = new DecompressionStream('gzip');
  const buf = await new Response(new Blob([u8]).stream().pipeThrough(ds)).arrayBuffer();
  return new Uint8Array(buf);
};
// 埋め込みの 1 品 → 位置 (Float32 3N) と テクスチャ用の配列 (4 texel / ガウシアン: [x y z op] [c00 c01 c02 c11] [c12 c22 r g] [b 0 0 0])
GS.unpack = function(raw, m){
  const n = m.n, dv = new DataView(raw.buffer, raw.byteOffset, raw.byteLength);
  const TW = 4096, per = TW / 4, rows = Math.max(1, Math.ceil(n / per));
  const tex = new Float32Array(TW * rows * 4), pos = new Float32Array(3 * n);
  const oS = 6 * n, oQ = 12 * n, oC = 16 * n;
  for (let i = 0; i < n; i++){
    const x = m.lo[0] + dv.getUint16(2 * i, true) / 65535 * m.span[0];
    const y = m.lo[1] + dv.getUint16(2 * (n + i), true) / 65535 * m.span[1];
    const z = m.lo[2] + dv.getUint16(2 * (2 * n + i), true) / 65535 * m.span[2];
    const s0 = Math.exp(m.slo + dv.getUint16(oS + 2 * i, true) / 65535 * m.sspan);
    const s1 = Math.exp(m.slo + dv.getUint16(oS + 2 * (n + i), true) / 65535 * m.sspan);
    const s2 = Math.exp(m.slo + dv.getUint16(oS + 2 * (2 * n + i), true) / 65535 * m.sspan);
    let w = (raw[oQ + i] - 127.5) / 127.5, a = (raw[oQ + n + i] - 127.5) / 127.5,
        b = (raw[oQ + 2 * n + i] - 127.5) / 127.5, c = (raw[oQ + 3 * n + i] - 127.5) / 127.5;
    const qn = Math.hypot(w, a, b, c) || 1; w /= qn; a /= qn; b /= qn; c /= qn;
    // R(四元数 wxyz)の列に大きさを掛けた M = R diag(s) → Σ = M Mᵀ
    const r00 = 1 - 2 * (b * b + c * c), r01 = 2 * (a * b - w * c), r02 = 2 * (a * c + w * b);
    const r10 = 2 * (a * b + w * c), r11 = 1 - 2 * (a * a + c * c), r12 = 2 * (b * c - w * a);
    const r20 = 2 * (a * c - w * b), r21 = 2 * (b * c + w * a), r22 = 1 - 2 * (a * a + b * b);
    const m00 = r00 * s0, m01 = r01 * s1, m02 = r02 * s2, m10 = r10 * s0, m11 = r11 * s1, m12 = r12 * s2,
          m20 = r20 * s0, m21 = r21 * s1, m22 = r22 * s2;
    const c00 = m00 * m00 + m01 * m01 + m02 * m02, c01 = m00 * m10 + m01 * m11 + m02 * m12,
          c02 = m00 * m20 + m01 * m21 + m02 * m22, c11 = m10 * m10 + m11 * m11 + m12 * m12,
          c12 = m10 * m20 + m11 * m21 + m12 * m22, c22 = m20 * m20 + m21 * m21 + m22 * m22;
    const o = 16 * i;
    tex[o] = x; tex[o + 1] = y; tex[o + 2] = z; tex[o + 3] = raw[oC + 3 * n + i] / 255;
    tex[o + 4] = c00; tex[o + 5] = c01; tex[o + 6] = c02; tex[o + 7] = c11;
    tex[o + 8] = c12; tex[o + 9] = c22; tex[o + 10] = raw[oC + i] / 255; tex[o + 11] = raw[oC + n + i] / 255;
    tex[o + 12] = raw[oC + 2 * n + i] / 255;
    pos[3 * i] = x; pos[3 * i + 1] = y; pos[3 * i + 2] = z;
  }
  return {n: n, tex: tex, rows: rows, TW: TW, pos: pos};
};
// 前後の並べ替え(Worker の中と、Worker が使えない時の本体とで同じ関数)。深さ d = −(r·p + t) を 16 bit の桶で数えて手前から。
GS.SORT_SRC = `
function gsSort(pos, n, r0, r1, r2, t, keep){
  const m = Math.min(n, keep); const d = new Float32Array(m); let lo = Infinity, hi = -Infinity;
  for (let i = 0; i < m; i++){ const v = -(r0 * pos[3*i] + r1 * pos[3*i+1] + r2 * pos[3*i+2] + t); d[i] = v;
    if (v > 1e-6){ if (v < lo) lo = v; if (v > hi) hi = v; } }
  if (!(hi >= lo)) return new Uint32Array(0);
  const NB = 65536, sc = (NB - 1) / Math.max(hi - lo, 1e-30), cnt = new Uint32Array(NB), key = new Uint16Array(m);
  let nv = 0;
  for (let i = 0; i < m; i++){ if (d[i] > 1e-6){ const k = Math.min(NB - 1, Math.floor((d[i] - lo) * sc)); key[i] = k; cnt[k]++; nv++; } }
  for (let k = 1; k < NB; k++) cnt[k] += cnt[k - 1];
  const out = new Uint32Array(nv);
  for (let i = m - 1; i >= 0; i--){ if (d[i] > 1e-6){ out[--cnt[key[i]]] = i; } }
  return out;
}`;
GS.WORKER_SRC = GS.SORT_SRC + `
let P = null, N = 0;
onmessage = function(e){ const m = e.data;
  if (m.pos){ P = m.pos; N = m.n; return; }
  const idx = gsSort(P, N, m.v[0], m.v[1], m.v[2], m.v[3], m.keep);
  postMessage({idx: idx, id: m.id, gen: m.gen}, [idx.buffer]); };`;
GS.gsSortLocal = (new Function(GS.SORT_SRC + '; return gsSort;'))();

GS.VS = `#version 300 es
precision highp float; precision highp int; precision highp sampler2D;
uniform sampler2D u_tex; uniform mat3 u_R; uniform vec3 u_t; uniform vec4 u_K; uniform vec2 u_vp;
uniform float u_maxr; uniform float u_minop;
in vec2 a_corner; in uint a_idx;
out vec3 v_col; out float v_op; out vec3 v_conic; out vec2 v_center;
void main(){
  int base = int(a_idx) * 4; int TW = textureSize(u_tex, 0).x;
  ivec2 p0 = ivec2(base % TW, base / TW);
  vec4 t0 = texelFetch(u_tex, p0, 0), t1 = texelFetch(u_tex, p0 + ivec2(1, 0), 0),
       t2 = texelFetch(u_tex, p0 + ivec2(2, 0), 0), t3 = texelFetch(u_tex, p0 + ivec2(3, 0), 0);
  gl_Position = vec4(0.0, 0.0, 2.0, 1.0);
  if (t0.w < u_minop) return;
  vec3 pc = u_R * t0.xyz + u_t; float d = -pc.z;
  if (d <= 1e-6) return;
  mat3 S = mat3(t1.x, t1.y, t1.z,  t1.y, t1.w, t2.x,  t1.z, t2.x, t2.y);
  mat3 Sc = u_R * S * transpose(u_R);
  float fx = u_K.x, fy = u_K.y;
  vec3 j0 = vec3(fx / d, 0.0, fx * pc.x / (d * d));
  vec3 j1 = vec3(0.0, -fy / d, -fy * pc.y / (d * d));
  vec3 s0 = Sc * j0, s1 = Sc * j1;
  float a = dot(j0, s0), b = dot(j0, s1), c = dot(j1, s1);
  float det0 = a * c - b * b; a += 0.3; c += 0.3; float det = a * c - b * b;
  if (det <= 0.0) return;
  float comp = sqrt(max(det0, 0.0) / det);
  float lam = 0.5 * (a + c) + sqrt(max(0.25 * (a - c) * (a - c) + b * b, 0.0));
  float r = min(ceil(3.0 * sqrt(lam)), u_maxr);
  float u = fx * pc.x / d + u_K.z, v = u_K.w - fy * pc.y / d;
  vec2 ctr = floor(vec2(u, v) + 0.5);
  vec2 px = ctr + a_corner * (r + 0.5);
  gl_Position = vec4((px.x + 0.5) / u_vp.x * 2.0 - 1.0, 1.0 - (px.y + 0.5) / u_vp.y * 2.0, 0.0, 1.0);
  v_conic = vec3(c, -b, a) / det; v_center = vec2(u, v); v_col = vec3(t2.z, t2.w, t3.x); v_op = t0.w * comp;
}`;
GS.FS = `#version 300 es
precision highp float;
uniform vec2 u_vp;
in vec3 v_col; in float v_op; in vec3 v_conic; in vec2 v_center;
out vec4 o;
void main(){
  vec2 p = vec2(gl_FragCoord.x - 0.5, u_vp.y - gl_FragCoord.y - 0.5);
  vec2 dl = p - v_center;
  float q = v_conic.x * dl.x * dl.x + 2.0 * v_conic.y * dl.x * dl.y + v_conic.z * dl.y * dl.y;
  float al = min(0.99, v_op * exp(-0.5 * q));
  if (al < 1.0 / 255.0) discard;
  o = vec4(v_col * al, al);
}`;
GS.VS2 = `#version 300 es
in vec2 a_p; out vec2 v_uv; void main(){ v_uv = a_p * 0.5 + 0.5; gl_Position = vec4(a_p, 0.0, 1.0); }`;
GS.FS2 = `#version 300 es
precision highp float; uniform sampler2D u_acc; uniform vec3 u_bg; in vec2 v_uv; out vec4 o;
void main(){ vec4 c = texture(u_acc, v_uv); o = vec4(c.rgb + (1.0 - c.a) * u_bg, 1.0); }`;

GS.Renderer = class {
  constructor(canvas){
    const gl = canvas.getContext('webgl2', {antialias: false, alpha: false, depth: false, stencil: false,
                                            premultipliedAlpha: false, preserveDrawingBuffer: true});
    if (!gl) throw new Error('nogl');
    this.gl = gl; this.canvas = canvas;
    this.floatFB = !!gl.getExtension('EXT_color_buffer_float');
    const mk = (vs, fs) => { const p = gl.createProgram(); GS.stats.programs++;
      for (const [t, s] of [[gl.VERTEX_SHADER, vs], [gl.FRAGMENT_SHADER, fs]]){ const sh = gl.createShader(t); gl.shaderSource(sh, s);
        gl.compileShader(sh); if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh)); gl.attachShader(p, sh); }
      gl.linkProgram(p); if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p)); return p; };
    this.prog = mk(GS.VS, GS.FS); this.prog2 = mk(GS.VS2, GS.FS2);
    this.U = {}; for (const k of ['u_tex', 'u_R', 'u_t', 'u_K', 'u_vp', 'u_maxr', 'u_minop']) this.U[k] = gl.getUniformLocation(this.prog, k);
    this.U2 = {acc: gl.getUniformLocation(this.prog2, 'u_acc'), bg: gl.getUniformLocation(this.prog2, 'u_bg')};
    this.quad = this.buf(new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]));
    this.tri = this.buf(new Float32Array([-1, -1, 3, -1, -1, 3]));
    this.fb = null; this.fbTex = null; this.fbW = 0; this.fbH = 0; this.item = null;
  }
  buf(data){ const gl = this.gl, b = gl.createBuffer(); GS.stats.buffers++; gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW); return b; }
  delBuf(b){ if (b){ this.gl.deleteBuffer(b); GS.stats.buffers--; } }
  delTex(t){ if (t){ this.gl.deleteTexture(t); GS.stats.textures--; } }
  // 1 品を GPU に載せる(前の品は呼び手が dispose する)
  load(u){
    const gl = this.gl; const tex = gl.createTexture(); GS.stats.textures++;
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA32F, u.TW, u.rows, 0, gl.RGBA, gl.FLOAT, u.tex);
    const idx = gl.createBuffer(); GS.stats.buffers++;
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quad); const ac = gl.getAttribLocation(this.prog, 'a_corner');
    gl.enableVertexAttribArray(ac); gl.vertexAttribPointer(ac, 2, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, idx); gl.bufferData(gl.ARRAY_BUFFER, new Uint32Array(0), gl.DYNAMIC_DRAW);
    const ai = gl.getAttribLocation(this.prog, 'a_idx');
    gl.enableVertexAttribArray(ai); gl.vertexAttribIPointer(ai, 1, gl.UNSIGNED_INT, 0, 0); gl.vertexAttribDivisor(ai, 1);
    gl.bindVertexArray(null);
    this.item = {tex: tex, idx: idx, vao: vao, count: 0, n: u.n};
    return this.item;
  }
  setOrder(order){ const gl = this.gl, it = this.item; if (!it) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, it.idx); gl.bufferData(gl.ARRAY_BUFFER, order, gl.DYNAMIC_DRAW); it.count = order.length; }
  dispose(){ const gl = this.gl, it = this.item; if (!it) return;
    this.delTex(it.tex); this.delBuf(it.idx); gl.deleteVertexArray(it.vao); this.item = null; }
  ensureFB(w, h){
    const gl = this.gl; if (this.fb && this.fbW === w && this.fbH === h) return;
    if (this.fb){ gl.deleteFramebuffer(this.fb); this.delTex(this.fbTex); }
    const t = gl.createTexture(); GS.stats.textures++; gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    if (this.floatFB) gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA16F, w, h, 0, gl.RGBA, gl.HALF_FLOAT, null);
    else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, t, 0);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    this.fb = fb; this.fbTex = t; this.fbW = w; this.fbH = h;
  }
  // cam = {R: 9 (行優先 world→camera), t: 3, K: [fx, fy, cx, cy]}; opt = {bg: [r,g,b], minop, maxr}
  draw(cam, opt){
    const gl = this.gl, W = this.canvas.width, H = this.canvas.height, it = this.item;
    this.ensureFB(W, H);
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.fb); gl.viewport(0, 0, W, H);
    gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    if (it && it.count > 0){
      gl.useProgram(this.prog);
      gl.enable(gl.BLEND); gl.blendFunc(gl.ONE_MINUS_DST_ALPHA, gl.ONE); gl.blendEquation(gl.FUNC_ADD);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, it.tex); gl.uniform1i(this.U.u_tex, 0);
      const R = cam.R;   // mat3 は列優先で渡す → 行優先の R を転置して渡す
      gl.uniformMatrix3fv(this.U.u_R, false, [R[0], R[3], R[6], R[1], R[4], R[7], R[2], R[5], R[8]]);
      gl.uniform3fv(this.U.u_t, cam.t); gl.uniform4fv(this.U.u_K, cam.K); gl.uniform2f(this.U.u_vp, W, H);
      gl.uniform1f(this.U.u_maxr, opt.maxr || 64); gl.uniform1f(this.U.u_minop, opt.minop || 0);
      gl.bindVertexArray(it.vao); gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, it.count); gl.bindVertexArray(null);
      gl.disable(gl.BLEND);
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.viewport(0, 0, W, H);
    gl.useProgram(this.prog2); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, this.fbTex);
    gl.uniform1i(this.U2.acc, 0); gl.uniform3fv(this.U2.bg, opt.bg);
    gl.bindBuffer(gl.ARRAY_BUFFER, this.tri); const ap = gl.getAttribLocation(this.prog2, 'a_p');
    gl.enableVertexAttribArray(ap); gl.vertexAttribPointer(ap, 2, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 3); gl.disableVertexAttribArray(ap);
  }
};

// カメラ: render3d.look_at と同じ規約(−Z を見る、+Y が上)。orbit → {R(行優先), t, eye}
GS.lookAt = function(e, tg, up){
  let f = [tg[0] - e[0], tg[1] - e[1], tg[2] - e[2]]; const fn = Math.hypot(...f); f = f.map(v => v / fn);
  let s = [f[1] * up[2] - f[2] * up[1], f[2] * up[0] - f[0] * up[2], f[0] * up[1] - f[1] * up[0]];
  const sn = Math.hypot(...s); s = s.map(v => v / sn);
  const u = [s[1] * f[2] - s[2] * f[1], s[2] * f[0] - s[0] * f[2], s[0] * f[1] - s[1] * f[0]];
  const R = [s[0], s[1], s[2], u[0], u[1], u[2], -f[0], -f[1], -f[2]];
  const t = [0, 1, 2].map(i => -(R[3 * i] * e[0] + R[3 * i + 1] * e[1] + R[3 * i + 2] * e[2]));
  return {R: R, t: t, eye: e};
};
GS.basis = function(up){
  const n = Math.hypot(...up), u = up.map(v => v / n);
  const ref = Math.abs(u[0]) < 0.9 ? [1, 0, 0] : [0, 1, 0]; const d = ref[0] * u[0] + ref[1] * u[1] + ref[2] * u[2];
  let e1 = [ref[0] - d * u[0], ref[1] - d * u[1], ref[2] - d * u[2]]; const n1 = Math.hypot(...e1); e1 = e1.map(v => v / n1);
  const e2 = [u[1] * e1[2] - u[2] * e1[1], u[2] * e1[0] - u[0] * e1[2], u[0] * e1[1] - u[1] * e1[0]];
  return [e1, e2, u];
};
GS.orbit = function(o, up){
  const [e1, e2, u] = GS.basis(up), y = o.yaw * Math.PI / 180, p = o.pitch * Math.PI / 180;
  const d = [0, 1, 2].map(i => Math.cos(p) * (Math.cos(y) * e1[i] + Math.sin(y) * e2[i]) + Math.sin(p) * u[i]);
  const e = [0, 1, 2].map(i => o.target[i] + o.dist * d[i]);
  return GS.lookAt(e, o.target, u);
};
GS.project = function(cam, p){
  const R = cam.R, x = R[0] * p[0] + R[1] * p[1] + R[2] * p[2] + cam.t[0], y = R[3] * p[0] + R[4] * p[1] + R[5] * p[2] + cam.t[1],
        z = R[6] * p[0] + R[7] * p[1] + R[8] * p[2] + cam.t[2], d = -z;
  if (d <= 1e-6) return null;
  return [cam.K[0] * x / d + cam.K[2], cam.K[3] - cam.K[1] * y / d, d];
};
"""

#: 画面の部品(1 品を開いて回す。単体ビューアは最初から 1 品を開き、カタログは選ばれた品を開く)。
_JS_VIEW = r"""
const D = JSON.parse(document.getElementById('gscfg').textContent);
const qs = new URLSearchParams(location.search);
""" + _JS_PICK_LANG + r"""
const $ = id => document.getElementById(id);
const tr = k => (D.ui[k] && D.ui[k][L]) || k;
const GATE = qs.get('gate') === '1';
if (GATE) document.body.classList.add('gate');
const V = {renderer: null, worker: null, item: null, data: null, cam: null, orbit: null, gen: 0, sortBusy: false, sortWant: false,
           lastKey: '', keep: 1, minop: 0, bg: D.bg, spin: !GATE, dims: false, vel: [0, 0], ready: false, pend: null, dirty: true};
window.__gs = V; window.__gsStats = GS.stats;
function setMsg(t){ $('msg').textContent = t || ''; }
function applyLang(){
  document.documentElement.lang = L;
  document.querySelectorAll('[data-i18n]').forEach(e => { e.textContent = tr(e.dataset.i18n); });
  document.querySelectorAll('[data-i18n-title]').forEach(e => { e.title = tr(e.dataset.i18nTitle); e.setAttribute('aria-label', tr(e.dataset.i18nTitle)); });
  if (V.item) fillItemText();
  if (typeof fillCards === 'function') fillCards();
}
function fillItemText(){
  const it = V.item; $('title').textContent = (it.name && it.name[L]) || D.title[L] || '';
  document.title = $('title').textContent;
  const p = [];
  if (it.note && it.note[L]) p.push(it.note[L]);
  p.push(tr('sh'));
  if (it.thinning && it.thinning.thinned) p.push(tr('thin').replace('{k}', it.thinning.n_dropped.toLocaleString()).replace('{n}', it.thinning.n_input.toLocaleString()));
  if (it.dims) p.push(tr('dimnote'));
  $('aboutBody').innerHTML = '';
  for (const s of p){ const e = document.createElement('p'); e.textContent = s; $('aboutBody').appendChild(e); }
  const hs = $('hsLayer'); hs.innerHTML = '';
  (it.hotspots || []).forEach((h, i) => { const b = document.createElement('button'); b.className = 'hs'; b.textContent = String(i + 1);
    b.setAttribute('aria-label', h.label[L]); b.title = h.label[L]; b.onclick = ev => { ev.stopPropagation(); openHotspot(i); }; hs.appendChild(b); });
  if (V.openHs != null) openHotspot(V.openHs);
  $('dimsBtn').hidden = !it.dims; updateCount();
}
function openHotspot(i){
  const h = V.item.hotspots[i]; if (!h) return; V.openHs = i;
  $('popT').textContent = (i + 1) + '. ' + h.label[L]; $('popD').textContent = h.desc[L] || ''; $('pop').hidden = false; V.dirty = true;
}
function closeHotspot(){ V.openHs = null; $('pop').hidden = true; }
function updateCount(){
  if (!V.data) return; const k = Math.max(1, Math.round(V.data.n * V.keep));
  $('count').textContent = tr('shown') + ' ' + k.toLocaleString() + ' / ' + V.data.n.toLocaleString();
}
function camNow(){
  const W = $('gl').width, H = $('gl').height;
  if (V.gateCam) return V.gateCam;
  const o = V.orbit, c = GS.orbit(o, D.up), f = (Math.min(W, H) / 2) / Math.tan(o.fov * Math.PI / 360);   // 画角は短い辺に(縦長のスマホでもはみ出さない)
  c.K = [f, f, (W - 1) / 2, (H - 1) / 2]; return c;
}
function requestSort(){
  if (!V.data) return;
  const c = V.cam, keep = Math.max(1, Math.round(V.data.n * V.keep));
  const key = c.R[6].toFixed(5) + ',' + c.R[7].toFixed(5) + ',' + c.R[8].toFixed(5) + ',' + c.t[2].toPrecision(6) + ',' + keep;
  if (key === V.lastKey) return;
  if (V.sortBusy){ V.sortWant = true; return; }
  V.lastKey = key; V.sortBusy = true;
  const msg = {v: [c.R[6], c.R[7], c.R[8], c.t[2]], keep: keep, gen: V.gen};
  if (V.worker) V.worker.postMessage(msg);
  else setTimeout(() => onSorted({idx: GS.gsSortLocal(V.data.pos, V.data.n, msg.v[0], msg.v[1], msg.v[2], msg.v[3], keep), gen: msg.gen}), 0);
}
function onSorted(m){
  V.sortBusy = false;
  if (m.gen !== V.gen) { if (V.sortWant){ V.sortWant = false; requestSort(); } return; }
  V.renderer.setOrder(m.idx); V.sorted = V.lastKey; V.dirty = true;
  if (V.sortWant){ V.sortWant = false; requestSort(); }
}
function startWorker(){
  try { V.worker = new Worker(URL.createObjectURL(new Blob([GS.WORKER_SRC], {type: 'text/javascript'})));
        V.worker.onmessage = e => onSorted(e.data); V.worker.onerror = () => { V.worker = null; V.sortBusy = false; V.lastKey = ''; }; }
  catch (e) { V.worker = null; }
}
async function openItem(it){
  closeItem(); V.item = it; V.gen++; setMsg(tr('loading'));
  const myGen = V.gen;
  const raw = await GS.inflate(it.b64);
  if (myGen !== V.gen) return;
  const u = GS.unpack(raw, it.meta);
  V.data = {n: u.n, pos: u.pos};
  V.renderer.load(u);
  if (V.worker) V.worker.postMessage({pos: u.pos, n: u.n});
  V.orbit = Object.assign({}, it.camera);
  applyUrlView();
  V.keep = D.mobileQuality && u.n > D.mobileAbove && matchMedia('(pointer: coarse)').matches ? D.mobileQuality : 1; $('quality').value = Math.round(V.keep * 100);
  fillItemText(); setMsg(''); V.lastKey = ''; V.dirty = true;
}
function closeItem(){
  V.gen++; if (V.renderer) V.renderer.dispose(); V.item = null; V.data = null; V.lastKey = ''; V.sortBusy = false; V.sortWant = false;
  V.sorted = null; closeHotspot(); if ($('hsLayer')) $('hsLayer').innerHTML = ''; drawOverlay(null);
}
const PRESET = {front: [-90, 0], side: [0, 0], top: [-90, 89.5], iso: [-60, 22]};
function setPreset(k){ const p = PRESET[k]; if (!p || !V.orbit) return; V.orbit.yaw = p[0]; V.orbit.pitch = p[1]; V.vel = [0, 0]; stopSpin(); V.dirty = true; }
function stopSpin(){ V.spin = false; $('spinBtn').setAttribute('aria-pressed', 'false'); }
function setBg(k){ V.bgKey = k; V.bg = D.bgs[k]; document.querySelectorAll('[data-bg]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.bg === k))); V.dirty = true; }
function applyUrlView(){
  if (qs.get('view') && PRESET[qs.get('view')]){ const p = PRESET[qs.get('view')]; V.orbit.yaw = p[0]; V.orbit.pitch = p[1]; }
  if (qs.get('yaw')) V.orbit.yaw = +qs.get('yaw'); if (qs.get('pitch')) V.orbit.pitch = +qs.get('pitch');
  if (qs.get('zoom')) V.orbit.dist /= +qs.get('zoom');
}
function drawOverlay(cam){
  // インラインの <svg> の innerHTML は SVG の名前空間で読まれる(名前空間の URL をページに書かずに済む)
  const svg = $('ov'); svg.innerHTML = '';
  if (!cam || !V.dims || !V.item || !V.item.dims) return;
  const dpr = $('gl').width / $('gl').clientWidth, C = V.item.dims.corners.map(p => GS.project(cam, p));
  if (C.some(p => !p)) return;
  const P = C.map(p => [((p[0] + 0.5) / dpr).toFixed(1), ((p[1] + 0.5) / dpr).toFixed(1)]);
  const E = [[0,4],[1,5],[2,6],[3,7],[0,2],[1,3],[4,6],[5,7],[0,1],[2,3],[4,5],[6,7]];
  let s = '';
  for (const [a, b] of E) s += '<line x1="' + P[a][0] + '" y1="' + P[a][1] + '" x2="' + P[b][0] + '" y2="' + P[b][1] + '"/>';
  const mm = V.item.dims.mm, lab = [['W', 0, 4], ['D', 0, 2], ['H', 0, 1]];
  for (const [k, a, b] of lab){ const x = (+P[a][0] + +P[b][0]) / 2 + 4, y = (+P[a][1] + +P[b][1]) / 2 - 4;
    s += '<text x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '">' + k + ' ' + mm[k].toFixed(mm[k] < 100 ? 1 : 0) + ' mm</text>'; }
  svg.innerHTML = s;
}
function placeHotspots(cam){
  const btns = $('hsLayer').children, dpr = $('gl').width / $('gl').clientWidth;
  (V.item ? V.item.hotspots : []).forEach((h, i) => { const p = GS.project(cam, h.pos), b = btns[i]; if (!b) return;
    if (!p){ b.hidden = true; return; } b.hidden = false; b.style.left = ((p[0] + 0.5) / dpr) + 'px'; b.style.top = ((p[1] + 0.5) / dpr) + 'px';
    if (V.openHs === i){ const pop = $('pop'); pop.style.left = Math.min(innerWidth - pop.offsetWidth - 12, Math.max(12, (p[0] + 0.5) / dpr + 20)) + 'px';
      pop.style.top = Math.min(innerHeight - pop.offsetHeight - 70, Math.max(56, (p[1] + 0.5) / dpr - 10)) + 'px'; } });
}
function resize(){
  const cv = $('gl');
  if (V.gateCam){ cv.width = V.gateCam.W; cv.height = V.gateCam.H; cv.style.width = V.gateCam.W + 'px'; cv.style.height = V.gateCam.H + 'px'; return; }
  const dpr = Math.min(devicePixelRatio || 1, 2), w = Math.max(1, Math.round(cv.clientWidth * dpr)), h = Math.max(1, Math.round(cv.clientHeight * dpr));
  if (cv.width !== w || cv.height !== h){ cv.width = w; cv.height = h; V.dirty = true; }
}
let lastT = performance.now();
function frame(t){
  const dt = Math.min(0.05, (t - lastT) / 1000); lastT = t;
  if (V.data && V.orbit && !V.gateCam){
    if (V.spin){ V.orbit.yaw += D.spinDeg * dt; V.dirty = true; }
    if (!V.drag && (Math.abs(V.vel[0]) > 0.01 || Math.abs(V.vel[1]) > 0.01)){
      V.orbit.yaw += V.vel[0] * dt; V.orbit.pitch = Math.max(-89.5, Math.min(89.5, V.orbit.pitch + V.vel[1] * dt));
      const k = Math.exp(-4 * dt); V.vel[0] *= k; V.vel[1] *= k; V.dirty = true; }
  }
  resize();
  if (V.data && V.dirty){
    V.dirty = false; V.cam = camNow(); requestSort();
    V.renderer.draw(V.cam, {bg: V.bg, minop: V.minop, maxr: D.maxRadius});
    drawOverlay(V.cam); placeHotspots(V.cam);
    // 準備完了 = 並べ替えた順で 1 回描いた後(視点が止まっていれば、その視点の順そのもの = 門が撮る絵)
    if (V.sorted && !V.ready && (V.gateCam ? (!V.sortBusy && V.sorted === V.lastKey) : true)) V.ready = true;
  } else if (V.data && !V.ready && V.sorted){ V.dirty = true; }
  requestAnimationFrame(frame);
}
function bindInput(){
  const cv = $('gl'), ptrs = new Map(); let pinch = 0;
  cv.addEventListener('pointerdown', e => { cv.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, [e.clientX, e.clientY]); V.drag = true; V.vel = [0, 0];
    stopSpin(); closeHotspot(); if (ptrs.size === 2){ const [a, b] = [...ptrs.values()]; pinch = Math.hypot(a[0] - b[0], a[1] - b[1]); } });
  cv.addEventListener('pointermove', e => { if (!ptrs.has(e.pointerId) || !V.orbit) return; const p = ptrs.get(e.pointerId);
    if (ptrs.size === 1){ const dx = e.clientX - p[0], dy = e.clientY - p[1], s = 0.4;
      V.orbit.yaw -= dx * s; V.orbit.pitch = Math.max(-89.5, Math.min(89.5, V.orbit.pitch + dy * s)); V.vel = [-dx * s * 30, dy * s * 30]; }
    ptrs.set(e.pointerId, [e.clientX, e.clientY]);
    if (ptrs.size === 2){ const [a, b] = [...ptrs.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]); if (pinch > 0) zoom(pinch / d); pinch = d; }
    V.dirty = true; });
  const up = e => { ptrs.delete(e.pointerId); if (ptrs.size === 0) V.drag = false; pinch = 0; };
  cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', up);
  cv.addEventListener('wheel', e => { e.preventDefault(); stopSpin(); zoom(Math.exp(e.deltaY * 0.0015)); }, {passive: false});
  addEventListener('keydown', e => { if (!V.orbit || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    const k = e.key; if (k === 'Escape'){ if (!$('pop').hidden) closeHotspot(); else if (!$('about').hidden) $('about').hidden = true; else if (typeof backToGrid === 'function') backToGrid(); return; }
    const st = {ArrowLeft: [5, 0], ArrowRight: [-5, 0], ArrowUp: [0, 5], ArrowDown: [0, -5]}[k];
    if (st){ stopSpin(); V.orbit.yaw += st[0]; V.orbit.pitch = Math.max(-89.5, Math.min(89.5, V.orbit.pitch + st[1])); V.dirty = true; e.preventDefault(); }
    if (k === '+' || k === '=') zoom(0.9); if (k === '-') zoom(1.1); });
}
function zoom(f){ if (!V.orbit) return; const r = V.item.camera.radius || 1; V.orbit.dist = Math.max(r * 0.6, Math.min(r * 20, V.orbit.dist * f)); V.dirty = true; }
function bindUi(){
  document.querySelectorAll('[data-preset]').forEach(b => b.onclick = () => setPreset(b.dataset.preset));
  document.querySelectorAll('[data-bg]').forEach(b => b.onclick = () => setBg(b.dataset.bg));
  $('spinBtn').onclick = () => { V.spin = !V.spin; $('spinBtn').setAttribute('aria-pressed', String(V.spin)); V.dirty = true; };
  $('dimsBtn').onclick = () => { V.dims = !V.dims; $('dimsBtn').setAttribute('aria-pressed', String(V.dims)); V.dirty = true; };
  $('opacity').oninput = e => { V.minop = e.target.value / 100; V.dirty = true; };
  $('quality').oninput = e => { V.keep = Math.max(0.02, e.target.value / 100); updateCount(); V.dirty = true; };
  $('aboutBtn').onclick = () => { $('about').hidden = !$('about').hidden; };
  $('aboutClose').onclick = () => { $('about').hidden = true; };
  $('popClose').onclick = closeHotspot;
  const sel = $('lang');
  if (D.langs.length < 2) sel.hidden = true;
  D.langs.forEach(l => { const o = document.createElement('option'); o.value = l; o.textContent = D.langnames[l]; sel.appendChild(o); });
  sel.value = L; sel.onchange = () => { L = sel.value; applyLang(); };
}
function initCommon(){
  try { V.renderer = new GS.Renderer($('gl')); } catch (e) { setMsg(tr('nogl')); console.error(e); return false; }
  startWorker(); bindUi(); bindInput(); setBg(qs.get('bg') && D.bgs[qs.get('bg')] ? qs.get('bg') : D.bgDefault);
  if (qs.get('spin') === '0' || GATE) stopSpin(); else { V.spin = D.spin; $('spinBtn').setAttribute('aria-pressed', String(V.spin)); }
  if (qs.get('dims') === '1'){ V.dims = true; $('dimsBtn').setAttribute('aria-pressed', 'true'); }
  if (qs.get('minop')) { V.minop = +qs.get('minop'); $('opacity').value = Math.round(V.minop * 100); }
  if (GATE && qs.get('cam')){ const a = qs.get('cam').split(',').map(Number);
    V.gateCam = {R: a.slice(0, 9), t: a.slice(9, 12), K: a.slice(12, 16), W: a[16], H: a[17]}; }
  applyLang(); requestAnimationFrame(frame); return true;
}
"""

_JS_SINGLE = r"""
(async () => {
  if (!initCommon()) return;
  await openItem(D.items[0]);
  if (qs.get('quality')) { V.keep = Math.max(0.02, +qs.get('quality')); $('quality').value = Math.round(V.keep * 100); updateCount(); }
  if (qs.get('hs') != null && qs.get('hs') !== '') openHotspot(+qs.get('hs'));
  if (qs.get('t')) { V.orbit.yaw += D.spinDeg * (+qs.get('t')); }
  V.dirty = true;
})();
"""

_JS_CATALOG = r"""
function fillCards(){
  const box = $('cards'); if (!box) return; box.innerHTML = '';
  $('gridTitle').textContent = D.title[L] || ''; $('gridSub').textContent = tr('pick');
  D.items.forEach((it, i) => { const b = document.createElement('button'); b.className = 'card'; b.dataset.i = i;
    const img = document.createElement('img'); img.src = it.thumb; img.alt = it.name[L]; img.width = 256; img.height = 256;
    const n = document.createElement('b'); n.textContent = it.name[L];
    const d = document.createElement('span'); d.textContent = it.desc[L] + (it.dims ? '  ·  ' + ['W', 'D', 'H'].map(k => it.dims.mm[k].toFixed(0)).join(' × ') + ' mm' : '');
    b.append(img, n, d); b.onclick = () => selectItem(i); box.appendChild(b); });
  if (V.item) fillItemText();
}
function showGrid(on){ $('grid').hidden = !on; $('backBtn').hidden = on; if (!on) return; document.title = D.title[L] || ''; }
async function selectItem(i){
  V.cur = i; showGrid(false); V.ready = false; await openItem(D.items[i]);
  if (!GATE) history.replaceState(null, '', '#item=' + i);
  $('gl').focus && $('gl').focus();
}
function backToGrid(){
  const last = V.cur; closeItem(); showGrid(true); if (!GATE) history.replaceState(null, '', '#');
  const c = document.querySelector('.card[data-i="' + last + '"]'); if (c) c.focus();
}
(async () => {
  if (!initCommon()) return;
  $('backBtn').onclick = backToGrid; fillCards();
  const m = /item=(\d+)/.exec(location.hash) || (qs.get('item') ? [0, qs.get('item')] : null);
  if (m && D.items[+m[1]]) await selectItem(+m[1]); else showGrid(true);
  if (qs.get('cycle')){ // 門: 品を n 回切り替え、GPU の資源の数を記録する
    const log = []; const n = +qs.get('cycle');
    for (let k = 0; k < n; k++){ await selectItem(k % D.items.length);
      await new Promise(r => { const w = () => (V.ready ? r() : setTimeout(w, 20)); w(); });
      log.push({item: k % D.items.length, buffers: GS.stats.buffers, textures: GS.stats.textures}); backToGrid(); }
    window.__gsCycle = log;
  }
})();
"""


def _page(cfg: dict, *, catalog: bool) -> str:
    """設定(JSON)を 1 枚の HTML にする。外部の読み込みは無い(CSS・JS・データはすべてページの中)。"""
    js = _JS_CORE + _JS_VIEW + (_JS_CATALOG if catalog else _JS_SINGLE)
    cfg_json = json.dumps(cfg, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    t0 = _html.escape(cfg["title"][cfg["langs"][0]])
    grid = ('<div id="grid" hidden><h1 id="gridTitle"></h1><p class="sub" id="gridSub"></p><div id="cards"></div></div>'
            if catalog else "")
    back = '<button id="backBtn" hidden data-i18n="back"></button>' if catalog else ""
    return (
        '<!doctype html>\n<html lang="%s"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<title>%s</title><style>%s</style></head><body>\n'
        '<div id="stage"><canvas id="gl" tabindex="0"></canvas><svg id="ov" aria-hidden="true"></svg>'
        '<div id="hsLayer"></div><div id="msg"></div></div>\n'
        '<div class="bar" id="top">%s<h1 id="title">%s</h1>'
        '<button id="aboutBtn" data-i18n="about"></button>'
        '<label class="grp"><span data-i18n="lang" hidden></span><select id="lang" data-i18n-title="lang"></select></label></div>\n'
        '<div id="about" hidden role="dialog"><h2 data-i18n="about"></h2><div id="aboutBody"></div>'
        '<button id="aboutClose" data-i18n="close"></button></div>\n'
        '<div id="pop" hidden role="dialog"><h2 id="popT"></h2><p id="popD"></p><button id="popClose" data-i18n="close"></button></div>\n'
        '<div class="bar" id="bot">'
        '<div class="grp"><button data-preset="front" data-i18n="front"></button><button data-preset="side" data-i18n="side"></button>'
        '<button data-preset="top" data-i18n="top"></button><button data-preset="iso" data-i18n="iso"></button></div>'
        '<div class="grp"><button id="spinBtn" aria-pressed="false" data-i18n="spin"></button>'
        '<button id="dimsBtn" aria-pressed="false" data-i18n="dims"></button></div>'
        '<div class="grp"><label data-i18n="bg"></label><button data-bg="white" data-i18n="white"></button>'
        '<button data-bg="gray" data-i18n="gray"></button><button data-bg="black" data-i18n="black"></button></div>'
        '<div class="grp"><label for="opacity" data-i18n="opacity"></label><input id="opacity" type="range" min="0" max="95" value="0"></div>'
        '<div class="grp"><label for="quality" data-i18n="quality"></label><input id="quality" type="range" min="2" max="100" value="100">'
        '<span id="count"></span></div>'
        '<div class="grp"><label data-i18n="help"></label></div></div>\n%s'
        '<script id="gscfg" type="application/json">%s</script>\n<script>%s</script></body></html>\n'
        % (cfg["langs"][0], t0, _CSS, back, t0, grid, cfg_json, js))


def _base_cfg(title, langs, *, up, bg: str, spin: bool, spin_deg_per_s: float, max_radius: int, mobile_quality,
              mobile_above: int = 300_000) -> dict:
    if bg not in BACKGROUNDS:
        raise ValueError("bg must be one of %s" % ", ".join(BACKGROUNDS))
    return {"title": _texts(title, "title", langs), "langs": langs, "langnames": {l: LANG_NAMES[l] for l in langs},
            "ui": {k: {l: v[l] for l in langs} for k, v in UI.items()}, "up": [float(v) for v in np.asarray(up, np.float64)],
            "bgs": {k: list(v) for k, v in BACKGROUNDS.items()}, "bgDefault": bg, "bg": list(BACKGROUNDS[bg]),
            "spin": bool(spin), "spinDeg": float(spin_deg_per_s), "maxRadius": int(max_radius),
            "mobileQuality": None if mobile_quality is None else float(mobile_quality), "mobileAbove": int(mobile_above)}


def gs_viewer_html(gs, out_path=None, *, title="3D Gaussian Splatting", lang=LANGS, note=None, hotspots=None,
                   dims=True, unit_mm: float = 1000.0, up=(0.0, 0.0, 1.0), bg: str = "gray",
                   max_bytes: int = DEFAULT_MAX_BYTES, fov_deg: float = 35.0, camera=None, spin: bool = True,
                   spin_deg_per_s: float = 20.0, bake_light=(0.3, -0.5, 0.8), ambient: float = 0.35,
                   max_radius: int = 64, mobile_quality=0.5,
                   mobile_above: int = 300_000) -> dict:
    """3DGS を、ブラウザで回して見られる1 枚で完結する HTML にする(外部 URL 0・CDN 無し・オフラインで動く)。

    データは位置 3×u16(軸ごとの範囲)・log 大きさ 3×u16・四元数 4×u8・RGBA 4×u8 = 1 個 20 バイトに量子化し、
    gzip → base64 でページに埋める。ブラウザは ``DecompressionStream('gzip')`` で伸ばし、WebGL2 のインスタンス化した
    四角形で描く。2-D 共分散は :func:`gsplatnp.gs_render` と同じ Σ' = J W Σ Wᵀ Jᵀ + 0.3 px²(不透明度は
    √(det Σ / det(Σ + 0.3 I)) 倍)、窓は中心の丸めから ±⌈3√λ_max⌉ 画素(≤ ``max_radius``)、手前から
    C = Σ c_i α_i T_i(半精度の浮動小数のバッファに足してから背景を合成)。前後の並べ替えは Web Worker が
    視点の変わったときだけ行う(ガウシアンの中心の深さを 16 bit の桶で数える)。

    商品の閲覧の機能: ドラッグで回す(慣性つき)・ホイール / ピンチで拡大・自動の回転台(触ると止まる)・視点のプリセット
    (正面 / 側面 / 上 / 斜め)・背景(白 / 灰 / 黒)・注記点(押すと説明が開く、8 言語)・寸法(W × D × H mm)・
    不透明度のしきい値・品質つまみ(ガウシアンの数を重要度の高い順に減らす、スマホの既定 ``mobile_quality``)。
    URL でも開ける: ``?lang=en&bg=white&view=front&dims=1&hs=0&spin=0&quality=0.5``。

    Parameters
    ----------
    gs : dict または パス
        :func:`gsplatnp.gs_read_file` / :func:`gsplatnp.gs_from_world` の dict、または .ply / .splat のパス。
    out_path : str または None
        書き出す先。None なら書かずに返り値の ``html`` に入れる。
    title, note : str または {lang: str}
        題と、ページの「この表示について」に出す注記(例: 「メッシュから初期化した 3DGS で、写真から学習したものではない」)。
    lang : str または 言語の並び
        ``LANGS``(ja, en, zh, tw, ko, de, hi, fr)の部分集合。先頭が既定、``?lang`` と navigator.language で選ぶ。
    hotspots : [{"pos": (x, y, z), "label": str|{lang}, "desc": str|{lang}}]
        注記点。辞書で渡すなら要求した言語が全部要る(黙って補わない)。
    dims : bool または {"upright", "obb"}
        寸法を出すか。True = ``"upright"``(上向きを H に固定した最小の箱)、``"obb"`` = 向き自由の最小体積の箱。
        どちらも向きは :func:`measure3d.smallest_box3` が決め、大きさは全部の不透明なガウシアンの中心で測る。
    unit_mm : float
        座標の 1 単位が何 mm か(既定 1000 = メートル)。
    up : (3,)
        上向きの軸(回転台の軸、寸法の H)。
    bg : {"white", "gray", "black"}
        最初の背景。
    max_bytes : int
        埋め込むデータの上限(base64 後のバイト数、既定 16 MB)。超えたら不透明度・大きさの小さい順に間引く。
    fov_deg, camera, spin, spin_deg_per_s :
        縦の画角・最初の視点(``{"yaw", "pitch", "dist", "target"}`` の一部でよい)・回転台を回して開くか・その速さ。
    bake_light, ambient :
        gs_from_world の dict のとき、世界の座標の光で陰影を色へ焼き込む(gs_render と同じ Lambert)。None で焼かない。
    max_radius : int
        1 個の窓の半径の上限(画素、gs_render の ``max_radius`` と同じ意味)。
    mobile_quality, mobile_above : float または None, int
        指で触る端末(``pointer: coarse``)で、ガウシアンが ``mobile_above`` 個を超えるときに最初に描く割合。
        None なら全部。品質つまみは重要度の順(間引きと同じ順)の先頭から描くので、小さな部品から消える。

    Returns
    -------
    dict
        ``path``・``bytes``(HTML の大きさ)・``n_input``・``n_kept``・``n_dropped``・``thinned``・``thinning``(間引きの記録)・
        ``dims_mm``(W, D, H)・``dims``(箱の 8 隅つき)・``camera``・``sh_degree_in``・``sh_degree_used``(= 0)・
        ``sh_dropped``・``embedded_bytes``・``external_urls``(= 0 を確かめた数)。``out_path`` が None なら ``html`` も。

    Raises
    ------
    ValueError
        gs が空・形が合わない・非有限、未対応の言語、文言の言語の欠け、bg が 3 色以外、上限に 1 個も入らない。

    空の入力(``gs`` が空の dict)は ValueError。

    Examples
    --------
    >>> import gsplatnp, gsviewer
    >>> r = gsviewer.gs_viewer_html("scene.ply", "view.html", title="My product")    # doctest: +SKIP
    >>> r["n_kept"], r["dims_mm"]                                                    # doctest: +SKIP

    CLI: ``py -3.11 -m gsviewer in.ply --out view.html --title "My product"``。
    """
    langs = _langs(lang)
    cfg = _base_cfg(title, langs, up=up, bg=bg, spin=spin, spin_deg_per_s=spin_deg_per_s, max_radius=max_radius,
                    mobile_quality=mobile_quality, mobile_above=mobile_above)
    shell = len(_page(dict(cfg, items=[]), catalog=False).encode("utf-8"))
    budget = int(max_bytes) - shell - 4096
    if budget <= 0:
        raise ValueError("gs_viewer_html: max_bytes %d is smaller than the page itself (%d)" % (int(max_bytes), shell))
    c0 = _canon(gs, bake_light=bake_light, ambient=ambient)
    for _try in range(4):                       # 注記などの文言が予想より長ければ、はみ出した分だけ割り当てを減らす
        payload, info, _c = _item_payload(c0, budget=budget, up=up, unit_mm=unit_mm, fov_deg=fov_deg, bake_light=None,
                                          ambient=ambient, dims=dims, hotspots=hotspots, langs=langs, name=title, note=note,
                                          camera=camera)
        cfg["items"] = [payload]
        page = _page(cfg, catalog=False)
        over = len(page.encode("utf-8")) - int(max_bytes)
        if over <= 0:
            break
        budget -= over + 1024
    return _finish(page, out_path, info, max_bytes)


def _finish(page: str, out_path, info: dict, max_bytes: int) -> dict:
    data = page.encode("utf-8")
    n_url = page.count("http://") + page.count("https://")
    if n_url:
        raise ValueError("gs viewer page would contain %d external URLs (refusing to write)" % n_url)
    out = dict(info)
    out.update({"bytes": len(data), "external_urls": 0, "max_bytes": int(max_bytes)})
    if len(data) > int(max_bytes):
        raise ValueError("gs viewer page is %d bytes > max_bytes %d" % (len(data), int(max_bytes)))
    if out_path is None:
        out["html"] = page
        out["path"] = None
    else:
        p = os.fspath(out_path)
        d = os.path.dirname(os.path.abspath(p))
        os.makedirs(d, exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        out["path"] = p
    return out


def gs_catalog_html(items, out_path=None, *, title="3DGS catalogue", lang=LANGS, up=(0.0, 0.0, 1.0), bg: str = "gray",
                    max_bytes: int = DEFAULT_MAX_BYTES, unit_mm: float = 1000.0, fov_deg: float = 35.0, thumb_px: int = 256,
                    dims=True, spin: bool = True, spin_deg_per_s: float = 20.0, bake_light=(0.3, -0.5, 0.8),
                    ambient: float = 0.35, max_radius: int = 64, mobile_quality=0.5,
                   mobile_above: int = 300_000) -> dict:
    """複数の 3DGS をサムネイルの一覧から選んで見る、1 枚で完結するカタログの HTML を書く。

    各品のサムネイルは :func:`gsplatnp.gs_render`(numpy の EWA 描画)が、ページの最初の視点と同じカメラで描いた PNG
    (``thumb_px`` 四方)。押すと同じページの中で 3-D の表示に切り替わり、「一覧に戻る」(Esc でも)で戻る。
    データは選ばれた品の分だけ ``DecompressionStream`` で伸ばし、切り替えると前の品のテクスチャ・バッファを解放する。
    容量の上限 ``max_bytes`` は全体で、品ごとの割り当て = (上限 − ページ − サムネイル) をガウシアンの数に比例して配る。
    割り当てを超える品は :func:`gs_viewer_html` と同じ順で間引き、品ごとの記録を返す。

    Parameters
    ----------
    items : list of dict
        ``{"gs": dict | "path": str, "name": str|{lang}, "desc": str|{lang}, "note": str|{lang}, "hotspots": [...],
        "camera": {...}}``。``name`` は必須。
    out_path, title, lang, up, bg, max_bytes, unit_mm, fov_deg, dims, spin, bake_light, ambient, max_radius, mobile_quality :
        :func:`gs_viewer_html` と同じ。
    thumb_px : int
        サムネイルの 1 辺(画素)。

    Returns
    -------
    dict
        ``path``・``bytes``・``items``(品ごとの ``n_input`` / ``n_kept`` / ``n_dropped`` / ``thinned`` / ``dims_mm`` /
        ``thumb_bytes`` / ``camera``)・``n_dropped_total``・``external_urls``(= 0)。``out_path`` が None なら ``html`` も。

    Raises
    ------
    ValueError
        items が空・name が無い・gs と path のどちらも無い、ほかは :func:`gs_viewer_html` と同じ。

    空の入力(``items`` が空の list)は ValueError。

    Examples
    --------
    >>> import gsviewer
    >>> r = gsviewer.gs_catalog_html([{"path": "mug.ply", "name": "Mug"}, {"path": "shoe.splat", "name": "Shoe"}],
    ...                              "catalog.html", title="Shop")                        # doctest: +SKIP
    """
    import gsplatnp as _g
    from pocviewer import _png_encode
    if not items:
        raise ValueError("gs_catalog_html: items is empty — pass at least one item")
    langs = _langs(lang)
    cfg = _base_cfg(title, langs, up=up, bg=bg, spin=spin, spin_deg_per_s=spin_deg_per_s, max_radius=max_radius,
                    mobile_quality=mobile_quality, mobile_above=mobile_above)
    canons, thumbs, cams = [], [], []
    for i, it in enumerate(items):
        if not isinstance(it, dict) or "name" not in it:
            raise ValueError("gs_catalog_html: item %d needs a name" % i)
        src = it.get("gs", it.get("path"))
        if src is None:
            raise ValueError("gs_catalog_html: item %d needs gs or path" % i)
        canons.append(src)
    # サムネイル: 量子化前の canon を、最初の視点のカメラで gs_render する(ページの最初の表示と同じ絵になるはず = 門)
    infos, payloads = [], []
    shell = len(_page(dict(cfg, items=[]), catalog=True).encode("utf-8")) + 4096
    pre = [_canon(s, bake_light=bake_light, ambient=ambient) for s in canons]
    for i, (it, c0) in enumerate(zip(items, pre)):
        dm = (_dimensions(c0, up, unit_mm=unit_mm, mode="upright" if dims is True else str(dims)) if dims else None)
        cam = _default_camera(c0, up, fov_deg, dm)
        if it.get("camera"):
            cam.update({k: (list(map(float, v)) if k == "target" else float(v)) for k, v in it["camera"].items()})
        pose = _orbit_pose(cam["target"], cam["yaw"], cam["pitch"], cam["dist"], up)
        K = _intrinsics(cam["fov"], thumb_px, thumb_px)
        r = _g.gs_render(_renderable(c0), pose, K, thumb_px, thumb_px, ambient=1.0, sky=BACKGROUNDS[bg],
                         max_radius=max_radius, max_pairs=60_000_000)
        png = _png_encode((np.clip(r["color"], 0, 1) * 255.0 + 0.5).astype(np.uint8))
        thumbs.append("data:image/png;base64," + base64.b64encode(png).decode("ascii"))
        cams.append(cam)
    budget_all = int(max_bytes) - shell - sum(len(t) for t in thumbs) - 2048 * len(items)
    if budget_all <= 0:
        raise ValueError("gs_catalog_html: max_bytes %d leaves no room for data after the page and thumbnails" % int(max_bytes))
    ns = np.array([len(c["mu"]) for c in pre], np.float64)
    est = ns * BYTES_PER_SPLAT * 0.75 * 4 / 3          # 圧縮後の見込み(配分の比だけに使う)
    share = budget_all * ns / ns.sum() if est.sum() > budget_all else np.full(len(ns), float(budget_all))
    for i, (it, c0) in enumerate(zip(items, pre)):
        payload, info, _c = _item_payload(c0, budget=int(share[i]), up=up, unit_mm=unit_mm,
                                          fov_deg=fov_deg, bake_light=bake_light, ambient=ambient, dims=dims,
                                          hotspots=it.get("hotspots"), langs=langs, name=it["name"], desc=it.get("desc", ""),
                                          note=it.get("note"), camera=it.get("camera"))
        payload["thumb"] = thumbs[i]
        payload["camera"] = cams[i]
        info.update({"thumb_bytes": len(thumbs[i]), "name": payload["name"][langs[0]]})
        payloads.append(payload)
        infos.append(info)
    cfg["items"] = payloads
    page = _page(cfg, catalog=True)
    out = _finish(page, out_path, {"items": infos}, max_bytes)
    out["n_dropped_total"] = int(sum(i["n_dropped"] for i in infos))
    out["thumb_px"] = int(thumb_px)
    return out


# ───────────────────────────── 読み戻し(門と検査用)───────────────────────────── #
def _read_embedded(page_or_path) -> dict:
    """書いた HTML から設定と、品ごとの量子化を戻したガウシアン(:func:`_decode` の形)を取り出す。"""
    s = page_or_path
    if isinstance(s, (str, os.PathLike)) and not str(s).lstrip().startswith("<"):
        with open(s, encoding="utf-8") as f:
            s = f.read()
    a = s.index('<script id="gscfg" type="application/json">') + len('<script id="gscfg" type="application/json">')
    b = s.index("</script>", a)
    cfg = json.loads(s[a:b].replace("<\\/", "</"))
    items = [_decode(base64.b64decode(it["b64"]), it["meta"]) for it in cfg["items"]]
    return {"cfg": cfg, "items": items}


def _main(argv=None) -> int:
    """CLI: ``py -3.11 -m gsviewer in.ply [more.splat ...] --out view.html --title "..."``(2 つ以上ならカタログ)。"""
    import argparse
    ap = argparse.ArgumentParser(prog="gsviewer", description="3DGS (.ply / .splat) → one self-contained HTML viewer")
    ap.add_argument("inputs", nargs="+", help=".ply (INRIA 3DGS) or .splat files; two or more make a catalogue")
    ap.add_argument("--out", required=True, help="output .html")
    ap.add_argument("--title", default="3D Gaussian Splatting")
    ap.add_argument("--lang", default=",".join(LANGS), help="comma-separated, first is default: " + ",".join(LANGS))
    ap.add_argument("--max-mb", type=float, default=16.0, help="size limit of the page in MB (thins Gaussians to fit)")
    ap.add_argument("--unit-mm", type=float, default=1000.0, help="mm per scene unit (1000 = metres)")
    ap.add_argument("--up", default="0,0,1", help="up axis, e.g. 0,-1,0 for most captured scenes")
    ap.add_argument("--bg", default="gray", choices=sorted(BACKGROUNDS))
    ap.add_argument("--no-dims", action="store_true", help="do not show the W x D x H box")
    ap.add_argument("--note", default=None, help="text for 'About this view'")
    a = ap.parse_args(argv)
    up = tuple(float(v) for v in a.up.split(","))
    langs = [l.strip() for l in a.lang.split(",") if l.strip()]
    mb = int(a.max_mb * 1024 * 1024)
    if len(a.inputs) == 1:
        r = gs_viewer_html(a.inputs[0], a.out, title=a.title, lang=langs, up=up, bg=a.bg, max_bytes=mb, unit_mm=a.unit_mm,
                           dims=not a.no_dims, note=a.note)
        print("wrote %s  %.2f MB  Gaussians %d / %d (dropped %d)  dims %s" % (
            r["path"], r["bytes"] / 1048576, r["n_kept"], r["n_input"], r["n_dropped"],
            "x".join("%.1f" % r["dims_mm"][k] for k in "WDH") + " mm" if r["dims_mm"] else "-"))
    else:
        items = [{"path": p, "name": os.path.splitext(os.path.basename(p))[0]} for p in a.inputs]
        r = gs_catalog_html(items, a.out, title=a.title, lang=langs, up=up, bg=a.bg, max_bytes=mb, unit_mm=a.unit_mm,
                            dims=not a.no_dims)
        print("wrote %s  %.2f MB  %d items  dropped %d" % (r["path"], r["bytes"] / 1048576, len(items), r["n_dropped_total"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
