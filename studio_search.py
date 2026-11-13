# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""studio_search — 「やりたいこと」から op を探し、今の入力に合うかで 3 群に分ける(Studio の論理層、Qt を使わない)。

Studio の UX 案 ①(目的検索): 利用者は正式な op 名を知らない。「小さい領域を消す」と打つと、
名前の一覧ではなく次の 3 群で返す。

* ``applicable``         — 今の入力の型(sort)のまま適用できる(台帳が宣言している、または
  :func:`opassist.accepted_sorts` の**実測**が ``works``)。
* ``needs_preprocessing`` — 型が合わないが、2 手以内の前処理(producers / consumers で繋ぐ op の列 = ``bridge``)で届く。
* ``other``              — 今の入力が分からない、または 2 手以内では届かない。

★設計の約束

* 検索そのものは :func:`fullseye.opsearch.search_ops` に任せ、**順位は作り直さない**
  (群の中の並びは検索の点数順 = 同点は ``search_ops`` の並びのまま)。
* :func:`opassist.accepted_sorts` は op を何度も走らせて測る高価な関数。**上位 k 件にだけ**、
  型が宣言と合わなかった台帳 op にだけ使い、op ごとに ``_ACCEPTED`` へ覚える(全レジストリには掛けない)。
* 型の語彙は 2 つある(台帳 = ``image2d`` / ``mask`` …、2-D レジストリ = ``image`` / ``region`` …)。
  同じものを指す対を :data:`SORT_ALIASES` で同一視してから比べる。
* このモジュールは**提案を返すだけ**。処理列へ追加も実行もしない(UI が「今のデータで試す」で一時試行する)。

Qt 非依存・標準ライブラリ + numpy のみ(``opassist`` / ``fullseye.opsearch`` は同梱)。
"""
from __future__ import annotations

import difflib
from collections import Counter
from typing import Any, Optional

import numpy as np

__all__ = [
    "current_sort_of", "search_grouped", "search_zero_results_help",
    "SORT_ALIASES", "canonical_sort", "clear_caches", "STAPLES", "STAPLE_EXCLUDE_JA", "staples_for",
    "SAMPLE_TERMS", "samples_for",
]

#: 台帳の型名 → 2-D レジストリの型名(同じものを指す対)。比べる前にこれで寄せる。
SORT_ALIASES = {
    "image2d": "image", "mask": "region", "rgbimage": "color", "rgb": "color", "voxel": "volume",
}

#: 群の名前(この順に並べる)
GROUPS = ("applicable", "needs_preprocessing", "other")

#: 入門の語 → 定番の op(★2026-11-12、使い勝手の点検 P-09)。
#: 「二値化」で `hx_close_edges`、「回転」で `rope_rotate`、「ラベリング」で `polar_unwrap` が先頭に出ていた
#: (検索は説明文の語の重みで並べるので、3,800 本の中で基本の op が埋もれる)。
#: 検索の順位(``search_ops``)は変えず、**別の欄 ``staples``** として返す —— 画面はそれを先頭の「定番」に出す。
#: 当て方(★2026-11-12 の独立レビューで部分一致の誤爆が出たので締めた。`顕微鏡` → mirror、`account` → ラベリング、
#: `nothing` → skeleton、`knowledge` → エッジ など):
#:
#: * 英語は**単語として**当てる(問い合わせを英数字の語に切り、表の語と完全一致。2 語の句は連続する語として)。
#: * 日本語は部分文字列で当てるが、先に :data:`STAPLE_EXCLUDE_JA` の語(別の意味の複合語)を問い合わせから除く。
#: * 問い合わせに ``_`` がある(op 名を打っている途中)、または語のどれかが op 名そのもの(``canny edge`` の
#:   ``canny``)なら、定番は出さない —— 名前で探している人の先頭に別の op を置かない。
#:
#: op は索引に在るものだけ返す(表の全 op が索引に在ることは試験で数える)。
STAPLES = (
    (("二値化", "2値化", "2 値化", "しきい値", "閾値", "binarize", "binarise", "binarization", "thresholding"),
     ("otsu", "threshold", "auto_threshold", "binary_threshold")),
    (("エッジ保存", "エッジを保", "edge preserving"), ("bilateral", "median")),
    (("ノイズ", "雑音", "denoise", "denoising", "noise"), ("median", "bilateral", "gaussian")),
    (("ぼかし", "ぼかす", "ぼけ", "平滑", "スムージング", "blur", "blurring", "smooth", "smoothing"),
     ("gaussian", "mean_image", "median")),
    (("エッジ", "輪郭", "境界", "edge", "edges"), ("sobel_amp", "canny", "edges_image", "laplace")),
    (("明るく", "明るさ", "暗く", "輝度", "brightness", "brighten", "brighter"),
     ("scale_image", "gamma", "scale_image_max")),
    (("コントラスト", "contrast", "ヒストグラム平坦", "equalize", "equalise", "equalization"),
     ("equ_histo_image", "clahe", "scale_image_max")),
    (("鮮鋭", "シャープ", "くっきり", "sharpen", "sharpening"), ("unsharp", "laplace")),
    (("回転", "rotate", "rotation"), ("rotate_image",)),
    (("拡大", "縮小", "リサイズ", "resize", "zoom"), ("zoom_image_factor", "zoom_image_size")),
    (("反転", "ネガ", "invert", "negative"), ("invert_image",)),
    (("鏡像", "ミラー", "左右反転", "上下反転", "左右を", "上下を", "mirror", "flip"), ("mirror_image",)),
    (("膨張", "太らせ", "dilate", "dilation"), ("dilation_circle", "dilation_rectangle1")),
    (("収縮", "細らせ", "erosion", "erode"), ("erosion_circle", "erosion_rectangle1")),
    (("オープニング", "opening"), ("opening_circle",)),
    (("クロージング", "closing"), ("closing_circle",)),
    (("穴埋め", "穴を埋め", "fill holes", "fill hole"), ("fill_up",)),
    (("ラベリング", "ラベル付け", "連結成分", "個数", "数える", "labeling", "labelling", "connected components"),
     ("connect_and_holes", "area_center", "select_shape")),
    (("面積", "重心", "centroid"), ("area_center", "select_shape")),
    (("細線化", "骨格", "skeleton", "skeletonize", "thinning"), ("skeleton",)),
    (("距離変換", "distance transform"), ("distance_transform",)),
    (("円検出", "円を検出", "円を見つけ", "circle detection", "find circles", "detect circles"),
     ("cv_hough_circles", "hough_circle_trans")),
    (("直線検出", "直線を検出", "直線を見つけ", "line detection", "hough lines", "detect lines"), ("hough_line_trans",)),
    (("テンプレート", "マッチング", "template matching", "template"), ("ncc_locate", "shape_locate")),
    (("差分", "引き算", "difference", "subtract"), ("abs_diff_image", "sub_image")),
    (("フーリエ", "周波数", "fft", "fourier"), ("fft_image",)),
    (("領域分割", "ウォーターシェッド", "watershed"), ("watersheds",)),
    # ---- 現場の言葉(★2026-11-13、初回起動の点検 M12: 「傷」「へこみ」「熱」で 0 件だった)。欠陥の種類ごとに、
    # 1 枚の濃淡画像で最初に試す op(背景を引く・細い筋を強める・局所しきい値 …)。X 線・CT の語は足さない。
    (("傷", "きず", "キズ", "擦り傷", "引っかき", "scratch", "scratches", "scuff"),
     ("sk_rolling_ball", "bothat", "sk_frangi", "dyn_threshold")),
    (("へこみ", "凹み", "くぼみ", "窪み", "打痕", "dent", "dents"),
     ("hx_plane_deviation", "sk_rolling_ball", "tophat", "dyn_threshold")),
    (("欠け", "チッピング", "chipping", "chipped"), ("otsu", "fill_up", "sk_convex", "convexity")),
    (("割れ", "ひび", "ヒビ", "クラック", "亀裂", "crack", "cracks", "fissure"),
     ("sk_frangi", "bothat", "xsk_sato", "dyn_threshold")),
    (("汚れ", "よごれ", "シミ", "染み", "stain", "stains", "dirt", "smudge"),
     ("sk_rolling_ball", "dyn_threshold", "local_threshold", "sk_dog")),
    (("ムラ", "シェーディング", "mura", "shading", "uneven", "unevenness", "non-uniform"),
     ("sk_rolling_ball", "highpass", "sk_sauvola", "clahe")),
    (("異物", "ゴミ", "ごみ", "埃", "ほこり", "繊維", "foreign matter", "foreign fibre", "foreign fiber", "debris",
      "dust", "contamination"),
     ("tophat", "bothat", "dyn_threshold", "select_shape")),
    (("熱", "サーモ", "赤外", "温度", "thermal", "thermography", "infrared", "temperature", "hot spot"),
     ("scale_image_max", "threshold", "local_max", "clahe")),
    (("錆", "サビ", "腐食", "rust", "corrosion"), ("std_filter", "dyn_threshold", "local_threshold", "gabor")),
    (("刻印", "印字", "ロット", "engraved", "lot code", "marking", "ocr"),
     ("adaptive_gauss_thresh", "otsu", "dyn_threshold", "select_shape")),
    (("穴の数", "穴を数え", "穴の個数", "count holes", "hole count"),
     ("otsu", "sk_clear_border", "count_obj", "connect_and_holes")),
)

#: 現場の言葉 → 同梱の FA の見本(``recipes`` の名前。見本ごとに自分の画像を持つ)。★2026-11-13(初回起動の点検 M12):
#: 傷・打痕の見本があるのに、検索から届かなかった。当て方は :data:`STAPLES` と同じ(英語は単語、日本語は部分文字列、
#: op 名を含む問い合わせには出さない)。どの語も :data:`STAPLES` にもある(画面では定番の直後に並ぶ)。
#: X 線・CT の見本(溶接の気孔)には語を当てない。
SAMPLE_TERMS = (
    (("傷", "きず", "キズ", "擦り傷", "引っかき", "scratch", "scratches", "scuff"), ("FA — scratch on hairline metal",)),
    (("へこみ", "凹み", "くぼみ", "窪み", "打痕", "dent", "dents", "異物", "繊維", "foreign matter", "foreign fibre",
      "foreign fiber"), ("FA — dent and foreign fibre on resin",)),
    (("刻印", "印字", "ロット", "engraved", "lot code", "marking", "ocr"), ("FA — engraved lot code (binarize for OCR)",)),
    (("穴の数", "穴を数え", "穴の個数", "count holes", "hole count"), ("FA — count holes in a back-lit plate",)),
)

#: 英語の句で、別の意味になるもの(「edge preserving」の edge でエッジ検出を出さない)。問い合わせから除いてから当てる。
#: その句自身が表の語でもあるとき(「edge preserving」は bilateral の語)は、その表の語だけは除く前の問い合わせで当てる。
STAPLE_EXCLUDE_EN = ("edge preserving",)

#: 日本語の部分一致で、別の意味になる複合語。問い合わせから除いてから当てる。
#: ここに在る語が表の語そのものでもあるとき(「左右反転」は mirror の語で、かつ「反転」= invert から除きたい)は、
#: その表の語だけは除く前の問い合わせで当てる。
#: ★表の語は、2026-11-12 の 2 回目の独立レビューで、部分一致の誤爆を避けるため**意図して**狭めた(f54982b9f9):
#: 単独の「鏡」(顕微鏡・望遠鏡)・「左右」「上下」(上下限・左右対称)・「ラベル」(ラベル文字列)では定番を出さず、
#: 「鏡像」「左右反転」「上下反転」「左右を」「上下を」「ラベル付け」「ラベリング」で出す(試験 test_bare_ambiguous_words_*)。
STAPLE_EXCLUDE_JA = ("エッジ保存", "エッジを保", "顕微鏡", "望遠鏡", "内視鏡", "鏡面", "楕円", "半円", "同心円",
                     "ノイズ付加", "ノイズを加", "ノイズを足", "境界条件", "輪郭線の長さ", "左右反転", "上下反転")

#: 定番の欄に出す件数の上限
STAPLES_MAX = 6

#: ``accepted_sorts`` の実測結果を op ごとに覚える(高価なので。テストは :func:`clear_caches` で空にする)
_ACCEPTED: dict = {}
_EDGE_CACHE: dict = {}
_BRIDGE_CACHE: dict = {}
_NAME_CACHE: dict = {}


def clear_caches() -> None:
    """実測・型グラフ・名前表の覚えを捨てる(テストと、台帳が変わった後の再計算用)。"""
    _ACCEPTED.clear()
    _EDGE_CACHE.clear()
    _BRIDGE_CACHE.clear()
    _NAME_CACHE.clear()


def canonical_sort(sort: Optional[str]) -> Optional[str]:
    """型名を台帳・レジストリ共通の代表名に寄せる(``image2d`` → ``image``、``mask`` → ``region`` …)。"""
    if sort is None:
        return None
    return SORT_ALIASES.get(sort, sort)


# --------------------------------------------------------------------------- #
# 今の値 → 型                                                                  #
# --------------------------------------------------------------------------- #
def _is_binary(a: np.ndarray) -> bool:
    """値が 0/1 だけ(``studio._is_binary`` と同じ規則)。"""
    if a.dtype == bool:
        return True
    b = np.asarray(a, dtype=np.float64) if a.dtype.kind in "iu" else a
    u = np.unique(b[np.isfinite(b)]) if b.size else b
    return u.size <= 2 and set(np.round(u, 6).tolist()).issubset({0.0, 1.0})


def _looks_like_labels(a: np.ndarray) -> bool:
    """整数の 2 次元で、0.. の密な番号が付いた**ラベル画像**らしいか(ヒューリスティック)。

    8 ビット画像は階調が多いので、値の種類が 16 以下のときだけラベルとみなす。
    曖昧な値は呼び出し側が ``current_sort`` で上書きする。
    """
    if a.dtype.kind not in "iu" or a.ndim != 2 or a.size == 0:
        return False
    if int(a.min()) < 0:
        return False
    u = np.unique(a)
    n = int(u.size)
    if n < 3:
        return False
    if a.dtype == np.uint8 and n > 16:
        return False
    return n <= max(16, a.size // 64) and n >= 0.9 * (int(u.max()) - int(u.min()) + 1)


def current_sort_of(value: Any) -> Optional[str]:
    """実際の値から、台帳の型(sort)名を推す。分からなければ ``None``。

    * 2 次元: 二値 → ``mask``、ラベルらしい整数 → ``labels2d``、複素 → ``cimage``、他 → ``image2d``
    * 3 次元: ``(2, h, w)`` の実数 → ``flow2d``、最後の軸が 3 → ``rgbimage``、4 → ``rgba``、1 → ``image2d``、他 → ``voxel``
    * 1 次元の数列・数の列 → ``signal``、``(N, 3)``(N ≥ 4, 実数)→ ``points``
    * ``cs`` を持つ dict → ``contour``、他の dict → ``table``、数 → ``scalar``、文字列 → ``text``

    ★``(N, 3)`` は 3 画素幅の画像とも読めるが、実用上は点群が圧倒的なので ``points`` に倒す。
    推定は :func:`studio.inspect_result` の ``kind`` と矛盾しない(門が同じ見本で照合する)。
    """
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_, int, float, np.number)):
        return "scalar"
    if isinstance(value, str):
        return "text"
    if isinstance(value, dict):
        return "contour" if "cs" in value else "table"
    if hasattr(value, "cs") and not isinstance(value, np.ndarray):
        return "contour"
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        if all(isinstance(v, dict) for v in value):
            return "table"
        if all(isinstance(v, (int, float, np.number)) and not isinstance(v, bool) for v in value):
            return "signal"
        if all(isinstance(v, np.ndarray) and v.ndim == 2 and v.shape == value[0].shape for v in value):
            return "images"
        return None
    if not isinstance(value, np.ndarray):
        return None
    a = value
    if a.size == 0 or a.dtype.kind not in "biufc":
        return None
    if a.ndim == 0:
        return "scalar"
    if a.ndim == 1:
        return "signal"
    if a.ndim == 2:
        if a.dtype.kind == "c":
            return "cimage"
        if a.shape[1] == 3 and a.shape[0] >= 4 and a.dtype.kind == "f":
            return "points"
        if _is_binary(a):
            return "mask"
        if _looks_like_labels(a):
            return "labels2d"
        return "image2d"
    if a.ndim == 3:
        if a.shape[0] == 2 and a.shape[1] >= 2 and a.shape[2] >= 2 and a.shape[2] not in (3, 4) \
                and a.dtype.kind in "biuf":
            return "flow2d"
        if a.shape[2] == 3:
            return "rgbimage"
        if a.shape[2] == 4:
            return "rgba"
        if a.shape[2] == 1:
            return "image2d"
        return "voxel"
    if a.ndim == 4:
        return "rgbvideo" if a.shape[3] == 3 else "volseq"
    return None


# --------------------------------------------------------------------------- #
# 索引と台帳の表                                                               #
# --------------------------------------------------------------------------- #
def _index() -> dict:
    from fullseye import opsearch
    return opsearch.load_index()


def _row_of(name: str) -> Optional[dict]:
    ix = _index()
    i = ix["names"].get(name.lower())
    return ix["rows"][i] if i is not None else None


def _first_sort(in_sort: Optional[str]) -> tuple[Optional[str], list]:
    """``"image2d × mask"`` → (``"image2d"``, [``"mask"``])。入力が無ければ (None, [])。"""
    if not in_sort:
        return None, []
    parts = [p.strip() for p in in_sort.split("×") if p.strip()]
    return (parts[0] if parts else None), parts[1:]


def _ledger_names() -> frozenset:
    if "ledger" not in _NAME_CACHE:
        import opassist
        _NAME_CACHE["ledger"] = frozenset(opassist.known_ops())
    return _NAME_CACHE["ledger"]


def _is_registry(name: str) -> bool:
    import api
    return api.find_op(name) is not None


def _tier(name: str) -> str:
    """どの層の op か: ``registry``(単入力の 2-D レジストリ)/ ``ledger``(型付き台帳)/ ``nary``(複数入力の 2-D)/
    ``z_algo``(汎用アルゴリズム)/ ``unavailable``。索引に在るのにこの環境では登録されていない op
    (任意の依存が無い CI の一部の殻など)は ``unavailable`` —— 検索には出すが、UI は走らせられない印にする。"""
    if _is_registry(name):
        return "registry"
    if name in _ledger_names():
        return "ledger"
    if "tiers" not in _NAME_CACHE:
        import api
        _NAME_CACHE["tiers"] = {d["name"]: d["tier"] for d in api.list_ops(include_ledger=True, include_algo=True)}
    return _NAME_CACHE["tiers"].get(name, "unavailable")


def _edges() -> dict:
    """単入力 op の辺 ``{名前: (入力の代表型, 出力の代表型)}``。索引の i / o 欄が正本(台帳 + レジストリ)。"""
    if "edges" not in _EDGE_CACHE:
        edges = {}
        for r in _index()["rows"]:
            i, o = r.get("i"), r.get("o")
            if not i or not o or "×" in i or "×" in o:
                continue
            edges[r["n"]] = (canonical_sort(i), canonical_sort(o))
        _EDGE_CACHE["edges"] = edges
    return _EDGE_CACHE["edges"]


def _class_members(cls: str) -> list:
    """代表型 ``cls`` に寄る台帳側の型名(``producers`` / ``consumers`` に渡せるもの)。"""
    import opassist
    known = set(opassist.known_sorts())
    return [s for s in known if canonical_sort(s) == cls]


def _consuming(cls: str) -> set:
    """代表型 ``cls`` を単独の入力に取る op の名前(台帳は ``opassist.consumers``、レジストリは索引)。"""
    import opassist
    edges = _edges()
    found = {n for n, (i, _o) in edges.items() if i == cls}
    for s in _class_members(cls):
        found |= {n for n in opassist.consumers(s) if n in edges and edges[n][0] == cls}
    return found


def _producing(cls: str) -> set:
    """代表型 ``cls`` を単入力から作る op の名前(台帳は ``opassist.producers``)。"""
    import opassist
    edges = _edges()
    found = {n for n, (_i, o) in edges.items() if o == cls}
    for s in _class_members(cls):
        found |= {n for n in opassist.producers(s) if n in edges and edges[n][1] == cls}
    return found


def _required_knobs(name: str) -> int:
    """必須のつまみ(データ以外で既定値の無い引数)の数。台帳 op だけ数え、他は 0。"""
    if "req" not in _NAME_CACHE:
        _NAME_CACHE["req"] = {}
    memo = _NAME_CACHE["req"]
    if name not in memo:
        try:
            import opassist
            memo[name] = sum(1 for sp in opassist.param_spec(name)
                             if sp.get("kind") != "data" and sp.get("required"))
        except Exception:                                    # noqa: BLE001 - 数えられない op は 0 とみなす
            memo[name] = 0
    return memo[name]


def _bridge_rank(name: str) -> tuple:
    """橋渡し op の選び方: この環境で動く → 既定のまま走る(必須のつまみが少ない)→ レジストリの基本 op → 名前の短い順 → 辞書順(決定的)。"""
    return (1 if _tier(name) == "unavailable" else 0, _required_knobs(name), 0 if _is_registry(name) else 1,
            len(name), name)


def _bridge(cur: Optional[str], target: Optional[str], exclude: str = "") -> list:
    """現在の型 ``cur`` から ``target`` へ繋ぐ**最短の op の列**(0 手は無い。2 手まで。無ければ ``[]``)。"""
    if cur is None or target is None or cur == target:
        return []
    key = (cur, target, exclude)
    if key in _BRIDGE_CACHE:
        return list(_BRIDGE_CACHE[key])
    edges = _edges()
    prod = _producing(target) - {exclude}
    cons = _consuming(cur) - {exclude}
    one = sorted(prod & cons, key=_bridge_rank)
    if one:
        res = [one[0]]
    else:
        res = []
        by_mid: dict = {}
        for a in cons:
            mid = edges[a][1]
            if mid in (cur, target):
                continue
            by_mid.setdefault(mid, []).append(a)
        best = None
        for mid in sorted(by_mid):
            second = sorted(prod & _consuming(mid), key=_bridge_rank)
            if not second:
                continue
            first = sorted(by_mid[mid], key=_bridge_rank)[0]
            cand = (_bridge_rank(first), _bridge_rank(second[0]), [first, second[0]])
            if best is None or cand[:2] < best[:2]:
                best = cand
        if best is not None:
            res = best[2]
    _BRIDGE_CACHE[key] = tuple(res)
    return list(res)


# --------------------------------------------------------------------------- #
# 適合の判定                                                                   #
# --------------------------------------------------------------------------- #
def _fits_declared(in_sort: Optional[str], cur: Optional[str]) -> bool:
    """宣言された先頭入力の型が今の型と同じ(別名を寄せて比較)。``any`` は何でも通る。入力の無い op は False。"""
    first, _rest = _first_sort(in_sort)
    if first is None or cur is None:
        return False
    return first == "any" or canonical_sort(first) == cur


def _measured_works(name: str, cur_sort: str) -> bool:
    """台帳 op が宣言外の今の型も**実測で通す**か(``accepted_sorts`` の ``works``)。結果は op ごとに覚える。"""
    import opassist
    if name not in _ACCEPTED:
        try:
            _ACCEPTED[name] = opassist.accepted_sorts(name)
        except Exception:                                    # noqa: BLE001 - 測れない op は「通すとは言わない」
            _ACCEPTED[name] = {}
    got = _ACCEPTED[name]
    names = [cur_sort] + [s for s, c in SORT_ALIASES.items() if c == canonical_sort(cur_sort)]
    return any(got.get(s) in ("declared", "works") for s in names)


# --------------------------------------------------------------------------- #
# 当たった理由                                                                 #
# --------------------------------------------------------------------------- #
def _why(query: str, row: dict) -> list:
    """問い合わせのどの欄に当たったか: ``name`` / ``alias`` / ``summary`` / ``synonym`` / ``context`` / ``meta``。"""
    from fullseye import opsearch as so
    q = set(so.tokenize(query))
    extra = set(so._synonym_tokens(query, set(q)))
    if not q and not extra:
        return []
    name_t = set(so.tokenize(row["n"]))
    alias_t = set(so.tokenize(row.get("h") or ""))
    summ_t: set = set()
    for txt in (row.get("s") or {}).values():
        summ_t |= set(so.tokenize(txt))
    ctx_t: set = set()
    for txt in list(row.get("t") or ()) + list(row.get("te") or ()):
        ctx_t |= set(so.tokenize(txt))
    meta_t = set(so.tokenize(" ".join(x for x in (row.get("d"), row.get("c"), row.get("i"), row.get("o")) if x)))
    out = []
    if (q & name_t) or so._norm(query.strip()).replace(" ", "_") == so._norm(row["n"]):
        out.append("name")
    if q & alias_t:
        out.append("alias")
    if q & summ_t:
        out.append("summary")
    if extra & (name_t | alias_t | summ_t | ctx_t | meta_t):
        out.append("synonym")
    if q & ctx_t:
        out.append("context")
    if q & meta_t and not out:
        out.append("meta")
    return out


def _label(hit: dict) -> str:
    """表示名: 表示言語の要約の 1 行目。無ければ op 名。"""
    s = (hit.get("summary") or "").strip().splitlines()
    return s[0].strip() if s else hit["name"]


# --------------------------------------------------------------------------- #
# 本体                                                                         #
# --------------------------------------------------------------------------- #
def search_grouped(query: str, current_value: Any = None, current_sort: Optional[str] = None,
                   k: int = 20, lang: Optional[str] = None) -> dict:
    """「やりたいこと」で探し、今の入力に合うかで 3 群に分けて返す。

    Parameters
    ----------
    query : 検索語(:data:`fullseye.opsearch.LANGS` のどの言語でも)。
    current_value : 今の入力の値。型は :func:`current_sort_of` が推す。
    current_sort : 型を呼び出し側が分かっているときはこれが優先(推定を上書き)。
    k : 検索で取る件数の上限。``accepted_sorts`` の実測も**高々 k 回**。
    lang : 表示言語(既定は問い合わせから推す)。

    Returns
    -------
    ``{"query", "lang", "current_sort", "total", "applicable", "needs_preprocessing", "other", "help", "staples"}``。
    ``staples`` は入門の語に当たる定番の op(:func:`staples_for`)。行の形は 3 群と同じで、``group`` に
    その op が入るはずの群の名を持つ。**3 群の中身と並びは ``staples`` の有無で変わらない**。
    各行は ``{"name", "label", "in_sort", "out_sort", "score", "why", "tier", "fit", "bridge", "extra_inputs"}``。
    ``fit`` は ``declared`` / ``measured`` / ``bridge`` / ``none`` / ``unknown``(今の型が分からない)/ ``no_input``。
    該当が 0 件のときだけ ``help``(:func:`search_zero_results_help`)が入る。

    ★群の中の並びは ``search_ops`` の点数順のまま。今の型が分からなければ全部 ``other`` で、並びは
    ``search_ops`` と 1 対 1 に一致する。
    """
    from fullseye import opsearch
    if not isinstance(query, str) or not query.strip():
        raise ValueError("search_grouped: query must be a non-empty string")
    res = opsearch.search_ops(query, k, lang=lang)
    cur_raw = current_sort if current_sort is not None else current_sort_of(current_value)
    cur = canonical_sort(cur_raw)
    groups: dict = {g: [] for g in GROUPS}
    def _classify(hit: dict, rank: int) -> tuple:
        row_idx = _row_of(hit["name"])
        first, rest = _first_sort(hit["in_sort"])
        entry = {
            "name": hit["name"], "label": _label(hit), "in_sort": hit["in_sort"], "out_sort": hit["out_sort"],
            "score": hit["score"], "why": _why(query, row_idx) if row_idx else [], "tier": _tier(hit["name"]),
            "fit": "unknown", "bridge": [], "extra_inputs": rest, "_rank": rank,
        }
        if cur is None:
            group = "other"
        elif first is None:
            entry["fit"] = "no_input"
            group = "other"
        elif _fits_declared(hit["in_sort"], cur):
            entry["fit"] = "declared"
            group = "applicable"
        elif entry["tier"] == "ledger" and _measured_works(hit["name"], cur_raw):
            entry["fit"] = "measured"
            group = "applicable"
        else:
            br = _bridge(cur, canonical_sort(first), exclude=hit["name"])
            entry["bridge"] = br
            entry["fit"] = "bridge" if br else "none"
            group = "needs_preprocessing" if br else "other"
        return group, entry

    for rank, hit in enumerate(res["ops"]):
        group, entry = _classify(hit, rank)
        groups[group].append(entry)
    staples = []
    for rank, name in enumerate(staples_for(query)):
        group, entry = _classify(_staple_hit(name, res["lang"]), rank)
        entry.pop("_rank", None)
        entry["group"] = group
        staples.append(entry)
    for g in GROUPS:
        groups[g].sort(key=lambda e: (-e["score"], e["_rank"]))
        for e in groups[g]:
            e.pop("_rank", None)
    out = {"query": query, "lang": res["lang"], "current_sort": cur_raw, "total": res["total"], **groups,
           "help": None, "staples": staples}
    if not res["ops"]:
        out["help"] = search_zero_results_help(query, res["lang"])
    return out


def _staple_query_forms(query: str):
    """:func:`staples_for` と :func:`samples_for` が語を当てる形 ``(q, padded, padded_rest, q_ja)``。

    当てない問い合わせ(空、``_`` を含む = op 名を打っている途中、語のどれかが op 名そのもの)は None。"""
    if not isinstance(query, str) or not query.strip():
        return None
    import re
    import unicodedata
    q = unicodedata.normalize("NFKC", query).lower()
    if "_" in q:                                       # op 名を打っている途中(circle_fit、area_open …)
        return None
    words = re.findall(r"[a-z0-9]+", q)
    if any(_row_of(w) is not None for w in words) or _row_of(q.strip()) is not None:
        return None                                    # 名前で探している(canny edge、median blur、threshold)
    padded = " " + " ".join(words) + " "
    for phrase in STAPLE_EXCLUDE_EN:                   # 「edge preserving」の edge でエッジ検出を出さない
        if (" " + phrase + " ") in padded:
            padded_rest = padded.replace(" " + phrase + " ", "  ")
            break
    else:
        padded_rest = padded
    q_ja = q
    for phrase in STAPLE_EXCLUDE_JA:
        q_ja = q_ja.replace(phrase, " ")
    return q, padded, padded_rest, q_ja


def _staple_term_hit(term: str, forms) -> bool:
    """表の語 *term* が問い合わせ(:func:`_staple_query_forms` の形)に当たるか。英語は単語(句)、日本語は部分文字列。"""
    import re
    import unicodedata
    q, padded, padded_rest, q_ja = forms
    t = unicodedata.normalize("NFKC", term).lower()
    if re.fullmatch(r"[a-z0-9 ]+", t):
        t = " ".join(t.split())
        return (" " + t + " ") in (padded if t in STAPLE_EXCLUDE_EN else padded_rest)   # 単語(句)として
    return t in (q if t in STAPLE_EXCLUDE_JA else q_ja)                               # 日本語は部分文字列


def staples_for(query: str) -> list:
    """問い合わせに当たる定番の op 名(:data:`STAPLES` の表の順、重複なし、索引に在るものだけ、最大 :data:`STAPLES_MAX`)。

    当たる語が無ければ空のリスト。文字は NFKC で寄せて小文字にしてから、表の語を**部分文字列**として探す
    (「画像を二値化したい」でも「二値化」に当たる)。
    """
    forms = _staple_query_forms(query)
    if forms is None:
        return []
    out: list = []
    for terms, ops in STAPLES:
        if any(_staple_term_hit(t, forms) for t in terms):
            for name in ops:
                if name not in out and _row_of(name) is not None:
                    out.append(name)
    return out[:STAPLES_MAX]


def samples_for(query: str) -> list:
    """問い合わせに当たる同梱の FA の見本の名前(:data:`SAMPLE_TERMS` の表の順、重複なし、``recipes`` に在るものだけ)。

    当て方は :func:`staples_for` と同じ。当たる語が無ければ空のリスト。"""
    forms = _staple_query_forms(query)
    if forms is None:
        return []
    try:
        import recipes
        have = set(recipes.names())
    except Exception:                                  # noqa: BLE001 -- 見本が読めない環境では出さない
        return []
    out: list = []
    for terms, names in SAMPLE_TERMS:
        if any(_staple_term_hit(t, forms) for t in terms):
            out.extend(n for n in names if n in have and n not in out)
    return out


def _staple_hit(name: str, lang: Optional[str]) -> dict:
    """定番の op を ``search_ops`` の 1 行と同じ形にする。

    ★索引の行から直接組む(``search_ops`` を op ごとに呼ぶと、新しい定番が出た最初の検索が UI スレッドで
    約 1 秒かかった —— 2026-11-12 のレビュー)。型の名前の正規化と要約の切り方は ``search_ops`` と同じ。
    """
    from fullseye import opsearch
    row = _row_of(name) or {}
    summ = row.get("s") or {}
    summary = (summ.get(lang or "en") or summ.get("en") or summ.get("ja") or "").replace("\n", " ")
    if len(summary) > 160:
        summary = summary[:157] + "..."
    norm = getattr(opsearch, "normalize_sort", lambda x: x)
    return {"name": name, "in_sort": norm(row.get("i")), "out_sort": norm(row.get("o")), "score": 0.0,
            "summary": summary}


def _op_names() -> list:
    if "names" not in _NAME_CACHE:
        _NAME_CACHE["names"] = sorted(r["n"] for r in _index()["rows"])
    return _NAME_CACHE["names"]


def nearest_op_names(name: str, n: int = 5) -> list:
    """綴りの近い op 名(``difflib`` の類似度順)。無ければ空。壊れた/未知の op 名の案内に使う。"""
    if not isinstance(name, str) or not name.strip():
        return []
    return difflib.get_close_matches(name.strip().lower(), _op_names(), n=n, cutoff=0.5)


def search_zero_results_help(query: str, lang: Optional[str] = None) -> dict:
    """検索が 0 件のときの**立て直しの手掛かり**(空の一覧で終わらせない)。

    返り: ``{"query", "unknown_terms", "nearest_terms", "nearest_ops", "categories", "sorts", "hint"}``。

    * ``nearest_terms`` — 索引に無い語ごとに、綴りの近い索引の語と、言い換え表(``SYNONYMS``)の同じ組の語
    * ``nearest_ops``   — 問い合わせ全体に綴りの近い op 名
    * ``categories``    — 近い op のカテゴリ(無ければ索引で多いカテゴリ)
    * ``sorts``         — 近い op の入出力の型(無ければ索引で多い型)
    * ``hint``          — 利用者向けの 1 文(``lang`` が ``en`` 以外なら日本語)
    """
    from fullseye import opsearch as so
    ix = _index()
    toks = list(dict.fromkeys(so.tokenize(query))) if isinstance(query, str) else []
    idf = ix["idf"]
    unknown = [t for t in toks if t not in idf]
    vocab = sorted(idf)
    nearest_terms: dict = {}
    for t in unknown:
        near = difflib.get_close_matches(t, vocab, n=5, cutoff=0.6)
        if near:
            nearest_terms[t] = near
    fq = so._fold(query) if isinstance(query, str) else ""
    syn = []
    for group in so.SYNONYMS:
        if any(so._fold(w) in fq for w in group):
            syn.extend(w for w in group if so._fold(w) not in fq)
    if syn:
        nearest_terms["<synonym>"] = list(dict.fromkeys(syn))
    q_name = (query or "").strip().lower().replace(" ", "_")
    ops = difflib.get_close_matches(q_name, _op_names(), n=5, cutoff=0.5) if q_name else []
    rows = [r for r in (_row_of(n) for n in ops) if r]
    cats = Counter(r.get("c") for r in rows if r.get("c"))
    sorts = Counter(s for r in rows for s in (r.get("i"), r.get("o")) if s)
    if not cats:
        cats = Counter(r.get("c") for r in ix["rows"] if r.get("c"))
    if not sorts:
        sorts = Counter(s for r in ix["rows"] for s in (r.get("i"), r.get("o")) if s and "×" not in s)
    use_en = lang in (None, "en", "de")
    hint = ("No operator matched. Try another wording, an English term, or part of an operator name; "
            "the categories and types below show what exists."
            if use_en else
            "該当する op がありません。別の言い方・英語・op 名の一部を試すか、下のカテゴリと型から探してください。")
    return {"query": query, "unknown_terms": unknown, "nearest_terms": nearest_terms, "nearest_ops": ops,
            "categories": [c for c, _ in cats.most_common(8)], "sorts": [s for s, _ in sorts.most_common(8)],
            "hint": hint}
