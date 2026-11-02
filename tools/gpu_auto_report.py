#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Turn the sweep rows into classes, the allow-list and the published report.

``tools/gpu_auto_sweep.py report`` から呼ばれる。分類はここだけが決める(文書と許可リストが
別々の判定を持たない)。文書の数字はすべて JSONL の実測から数える。
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

#: 分類の表示順と見出し。
CLASSES = (("adopted", "採用(一致 + 転送込み 5 倍以上)"),
           ("adopted_resident", "常駐前提で採用(単独 1 回は 5 倍未満、GPU に載せたままの連続処理で 5 倍以上)"),
           ("match_slow", "一致したが遅い(5 倍未満)"),
           ("match_fixed", "一致したが実寸の入力を作れない(固定形の入力)"),
           ("mismatch", "不一致"),
           ("vacuous", "判定不能(出力が定数)"),
           ("exception", "例外(CuPy 側の不足・型の混在)"),
           ("wrapper", "包み(cv2 / skimage / PIL が本体)"),
           ("python_loop", "Python ループが律速"),
           ("unmeasured", "測れなかった"))

WRAP_LIBS = ("cv2", "skimage", "PIL", "sklearn", "pywt", "mahotas", "SimpleITK")


def classify(c, p, s, is_python_loop, min_ratio):
    """(分類, 理由) を返す。c / p / s は cpu / parity / scale の行(無ければ None)。"""
    if c is None:
        return "unmeasured", "cpu_pending"
    if c.get("status") != "ok":
        return "unmeasured", c.get("status")
    libs = c.get("libs") or {}
    lib = next((k for k in WRAP_LIBS if k in libs), None)
    if lib is not None and (p is None or p.get("status") != "match"):
        return "wrapper", lib
    if is_python_loop(c):
        return "python_loop", "lines_scale_with_input"
    if p is None:
        return "unmeasured", "parity_pending"
    st = p.get("status")
    if st == "gpu_exception":
        r = p.get("reason") or "unknown"
        if r.startswith("wrapper_"):
            return "wrapper", r[len("wrapper_"):]
        return "exception", r
    if st == "mismatch":
        return "mismatch", re.sub(r"[0-9.e+-]+$", "", p.get("why") or "")[:18].strip()
    if st == "vacuous":
        return "vacuous", "constant_output"
    if st in ("timeout", "crash"):
        return "exception", "gpu_" + st
    if st != "match":
        return "unmeasured", "parity_" + str(st)
    if s is None:
        return "unmeasured", "scale_pending"
    st = s.get("status")
    if st == "fixed_input":
        return "match_fixed", "fixed_input"
    if st == "measured" and s.get("stage") == "scale_cpu":
        return "unmeasured", "scale_gpu_pending"
    if st == "timeout" and s.get("stage") == "scale_cpu":
        return "unmeasured", "cpu_over_limit_at_real_size"
    if st == "measured":
        r = s.get("ratio") or 0.0
        return ("adopted", "ratio") if r >= min_ratio and s.get("nonconst") \
            else ("match_slow", "ratio")
    if st == "mismatch_at_scale":
        return "mismatch", "at_real_size"
    if st == "gpu_exception_at_scale":
        return "exception", "scale_" + (s.get("reason") or "unknown")
    if st == "cpu_exception_at_scale":
        return "match_fixed", "input_refused_at_real_size"
    if st == "transfer_bound":
        return "match_slow", "transfer_bound"
    if st == "timeout":
        return "match_slow", "gpu_over_limit_at_real_size"
    if st == "crash":
        return "exception", "scale_crash"
    return "unmeasured", "scale_" + str(st)


def classes(out, targets, is_python_loop, min_ratio, max_gen=None):
    """``max_gen`` を渡すと、その世代までの行だけで数える(修正層・常駐の前の状態)。"""
    import gpu_auto_sweep as S
    cpu, par = S.read_rows("cpu"), S.read_rows("parity", max_gen)
    sca = S.read_rows("scale", max_gen)
    base = S.read_rows("scale_cpu")
    res = S.read_rows("resident") if max_gen is None else {}
    vf = S.OUT / "verify.json"
    verify = json.loads(vf.read_text(encoding="utf-8")) if vf.exists() else {}
    rows = []
    for t in targets:
        n = t["name"]
        c, p, s = cpu.get(n), par.get(n), sca.get(n) or base.get(n)
        if s and s.get("t_gpu") and (base.get(n) or {}).get("t_cpu"):
            # 基準線は測り直しで速くなることがある。倍率は常に最新の基準線から出す
            s = dict(s, t_cpu=base[n]["t_cpu"], ratio=base[n]["t_cpu"] / s["t_gpu"])
        cl, why = classify(c, p, s, is_python_loop, min_ratio)
        v = verify.get(n)
        rz = res.get(n)
        if cl == "match_slow" and why == "ratio" and rz and rz.get("status") == "measured" \
                and rz.get("nonconst") and (rz.get("ratio") or 0) >= min_ratio \
                and not (rz.get("stats") or {}).get("n_cpu_fallback"):
            cl, why = "adopted_resident", "chain_%d" % rz.get("chain", 0)
        if cl == "adopted" and v is not None and not v["ok"]:
            cl, why = "mismatch", "at_full_resolution"
        rows.append({"name": n, "family": t.get("category") or "?", "tier": t.get("gpu_tier"),
                     "class": cl, "why": why, "c": c or {}, "p": p or {}, "s": s or {},
                     "verified": None if v is None else bool(v["ok"]), "r": rz or {}})
    return rows


def status(out, targets) -> int:
    import gpu_auto_sweep as S
    print({st: len(S.read_rows(st)) for st in ("cpu", "parity", "scale_cpu", "scale")},
          "of", len(targets))
    for st in ("parity", "scale_cpu", "scale"):
        print(st, collections.Counter(r.get("status") for r in S.read_rows(st).values()))
    return 0


def _fmt_t(x):
    if x is None:
        return "—"
    return "%.2f s" % x if x >= 1 else "%.0f ms" % (x * 1000)


def _shape(s):
    v = s.get("shape")
    return "×".join(str(i) for i in v) if v else "—"


def hand_written() -> set:
    """手書きの GPU 経路(``accel`` / ``accel_vol`` / ``accel_match``)を持つ op の名前。"""
    import accel
    import accel_match
    import accel_vol
    names = {core for _n, (_f, core, _h) in accel.ACCEL.items()}
    names |= {core for _n, (_f, core) in accel_vol.VOL_ACCEL.items()}
    names |= set(accel_match.MATCH_ACCEL)
    return names


#: 直せなかった原因ごとの理由(表に出す)。
UNFIXABLE = {
    "wrapper_skimage": "本体が skimage(ネイティブ)。CuPy 配列を受け付けない。CPU へ渡して戻すだけの"
                       "差し替えは GPU 化ではない",
    "wrapper_cv2": "本体が OpenCV(ネイティブ)。同上",
    "wrapper_PIL": "本体が PIL(ネイティブ)。同上",
    "implicit_numpy": "疎行列・グラフ・skimage 経由で本物の numpy が CuPy 配列を受け取る。"
                      "疎行列/グラフ(CPU アルゴリズム)は GPU に載せても転送が増えるだけ",
    "value_error": "疎グラフ(csgraph)・疎行列の解法・縮退入力・自作クラスの型比較。"
                   "CuPy 側に同等が無いか、入力の問題",
    "type_error": "0 次元 CuPy 配列を Python の添字・辞書キー・スライスに使う箇所、"
                  "SuperLU の LU.solve(CPU 専用)など。対応には op 側の書換えが要る",
    "numpy_cupy_mix": "CuPy が受け付けない型の混在(「直した」以外の残り)",
    "unhashable_array": "配列を set / dict のキーに使う Python ループ(GPU 化の対象でない)",
    "missing_attr": "CuPy に無い属性",
    "gpu_timeout": "90 秒で終わらない(小さなカーネルを大量に発行する Python ループ律速)",
    "gpu_crash": "プロセスが落ちる",
}


def _extra_sections(rows, ex) -> list:
    """道 1(修正層)と道 2(常駐)の前→後。``ex`` は ``report`` が作る。"""
    if not ex:
        return []
    old, cnt = ex["old"], collections.Counter(r["class"] for r in rows)
    L = ["", "## 追加掃引: 前 → 後", "",
         "修正層(`gpu_shadow.py`、道 1)と常駐の連続処理(道 2)を足す前後の件数。分母 %d 件は"
         "変えていない。" % len(rows), "",
         "| 分類 | 前 | 後 | 差 |", "|---|---:|---:|---:|"]
    for k, title in CLASSES:
        L.append("| %s | %d | %d | %+d |" % (title, old.get(k, 0), cnt.get(k, 0),
                                              cnt.get(k, 0) - old.get(k, 0)))
    L += ["", "採用の増分は道 1 が %d 件(単独 1 回呼び)、道 2 が %d 件(常駐前提・別枠)。"
          "常駐前提の採用は単独 1 回呼びの採用と混ぜて数えない。" % (ex["gain1"], ex["gain2"])]
    L += ["", "### 道 1: 原因別の結果", "",
          "| 原因 | 前の件数 | 直した(一致になった) | うち実寸で採用 | 直せない | 直せない理由 |",
          "|---|---:|---:|---:|---:|---|"]
    for reason, d in sorted(ex["by_reason"].items(), key=lambda kv: -kv[1]["n"]):
        L.append("| %s | %d | %d | %d | %d | %s |"
                 % (reason, d["n"], d["fixed"], d["adopted"], d["n"] - d["fixed"],
                    UNFIXABLE.get(reason, "—")))
    if ex["fixed_names"]:
        L += ["", "直した op と実寸の倍率:", "",
              "| op | 原因 | 結果 | 倍率(単独) |", "|---|---|---|---:|"]
        for n, reason, cl, ratio in ex["fixed_names"]:
            L.append("| `%s` | %s | %s | %s |" % (n, reason, cl, "—" if ratio is None
                                                 else "%.2f" % ratio))
    L += ["", "直した修正(`gpu_shadow.py`。numpy / scipy を呼ぶ側のソースは書き換えない):", "",
          "- `a[i] = (x, y)` のようにタプル・リストを CuPy 配列へ代入する形を、読み込み時の AST 書換えで"
          "配列に包む(CuPy は右辺のタプルを受け付けない)。",
          "- `x.max(initial=v)` / `min` / `sum` の `initial` を `maximum` / `minimum` / 加算に置く。",
          "- `np.repeat` の `repeats` が CuPy 配列のとき CPU の整数列にして渡す。",
          "- `np.full(shape, ndarray)` を broadcast に置く。",
          "- object dtype を CuPy が拒否した呼び出しは CPU に退避して数える。",
          "- `scipy.stats.kstest` の結果のようにキーワード専用の追加項目を持つ namedtuple を、"
          "同名の namedtuple で組み直す。"]
    L += ["", "### 道 2: 常駐前提の連続処理", "",
          "単独 1 回呼びで 3.5〜5 倍だった op を、入力を GPU に先に %d 個ぶん置き、計算を続け、"
          "出力を 1 回だけ戻して測り直した。1 回あたりの時間 = (往路の転送 + 計算の総和 + 復路の"
          "転送) / %d。計算は 1 回ごとに `Stream.synchronize()` の後に時計を読む。CPU に退避した"
          "呼び出しがある op は常駐前提にならないので採用から除く。" % (ex["chain"], ex["chain"]),
          "", "測った %d 件のうち、常駐前提で採用 %d 件、CPU 退避ありで除外 %d 件、5 倍未満 %d 件、"
          "不一致 %d 件。" % (ex["n_res"], cnt.get("adopted_resident", 0), ex["res_fb"],
                            ex["res_slow"], ex["res_mm"]),
          "", "「単独(再)」は常駐の測定と同じ場で単独 1 回呼びも測り直した倍率。先の測定より高い op が"
          "多く、先の単独の値は他の負荷で遅く出ていた可能性がある。採用の判定は先の測定のまま"
          "動かしていない(測り直しの値で採用に格上げしない)。", "",
          "| op | 族 | 単独 | 単独(再) | 常駐 | 計算のみ | CPU 退避 | 判定 |",
          "|---|---|---:|---:|---:|---:|---:|---|"]
    for r in sorted((r for r in rows if r["r"].get("status") == "measured"),
                    key=lambda r: -(r["r"].get("ratio") or 0)):
        z = r["r"]
        L.append("| `%s` | %s | %.2f | %.2f | %.1f | %.1f | %d | %s |"
                 % (r["name"], r["family"], z.get("ratio_single") or 0,
                    z.get("ratio_single_now") or 0, z.get("ratio") or 0,
                    z.get("ratio_compute_only") or 0,
                    (z.get("stats") or {}).get("n_cpu_fallback", 0), r["class"]))
    L.append("")
    return L


def render(rows, tol, min_ratio, method, hand=frozenset(), extra=None):
    total = len(rows)
    cnt = collections.Counter(r["class"] for r in rows)
    L = ["# 機械的 GPU 化の掃引 (2026-11-02)", "",
         "GPU 向き op(`gpu_tier` = required / suitable)%d 件を、1 件ずつ手書きせず既存の "
         "numpy/scipy 実装のまま CuPy 配列で走らせて採点した結果。" % total, "",
         "`tools/gpu_auto_sweep.py` の実測から `tools/gpu_auto_sweep.py report` が生成する。手で"
         "直さない。", "",
         "## 方式", "", method, "",
         "## 判定", "",
         "- 一致: 同じ入力・同じ種で CPU と GPU を実行し、内部の最大差が出力の振れ幅の "
         "%.0e 未満。端(4 画素以上)は比べない。NaN の位置も一致を要求する。" % tol,
         "- 入力は構造のある合成画像(`op_probe` の円・矩形・斜めエッジ、チャープ信号など)を"
         "先頭に置く。出力が定数の op は一致と数えない(判定不能)。",
         "- 倍率: 実寸(画像 2048²、体積 256³、信号 2²⁰、行列 1024²)で 1 回あたりの時間の比。"
         "GPU 側は転送 → 計算 → 転送(`.get()` が同期)を含み、CuPy のカーネルコンパイルは"
         "準備運転で除く。CPU 2 回、GPU 最大 3 回の最小値。バッチの融合は無い(1 枚ずつ)ので、"
         "N 枚の倍率も同じ値になる。CPU の基準線は他の作業と同時に測ったので、倍率 3 以上の op は"
         "1 本ずつ測り直し、速い方の時間を使った(倍率が低く出る向き)。GPU の時間も他の作業と"
         "同時に測ることがある。実寸の比較は出力を間引いた標本で行う。",
         "- 採用: 一致かつ %.1f 倍以上、かつ Python 行数が入力に比例しない。" % min_ratio,
         "- CPU の基準線はこのリポジトリの実装そのもので、多くは 1 スレッドで走る。`FULLSEYE_FAST` の "
         "cv2 版やタイル分割の並列は使っていないので、最速の CPU 実装との比ではない。",
         "- Python ループ律速: 入力を 2 倍にしたときの増分が 0.05 行/要素 以上(2048² で 20 万行)。"
         "固定形の入力は 1000 要素以上に限り 1 回の 行数/要素数 ≥ 0.5。", "",
         "## 全件の分類", "", "| 分類 | 件数 |", "|---|---:|"]
    for k, title in CLASSES:
        L.append("| %s | %d |" % (title, cnt.get(k, 0)))
    L.append("| **合計** | **%d** |" % total)
    L += ["", "例外と未計測の理由の内訳:", "", "| 分類 | 理由 | 件数 |", "|---|---|---:|"]
    why = collections.Counter((r["class"], r["why"]) for r in rows
                              if r["class"] in ("exception", "wrapper", "unmeasured", "mismatch"))
    for (cl, w), n in sorted(why.items(), key=lambda kv: (kv[0][0], -kv[1])):
        L.append("| %s | %s | %d |" % (cl, w, n))
    adopted = sorted((r for r in rows if r["class"] == "adopted"),
                     key=lambda r: -(r["s"].get("ratio") or 0))
    L += ["", "## 採用 op の実測倍率", ""]
    if adopted:
        L += ["| op | 族 | 入力 | CPU | GPU(転送込み) | 倍率 | 内部差(比) | CPU 退避 |",
              "|---|---|---|---:|---:|---:|---:|---:|"]
        for r in adopted:
            s = r["s"]
            L.append("| `%s` | %s | %s | %s | %s | %.1f | %.1e | %d |"
                     % (r["name"], r["family"], _shape(s), _fmt_t(s.get("t_cpu")),
                        _fmt_t(s.get("t_gpu")), s.get("ratio") or 0, s.get("rel") or 0,
                        (s.get("stats") or {}).get("n_cpu_fallback", 0)))
        rs = sorted(r["s"]["ratio"] for r in adopted)
        L += ["", "倍率の中央値 %.1f、最小 %.1f、最大 %.1f。"
              % (rs[len(rs) // 2], rs[0], rs[-1])]
        over = sum(1 for r in adopted if r["name"] in hand)
        L += ["", "採用 %d 件のうち %d 件は手書きの GPU 経路(`accel` 系)も持つ。新しく GPU で"
              "走るようになったのは %d 件。" % (len(adopted), over, len(adopted) - over)]
        x = sum(1 for r in rows if r["name"] in hand)
        L += ["", "### GPU 対応率への数え方(分母 %d 件 = required + suitable)" % len(rows), "",
              "| 経路 | 件数 |", "|---|---:|",
              "| 手書き経路(`accel` / `accel_vol` / `accel_match`) | %d |" % x,
              "| 許可リスト経由(機械的 GPU 化。`fullseye/data/gpu_auto_allow.json`) | %d |"
              % len(adopted),
              "| うち手書きと重複 | %d |" % over,
              "| 合算(重複を 1 回と数える) | %d |" % (x + len(adopted) - over),
              "", "注記: 許可リスト経由の %d 件は**既定では有効でない**。明示の GPU 指定か許可リスト"
              "を使ったときだけ GPU で走る。手書き経路とは数字を混ぜず、必ず上の内訳で示す。"
              "採用の門(内部差 < %.0e・転送込み %.1f 倍以上・出力定数は不採用)は変えていない。"
              % (len(adopted), tol, min_ratio)]
        ver = [r for r in rows if r["verified"] is not None]
        if ver:
            L += ["", "実寸の比較は間引いた標本で行ったので、倍率の上位と無作為標本の %d 件は全画素で"
                  "比べ直した(`tools/gpu_auto_verify.py`)。一致 %d 件。"
                  % (len(ver), sum(1 for r in ver if r["verified"]))]
    else:
        L.append("採用なし。")
    slow = sorted((r for r in rows if r["class"] == "match_slow"),
                  key=lambda r: -(r["s"].get("ratio") or 0))
    if slow:
        L += ["", "## 一致したが遅い op(倍率の高い順に上位 30)", "",
              "| op | 族 | 入力 | CPU | GPU | 倍率 |", "|---|---|---|---:|---:|---:|"]
        for r in slow[:30]:
            s = r["s"]
            L.append("| `%s` | %s | %s | %s | %s | %.2f |"
                     % (r["name"], r["family"], _shape(s), _fmt_t(s.get("t_cpu")),
                        _fmt_t(s.get("t_gpu")), s.get("ratio") or 0))
    L += _extra_sections(rows, extra or {})
    L += ["", "## 族別", "",
          "| 族 | 全 | 採用 | 遅い | 固定形 | 不一致 | 判定不能 | 例外 | 包み | Pyループ | 未計測 |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    fam: dict = {}
    for r in rows:
        fam.setdefault(r["family"], collections.Counter())[r["class"]] += 1
    for f, c in sorted(fam.items(), key=lambda kv: (-sum(kv[1].values()), kv[0])):
        L.append("| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d | %d |"
                 % (f, sum(c.values()), c["adopted"], c["match_slow"], c["match_fixed"],
                    c["mismatch"], c["vacuous"], c["exception"], c["wrapper"],
                    c["python_loop"], c["unmeasured"]))
    L += ["", "## 手書きに回す族の順位", "",
          "数式が numpy で書けているのに機械的に載らなかった op(例外・不一致)と、一致したのに"
          "5 倍に届かなかった op の数で並べた。包みは本体ライブラリの置き換えが要り、Python ループ"
          "は先にベクトル化が要るので、列を分けた。", "",
          "| 順位 | 族 | 例外+不一致+遅い | 包み | Pyループ |", "|---:|---|---:|---:|---:|"]
    rank = sorted(fam.items(), key=lambda kv: -(kv[1]["exception"] + kv[1]["mismatch"]
                                               + kv[1]["match_slow"]))
    for i, (f, c) in enumerate(rank[:15], 1):
        L.append("| %d | %s | %d | %d | %d |"
                 % (i, f, c["exception"] + c["mismatch"] + c["match_slow"], c["wrapper"],
                    c["python_loop"]))
    sites = collections.Counter(r["p"].get("at") for r in rows
                                if r["class"] == "exception" and r["p"].get("at"))
    L += ["", "例外が集中する場所(同じ行で落ちる op の数、上位 15):", "",
          "| 位置 | 件数 |", "|---|---:|"]
    for k, n in sites.most_common(15):
        L.append("| `%s` | %d |" % (k, n))
    L.append("")
    return "\n".join(L)


METHOD = (
    "CuPy {cupy} + PyTorch {torch} を同じプロセスで使い(DLPack の往復を確認)、`gpu_shadow.py` が"
    "プロジェクトのソースを別の名前空間でもう一度実行し、その中の `numpy` / `scipy` だけを CuPy へ"
    "向ける。大域の差し替えはしないので既定の CPU 経路は変わらない。CuPy に無い関数は CPU へ"
    "転送して実行し、回数を数える(速さの判定で落ちる)。乱数は numpy のものを使い、CPU と同じ"
    "系列を GPU へ転送する。比較の詳細は `docs/perf/gpu_auto_method_compare_2026-11-02.json`。")


def report(out, targets, root, is_python_loop, tol, min_ratio) -> int:
    rows = classes(out, targets, is_python_loop, min_ratio)
    import gpu_auto_sweep as S
    oldrows = classes(out, targets, is_python_loop, min_ratio, max_gen=1)
    oldc = collections.Counter(r["class"] for r in oldrows)
    newc = collections.Counter(r["class"] for r in rows)
    byname = {r["name"]: r for r in rows}
    by_reason, fixed_names = {}, []
    for o in oldrows:
        if o["class"] not in ("exception", "wrapper"):
            continue
        reason = o["why"] if o["class"] == "exception" else "wrapper_" + str(o["why"])
        d = by_reason.setdefault(reason, {"n": 0, "fixed": 0, "adopted": 0})
        d["n"] += 1
        nw = byname[o["name"]]
        if nw["class"] not in ("exception", "wrapper") and nw["p"].get("status") == "match":
            d["fixed"] += 1
            fixed_names.append((o["name"], reason, nw["class"], nw["s"].get("ratio")))
        if nw["class"] == "adopted":
            d["adopted"] += 1
    res = S.read_rows("resident")
    meas = [r for r in rows if r["r"].get("status") == "measured"]
    extra = {"old": oldc, "by_reason": by_reason, "fixed_names": sorted(fixed_names),
             "gain1": newc["adopted"] - oldc["adopted"], "gain2": newc["adopted_resident"],
             "chain": S.CHAIN, "n_res": len(res),
             "res_fb": sum(1 for r in meas if (r["r"].get("stats") or {}).get("n_cpu_fallback")
                           and (r["r"].get("ratio") or 0) >= min_ratio),
             "res_slow": sum(1 for r in meas if (r["r"].get("ratio") or 0) < min_ratio),
             "res_mm": sum(1 for r in res.values() if r.get("status") == "mismatch_at_scale")}
    perf = Path(root) / "docs" / "perf"
    import cupy
    import torch
    hand = hand_written()
    text = render(rows, tol, min_ratio, METHOD.format(cupy=cupy.__version__,
                                                      torch=torch.__version__), hand, extra)
    (perf / "gpu_auto_sweep_2026-11-02.md").write_text(text, encoding="utf-8")
    summary = {"n": len(rows), "classes": dict(collections.Counter(r["class"] for r in rows)),
               "ops": {r["name"]: {"family": r["family"], "class": r["class"], "why": r["why"],
                                   "ratio": r["s"].get("ratio"), "rel": r["p"].get("rel"),
                                   "at": r["p"].get("at")} for r in rows}}
    (perf / "gpu_auto_sweep_2026-11-02.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")
    allow = {"generated_by": "tools/gpu_auto_sweep.py report", "min_ratio": min_ratio,
             "ops": {r["name"]: {"ratio": round(r["s"]["ratio"], 2), "family": r["family"],
                                 "hand_written_gpu": r["name"] in hand}
                     for r in rows if r["class"] == "adopted"},
             "resident_ops": {r["name"]: {"ratio_resident": round(r["r"]["ratio"], 3),
                                          "ratio_single": round(r["s"].get("ratio") or 0, 3),
                                          "chain": r["r"].get("chain"), "family": r["family"]}
                              for r in rows if r["class"] == "adopted_resident"},
             "note": "ops = single-call adoption; resident_ops = adopted only when inputs and "
                     "outputs stay on the GPU across a chain (never mixed with ops)."}
    (Path(root) / "fullseye" / "data" / "gpu_auto_allow.json").write_text(
        json.dumps(allow, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(summary["classes"])
    return 0
