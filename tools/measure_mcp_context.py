"""Measure LLM-visible text for a minimal discovery/plan/cards cycle.

    py -3.11 tools/measure_mcp_context.py           # docs/mcp_context_benchmark.json を書く
    py -3.11 tools/measure_mcp_context.py --check   # 書かずに、commit 済みと一致するか(不一致で exit 1)
    py -3.11 tools/measure_mcp_context.py --help    # 何も書かない

★2026-11-03(完成度監査 A-10): 以前は引数を読まずに必ず書き直していて、``--help`` を渡しても
``docs/mcp_context_benchmark.json`` が上書きされた。引数の解釈を重い import と測定より先に置き、
``--check`` を足した。
"""
import argparse, json, math, os
from types import SimpleNamespace
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"docs/mcp_context_benchmark.json"
import sys

TASKS=[
 ("surface dent from reflected fringes",["image","image"],"normalmap","deflectometry_phase_to_slope"),
 ("find scratches using polarization","polsweep","image","polarization_dolp_map"),
 ("recover projected fringe height","images","depth","decode_fringe"),
 ("locate a part for handling","image","match","shape_locate"),
 ("fast structured-light depth","images","depth","decode_fringe"),
 ("switch product and detect corners","image","feature","cv_good_features"),
]
def tokens(value):
 return math.ceil(len(json.dumps(value,ensure_ascii=False,separators=(",",":")).encode("utf-8"))/4)
def build():
 # Heavy imports live here so that `--help` / a bad argument never loads the server.
 if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
 from fullseye.mcp.handles import HandleStore
 from fullseye.mcp.server import call_tool, handle_tools_list
 from fullseye.opsearch import known_sorts
 os.environ["FULLSEYE_MCP_PROFILE"]="minimal"
 schema=handle_tools_list({"profile":"minimal"})
 full_schema=handle_tools_list({"profile":"full"})
 # These three tools only need the catalog's sort vocabulary.  Avoid loading
 # every op note: that would make this small generated report depend on all docs.
 cat,store=SimpleNamespace(sorts=known_sorts()),HandleStore(roots=[])
 rows=[]
 for query,have,want,expected in TASKS:
  find_args={"query":query,"out_sort":want,"limit":7}
  # A list denotes several required inputs, which the unary search index cannot
  # represent.  Constrain only the output there; plan() validates the full arity.
  if not isinstance(have,list): find_args["in_sort"]=have
  found_result=call_tool("fullseye_find_ops",find_args,cat,store)
  found=found_result["structuredContent"]
  planned_result=call_tool("fullseye_plan",{"have":have,"want":want,"goal":query},cat,store)
  planned=planned_result["structuredContent"]
  names=planned.get("plans",[{}])[0].get("ops",[])[:5]
  card_result=call_tool("fullseye_op_cards",{"names":names},cat,store) if names else None
  visible=[found_result["content"][0]["text"],planned_result["content"][0]["text"]]
  if card_result: visible.append(card_result["content"][0]["text"])
  response_tokens=sum(tokens(text) for text in visible)
  found_names=[x["name"] for x in found["ops"]]
  rank=found_names.index(expected)+1 if expected in found_names else None
  rows.append({"task":query,"tool_schema_tokens":schema["estimated_tokens"],
               "response_tokens":response_tokens,"total_tokens":schema["estimated_tokens"]+response_tokens,
               "planned":bool(planned.get("ok")),"expected":expected,"expected_rank":rank,"ops":names})
 return {"method":"minimal tools schema plus only LLM-visible content[].text from find_ops(limit=7, typed), plan(k=7), and cards; UTF-8 JSON bytes/4; structuredContent excluded",
         "scope":"Counts discovery through planning/cards only; execution and answer-correctness evaluation are excluded.",
         "tool_profiles":{"full_tokens":full_schema["estimated_tokens"],
                          "minimal_tokens":schema["estimated_tokens"]},
         "target_tokens":2800,"tasks":rows,"recall_at_7":sum(r["expected_rank"] is not None for r in rows)/len(rows),
         "max_tokens":max(r["total_tokens"] for r in rows)}
def render():
 return json.dumps(build(),ensure_ascii=False,indent=2)+"\n"
def main(argv=None):
 ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
 ap.add_argument("--check",action="store_true",help="書かずに commit 済みと比べる(不一致で exit 1)")
 a=ap.parse_args(argv)
 text=render()
 if a.check:
  old=OUT.read_text(encoding="utf-8") if OUT.exists() else None
  if old!=text:
   print("drift: %s が今の測定と違う(py -3.11 tools/measure_mcp_context.py で書き直す)"%OUT)
   return 1
  print("ok: %s"%OUT)
  return 0
 OUT.write_text(text,encoding="utf-8",newline="\n")
 print(OUT)
 return 0
if __name__=="__main__":
 sys.exit(main())
