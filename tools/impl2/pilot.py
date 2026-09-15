# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""第 2 実装(別言語)を **op ノートだけから** 起こして突き合わせる。

**なぜ Python 実装を見せないのか。** 同じソースから機械翻訳した C は第 2 実装ではない。
解釈ごと複製されるので、構造的に一致し、何も見つからない。7 件の欠陥が出たのは
Rust を**契約から独立に**書き、仕様が沈黙している点でわざと別の選択をしたからだった
(`feedback_second_implementation_finds_what_tests_cannot`)。だからこの道具は
**`docs/ops/**/<op>.md` だけ**をモデルに渡す。ソースも、テストも、期待値も渡さない。

**二重の価値。** 出てきた C は (i) 仕様解釈の分岐を暴く検証器であると同時に、
(ii) **Python を載せられない現場で動く実装**でもある。今 `fs_apply` が Python 無しで
動かせるのは契約の 5 op だけで、残りは埋め込み CPython 経由。差分が解消した第 2 実装は
native 経路へ昇格できる資産なので、**判定が何であれ生成物は捨てず残す**
(`impl2/c/<op>.c` と `impl2/meta/<op>.json`、来歴つき)。

**探針は構造つきにする。** 乱数だけでは端も内部も「だいたい合っている」で終わる。
市松・斜め・定数・衝撃・枠・1xN を必ず混ぜる(`feedback_random_test_data_hides_structural_defects`)。
**一致は成果ではなく警告**でもある —— 何も出ないときは探針の弱さをまず疑う。

**判定は fail-closed。** どちらかに NaN/inf があれば差は inf。`max(0.0, nan)` が 0.0 に
畳まれて「合格」になる事故を封じる(`difftest.py` の `_finite_maxdiff` と同じ規律)。

使い方::

    py -3.11 tools/impl2/pilot.py --ops mean_box,invert --model qwen2.5-coder:32b
    py -3.11 tools/impl2/pilot.py --ops mean_box --no-generate   # 既存の C を再検査
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

IMPL2 = ROOT / "impl2"
OLLAMA = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

#: 第 2 実装が満たす C の契約。2-D の呼び出しモデル(1 画像 + つまみ a,b∈[0,1])に合わせる。
C_CONTRACT = """\
void fs2_apply(const double* in, int h, int w, double a, double b, double* out);
  in  : 入力画像。行優先 (row-major)。要素は in[y*w + x]。値域は [0,1] を想定するが
        範囲外の値が来ても落ちないこと。
  h,w : 高さ・幅。h>=1, w>=1。1xN / Nx1 も来る。
  a,b : つまみ。どちらも [0,1]。op が使わないつまみは無視してよい。
  out : 出力画像。呼び出し側が h*w 個確保済み。out[y*w + x] に書く。
"""


# --------------------------------------------------------------------------- #
# 探針(構造つき。乱数は最後の 1 枚だけ)                                        #
# --------------------------------------------------------------------------- #
def probes() -> list[tuple[str, np.ndarray]]:
    """端・対称性・パリティを分ける入力。**乱数だけでは出ない欠陥を狙う。**"""
    out: list[tuple[str, np.ndarray]] = []

    chk = np.indices((8, 8)).sum(axis=0) % 2
    out.append(("checkerboard8", chk.astype(np.float64)))

    n = 16
    out.append(("ramp_x", np.tile(np.linspace(0, 1, n), (n, 1))))
    out.append(("ramp_y", np.tile(np.linspace(0, 1, n), (n, 1)).T.copy()))
    out.append(("constant_half", np.full((n, n), 0.5)))
    out.append(("zeros", np.zeros((n, n))))

    imp = np.zeros((n, n)); imp[n // 2, n // 2] = 1.0
    out.append(("impulse_center", imp))

    # 端の扱い(パディング規約)が分かれる所。ここが `gauss` の reflect 差を出した形。
    cor = np.zeros((n, n)); cor[0, 0] = 1.0
    out.append(("impulse_corner", cor))
    edge = np.zeros((n, n)); edge[0, :] = 1.0; edge[-1, :] = 1.0
    edge[:, 0] = 1.0; edge[:, -1] = 1.0
    out.append(("frame", edge))

    diag = np.eye(n)
    out.append(("diagonal", diag))

    out.append(("row_1xN", np.linspace(0, 1, 12).reshape(1, 12)))
    out.append(("col_Nx1", np.linspace(0, 1, 12).reshape(12, 1)))
    out.append(("single_pixel", np.array([[0.7]])))

    rng = np.random.default_rng(12345)
    out.append(("random", rng.random((n, n))))
    return out


def region_probes() -> list[tuple[str, np.ndarray]]:
    """**二値マスク**の探針。region を食う op / 返す op はここを使う。

    画素の連続値でなく **離散の決定**(連結性・境界の開閉・物体の並び・空集合の扱い)が
    答えを変える層なので、探針もそこを分けるものにする。とりわけ **斜めだけで触れる 2 つの
    塊**は 4 連結なら 2 個、8 連結なら 1 個になり、`connection` の 4/8 食い違い
    (0.1.11 で直した実物)を一発で分ける。乱数では絶対に出ない。
    """
    out: list[tuple[str, np.ndarray]] = []
    n = 16

    chk = (np.indices((8, 8)).sum(axis=0) % 2).astype(np.float64)
    out.append(("checkerboard8", chk))                      # 4 連結なら 32 個、8 連結なら 1 個

    diag = np.zeros((n, n))
    diag[3, 3] = diag[4, 4] = 1.0                           # 斜めだけで触れる 2 画素
    out.append(("corner_touch2", diag))

    two = np.zeros((n, n))
    two[2:6, 2:6] = 1.0; two[8:12, 8:12] = 1.0              # 離れた 2 つの塊
    out.append(("two_blobs", two))

    ring = np.zeros((n, n))
    ring[4:12, 4:12] = 1.0; ring[6:10, 6:10] = 0.0          # 穴あき(充填・オイラー数)
    out.append(("ring_with_hole", ring))

    touch = np.zeros((n, n))
    touch[2:7, 2:7] = 1.0; touch[7:12, 7:12] = 1.0          # 角で接する 2 つの矩形
    out.append(("corner_touch_blocks", touch))

    edgeblob = np.zeros((n, n))
    edgeblob[0:4, 0:4] = 1.0                                # 端で切れる塊
    out.append(("blob_at_corner", edgeblob))

    full = np.ones((n, n))
    out.append(("all_ones", full))
    out.append(("all_zeros", np.zeros((n, n))))             # 空集合の扱い

    one = np.zeros((n, n)); one[7, 7] = 1.0
    out.append(("single_pixel_on", one))

    line = np.zeros((n, n)); line[8, :] = 1.0
    out.append(("horizontal_line", line))
    thin = np.zeros((n, n)); thin[:, 8] = 1.0
    out.append(("vertical_line", thin))

    out.append(("row_1xN", (np.arange(12) % 2).reshape(1, 12).astype(np.float64)))
    return out


def op_sorts(op: str) -> tuple[str, str]:
    """索引から in/out の型を引く(探針の選び方を決めるため)。"""
    global _SORTS
    if _SORTS is None:
        idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
        _SORTS = {o["name"]: (o["in_sort"], o["out_sort"]) for o in idx["ops"]}
    return _SORTS.get(op, ("image", "image"))


_SORTS = None

KNOBS = [(0.1, 0.5), (0.5, 0.5), (0.9, 0.5), (0.5, 0.9)]


# --------------------------------------------------------------------------- #
# op ノート(モデルに渡す唯一の入力)                                            #
# --------------------------------------------------------------------------- #
def find_note(op: str) -> Path | None:
    hits = sorted((ROOT / "docs" / "ops").rglob(f"{op}.md"))
    return hits[0] if hits else None


def build_prompt(op: str, note: str, in_sort: str = "image", out_sort: str = "image") -> str:
    extra = ""
    if in_sort == "region":
        extra = (chr(10) + "  ※ この op の入力は **領域(region)** です。``in`` の各要素は "
                 "0.0 か 1.0 の二値で、1.0 が領域に属する画素を表します。")
    if out_sort == "region":
        extra += (chr(10) + "  ※ この op の出力は **領域(region)** です。``out`` には "
                  "0.0 か 1.0 だけを書いてください(中間値を書かない)。")
    return f"""あなたは C の実装者です。以下は画像処理オペレータ `{op}` の**仕様書**です。

仕様書以外の情報(参照実装・テスト・期待値)は与えられません。**仕様書だけから**
C99 の関数を 1 つ書いてください。

--- 仕様書ここから ---
{note}
--- 仕様書ここまで ---

満たすべき C の契約:

{C_CONTRACT}{extra}

厳守:
- C99 のみ。標準ヘッダ(math.h / stdlib.h / string.h)以外に依存しない。
- 動的確保をするなら必ず free する。境界外アクセスをしない。
- 仕様書が**決めていない点**(例: 画像の端をどう埋めるか)は、あなたの判断で
  1 つ選び、**その選択をコメントで明記**してください。推測で「たぶんこうだろう」と
  黙って合わせないこと。ここが食い違えば、それは仕様書の側の欠落です。
- 出力は C のコードだけ。説明文を本文に混ぜない。コードブロック 1 つで返す。

関数名は必ず `fs2_apply` にしてください。"""


def engine_tag(engine: str) -> str:
    """成果物の置き場に使う安全な名前。**モデルごとに別々に残す** —— 同じ op を
    別のモデルに書かせたものを並べて持つこと自体が N-version の実体で、
    書き手を変えることが相関故障を下げる唯一の直接的な手段だから。"""
    return re.sub(r"[^A-Za-z0-9._-]", "-", engine)


def ask_cli(prompt: str, engine: str, timeout: int = 900) -> str:
    """外部 AI の CLI に**読み取り専用**で聞く。ワークスペースを触らせない。"""
    # Windows では ``codex`` の実体が ``codex.CMD`` で、``shutil.which`` で解決しないと
    # ``CreateProcess`` が見つけられない(WinError 2)。拡張子を自分で決め打ちしない。
    if engine.startswith("codex"):
        exe = shutil.which("codex")
        if not exe:
            raise RuntimeError("codex CLI が PATH に無い")
        # プロンプトは **stdin** で渡す。argv で渡すと codex が仕様書を受け取り切れず
        # 「仕様書の続きを送ってください」と返した(実測。プロンプトは 3,257 文字で
        # cmd.exe の長さ上限には達していないので、原因は長さではなく多行引数の扱い)。
        # codex 自身が "Reading additional input from stdin..." と言うとおり stdin が正路。
        cmd = [exe, "exec", "-s", "read-only"]
        stdin_text = prompt
    elif engine.startswith("copilot"):
        exe = shutil.which("copilot")
        if not exe:
            raise RuntimeError("copilot CLI が PATH に無い")
        cmd = [exe, "-p", prompt, "--allow-all-tools"]
        stdin_text = None
    else:
        raise ValueError(f"未知の CLI エンジン: {engine}")
    # ``codex exec`` は argv のプロンプトに加えて stdin も読もうとする
    # ("Reading additional input from stdin...")。DEVNULL で即 EOF を返さないと止まる。
    if stdin_text is None:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
    else:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           input=stdin_text, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "")[-600:])
    return r.stdout


def ask_model(prompt: str, model: str, timeout: int = 600) -> str:
    body = json.dumps({
        "model": model, "prompt": prompt, "stream": False,
        "options": {"temperature": 0, "seed": 7, "num_ctx": 8192},
    }).encode("utf-8")
    req = urllib.request.Request(f"{OLLAMA}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))["response"]


def extract_c(text: str) -> str:
    """コードブロックを取り出す。素の本文しか無ければそのまま返す。"""
    blocks = re.findall(r"```(?:c|C)?\s*\n(.*?)```", text, re.S)
    if blocks:
        return max(blocks, key=len).strip() + "\n"
    return text.strip() + "\n"


# --------------------------------------------------------------------------- #
# コンパイルして走らせる                                                        #
# --------------------------------------------------------------------------- #
_DRIVER = r"""
#include <stdio.h>
#include <stdlib.h>
void fs2_apply(const double* in, int h, int w, double a, double b, double* out);
int main(int argc, char** argv) {
    FILE* fi = fopen(argv[1], "rb"); FILE* fo = fopen(argv[2], "wb");
    if (!fi || !fo) return 2;
    int h, w; double a, b;
    if (fread(&h,4,1,fi)!=1 || fread(&w,4,1,fi)!=1) return 3;
    if (fread(&a,8,1,fi)!=1 || fread(&b,8,1,fi)!=1) return 3;
    double* in  = (double*)malloc(sizeof(double)*(size_t)h*w);
    double* out = (double*)calloc((size_t)h*w, sizeof(double));
    if (fread(in,8,(size_t)h*w,fi)!=(size_t)h*w) return 3;
    fs2_apply(in, h, w, a, b, out);
    fwrite(out, 8, (size_t)h*w, fo);
    free(in); free(out); fclose(fi); fclose(fo); return 0;
}
"""


def compile_c(csrc: Path, workdir: Path, cc: list[str]) -> tuple[Path | None, str]:
    drv = workdir / "driver.c"
    drv.write_text(_DRIVER, encoding="utf-8")
    exe = workdir / ("impl2.exe" if sys.platform == "win32" else "impl2")
    r = subprocess.run(list(cc) + ["-O2", "-std=c99", str(csrc), str(drv), "-lm", "-o", str(exe)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout)[-1200:]
    return exe, ""


def run_c(exe: Path, workdir: Path, img: np.ndarray, a: float, b: float) -> np.ndarray | None:
    h, w = img.shape
    fin, fout = workdir / "in.bin", workdir / "out.bin"
    with open(fin, "wb") as f:
        np.array([h, w], np.int32).tofile(f)
        np.array([a, b], np.float64).tofile(f)
        np.ascontiguousarray(img, np.float64).tofile(f)
    r = subprocess.run([str(exe), str(fin), str(fout)], capture_output=True, timeout=60)
    if r.returncode != 0 or not fout.exists():
        return None
    got = np.fromfile(fout, np.float64)
    if got.size != h * w:
        return None
    return got.reshape(h, w)


def finite_maxdiff(ref, got) -> float:
    """**fail-closed**: 形が違う / どちらかに非有限があれば inf。NaN が 0.0 に畳まれて
    「合格」になる事故を封じる(`difftest._finite_maxdiff` と同じ規律)。"""
    ref = np.asarray(ref, np.float64); got = np.asarray(got, np.float64)
    if ref.shape != got.shape:
        return float("inf")
    if ref.size == 0:
        return 0.0
    if not (np.isfinite(ref).all() and np.isfinite(got).all()):
        return float("inf")
    return float(np.max(np.abs(ref - got)))


# --------------------------------------------------------------------------- #
def run_op(op: str, model: str, generate: bool, cc: list[str], tol: float) -> dict:
    tag = engine_tag(model)
    import fullseye as fs

    note_p = find_note(op)
    if note_p is None:
        return {"op": op, "status": "no_note", "reason": "docs/ops に <op>.md が無い"}
    note = note_p.read_text(encoding="utf-8")
    note_sha = hashlib.sha256(note.encode("utf-8")).hexdigest()[:16]

    (IMPL2 / "c" / tag).mkdir(parents=True, exist_ok=True)
    (IMPL2 / "meta" / tag).mkdir(parents=True, exist_ok=True)
    csrc = IMPL2 / "c" / tag / f"{op}.c"

    rec = {"op": op, "note": str(note_p.relative_to(ROOT)).replace("\\", "/"),
           "note_sha256_16": note_sha, "model": model,
           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "c_path": str(csrc.relative_to(ROOT)).replace("\\", "/")}

    if generate or not csrc.exists():
        prompt = build_prompt(op, note, *op_sorts(op))
        rec["prompt_sha256_16"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
        t0 = time.time()
        try:
            if model.startswith(("codex", "copilot")):
                raw = ask_cli(prompt, model)
            else:
                raw = ask_model(prompt, model)
        except (urllib.error.URLError, TimeoutError, OSError, RuntimeError,
                subprocess.SubprocessError, ValueError) as e:
            rec.update(status="model_error", reason=str(e)[:400])
            return rec
        rec["gen_seconds"] = round(time.time() - t0, 1)
        csrc.write_text(extract_c(raw), encoding="utf-8")
    else:
        rec["reused_existing_c"] = True

    workdir = IMPL2 / "_work" / tag / op
    workdir.mkdir(parents=True, exist_ok=True)
    exe, err = compile_c(csrc, workdir, cc)
    if exe is None:
        rec.update(status="compile_error", compile_error=err)
        return rec
    rec["compiled"] = True

    in_sort, out_sort = op_sorts(op)
    probe_set = region_probes() if in_sort == "region" else probes()
    rec["in_sort"], rec["out_sort"] = in_sort, out_sort
    rec["probe_set"] = "region" if in_sort == "region" else "image"

    rows, worst = [], 0.0
    for a, b in KNOBS:
        for pname, img in probe_set:
            try:
                ref = np.asarray(fs.apply(img.copy(), op, a=a, b=b), np.float64)
            except Exception as e:                      # op が拒む入力は比較対象外
                rows.append({"probe": pname, "a": a, "b": b,
                             "status": "fullseye_refused", "detail": str(e)[:120]})
                continue
            got = run_c(exe, workdir, img, a, b)
            if got is None:
                rows.append({"probe": pname, "a": a, "b": b, "status": "impl2_crashed"})
                worst = float("inf")
                continue
            if ref.shape != got.shape:
                rows.append({"probe": pname, "a": a, "b": b, "status": "shape_differs",
                             "ref_shape": list(ref.shape), "impl2_shape": list(got.shape)})
                worst = float("inf")
                continue
            d = finite_maxdiff(ref, got)
            worst = max(worst, d)
            rows.append({"probe": pname, "a": a, "b": b, "status": "compared",
                         "max_abs_diff": None if d == float("inf") else d,
                         "non_finite": d == float("inf")})
    rec["probes"] = rows
    rec["worst_max_abs_diff"] = None if worst == float("inf") else worst
    rec["agrees"] = worst < tol
    rec["tol"] = tol
    # 一致は成果ではなく **警告**。探針が弱いだけかもしれない。
    rec["status"] = "agrees" if rec["agrees"] else "diverges"
    (IMPL2 / "meta" / tag / f"{op}.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False),
                                               encoding="utf-8")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ops", help="カンマ区切りの op 名")
    ap.add_argument("--model", default="qwen2.5-coder:32b")
    ap.add_argument("--tol", type=float, default=1e-9)
    ap.add_argument("--no-generate", action="store_true", help="既存の C を再検査するだけ")
    ap.add_argument("--skip-existing", action="store_true",
                    help="そのエンジンの C が既にある op は生成をやり直さない(長時間の無人実行用)")
    ap.add_argument("--all-image", action="store_true",
                    help="registry/color の image->image op を全部回す")
    ap.add_argument("--all-region", action="store_true",
                    help="region を食う/返す op(image->region / region->region)を全部回す")
    a = ap.parse_args()

    from algo_difftest import compiler_label, find_c_compiler
    cc = find_c_compiler()
    if not cc:
        print("C コンパイラが無い(gcc/clang か `pip install ziglang`)。")
        return 2
    print(f"compiler: {compiler_label(cc)} | model: {a.model}")

    names = [o.strip() for o in (a.ops or "").split(",") if o.strip()]
    if a.all_image:
        idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
        names += [o["name"] for o in idx["ops"]
                  if o["tier"] in ("registry", "color")
                  and o["in_sort"] == "image" and o["out_sort"] == "image"]
    if a.all_region:
        idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
        names += [o["name"] for o in idx["ops"]
                  if o["tier"] in ("registry", "color") and o["out_sort"] == "region"
                  and o["in_sort"] in ("image", "region")]
    names = list(dict.fromkeys(names))

    results = []
    for op in names:
        if a.skip_existing and (IMPL2 / "c" / engine_tag(a.model) / f"{op}.c").exists():
            gen = False
        else:
            gen = not a.no_generate
        r = run_op(op, a.model, gen, cc, a.tol)
        results.append(r)
        w = r.get("worst_max_abs_diff")
        print(f"[{r['status']:14s}] {op:20s} "
              + (f"worst diff {w:.3e}" if isinstance(w, float) else "")
              + (f" {r.get('reason','')}" if r.get("reason") else ""))
    n_div = sum(1 for r in results if r["status"] == "diverges")
    print(f"\n{len(results)} op: diverges={n_div} "
          f"agrees={sum(1 for r in results if r['status']=='agrees')} "
          f"other={sum(1 for r in results if r['status'] not in ('agrees','diverges'))}")
    print("生成物は impl2/c/ と impl2/meta/ に残してある(判定に関わらず捨てない)。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
