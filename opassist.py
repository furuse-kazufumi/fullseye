# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opassist — op ごとの入力補助(引数仕様・プリセット・入力の作り方・前提チェック)。

動機(2026-09-04、ユーザー「Studio の周りとか、入力補助機能とかもっと op 別にあったら
いいと思うよ」): `param_specs` は 2-D 側の **a, b という 0..1 ノブ 2 本**の見せ方を
説明する層で、台帳 op(3-D / optics / tomography …)には効かない。台帳 op は
`pitch_um` や `metal` や `n_sub` のような**実引数**を取るので、UI が助けられることが
まったく別にある:

  1. **引数仕様**   `param_spec(op)` — 名前 / 型 / 既定値 / 範囲 / 選択肢 / 単位 / 説明。
     署名と docstring から自動で取り、手書きの表で上書きする(推測を混ぜない)。
  2. **プリセット** `presets(op)` — 「CD / DVD / BD」「金 / 銀 / アルミ」「ヘアライン /
     旋盤目 / 梨地」のような**名前で選べる実在の設定**。数値を知らなくても試せる。
  3. **入力の作り方** `producers(sort)` — 「この op は normalmap が要る」→ それを
     **産む op の一覧**。型で繋ぐライブラリなので、これが一番効く導線になる。
  4. **試せる入力**  `sample_input(op)` — その op を今すぐ動かせる引数を 1 組作る。
  5. **前提チェック** `preflight(op, kwargs)` — 実行前に「これは動くが**意味のある絵に
     ならない**」を警告する。例: 回折は溝に直交して照らさないと色が出ない、
     全反射は密→疎でしか起きない。例外にはしない(実行は妨げない)。

設計方針: **台帳 op を増やさない**(これは UI 支援の層であって画像処理 op ではない)。
既存レジストリの上に乗るだけなので、台帳・ドキュメント生成には影響しない。
"""
from __future__ import annotations

import importlib
import inspect
import re
from typing import Any

#: 台帳(registry モジュール名, テーブル属性)。`tools/opdocs.LEDGER_DIMS` と同じ並び。
_LEDGERS = (
    ("ops3d", "OPS3D"), ("opsmath", "OPSMATH"), ("opsoptics", "OPSOPTICS"),
    ("opslightfield", "OPSLIGHTFIELD"), ("opsphoton", "OPSPHOTON"),
    ("opsspecular", "OPSSPECULAR"), ("opsmotionmag", "OPSMOTIONMAG"),
    ("opsquat", "OPSQUAT"), ("opsrangedoppler", "OPSRANGEDOPPLER"),
    ("opsacoustics", "OPSACOUSTICS"), ("opsinterferometry", "OPSINTERFEROMETRY"),
    ("opstomography", "OPSTOMOGRAPHY"), ("opsvolcolor", "OPSVOLCOLOR"),
    ("opsreprconv", "OPSREPRCONV"), ("opscadmap", "OPSCADMAP"),
    ("opsannotate", "OPSANNOTATE"), ("opsgfx2d", "OPSGFX2D"),
    ("opsimgmetrics", "OPSIMGMETRICS"), ("opscolortransport", "OPSCOLORTRANSPORT"),
    ("opsimgforensics", "OPSIMGFORENSICS"), ("opsastrostack", "OPSASTROSTACK"),
    ("opsvideostream", "OPSVIDEOSTREAM"),
)

#: 引数名 → 単位(表示のみ)。名前から機械的に付けられるものだけ。推測はしない。
_UNIT_BY_SUFFIX = (
    ("_um", "µm"), ("_nm", "nm"), ("_mm", "mm"), ("_cm", "cm"), ("_deg", "°"),
    ("_px", "px"), ("_per_mm", "1/mm"), ("_hz", "Hz"), ("_ms", "ms"), ("_s", "s"),
)

#: **手書きの選択肢**。署名からは分からない列挙(モジュールの定数から引く)。
#: 値は (モジュール, 属性) で、実体は import 時ではなく参照時に解決する
#: (循環 import を避け、任意依存が無い環境でも opassist 自体は読める)。
_CHOICE_SOURCES = {
    ("metal_optical_constants", "metal"): ("glassmirror", "METALS"),
    ("metal_mirror_rgb", "metal"): ("glassmirror", "METALS"),
    ("finish_shade", "metal"): ("glassmirror", "METALS"),
    ("finish_shade", "kind"): ("metalfinish", "FINISHES"),
    ("tangent_field", "kind"): ("metalfinish", "FINISHES"),
    ("roughness_field", "kind"): ("metalfinish", "FINISHES"),
    ("micro_normals", "kind"): ("metalfinish", "FINISHES"),
    ("prism_min_deviation_deg", "glass"): ("raytrace", "GLASS_NAMES"),
}

#: **手書きの列挙**(モジュール定数が無いもの)。docstring に列挙されている値を写した。
_CHOICE_LITERAL = {
    ("fresnel_dielectric", "polarization"): ("unpolarized", "s", "p"),
    ("fresnel_conductor", "polarization"): ("unpolarized", "s", "p"),
}

#: **プリセット** = 実在の設定に名前を付けたもの。数値を知らなくても試せるための導線。
#: 出典は各 op の docstring(CD/DVD/BD のピッチ、実硝材、材質の n,k)。
PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "grating_rgb": {
        "CD (1.6 µm)": {"pitch_um": 1.6},
        "DVD (0.74 µm)": {"pitch_um": 0.74},
        "Blu-ray (0.32 µm)": {"pitch_um": 0.32},
        "回折格子 600 本/mm": {"pitch_um": 1.0 / 0.6},
    },
    "grating_wavelengths": {
        "CD (1.6 µm)": {"pitch_um": 1.6},
        "DVD (0.74 µm)": {"pitch_um": 0.74},
        "Blu-ray (0.32 µm)": {"pitch_um": 0.32},
    },
    "thin_film_reflectance": {
        "シャボン膜 (水 380 nm)": {"thickness_nm": 380.0, "n_film": 1.33, "n_sub": 1.0},
        "陽極酸化被膜 (150 nm)": {"thickness_nm": 150.0, "n_film": 1.63, "n_sub": 1.5},
        "反射防止 (λ/4 MgF2)": {"thickness_nm": 550.0 / (4 * 1.38), "n_film": 1.38, "n_sub": 1.52},
        "焼き色 (チタン 90 nm)": {"thickness_nm": 90.0, "n_film": 2.4, "n_sub": 2.6},
    },
    "thin_film_rgb": {
        "シャボン膜 (380 nm)": {"thickness_nm": 380.0, "n_film": 1.33, "n_sub": 1.0},
        "陽極酸化 (150 nm)": {"thickness_nm": 150.0, "n_film": 1.63, "n_sub": 1.5},
    },
    "fresnel_dielectric": {
        "空気 → 水": {"n1": 1.0, "n2": 1.333},
        "空気 → BK7": {"n1": 1.0, "n2": 1.5168},
        "空気 → サファイア": {"n1": 1.0, "n2": 1.77},
        "ガラス → 空気 (全反射あり)": {"n1": 1.5168, "n2": 1.0},
    },
    "slab_transmittance": {
        "窓ガラス 3 mm": {"n2": 1.5168, "thickness_mm": 3.0, "sigma_per_mm": 0.0002},
        "厚板 19 mm (緑かぶり)": {"n2": 1.5168, "thickness_mm": 19.0, "sigma_per_mm": 0.002},
        "色ガラス 5 mm": {"n2": 1.52, "thickness_mm": 5.0, "sigma_per_mm": 0.05},
    },
    "prism_min_deviation_deg": {
        "N-BK7 60°": {"apex_deg": 60.0, "glass": "N-BK7"},
        "N-SF2 60° (分散大)": {"apex_deg": 60.0, "glass": "N-SF2"},
        "溶融石英 30°": {"apex_deg": 30.0, "glass": "SILICA"},
    },
    "ward_anisotropic": {
        "ヘアライン (強い異方性)": {"alpha_x": 0.32, "alpha_y": 0.022},
        "サテン (中)": {"alpha_x": 0.20, "alpha_y": 0.08},
        "等方 (梨地)": {"alpha_x": 0.16, "alpha_y": 0.16},
    },
    "oren_nayar": {
        "つるつる (Lambert 一致)": {"roughness_deg": 0.0},
        "紙": {"roughness_deg": 22.0},
        "石膏": {"roughness_deg": 30.0},
        "コンクリート": {"roughness_deg": 35.0},
    },
    "clearcoat_shade": {
        "光沢プラスチック": {"coat": 0.5, "coat_roughness": 0.10},
        "陶器の釉薬": {"coat": 0.9, "coat_roughness": 0.03},
        "車のクリア塗装": {"coat": 1.0, "coat_roughness": 0.02},
        "つや消し": {"coat": 0.05, "coat_roughness": 0.30},
    },
    "weave_normals": {
        "平織り": {"warp_px": 8.0, "weft_px": 8.0, "depth": 0.25},
        "カーボン綾織り": {"warp_px": 6.0, "weft_px": 12.0, "depth": 0.35},
        "粗い麻": {"warp_px": 14.0, "weft_px": 14.0, "depth": 0.45},
    },
    "corrosion_mask": {
        "点錆": {"coverage": 0.08, "scale_px": 10.0},
        "全面の錆": {"coverage": 0.55, "scale_px": 28.0},
        "緑青 (斑)": {"coverage": 0.30, "scale_px": 40.0},
    },
    "triangulate_column": {
        "構造化光ヘッド (基線 120 mm)": {"trans": (-120.0, 0.0, 0.0)},
    },
}

#: **前提チェック**。「動くが意味のある絵にならない」を警告する(例外にしない)。
#: 各項目 = (op 名, 判定関数, 警告文)。判定は解決済みの kwargs を受ける。
def _grating_light_across(kw):
    import numpy as np
    t = np.asarray(kw.get("tangent", (1.0, 0.0, 0.0)), float).ravel()[:3]
    l = np.asarray(kw.get("light", (0.0, 0.0, 1.0)), float).ravel()[:3]
    v = np.asarray(kw.get("view", (0.0, 0.0, 1.0)), float).ravel()[:3]
    d = l - v
    n = float(np.linalg.norm(d))
    if n < 1e-9:
        return True                                  # 光源と視線が同じ = 分散ゼロ
    across = float(np.linalg.norm(np.cross(t, d / n)))
    return across < 0.25                             # 溝とほぼ平行に振っている


_PREFLIGHT = (
    ("grating_rgb", _grating_light_across,
     "光源が溝とほぼ同じ向きです。回折の分散は**溝に直交する向き**にしか起きないので、"
     "この配置では λ = d·Δsin が可視域に届かず色が出ません(tangent に直交する向きへ "
     "light をずらしてください)。"),
    ("critical_angle_deg", lambda kw: float(kw.get("n1", 1.5)) <= float(kw.get("n2", 1.0)),
     "全反射は密→疎(n1 > n2)でしか起きません。この組では臨界角が存在せず ValueError になります。"),
    ("thin_film_reflectance", lambda kw: float(kw.get("thickness_nm", 350.0)) > 3000.0,
     "膜厚が可視光の波長より桁で大きいので、干渉の縞が積分の刻みより細かくなり、"
     "色ではなく平均値に潰れます(膜として意味を持つのは概ね 50–1000 nm)。"),
    ("slab_transmittance", lambda kw: float(kw.get("sigma_per_mm", 0.0)) * float(
        kw.get("thickness_mm", 3.0)) > 8.0,
     "σ·厚さ が 8 を超えています。透過率が 1e-4 未満になり、実質的に不透明です。"),
    ("oren_nayar", lambda kw: float(kw.get("roughness_deg", 20.0)) == 0.0,
     "roughness_deg=0 は Lambert と厳密に同じです(粗さの効果を見たいなら 15–35° 付近)。"),
    ("corrosion_mask", lambda kw: float(kw.get("coverage", 0.3)) <= 0.0,
     "coverage=0 は全面ゼロのマスクを返します(錆を出すなら 0.05 以上)。"),
)


#: tuple / list 引数の**構造**を推定するための名前ヒント。
#: 既定値の形(長さ・入れ子・要素型)だけでは「(0,0) が画素座標なのか範囲なのか」が
#: 決まらないので、名前で意味を足す。ここに無い名前は形だけで分類する(推測しない)。
_SEQ_ROLE_BY_NAME = {
    "light": ("vector3", ("x", "y", "z")), "view": ("vector3", ("x", "y", "z")),
    "tangent": ("vector3", ("x", "y", "z")), "normal": ("vector3", ("x", "y", "z")),
    "direction": ("vector3", ("x", "y", "z")), "axis": ("vector3", ("x", "y", "z")),
    "trans": ("vector3", ("x", "y", "z")), "translation": ("vector3", ("x", "y", "z")),
    "center": ("point", None), "origin": ("point", None),
    "albedo": ("rgb", ("R", "G", "B")), "color": ("rgb", ("R", "G", "B")),
    "rgb": ("rgb", ("R", "G", "B")), "background": ("rgb", ("R", "G", "B")),
    "size": ("shape", ("H", "W")), "shape": ("shape", ("H", "W")),
    "resolution": ("shape", ("H", "W")),
    "bounds": ("bounds", None), "extent": ("bounds", None), "range": ("range", ("min", "max")),
    "orders": ("list_int", None), "angles_deg": ("list_number", None),
    "wavelength_nm": ("list_number", None), "sigmas": ("list_number", None),
    # 行列(3x3)。tuple ではないが「数値 1 個ではない」点は同じで、UI は格子で見せる。
    "k_cam": ("matrix3", None), "k_proj": ("matrix3", None), "intrinsics": ("matrix3", None),
    "K": ("matrix3", None), "rot": ("matrix3", None), "R": ("matrix3", None),
    "pose": ("matrix4", None), "matrix": ("matrix", None),
    "t": ("vector3", ("x", "y", "z")),
}

#: 役割 → 既定の要素数(既定値が tuple で与えられていない引数のために使う)。
#: None = 可変長。行列は (行, 列)。
_ROLE_LENGTH = {
    "vector3": 3, "rgb": 3, "shape": 2, "range": 2, "point": None,
    "bounds": None, "list_int": None, "list_number": None,
    "matrix3": (3, 3), "matrix4": (4, 4), "matrix": None,
}


#: 容器の形の**統一スキーマ**。すべての引数がこの 1 つの形で容器を説明する。
#:
#:   form   "scalar" | "vector" | "matrix" | "list" | "nested"
#:   shape  常に tuple。スカラ = ()、3 ベクトル = (3,)、3x3 = (3, 3)、
#:          可変長 = (None,)、入れ子の可変長 = (None, 2)
#:   elem   要素の値型("number" / "int" / "bool" / "text")
#:   role   意味("vector3" / "rgb" / "point" / "shape" / "bounds" / "matrix3" …)
#:   labels 要素名(["x","y","z"] など)or None
#:
#: ★ 設計(2026-09-04、ユーザー「色々なコンテナ型は扱えるほうが良いけど、統一感も
#: 大事です」): 最初は `kind` に "seq" や "matrix" を混ぜていた ―― つまり**値の型**
#: (数値か整数か選択肢か)と**容器の形**(1 個かベクトルか行列か)が 1 つの欄で
#: 競合していた。UI から見ると「int の 3 ベクトル」が表現できず、行列だけ構造が
#: `seq` キーの下にあるなど、扱いがばらける。ここを直交させ、`kind` は値型だけ、
#: 容器は常に `container` に入れる形へ統一した。スカラも例外にしない
#: (`{"form": "scalar", "shape": ()}`)ので、UI は分岐を 1 本に書ける。
SCALAR_CONTAINER = {"form": "scalar", "shape": (), "elem": None, "role": "scalar",
                    "labels": None, "inner": None}


def _container_from_structure(st: dict) -> dict:
    """内部表現(`_seq_structure` の返り)→ 統一スキーマの容器記述。"""
    role = st.get("role") or "fixed"
    n = st.get("length")
    if str(role).startswith("matrix"):
        shape = tuple(n) if isinstance(n, (tuple, list)) else (None, None)
        form = "matrix"
    elif st.get("inner") is not None or role == "bounds":
        inner_n = (st.get("inner") or {}).get("length")
        shape = (n if isinstance(n, int) else None, inner_n if isinstance(inner_n, int) else None)
        form = "nested"
    elif n is None:
        shape, form = (None,), "list"
    else:
        shape, form = (int(n),), "vector"
    return {"form": form, "shape": shape, "elem": st.get("elem"), "role": role,
            "labels": st.get("labels"), "inner": st.get("inner")}


def _seq_structure(param: str, default) -> dict:
    """tuple / list の既定値 → UI がフォームを組める構造情報。

    返すキー: ``length``(None = 可変)/ ``elem``("int" | "number" | "seq" | "text")/
    ``role``("vector3" / "rgb" / "point" / "shape" / "bounds" / "range" /
    "list_int" / "list_number" / "nested" / "fixed")/ ``labels``(要素名 or None)/
    ``inner``(入れ子のときの 1 要素ぶんの構造)。

    ★ 形だけでは決まらないものがある: ``(0, 0)`` は画素座標にも範囲にもなりうるし、
    ``(0.0, 0.0, 1.0)`` は方向ベクトルにも RGB にもなる。だから名前ヒント
    (`_SEQ_ROLE_BY_NAME`)を先に見て、無ければ**形だけで**分類する ―― 推測で
    役割を付けると、UI が「x/y/z」と書いた欄に RGB を入れさせることになる。
    """
    seq = list(default)
    n = len(seq)
    inner = None
    if seq and all(isinstance(v, (tuple, list)) for v in seq):
        elem = "seq"
        inner = _seq_structure(param, seq[0])
        role = "bounds" if all(len(v) == 2 for v in seq) else "nested"
    elif all(isinstance(v, bool) for v in seq) and seq:
        elem, role = "bool", "fixed"
    elif all(isinstance(v, int) and not isinstance(v, bool) for v in seq) and seq:
        elem, role = "int", "fixed"
    elif all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in seq) and seq:
        elem, role = "number", "fixed"
    elif all(isinstance(v, str) for v in seq) and seq:
        elem, role = "text", "fixed"
    else:
        elem, role = "mixed", "fixed"

    labels = None
    hint = _SEQ_ROLE_BY_NAME.get(param)
    if hint is not None and inner is None:
        role, labels = hint
        # 名前ヒントと実際の長さが食い違うときは**形を優先**する(名前は当てにならない)
        if role in ("vector3", "rgb") and n != 3:
            role, labels = ("list_number" if elem == "number" else "list_int"), None
        elif role in ("shape", "range") and n != 2:
            role, labels = ("list_number" if elem == "number" else "list_int"), None
    if labels is None and role == "point":
        labels = ("row", "col") if n == 2 else tuple("xyz"[:n]) if n == 3 else None
    variable = role in ("list_int", "list_number", "nested") or (
        hint is None and elem in ("int", "number") and n > 4)
    return {"length": None if variable else n, "elem": elem, "role": role,
            "labels": list(labels) if labels else None, "inner": inner}


def _ledger_entry(op_name: str):
    """op 名 → (台帳モジュール名, エントリ dict)。見つからなければ (None, None)。"""
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                            # noqa: BLE001 — 任意依存の台帳
            continue
        entries = getattr(mod, table, None)
        if isinstance(entries, dict) and op_name in entries:
            return mod_name, entries[op_name]
    return None, None


def known_ops() -> list[str]:
    """入力補助を出せる op(= どれかの台帳に載っている op)の一覧。"""
    names: set[str] = set()
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                            # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if isinstance(entries, dict):
            names.update(entries)
    return sorted(names)


#: 引数名そのものが単位を表す場合(接尾辞では拾えない)。`cie_xyz_from_wavelength(nm)`
#: のように名前が単位そのものの op があり、拾えないと種が汎用 0..1 になって動かない。
_UNIT_BY_NAME = {"nm": "nm", "wavelength": "nm", "um": "µm", "mm": "mm",
                 "deg": "°", "angle": "°", "px": "px"}


def _unit_for(param: str):
    exact = _UNIT_BY_NAME.get(param)
    if exact:
        return exact
    # ★ 最長一致。短い順に見ると `sigma_per_mm` が `_mm` に当たって "mm" になる
    #    (実際は 1/mm)。単位を間違えると UI の数字が黙って別物になる。
    for suffix, unit in sorted(_UNIT_BY_SUFFIX, key=lambda kv: -len(kv[0])):
        if param.endswith(suffix):
            return unit
    return None


def _doc_line(doc: str, param: str):
    """docstring から ``param:`` で始まる説明行を拾う(無ければ None)。"""
    if not doc:
        return None
    pat = re.compile(r"^\s*%s\s*[:：]\s*(.+)$" % re.escape(param), re.M)
    m = pat.search(doc)
    if m:
        return m.group(1).strip()
    # "a / b: ..." のようにまとめて書かれている行も拾う
    pat2 = re.compile(r"^\s*[\w_]+(?:\s*/\s*[\w_]+)*\s*[:：]\s*.+$", re.M)
    for line in pat2.findall(doc):
        head = line.split(":", 1)[0].split("：", 1)[0]
        if param in [t.strip() for t in head.split("/")]:
            return line.split(":", 1)[-1].strip()
    return None


def _choices_for(op_name: str, param: str):
    lit = _CHOICE_LITERAL.get((op_name, param))
    if lit is not None:
        return list(lit)
    src = _CHOICE_SOURCES.get((op_name, param))
    if src is None:
        return None
    try:
        mod = importlib.import_module(src[0])
        vals = getattr(mod, src[1], None)
    except Exception:                                # noqa: BLE001
        return None
    if vals is None:
        return None
    try:
        return [str(v) for v in vals]
    except TypeError:
        return None


def param_spec(op_name: str) -> list[dict]:
    """台帳 op の**実引数**の仕様を返す(UI がフォームを組める形)。

    返り値: 引数ごとの dict のリスト。キーは
    ``name`` / ``kind``("data" = 入力データ、"number" / "int" / "bool" / "choice" /
    "text" / "seq")/ ``default`` / ``required`` / ``unit`` / ``choices`` / ``doc``。

    第 1 引数から順に、台帳の宣言 in 型の本数だけを **データ入力**(``kind="data"``、
    ``sort`` に型名)として扱い、残りをパラメータとする ―― 台帳が「何本のデータを
    取るか」を持っているので、そこは推測せずに宣言に従う。

    未知の op には ``ValueError``(黙って空を返すと「引数が無い op」と区別できない)。
    """
    mod_name, entry = _ledger_entry(op_name)
    if entry is None:
        raise ValueError(f"opassist: unknown op {op_name!r} (not in any ledger)")
    fn = entry.get("func")
    ins = list(entry.get("in") or [])
    doc = inspect.getdoc(fn) or entry.get("doc") or ""
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        params = []
    out = []
    for i, p in enumerate(params):
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        spec = {"name": p.name, "doc": _doc_line(doc, p.name), "unit": _unit_for(p.name)}
        if i < len(ins):
            spec.update(kind="data", sort=ins[i], required=True, default=None,
                        container=dict(SCALAR_CONTAINER, form="data", role=ins[i]))
            out.append(spec)
            continue
        default = None if p.default is inspect.Parameter.empty else p.default
        spec["default"] = default
        spec["required"] = p.default is inspect.Parameter.empty
        choices = _choices_for(op_name, p.name)
        if choices is not None:
            spec.update(kind="choice", choices=choices)
        elif isinstance(default, bool):
            spec["kind"] = "bool"
        elif isinstance(default, int):
            spec["kind"] = "int"
        elif isinstance(default, float):
            spec["kind"] = "number"
        elif isinstance(default, str):
            spec["kind"] = "text"
        elif isinstance(default, (tuple, list)):
            st = _seq_structure(p.name, default)
            spec["kind"] = {"int": "int", "bool": "bool", "text": "text"}.get(st["elem"], "number")
            spec["container"] = _container_from_structure(st)
        else:
            # ★ ここが要点: **既定値が tuple で与えられていない**引数がある。
            # `center=None`(省略可の (row,col))、必須の `trans`(3 ベクトル)、
            # `k_cam`(3x3 行列)…… 既定値だけを見ると「数値 1 個」に見えてしまい、
            # UI が spin box を 1 個出して破綻する。名前で構造を補う。
            hint = _SEQ_ROLE_BY_NAME.get(p.name)
            if hint is not None:
                role, labels = hint
                st = {"length": _ROLE_LENGTH.get(role), "elem": "number", "role": role,
                      "labels": list(labels) if labels else None, "inner": None}
                spec["kind"] = "number"
                spec["container"] = _container_from_structure(st)
            else:
                spec["kind"] = "number" if default is None else "text"
        spec.setdefault("container", dict(SCALAR_CONTAINER))
        out.append(spec)
    return out


def presets(op_name: str) -> dict:
    """op の名前つきプリセット(``{表示名: {引数: 値}}``)。無ければ空 dict。

    数値を知らなくても「CD」「陶器の釉薬」「窓ガラス 3 mm」で試せるようにするための表。
    値の出どころは各 op の docstring(実在の規格値・実硝材・実材質)。
    """
    return {k: dict(v) for k, v in PRESETS.get(op_name, {}).items()}


def producers(sort: str) -> list[str]:
    """その型(sort)を**産む** op の一覧。「この入力はどう作る?」への答え。

    型で繋ぐライブラリなので、UI で一番効く導線がこれ ―― 「normalmap が要る」と
    言われた利用者が、次にどの op を押せばよいかが分かる。
    """
    if not isinstance(sort, str) or not sort:
        raise ValueError("opassist.producers: sort must be a non-empty string")
    found = []
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                            # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if not isinstance(entries, dict):
            continue
        for name, info in entries.items():
            if info.get("out") == sort:
                found.append(name)
    return sorted(set(found))


def consumers(sort: str) -> list[str]:
    """その型を**受け取れる** op の一覧(産んだ後にどこへ繋げるか)。"""
    if not isinstance(sort, str) or not sort:
        raise ValueError("opassist.consumers: sort must be a non-empty string")
    found = []
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                            # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if not isinstance(entries, dict):
            continue
        for name, info in entries.items():
            if sort in (info.get("in") or []):
                found.append(name)
    return sorted(set(found))


def preflight(op_name: str, kwargs=None) -> list[str]:
    """実行前の注意書き(0 件以上)。**例外にはしない** — 実行は妨げない。

    「動くが意味のある絵にならない」配置を先に伝えるための層。例: 回折を溝と同じ
    向きから照らしている / 全反射を疎→密で呼んでいる / 膜厚が桁違い。
    どれも実際に踏んだ失敗から起こしている(CHANGELOG 参照)。
    """
    kw = dict(kwargs or {})
    # 既定値で埋めてから判定する(利用者が省いた引数も既定の意味で効くため)
    try:
        for spec in param_spec(op_name):
            if spec["kind"] != "data" and spec["name"] not in kw and spec.get("default") is not None:
                kw.setdefault(spec["name"], spec["default"])
    except ValueError:
        return []
    notes = []
    for name, test, message in _PREFLIGHT:
        if name != op_name:
            continue
        try:
            if test(kw):
                notes.append(message)
        except Exception:                            # noqa: BLE001 — 補助が本体を壊さない
            continue
    return notes


def _sample_value(spec: dict):
    """必須パラメータの「とりあえず動く値」を**容器の形から**作る。

    ★ ここを値型だけで決めると壊れる: `corrosion_mask(shape, ...)` の `shape` は
    (H, W) の組なのに、kind だけ見て 1.0 を入れると op の中で
    「'float' object is not iterable」になる(実際に踏んだ)。容器の role と shape を
    見て、ベクトル・行列・画像サイズ・範囲をそれぞれ妥当な形で埋める。
    """
    import numpy as np
    c = spec.get("container") or {}
    role, shape = c.get("role"), c.get("shape") or ()
    if spec["kind"] == "choice":
        return (spec.get("choices") or ["default"])[0]
    if role == "shape":
        return (64, 64)
    if role == "bounds":
        return ((0.0, 10.0),) * 3
    if role == "range":
        return (0.0, 1.0)
    if role == "point":
        return (32.0, 32.0)
    if role == "rgb":
        return (0.6, 0.4, 0.3)
    if role == "vector3":
        return (0.0, 0.0, 1.0)
    if str(role).startswith("matrix"):
        n = shape[0] if shape and isinstance(shape[0], int) else 3
        return np.eye(int(n))
    if c.get("form") in ("vector", "list") and shape and isinstance(shape[0], int):
        return tuple([1.0] * shape[0]) if spec["kind"] == "number" else tuple([1] * shape[0])
    if spec["kind"] == "bool":
        return False
    if spec["kind"] == "text":
        return ""
    return 1.0 if spec["kind"] == "number" else 1


def sample_input(op_name: str):
    """その op を**今すぐ動かせる**引数を 1 組作って返す ``(args, kwargs)``。

    データ引数は宣言 sort に応じた最小の種を作る。作れない sort は ``None`` を入れて
    返す(黙って別の型を渡すより、埋められなかったことが見える方がよい)。
    """
    import numpy as np

    specs = param_spec(op_name)
    seeds = {
        "image2d": lambda: np.linspace(0.0, 1.0, 64 * 64).reshape(64, 64),
        "depth": lambda: 500.0 + 30.0 * np.random.default_rng(0).random((64, 64)),
        "signal": lambda: np.linspace(0.0, 1.0, 64),
        "normalmap": _sample_normalmap,
        "rgbimage": lambda: np.tile(np.array([0.6, 0.4, 0.3]), (32, 32, 1)),
        "points": lambda: np.random.default_rng(0).normal(size=(64, 3)),
        "pointmap": lambda: np.random.default_rng(0).normal(size=(16, 16, 3)),
        "voxel": lambda: np.random.default_rng(0).random((16, 16, 16)),
        "sdf": lambda: np.random.default_rng(0).normal(size=(16, 16, 16)),
        "coordgrid": lambda: __import__("sdf_ops").grid_coords(((0.0, 10.0),) * 3, 16)[0],
        "images": lambda: [np.random.default_rng(k).random((32, 32)) for k in range(4)],
    }
    #: 単位に合う種(汎用の 0..1 では意味を持たない量がある)。
    #: ★ 実測で判明: `prism_min_deviation_deg` の波長入力に 0..1 の汎用 signal を渡すと
    #: 「波長は正の値」で弾かれ、**サンプルが動かない op** になっていた。単位が分かる
    #: なら、その量として妥当な範囲を種にする方が「押せば動く」に近い。
    unit_seeds = {
        "nm": lambda: np.linspace(400.0, 700.0, 64),      # 可視域
        "µm": lambda: np.linspace(0.4, 0.7, 64),
        "mm": lambda: np.linspace(0.5, 20.0, 64),
        "°": lambda: np.linspace(0.0, 80.0, 64),
        "1/mm": lambda: np.linspace(0.0, 0.1, 64),
    }
    args, kwargs = [], {}
    for spec in specs:
        if spec["kind"] == "data":
            maker = None
            if spec.get("sort") in ("signal", "image2d") and spec.get("unit") in unit_seeds:
                maker = unit_seeds[spec["unit"]]
            if maker is None:
                maker = seeds.get(spec.get("sort"))
            args.append(maker() if maker is not None else None)
        elif spec["required"]:
            kwargs[spec["name"]] = _sample_value(spec)
    return args, kwargs


def _sample_normalmap():
    import numpy as np
    y, x = np.mgrid[-1:1:64j, -1:1:64j]
    r2 = x * x + y * y
    m = r2 < 1.0
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    return np.stack([x, y, z], -1) * m[..., None]


#: 実測プローブ用の種。`sample_input` と同じ形だが、こちらは**宣言と違う型も**入れて
#: 「実は通る型」を探すために使う。小さめに作る(1 op あたり数十 ms に収める)。
def _probe_seeds():
    import numpy as np
    y, x = np.mgrid[-1:1:24j, -1:1:24j]
    r2 = x * x + y * y
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    nmap = np.stack([x, y, z], -1) * (r2 < 1.0)[..., None]
    rng = np.random.default_rng(0)
    return {
        "signal": np.linspace(0.05, 0.95, 32),
        "image2d": np.linspace(0.05, 0.95, 24 * 24).reshape(24, 24),
        "depth": 500.0 + 30.0 * rng.random((24, 24)),
        "normalmap": nmap,
        "rgbimage": np.tile(np.array([0.6, 0.4, 0.3]), (24, 24, 1)),
        "pointmap": rng.normal(size=(12, 12, 3)),
        "points": rng.normal(size=(48, 3)),
        "voxel": rng.random((12, 12, 12)),
        "sdf": rng.normal(size=(12, 12, 12)),
        "images": [rng.random((24, 24)) for _ in range(4)],
    }


def accepted_sorts(op_name: str, extra_kwargs=None) -> dict:
    """その op が**実際に受け取れる型**を測って返す(宣言ではなく実測)。

    返り値: ``{sort: "declared" | "works" | "rejected" | "error"}``。
      * ``declared`` 台帳が宣言している型(当然通る)
      * ``works``    宣言していないが**通った**型(= op は多態。UI はこれも許してよい)
      * ``rejected`` op 自身が ValueError で断った(fail-closed が効いている = 正しい)
      * ``error``    ValueError 以外の例外(素の TypeError 等 = 番人の穴かもしれない)

    動機(2026-09-04、ユーザー「op は複数の型に対応してるといいね」): 台帳は 1 op に
    1 つの入力型しか書けないが、実体は要素ごとの演算が多く、`signal` と宣言した op が
    `image2d` も `voxel` も通ることがある。**宣言を広げる**のは台帳と champion に
    波及するので、まずは「測って見せる」層としてここに置く ―― 数えられていない
    多態性は「無い」のと同じで、UI も利用者も使えないままになる。

    ★ 測るので**副作用のある op には使わない**こと(ここで扱う台帳 op は純関数)。
    第 1 引数だけを差し替えて呼び、返りが有限かどうかまでは見ない(型の受理のみ)。
    """
    import numpy as np

    mod_name, entry = _ledger_entry(op_name)
    if entry is None:
        raise ValueError(f"opassist: unknown op {op_name!r} (not in any ledger)")
    specs = param_spec(op_name)
    data = [s for s in specs if s["kind"] == "data"]
    if not data:
        return {}
    fn = entry["func"]
    declared = list(entry.get("in") or [])
    seeds = _probe_seeds()

    # 第 2 引数以降のデータ入力と必須パラメータは宣言どおりに埋める
    base_args, base_kwargs = sample_input(op_name)
    base_kwargs.update(dict(extra_kwargs or {}))

    out = {}
    for sort, seed in seeds.items():
        if sort == declared[0] if declared else False:
            out[sort] = "declared"
            continue
        args = list(base_args)
        if not args:
            continue
        args[0] = seed
        try:
            res = fn(*args, **base_kwargs)
        except ValueError:
            out[sort] = "rejected"
            continue
        except Exception:                                # noqa: BLE001
            out[sort] = "error"
            continue
        ok = res is not None and (not isinstance(res, np.ndarray) or res.size > 0)
        out[sort] = "works" if ok else "rejected"
    if declared:
        out[declared[0]] = "declared"
    return out


# --------------------------------------------------------------------------- #
# 使いやすさ: 探す / すぐ動かす / 型を繋ぐ                                       #
# --------------------------------------------------------------------------- #
def find(query: str, limit: int = 20) -> list[dict]:
    """自由語で op を探す(名前・説明・カテゴリ・モジュールを横断)。

    「虹」「rust」「fresnel」「旋盤」のように**やりたいこと**で引ける入口。
    完全一致 > 名前の部分一致 > 説明の一致 の順に並べる。

    返り値: ``[{"op", "ledger", "module", "category", "doc", "score"}, ...]``
    """
    q = str(query).strip().lower()
    if not q:
        raise ValueError("opassist.find: query must not be empty")
    hits = []
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                                # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if not isinstance(entries, dict):
            continue
        for name, info in entries.items():
            doc = str(info.get("doc") or "")
            hay_name = name.lower()
            score = 0
            if hay_name == q:
                score = 100
            elif q in hay_name:
                score = 60 + max(0, 20 - len(hay_name))
            elif q in doc.lower():
                score = 30
            elif q in str(info.get("category", "")).lower() or q in str(info.get("module", "")).lower():
                score = 20
            if score:
                hits.append({"op": name, "ledger": mod_name, "module": info.get("module"),
                             "category": info.get("category"), "doc": doc, "score": score})
    hits.sort(key=lambda h: (-h["score"], h["op"]))
    return hits[: max(int(limit), 1)]


def run(op_name: str, *data, preset=None, strict: bool = False, **kwargs):
    """op を**1 行で**動かす(プリセット解決 → 前提チェック → 宣言型で返す)。

    ``opassist.run("grating_rgb", normals, preset="CD (1.6 µm)", light=(0, .55, .83))``

    data:   位置のデータ入力(省略すると `sample_input` の種を使う = そのまま試せる)。
    preset: `presets(op)` の表示名。中身は kwargs より**弱い**(明示指定が勝つ)。
    strict: True なら前提チェックの警告を ``ValueError`` にする。既定は False で、
            警告は返り値の ``notes`` に入れるだけで実行は妨げない。

    返り値: ``(result, notes)``。result は**台帳の宣言 out 型**(adapter 適用後)なので、
    そのまま次の op へ渡せる ―― 素の関数のタプル返しを呼び手が剥がす必要が無い。
    """
    mod_name, entry = _ledger_entry(op_name)
    if entry is None:
        raise ValueError(f"opassist: unknown op {op_name!r} (not in any ledger)")
    kw = {}
    if preset is not None:
        table = presets(op_name)
        if preset not in table:
            raise ValueError(f"opassist.run: unknown preset {preset!r} for {op_name}; "
                             f"available: {sorted(table)}")
        kw.update(table[preset])
    kw.update(kwargs)                                    # 明示指定がプリセットに勝つ

    args = list(data)
    if not args:
        args, auto_kw = sample_input(op_name)
        for k, v in auto_kw.items():
            kw.setdefault(k, v)
    notes = preflight(op_name, kw)
    if notes and strict:
        raise ValueError("opassist.run: preflight: " + " / ".join(notes))
    mod = importlib.import_module(mod_name)
    caller = getattr(mod, "call", None)
    result = caller(op_name, *args, **kw) if caller else entry["func"](*args, **kw)
    return result, notes


def path(from_sort: str, to_sort: str, max_len: int = 4) -> list[list[str]]:
    """型 A から型 B へ**繋ぐ op の列**を探す(型グラフ上の最短路)。

    ``path("coordgrid", "mesh")`` → ``[["sphere_sdf", "marching_cubes"], ...]``
    のように、「持っているもの」から「欲しいもの」までの手順が出る。型で繋ぐ
    ライブラリなので、これが UI で一番効く導線になる(手順を知らなくても辿れる)。

    max_len: 段数の上限(既定 4)。同じ長さの経路は op 名の辞書順で返す。
    """
    if not isinstance(from_sort, str) or not isinstance(to_sort, str):
        raise ValueError("opassist.path: sorts must be strings")
    if from_sort == to_sort:
        return [[]]
    edges: dict[str, list[tuple[str, str]]] = {}
    for mod_name, table in _LEDGERS:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:                                # noqa: BLE001
            continue
        entries = getattr(mod, table, None)
        if not isinstance(entries, dict):
            continue
        for name, info in entries.items():
            ins = info.get("in") or []
            out = info.get("out")
            if not out:
                continue
            for src in ins:
                edges.setdefault(src, []).append((name, out))
    # 幅優先。同じ段数の解を全部集めてから返す(最短だけを見せる)
    frontier = [(from_sort, [])]
    seen = {from_sort}
    for _ in range(max(int(max_len), 1)):
        found, nxt, reached = [], [], set()
        for sort, chain in frontier:
            for name, out in sorted(edges.get(sort, [])):
                if out == to_sort:
                    found.append(chain + [name])
                elif out not in seen and out not in reached:
                    reached.add(out)
                    nxt.append((out, chain + [name]))
        if found:
            return sorted(found)
        seen |= reached
        frontier = nxt
        if not frontier:
            break
    return []


def assist(op_name: str, measure: bool = True) -> dict:
    """UI が 1 回で取れるまとめ: 仕様・プリセット・入力の作り方・次に繋げる先・受理型。

    ``measure=True``(既定)は `accepted_sorts` を実測するので op を数回呼ぶ。
    一覧を作るときなど回数が要る場面では ``measure=False`` にする。
    """
    mod_name, entry = _ledger_entry(op_name)
    if entry is None:
        raise ValueError(f"opassist: unknown op {op_name!r} (not in any ledger)")
    specs = param_spec(op_name)
    needs = [s.get("sort") for s in specs if s["kind"] == "data"]
    return {
        "op": op_name,
        "ledger": mod_name,
        "module": entry.get("module"),
        "category": entry.get("category"),
        "doc": entry.get("doc"),
        "params": specs,
        "presets": presets(op_name),
        "inputs": {sort: producers(sort) for sort in dict.fromkeys(needs) if sort},
        "next": consumers(entry.get("out")) if entry.get("out") else [],
        "preflight": preflight(op_name),
        # 宣言は 1 型でも実体は多態なことが多い。UI が「この型も入る」を出せるよう
        # **実測**して返す(measure=False で省略できる — 一覧表示など数を捌く場面用)。
        "accepts": accepted_sorts(op_name) if measure else {},
    }


# --------------------------------------------------------------------------- #
# `fullseye.*` へ出す別名(名前が一般語すぎるものに op_ を付ける)                #
# --------------------------------------------------------------------------- #
#: `find` / `run` / `path` はトップレベルの名前として一般的すぎるので、公開名は
#: `op_find` / `op_run` / `op_path` にする(モジュール経由 `opassist.find` は不変)。
op_find = find
op_run = run
op_path = path
op_assist = assist
op_presets = presets
op_producers = producers
op_consumers = consumers
op_accepts = accepted_sorts
