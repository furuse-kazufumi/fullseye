"""Measure business-language recipe recall and publish the source inventory."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from fullseye.recipesearch import find_recipes, load_recipe_index

QUERIES=[
 ("remove impulse noise", "Denoise — median"),
 ("count holes in backlit plate", "FA — count holes in a back-lit plate"),
 ("uneven lighting document", "Binarize — document (adaptive)"),
 ("detect bright spots", "Spots — local maxima"),
 ("hairline metal scratch", "FA — scratch on hairline metal"),
 ("weld x-ray pores", "FA — weld porosity (X-ray)"),
]
rows=[]
for query,want in QUERIES:
    got=[r["name"] for r in find_recipes(query,limit=2)]
    rows.append({"query":query,"expected":want,"top_2":got,"hit":want in got})
data={"method":"Business-language queries contain no operator names; hit when the expected existing recipe is in top 2.",
      "recall_at_2":sum(r["hit"] for r in rows)/len(rows),"queries":rows,
      "inventory":load_recipe_index()["inventory"]}
(ROOT/"docs/recipe_retrieval_report.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
