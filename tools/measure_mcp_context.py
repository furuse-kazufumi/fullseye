"""Measure a reproducible minimal-tool discovery/plan/cards cycle for six tasks."""
import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from fullseye.mcp.server import handle_tools_list
from fullseye.opsearch import search_ops,plan,op_cards

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
 schema=handle_tools_list({"profile":"minimal"})
 full_schema=handle_tools_list({"profile":"full"})
 rows=[]
 for query,have,want,expected in TASKS:
  found=search_ops(query,7)
  planned=plan(have,want,goal=query,constraints={"k":7,"max_depth":4})
  # Wall time is diagnostic, not model context.  Counting it makes this generated
  # benchmark drift whenever the decimal representation of elapsed_ms changes.
  planned.get("search",{}).pop("elapsed_ms",None)
  names=planned.get("plans",[{}])[0].get("ops",[])[:5]
  cards=op_cards(names,700) if names else {"cards":[]}
  response_tokens=tokens(found)+tokens(planned)+tokens(cards)
  found_names=[x["name"] for x in found["ops"]]
  rank=found_names.index(expected)+1 if expected in found_names else None
  rows.append({"task":query,"tool_schema_tokens":schema["estimated_tokens"],
               "response_tokens":response_tokens,"total_tokens":schema["estimated_tokens"]+response_tokens,
               "planned":bool(planned.get("ok")),"expected":expected,"expected_rank":rank,"ops":names})
 return {"method":"minimal tools schema + find_ops(limit=7) + plan(k=7 diverse paths) + cards; UTF-8 bytes/4; volatile timing excluded",
         "scope":"Counts discovery through planning/cards only; execution and answer-correctness evaluation are excluded.",
         "tool_profiles":{"full_tokens":full_schema["estimated_tokens"],
                          "minimal_tokens":schema["estimated_tokens"]},
         "target_tokens":4000,"tasks":rows,"recall_at_7":sum(r["expected_rank"] is not None for r in rows)/len(rows),
         "max_tokens":max(r["total_tokens"] for r in rows)}
if __name__=="__main__":
 out=ROOT/"docs/mcp_context_benchmark.json"
 out.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
 print(out)
