# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_op_catalog — Fullseye の全 op を LLM に渡せる markdown 台帳(OP_CATALOG.md)に出力。

    py -3.11 tools/gen_op_catalog.py [--out docs/OP_CATALOG.md]

目的: op が増えたので、用途を伝えれば **どの op をどう組み合わせるか AI が提案できる**
一枚の台帳を作る。人にも読めるが、第一の読者は LLM。内容:
    1. AI 向けの使い方(用途→パイプライン提案の手順)。
    2. worked examples(用途→使う op)= 実際の組合せの手本。
    3. スタンドアロン幾何/数学モジュールの関数 API(署名+一行説明)。
    4. 3D op 一覧(カテゴリ別、in→out と説明)。
    5. 2D パイプライン op 一覧(カテゴリ別、HALCON別名 と in→out)。
    6. 参照(アルゴリズムの一次情報・further reading の URL)。

設計: 内省は全て try/except で囲み、1 つの op/モジュールの失敗が台帳全体を壊さない
(壊れた項目は "(introspection failed)" と明示し、握り潰さない)。
"""
from __future__ import annotations

import argparse
import inspect
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


def _doc1(obj) -> str:
    """オブジェクトの docstring 先頭行(無ければ空文字)。"""
    try:
        d = (inspect.getdoc(obj) or "").strip()
        return d.splitlines()[0].strip() if d else ""
    except Exception:
        return ""


def _sig(fn) -> str:
    try:
        return str(inspect.signature(fn))
    except (TypeError, ValueError):
        return "(...)"


# --------------------------------------------------------------------------- #
# セクション生成(各々エラー隔離)                                             #
# --------------------------------------------------------------------------- #
def _preamble() -> list[str]:
    return [
        "# Fullseye Operator Catalog — AI capability ledger",
        "",
        "Fullseye は説明可能な古典/幾何ビジョンの Physical-AI ツールキット。この台帳は "
        "**用途を伝えれば、どの op をどう組み合わせればよいかを AI が提案する**ための一覧です。",
        "",
        "## この台帳の使い方(assistant 向け)",
        "",
        "1. ユーザーの**用途(入力データ・欲しい出力)**を特定する。",
        "2. まず **Worked examples**(用途→op の実例)から最も近いものを探し、その op 連鎖を土台にする。",
        "3. 連鎖は **in → out のデータ種**が繋がるように組む(例: `image → region → feature`、"
        "`points → voxel → mesh`)。2D パイプライン op は 1 画像+2 スカラつまみのモデル、"
        "点群/体積の 3D op と 2 画像を取る op(morph 等)は関数として呼ぶ。",
        "4. 各 op の**前提と失敗条件**(退化入力・必要点数など)を必ず確認し、fail-closed に扱う。",
        "5. 提案には**具体的な op 名**と、可能なら該当する worked example / References を添える。",
        "6. 実装が不確かなら、対応する `examples*/` を実行して ground-truth 出力で確かめる。",
        "",
    ]


def _examples_section() -> list[str]:
    out = ["## Worked examples(用途 → 使う op の実例=推奨組合せの手本)", ""]
    for mod_name, label, run_dir in [("examples2d", "2-D 画像/信号/幾何", "examples"),
                                     ("examples3d", "3-D 点群/体積/曲面", "examples_3d")]:
        try:
            EX = __import__(mod_name)
            names = EX.names()
        except Exception as e:
            out += [f"### {label}", f"- (catalog: {mod_name} を読めませんでした: {e})", ""]
            continue
        out += [f"### {label}({len(names)} 例)", ""]
        try:
            grouped = EX.by_task()
        except Exception:
            grouped = {"(all)": names}
        for task, ids in grouped.items():
            out.append(f"**{task}**")
            for i in ids:
                try:
                    e = EX.get(i)
                    out.append(f"- **{e.get('name', i)}** — {e.get('summary', '')} "
                               f"`py -3.11 {run_dir}/{i}.py`")
                except Exception as ex:
                    out.append(f"- {i} (introspection failed: {ex})")
            out.append("")
    return out


_STANDALONE = [
    ("imagemorph", "対応点駆動の2D画像ワープ・顔モーフ"),
    ("fourierdesc", "閉輪郭の楕円フーリエ記述子・平滑化"),
    ("imagedraw", "画像へのラスタ描画(マーカー/線/円/輪郭)"),
    ("signal1d", "点列の多項式/FFT/フィルタ/スプライン(開閉・2D/3D)"),
]


def _modules_section() -> list[str]:
    out = ["## スタンドアロン幾何/数学モジュール(関数 API)", "",
           "1画像パイプラインに乗らない op(2画像・点列・可変引数)。関数として呼ぶ。", ""]
    for mod_name, hint in _STANDALONE:
        try:
            m = __import__(mod_name)
        except Exception as e:
            out += [f"### `{mod_name}` — {hint}", f"- (import 失敗: {e})", ""]
            continue
        out += [f"### `{mod_name}` — {_doc1(m) or hint}", ""]
        names = getattr(m, "__all__", None) or [n for n in dir(m) if not n.startswith("_")]
        for n in names:
            try:
                fn = getattr(m, n)
                if not callable(fn):
                    continue
                out.append(f"- `{n}{_sig(fn)}` — {_doc1(fn)}")
            except Exception as ex:
                out.append(f"- `{n}` (introspection failed: {ex})")
        out.append("")
    return out


def _ops3d_section() -> list[str]:
    out = ["## 3-D operators(ops3d)by category", ""]
    try:
        import ops3d
        cats = ops3d.categories()
        catalog = getattr(ops3d, "_CATALOG", {})
    except Exception as e:
        return out + [f"- (ops3d を読めませんでした: {e})", ""]
    total = 0
    for cat in sorted(cats):
        entries = catalog.get(cat, [])
        if not entries:
            continue
        out.append(f"### {cat}({len(entries)})")
        for entry in entries:
            try:
                name = entry[0]
                info = ops3d.info(name)
                io = f"{', '.join(info.get('in', []))} → {info.get('out', '')}"
                doc = info.get("doc", "") or ""
                out.append(f"- `{name}` (`{io}`) — {doc}")
                total += 1
            except Exception as ex:
                out.append(f"- `{entry[0] if entry else '?'}` (introspection failed: {ex})")
        out.append("")
    out.insert(1, f"_計 {total} ops / {len([c for c in cats if catalog.get(c)])} categories。_\n")
    return out


def _ops2d_section() -> list[str]:
    out = ["## 2-D pipeline operators(ops registry)by category", "",
           "1 画像を取り 1 画像/領域/輪郭/特徴を返すパイプライン op。`in → out` の"
           "データ種で連鎖を組む。HALCON 別名は用途の手掛かり。", ""]
    try:
        import ops
        reg = ops.REGISTRY
    except Exception as e:
        return out + [f"- (ops を読めませんでした: {e})", ""]
    by_cat: dict[str, list] = {}
    for o in reg:
        try:
            by_cat.setdefault(o.category, []).append(o)
        except Exception:
            continue
    out.insert(1, f"_計 {len(reg)} ops / {len(by_cat)} categories。_\n")
    for cat in sorted(by_cat):
        ops_in = by_cat[cat]
        out.append(f"### {cat}({len(ops_in)})")
        for o in ops_in:
            try:
                hal = f" (halcon: `{o.halcon}`)" if getattr(o, "halcon", None) else ""
                io = f"`{getattr(o, 'in_sort', '?')} → {getattr(o, 'out_sort', '?')}`"
                out.append(f"- `{o.name}`{hal} {io}")
            except Exception as ex:
                out.append(f"- `{getattr(o, 'name', '?')}` (introspection failed: {ex})")
        out.append("")
    return out


# 参照(実在する一次情報/Wikipedia。捏造しない — 主要な技術族のみ curated)。
_REFERENCES = [
    ("Marching cubes(voxel→mesh)", "https://en.wikipedia.org/wiki/Marching_cubes"),
    ("Elliptic Fourier descriptors", "https://en.wikipedia.org/wiki/Elliptic_Fourier_descriptor"),
    ("Thin plate spline(TPS 変形)", "https://en.wikipedia.org/wiki/Thin_plate_spline"),
    ("Image morphing(feature-based)", "https://en.wikipedia.org/wiki/Morphing"),
    ("Perspective-n-Point(PnP 姿勢)", "https://en.wikipedia.org/wiki/Perspective-n-Point"),
    ("RANSAC(ロバスト推定)", "https://en.wikipedia.org/wiki/Random_sample_consensus"),
    ("Iterative closest point(ICP/GICP)", "https://en.wikipedia.org/wiki/Iterative_closest_point"),
    ("Superquadrics", "https://en.wikipedia.org/wiki/Superquadrics"),
    ("Signed distance function(ESDF)", "https://en.wikipedia.org/wiki/Signed_distance_function"),
    ("Photometric stereo", "https://en.wikipedia.org/wiki/Photometric_stereo"),
    ("Phase unwrapping(structured light)", "https://en.wikipedia.org/wiki/Phase_unwrapping"),
    ("Medial axis / skeleton", "https://en.wikipedia.org/wiki/Medial_axis"),
    ("Geodesic(距離)", "https://en.wikipedia.org/wiki/Geodesic"),
    ("Digital elevation model(DEM)", "https://en.wikipedia.org/wiki/Digital_elevation_model"),
    ("Spline interpolation", "https://en.wikipedia.org/wiki/Spline_interpolation"),
    ("Delaunay triangulation", "https://en.wikipedia.org/wiki/Delaunay_triangulation"),
    ("Fourier transform", "https://en.wikipedia.org/wiki/Fourier_transform"),
    ("Image moment(invariants)", "https://en.wikipedia.org/wiki/Image_moment"),
]


def _references_section() -> list[str]:
    out = ["## References(アルゴリズムの一次情報・further reading)", "",
           "各 op の原理はモジュール docstring にも一次文献名を明記。以下は主要技術族の外部参照。", ""]
    out += [f"- {name} — <{url}>" for name, url in _REFERENCES]
    out.append("")
    return out


def build_catalog() -> str:
    lines: list[str] = []
    for section in (_preamble, _examples_section, _modules_section,
                    _ops3d_section, _ops2d_section, _references_section):
        try:
            lines += section()
        except Exception as e:                          # 1 セクションの失敗で全体を壊さない
            lines += [f"## (section {section.__name__} failed: {e})", ""]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(_REPO, "docs", "OP_CATALOG.md"))
    args = ap.parse_args()
    md = build_catalog()
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"wrote {args.out} ({len(md):,} bytes, {md.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
