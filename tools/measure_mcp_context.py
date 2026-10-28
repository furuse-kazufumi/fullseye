"""Measure a reproducible minimal-tool discovery/plan/cards cycle for six tasks."""
import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from fullseye.mcp.server import handle_tools_list
from fullseye.opsearch import search_ops,plan,op_cards

TASKS=[
 ("surface dent from reflected fringes",["image","image"],"normalmap"),
 ("find scratches using polarization","polsweep","image"),
 ("recover projected fringe height","images","depth"),
 ("locate a part for handling","image","match"),
 ("fast structured-light depth","images","depth"),
 ("switch product and detect corners","image","feature"),
]
def tokens(value):
 return math.ceil(len(json.dumps(value,ensure_ascii=False,separators=(",",":")).encode("utf-8"))/4)
def build():
 schema=handle_tools_list({"profile":"minimal"})
 full_schema=handle_tools_list({"profile":"full"})
 rows=[]
 for query,have,want in TASKS:
  found=search_ops(query,3)
  planned=plan(have,want,goal=query,constraints={"k":3,"max_depth":4})
  names=planned.get("plans",[{}])[0].get("ops",[])[:5]
  cards=op_cards(names,700) if names else {"cards":[]}
  response_tokens=tokens(found)+tokens(planned)+tokens(cards)
  rows.append({"task":query,"tool_schema_tokens":schema["estimated_tokens"],
               "response_tokens":response_tokens,"total_tokens":schema["estimated_tokens"]+response_tokens,
               "planned":bool(planned.get("ok")),"ops":names})
 return {"method":"minimal tools schema + find_ops(limit=3) + plan(k=3) + cards; UTF-8 bytes/4",
         "scope":"Counts discovery through planning/cards only; execution and answer-correctness evaluation are excluded.",
         "tool_profiles":{"full_tokens":full_schema["estimated_tokens"],
                          "minimal_tokens":schema["estimated_tokens"]},
         "target_tokens":4000,"tasks":rows,"max_tokens":max(r["total_tokens"] for r in rows)}
if __name__=="__main__":
 out=ROOT/"docs/mcp_context_benchmark.json"
 out.write_text(json.dumps(build(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
 print(out)
