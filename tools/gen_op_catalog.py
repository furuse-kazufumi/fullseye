# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gen_op_catalog — Fullseye の全 op を LLM に渡せる markdown 台帳(OP_CATALOG.md)に出力。

    py -3.11 tools/gen_op_catalog.py [--out docs/OP_CATALOG.md]

目的: op が増えたので、用途を伝えれば **どの op をどう組み合わせるか AI が提案できる**
一枚の台帳を作る。人にも読めるが、第一の読者は LLM。内容:
    1. AI 向けの使い方(用途→パイプライン提案の手順)。
    2. worked examples(用途→使う op)= 実際の組合せの手本。
    3. スタンドアロン幾何/数学モジュールの関数 API(署名+一行説明)。
    4. 全 op を族(``docs/ops/<族>/``)→ カテゴリの順に(in→out・要約・HALCON 別名・例)。
       母集団は op ノートと同じ ``tools/opdocs._records``(48 族)。
    5. 参照(アルゴリズムの一次情報・further reading の URL)。

設計: 補助の節(例・単体モジュール・参照)は try/except で囲み、1 つの失敗が台帳全体を
壊さない(壊れた項目は "(introspection failed)" と明示し、握り潰さない)。**op の一覧の節だけは
fail-closed** —— そこが空なら台帳の意味が無い。
"""
from __future__ import annotations

import argparse
import inspect
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)


# op -> worked-example index (HDevelop-style "この op を使うサンプル"リンク)。壊れても台帳は出す。
_EX3D, _EX2D = None, None


def _ex_index():
    global _EX3D, _EX2D
    if _EX3D is None:
        try:
            from op_example_index import build_index
            _EX3D, _EX2D = build_index(split=True)
        except Exception:
            _EX3D, _EX2D = {}, {}
    return _EX3D, _EX2D


def _ex_link(exs) -> str:
    """例 id のリストを ' · 例: `a`, `b`'(無ければ ' · 例: なし')に整形。"""
    if exs:
        return " · 例: " + ", ".join(f"`{e}`" for e in exs)
    return " · 例: なし"


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


#: 族の冒頭に置く手書きの一言(op の一覧そのものは生成)。無い族は一言なしで出す。
_FAMILY_INTRO = {
    "2d": ("1 画像を取り 1 画像/領域/輪郭/特徴を返すパイプライン op(`ops.REGISTRY`)と、複数画像を取る "
           "n-ary op(`imgops_nary`)。`in → out` のデータ種で連鎖を組む。HALCON 別名は用途の手掛かり。"),
    "3d": "点群・体積・メッシュ・深度の op(`ops3d.OPS3D`)。関数として呼ぶ。",
    "oned": ("プロファイル/信号の 1-D op。源流は 2-D の measure1d・3-D の probe・"
             "音声/センサー系列(dsp)— 取り出した (x, y) 列を funct1d/dsp で加工して測る。"),
    "math": ("視覚計測を支える数学 op(線形代数/統計/補間・多項式)+ 複素解析の"
             "計算可能な切り口(周回積分・Cauchy 積分公式・偏角の原理・Laurent 係数/"
             "留数・等角写像・Cauchy-Riemann 残差)。FFT/複素画像は complexops・"
             "volfreq、1-D 関数は funct1d を参照。"),
    "optics": ("レンズより上・画素より下の層。幾何光学(薄レンズ結像・ABCD 光線伝達・"
               "被写界深度・cos⁴ 口径食)/ 波動光学(Airy パターン・角スペクトル伝搬・"
               "Fraunhofer 回折・ガウシアンビーム)/ 結像品質(PSF→MTF・回折限界 MTF・"
               "Zernike 波面統計)/ 偏光(Jones・Stokes・Mueller)/ 材料の物性表(matprop)・"
               "光ファイバ(fiber)・センサーの特性(sensorchar)・大域光輸送ほか。"),
    "drive": ("名前は運転だが、中身は**物理シミュレーションとロボットの PoC の台帳**: 運転(コース・交通・判断・"
              "CARLA / CommonRoad)に加え、触覚(tac*)・peg-in-hole(peg*)・研磨(polish)・研削(grind)・切削(cutting)・"
              "粉体(granular / scoop)・粉末 X 線回折(pxrd)・球技(ball / puck)などがカテゴリとして同居している。"
              "カテゴリ名で引くこと。"),
}


def _family_order(recs) -> list:
    """族の並び = ``docs/ops/INDEX.md`` と同じ(2d, 3d, 台帳の登録順)。台帳に無い族は最後に名前順。"""
    sys.path.insert(0, os.path.join(_REPO, "tools"))
    import opdocs as OD
    order = ["2d", "3d", *OD.LEDGER_DIMS]
    present = {r["dim"] for r in recs}
    return [d for d in order if d in present] + sorted(present - set(order))


def _families_section() -> list[str]:
    """全 op を**族(``docs/ops/<族>/``)→ カテゴリ**の順に並べる。

    ★2026-10-15 まで、このカタログは ops / ops3d / ops1d / opsmath / opsoptics の **5 つのレジストリだけ**を
    手で 1 節ずつ書いていて、残る 43 の台帳族(drive 694・segmentation 54・annotate 51 …)の **1,351 名が
    1 度も出てこなかった**。pip だけで入れた利用者の RAG(``fullseye-rag``)はこのファイルしか持たないので、
    その op は wheel の利用者からは探しようがなかった。op ノートと**同じ母集団**(``tools/opdocs._records``)
    から書くことで、族を足しても節を書き足す必要がなくなる(門 = ``tests/test_rag_by_ops.py``)。
    """
    sys.path.insert(0, os.path.join(_REPO, "tools"))
    import opdocs as OD
    recs = OD._records()[0]
    if not recs:
        raise RuntimeError("opdocs._records() が 0 件 —— 空のカタログを書かない(fail-closed)")
    by_dim: dict[str, dict[str, list]] = {}
    for r in recs:
        by_dim.setdefault(r["dim"], {}).setdefault(r["category"] or "(none)", []).append(r)
    order = _family_order(recs)
    out = ["## Operators by family(族 → カテゴリ、全 op)", "",
           f"_計 {len(recs)} ops / {len(order)} families。並びとノートの在り処は `docs/ops/INDEX.md` と同じ"
           "(ノート = `docs/ops/<族>/<カテゴリ>/<op>.md`)。台帳族の op は `fs.ledger.<op>` で呼ぶ。_", ""]
    out.append("族の一覧: " + " · ".join(
        f"**{d}** {sum(len(v) for v in by_dim[d].values())}" for d in order))
    out.append("")
    for dim in order:
        cats = by_dim[dim]
        n = sum(len(v) for v in cats.values())
        out.append(f"### {dim}({n} ops / {len(cats)} categories)")
        out.append("")
        if dim in _FAMILY_INTRO:
            out += [_FAMILY_INTRO[dim], ""]
        for cat in sorted(cats):
            rows = sorted(cats[cat], key=lambda r: r["name"])
            out.append(f"#### {dim} / {cat}({len(rows)})")
            for r in rows:
                summ = (OD.summary_and_rest(r.get("doc"))[0] or "").strip()
                hal = f" (halcon: `{r['halcon']}`)" if r.get("halcon") else ""
                io_ = f"`{r.get('in') or '入力なし'} → {r.get('out') or '?'}`"
                ex = _ex_link(r.get("examples")) if dim in ("2d", "3d") else (
                    _ex_link(r.get("examples")) if r.get("examples") else "")
                out.append(f"- `{r['name']}`{hal} {io_}" + (f" — {summ}" if summ else "") + ex)
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
                    _families_section, _references_section):
        if section is _families_section:
            # ★fail-closed: op の一覧は台帳の本体。ここを「(section failed)」の 1 行で済ませると
            #   カタログが黙って空になる(pip だけの利用者の RAG はこのファイルしか持たない)。
            lines += section()
            continue
        try:
            lines += section()
        except Exception as e:                          # 補助の節は 1 つ壊れても全体を出す
            lines += [f"## (section {section.__name__} failed: {e})", ""]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(_REPO, "docs", "OP_CATALOG.md"))
    args = ap.parse_args()
    md = build_catalog()
    # docs/ の人間向けコピーと、fullseye/ 配下の同梱コピー(wheel に載る)の両方に書く。
    targets = [args.out]
    shipped = os.path.join(_REPO, "fullseye", "OP_CATALOG.md")
    if os.path.isdir(os.path.dirname(shipped)) and os.path.abspath(shipped) != os.path.abspath(args.out):
        targets.append(shipped)
    for path in targets:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"wrote {path} ({len(md):,} bytes, {md.count(chr(10))} lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
