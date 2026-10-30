"""Measure LLM-visible text for a minimal discovery/plan/cards cycle."""
import json, math, os
from types import SimpleNamespace
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from fullseye.mcp.handles import HandleStore
from fullseye.mcp.server import call_tool, handle_tools_list
from fullseye.opsearch import known_sorts

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
if __name__=="__main__":
 out=ROOT/"docs/mcp_context_benchmark.json"
 out.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
 print(out)
