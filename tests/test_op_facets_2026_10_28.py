import json
from pathlib import Path

from fullseye import opsearch
from fullseye.mcp.server import TOOLS

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    return json.loads((ROOT / "fullseye/data" / name).read_text(encoding="utf-8"))

def test_graph_is_non_vacuous_and_edges_have_sources():
    g=load("OP_GRAPH.json")
    assert len(g["nodes"]) >= 90 and len(g["edges"]) >= 2500
    missing=[e["op"] for e in g["edges"] if not e.get("source_ref") or not e.get("compute",{}).get("source_ref")]
    assert not missing

def test_family_ops_exist_and_properties_have_sources():
    names={e["op"] for e in load("OP_GRAPH.json")["edges"]}
    fs=load("OP_FAMILIES.json")["families"]
    assert len(fs) >= 7 and sum(len(f["ops"]) for f in fs) >= 17
    bad=[r["op"] for f in fs for r in f["ops"] if r["op"] not in names or not r["membership_source"]]
    assert not bad

def test_backward_solutions_are_forward_edges():
    r=opsearch.required_inputs("depth", max_depth=3, k=5)
    edges={e["op"] for e in load("OP_GRAPH.json")["edges"]}
    assert r["solutions"]
    bad=[s["path"] for s in r["solutions"] if not {x for x in s["path"] if not x.startswith("acquire:")} <= edges]
    assert not bad
    edge_map={e["op"]:e for e in load("OP_GRAPH.json")["edges"]}
    invalid=[]
    for solution in r["solutions"]:
        have=set()
        for name in solution["path"]:
            if name.startswith("acquire:"): have.add(name.split(":",1)[1]); continue
            edge=edge_map[name]
            missing_inputs=[x for x in edge["inputs"] if x!="any" and x not in have]
            if missing_inputs: invalid.append((name,sorted(have)))
            have.add(edge["output"] if edge["output"]!="any" else "depth")
        if "depth" not in have: invalid.append((solution["path"],sorted(have)))
    assert not invalid

def test_unused_knobs_are_not_searchable():
    g=load("OP_GRAPH.json")
    edge=next(e for e in g["edges"] if any(not x.get("used") for x in e.get("parameters",{}).values()))
    r=opsearch.param_space(edge["op"], {})
    bad=[p for p in r["parameters"].values() if not p["used"] and p["search"]]
    assert not bad

def test_new_mcp_surfaces_are_declared():
    retired={"fullseye_plan_chain","fullseye_required_inputs","fullseye_pipeline_shape",
             "fullseye_sort_guide","fullseye_param_space","fullseye_choose_op"}
    assert retired.isdisjoint(TOOLS)
    assert {"fullseye_plan","fullseye_describe","fullseye_choose"} <= set(TOOLS)

def test_shape_pattern_and_sort_queries():
    assert opsearch.pipeline_shape("single","dense_field")["found"]
    assert not opsearch.pattern_skeleton("Pipe-and-Filter","image","region")["found"]
    guide=opsearch.sort_guide()
    assert guide["sorts"] and guide["truncated"]
    assert guide["documented_choose_when"] + guide["undocumented_choose_when"] == guide["total"]

def test_graph_population_vocabulary_and_execution_boundary():
    g=load("OP_GRAPH.json")
    idx=json.loads((ROOT/"docs/OP_INDEX.json").read_text(encoding="utf-8"))
    graph_names={e["op"] for e in g["edges"] if not e.get("population_extension_reason")}
    assert graph_names == {e["name"] for e in idx["ops"]}
    assert g["sort_aliases"]["image2d"] == "image" and g["sort_aliases"]["mask"] == "region"
    assert len({e["op"] for e in g["edges"]}) == len(g["edges"])
    assert any(x["op"]=="gaussians_to_voxel" for x in g["diagnostics"]["duplicate_declarations"])
    core=("threshold","canny","gaussian","median","otsu")
    nonexec=[name for name in core if not next(e for e in g["edges"] if e["op"]==name)["executable"]]
    assert not nonexec

def test_any_is_split_and_unknown_edges_are_not_planned():
    g=load("OP_GRAPH.json")
    assert "any" not in {n["sort"] for n in g["nodes"]}
    invalid_semantics=[e["op"] for e in g["edges"] if e["type_semantics"] not in {"typed","poly","unknown","source"}]
    assert invalid_semantics == []
    unknown={e["op"] for e in g["edges"] if e["type_semantics"]=="unknown"}
    r=opsearch.plan("image","pose",goal="register",constraints={"executable_only":False,"k":20})
    planned={op for p in r.get("plans",[]) for op in p["ops"]}
    assert planned.isdisjoint(unknown)
    invalid_consumption=[e["op"] for e in g["edges"] if e["consumes_input"] != bool(e["inputs"])]
    assert invalid_consumption == []

def test_nary_registry_declarations_are_exact_and_duplicate_is_explained():
    g=load("OP_GRAPH.json"); idx=load("OP_INDEX.json")
    edges={e["op"]:e for e in g["edges"]}
    nary=[r for r in idx["ops"] if r.get("tier")=="nary"]
    assert nary
    mismatches=[r["name"] for r in nary if edges[r["name"]]["inputs"] != r["in_sorts"]]
    assert mismatches == []
    duplicate=next(x for x in g["diagnostics"]["duplicate_declarations"] if x["op"]=="gaussians_to_voxel")
    assert duplicate["exemption"]

def test_bundle_types_are_nodes_and_only_grounded_elementwise_ops_are_lifted():
    g=load("OP_GRAPH.json")
    assert "seq<image>" in {n["sort"] for n in g["nodes"]}
    equivalence={e["op"] for e in g["edges"] if e["category"]=="type_equivalence"}
    assert equivalence == set()
    assert g["sort_aliases"]["images"] == "seq<image>"
    edges={e["op"]:e for e in g["edges"]}
    unsafe=[r["base_op"] for r in g["lifted_map_edges"]
            if edges[r["base_op"]]["bundle_semantics"] != "elementwise"]
    assert unsafe == []
    forbidden=[r["base_op"] for r in g["lifted_map_edges"]
               if r["base_op"].startswith(("aug_","tb_random_")) or r["base_op"] in {"equalize","autocontrast","autolevel"}]
    assert forbidden == []
    assert {r["op"] for r in g["lifted_map_edges"]} <= {e["op"] for e in g["edges"]}

def test_six_business_plans_put_grounded_main_op_in_results():
    tasks=[
      ("turn reflected fringe phase gradients into mirror normals",["image","image"],"normalmap","deflectometry_phase_to_slope"),
      ("map degree of polarization for surface scratches","polsweep","image","polarization_dolp_map"),
      ("measure weld bead height from projected stripes","images","depth","decode_fringe"),
      ("locate each part against its reference patch","image","match","ncc_locate"),
      ("recover a fast depth map on the production line","images","depth","decode_fringe"),
      ("corner landmarks for tracking product pose","image","feature","cv_good_features")]
    results=[(main,opsearch.plan(have,want,constraints={"query":query,"max_depth":3,"k":5,"executable_only":False}))
             for query,have,want,main in tasks]
    failed=[main for main,r in results if not r["ok"] or not r["plans"] or main not in r["plans"][0]["ops"]]
    assert not failed
    assert all(all("dag" in p and p["dag"]["outputs"] for p in r["plans"]) for _,r in results)

def test_hypergraph_plan_is_bounded_and_shared_by_both_directions():
    forward=opsearch.plan("images","depth",goal="fringe projection height",
                          constraints={"max_depth":4,"k":3,"executable_only":False})
    backward=opsearch.plan(None,"depth",direction="backward",goal="fringe projection height",
                           constraints={"max_depth":4,"k":3,"executable_only":False})
    assert forward["ok"] and backward["ok"]
    assert "decode_fringe" in forward["plans"][0]["ops"]
    assert "decode_fringe" in backward["plans"][0]["ops"]
    assert forward["search"]["expanded"] > 0
    capped=opsearch.plan("image","feature",goal="features",constraints={"max_expansions":1})
    assert capped["partial"]["limit_reached"] == "max_expansions"

def test_business_plan_mutation_is_caught(monkeypatch):
    g=load("OP_GRAPH.json"); g["edges"]=[e for e in g["edges"] if e["op"]!="decode_fringe"]
    monkeypatch.setitem(opsearch._CACHE,"json:OP_GRAPH.json",g)
    r=opsearch.plan("images","depth",constraints={"query":"fringe projection height","k":5,"executable_only":False})
    matching_plans=[p for p in r.get("plans",[]) if "decode_fringe" in p["ops"]]
    assert matching_plans == []

def test_three_multi_input_business_dags_execute_through_mcp():
    import numpy as np
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import call_tool
    store=HandleStore(roots=[]); cat=Catalog.load()
    def put(value,sort="image"):
        return store.put(np.asarray(value,float),sort=sort,provenance=[{"synthetic":True}])["handle"]
    diffuse=put(np.full((32,32),.3)); specular_image=np.full((32,32),.1); specular_image[:,16:]=.8
    specular=put(specular_image)
    polar=call_tool("fullseye_pipeline",{"handle":diffuse,"stages":[
        {"op":"polarization_render","inputs":[diffuse,specular],"params":{}},
        {"op":"polarization_dolp_map","inputs":["stage:1"],"params":{}},
        {"op":"threshold","inputs":["stage:2"],"params":{},"a":.5}]},cat,store)
    frames=np.stack([.5+.4*np.cos(2*(2*np.pi*i/4))*np.ones((32,32)) for i in range(4)])
    stack=put(frames,"images")
    fringe=call_tool("fullseye_pipeline",{"handle":stack,"stages":[
        {"op":"decode_fringe","inputs":[stack],"params":{"k":1.0}}]},cat,store)
    phase=put(np.zeros((32,32))); phase_y=put(np.full((32,32),1e-6))
    mirror=call_tool("fullseye_pipeline",{"handle":phase,"stages":[
        {"op":"deflectometry_phase_to_slope","inputs":[phase,phase_y],"params":{}}]},cat,store)
    assert [polar.get("isError"),fringe.get("isError"),mirror.get("isError")] == [False,False,False]
    assert polar["structuredContent"]["out_sort"] == "region"
    assert fringe["structuredContent"]["out_sort"] == "depth"
    assert mirror["structuredContent"]["out_sort"] == "normalmap"
    polar_value=np.asarray(store.get(polar["structuredContent"]["handle"])[1])
    depth_value=np.asarray(store.get(fringe["structuredContent"]["handle"])[1])
    assert 0 < np.count_nonzero(polar_value) < polar_value.size
    expected_height=np.full((32,32),1.6814535479687922)
    assert float(np.sqrt(np.mean((depth_value-expected_height)**2))) < 1e-9

def test_validate_distinguishes_unknown_from_known_non_executable():
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.server import validate_pipeline
    cat=Catalog.load()
    known=validate_pipeline([{"op":"register_cross","inputs":["input","input"],"params":{}}],"image",cat)
    missing=validate_pipeline([{"op":"definitely_missing_op","inputs":["input"],"params":{}}],"image",cat)
    assert known["errors"][0]["reason"] == "not_executable_in_mcp"
    assert missing["errors"][0]["reason"] == "unknown_op"
    assert "definitely_missing_op" not in missing["errors"][0]["candidates"]

def test_family_negative_examples_and_cpu_measurements():
    f=load("OP_FAMILIES.json"); members={x["name"]:{r["op"] for r in x["ops"]} for x in f["families"]}
    assert "thin_lens" not in members["morphology"]
    assert "holdout_threshold" not in members["thresholding"]
    timing=json.loads((ROOT/"docs/ops/families_timing.json").read_text(encoding="utf-8"))
    measured=[r for r in timing["measurements"].values() if r["status"]=="measured"]
    assert measured
    missing_exponents=[r for r in measured if r.get("complexity_exponent") is None]
    assert missing_exponents == []
    quick=timing["measurements"]["quicksort"]
    assert set(quick["complexity_exponents"]) == {"random","nearly_sorted","reverse","duplicates"}
    assert quick["complexity_exponents"]["nearly_sorted"] > 1.2
    stability={n:next(p["value"] for p in timing["measurements"][n]["properties"] if p["name"]=="stable")
               for n in ("quicksort","heapsort","mergesort")}
    assert stability == {"quicksort":False,"heapsort":False,"mergesort":True}
    g=load("OP_GRAPH.json")
    heuristic=[e for e in g["edges"] if e.get("family_candidate") and not e.get("family")]
    assert heuristic
    assert {e["family_candidate_source"] for e in heuristic} == {"heuristic_regex"}

def test_knob_schema_context_edges_and_system_params():
    assert opsearch.param_space("lowpass",{"width":512})["parameters"]["a"]["search"]
    gaussian=opsearch.param_space("gaussian",{})["parameters"]["a"]
    assert gaussian["search"] and gaussian["physical_range"] == [0.3,3.0]
    assert opsearch.param_space("local_std",{"width":512})["parameters"]["a"]["enum"] == [.125,.375,.625,.875]
    one=opsearch.param_space("median",{"width":1,"height":1})
    assert one["parameters"]["a"]["max"] == 0.0
    assert one["parameters"]["a"]["allowed_physical_values"] == []
    system=opsearch.system_params(); params=system["params"]
    assert system["generated_from"] == "fssystem.SYSTEM_PARAMS"
    missing=[name for name,r in params.items() if not r["hide_from_ai"] or "applied_by" not in r]
    assert missing == []

def test_mcp_minimal_profile_is_ten_tools_and_patterns_are_hidden():
    from fullseye.mcp.server import handle_tools_list
    r=handle_tools_list({"profile":"minimal"}); assert len(r["tools"])==10 and r["estimated_tokens"] < 1500
    full=handle_tools_list({"profile":"full"}); assert "fullseye_patterns" not in {x["name"] for x in full["tools"]}

def test_round2_honesty_gates_for_choose_region_paths_and_compact_output(tmp_path):
    import math
    import numpy as np
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.diagnose import stats_of,verdict_of
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import call_tool
    chosen=opsearch.choose(["gaussian","median"],{"device":"cuda"})
    assert not chosen["ok"] and chosen["candidates"] == [] and chosen["missing_measurements"]
    region=np.ones((100,100)); region.flat[:30]=0
    verdict=verdict_of(stats_of(region),op_name="dyn_threshold",out_sort="region")
    assert verdict["verdict"] == "degenerate_region" and verdict["escalate"]
    root=tmp_path/"root"; root.mkdir(); np.save(root/"relative.npy",np.zeros((4,4)))
    store=HandleStore(roots=[str(root)]); loaded=store.load("relative.npy")
    assert loaded["shape"] == [4,4]
    result=call_tool("fullseye_plan",{"have":"image","want":"region","goal":"segment"},Catalog.load(),store)
    assert not result["content"][0]["text"].lstrip().startswith("{")
    cards=opsearch.op_cards(["gaussian"],10000)
    actual=math.ceil(len(json.dumps(cards["cards"],ensure_ascii=False,separators=(",",":")))/4)
    assert cards["used_tokens"] == actual

def test_backward_acquisition_steps_are_unique():
    r=opsearch.required_inputs("normalmap",max_depth=4,k=10)
    duplicates=[]
    for solution in r.get("solutions",[]):
        acquire=[x for x in solution["path"] if x.startswith("acquire:")]
        if len(acquire) != len(set(acquire)): duplicates.append(acquire)
    assert duplicates == []

def test_mcp_execution_is_probe_verified_and_runtime_targets_are_exact(tmp_path):
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import call_tool
    graph=load("OP_GRAPH.json"); edges={e["op"]:e for e in graph["edges"]}
    assert edges["psnr"]["runtime_target"] == {"module":"imgmetrics","callable":"psnr"}
    assert edges["triangulate"]["runtime_target"] == {"module":"twoview","callable":"triangulate"}
    assert edges["lens_file_read"]["not_executable_in_mcp"] == "io_side_effect"
    assert edges["lens_file_write"]["not_executable_in_mcp"] == "io_side_effect"
    verified=[e for e in graph["edges"] if e.get("verified_executable")]
    assert verified
    assert {e.get("verification",{}).get("status") for e in verified} == {"ok"}
    registry_verified=[e for e in verified if e.get("executor",{}).get("kind")=="registry"]
    required_checks={"temporary_cwd","filesystem_unchanged","random_state_unchanged","under_2_seconds"}
    missing_side_effect_checks=[e["op"] for e in registry_verified
                                if not required_checks <= set(e["verification"]["checks"])]
    assert missing_side_effect_checks == []
    registry_failures=[e for e in graph["edges"] if e.get("executor",{}).get("kind")=="registry"
                       and not e.get("verified_executable") and e.get("verification")]
    assert {e["verification"]["status"] for e in registry_failures} == {"failed"}

    from tools.gen_op_facets import VERIFIED_PYTHON
    cited_python={"polarization_render","polarization_dolp_map","decode_fringe",
                  "deflectometry_phase_to_slope"}
    assert VERIFIED_PYTHON == cited_python
    graph_python={e["op"] for e in verified if e.get("executor",{}).get("kind")=="python"}
    assert graph_python == cited_python
    import ops
    collision_names={"fill_holes","lowpass","highpass","local_std","companding_mu_law"}
    collision_targets={name:(edges[name]["runtime_target"]["module"],edges[name]["runtime_target"]["callable"])
                       for name in collision_names}
    registered_targets={name:(ops._BY_NAME[name].fn.__module__,ops._BY_NAME[name].fn.__qualname__)
                        for name in collision_names}
    assert collision_targets == registered_targets
    assert {name:edges[name]["inputs"] for name in collision_names} == {
        "fill_holes":["region"],"lowpass":["image"],"highpass":["image"],
        "local_std":["image"],"companding_mu_law":["image"]}

    outside=tmp_path/"outside.json"
    store=HandleStore(roots=[])
    import numpy as np
    seed=store.put(np.zeros((2,2)),sort="image",provenance=[])["handle"]
    attack=call_tool("fullseye_pipeline",{"stages":[
        {"op":"lens_file_read","inputs":[],"params":{"source":str(outside)}},
        {"op":"lens_file_write","inputs":["stage:1"],"params":{"path":str(outside)}}],
        "handle":seed},Catalog.load(),store)
    assert attack["isError"] is True
    assert "not_executable_in_mcp" in str(attack["structuredContent"])
    assert not outside.exists()

    unlisted=call_tool("fullseye_validate_pipeline",{"start_sort":"image","stages":[
        {"op":"psnr","inputs":["input","input"],"params":{}}]},Catalog.load(),store)
    assert unlisted["structuredContent"]["valid"] is False
    assert unlisted["structuredContent"]["errors"][0]["reason"] == "not_executable_in_mcp"

def test_plan_dag_contract_accepts_have_bindings_reorders_and_rejects_role_aliasing():
    import numpy as np
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import call_tool,validate_pipeline
    cat=Catalog.load(); store=HandleStore(roots=[])
    images=store.put(np.zeros((8,8)),sort="image",provenance=[])["handle"]
    dag={"handle":images,"bindings":{"have:image":images},"outputs":["stage:1"],"stages":[
        {"op":"invert","inputs":["stage:2"],"params":{}},
        {"op":"gaussian","inputs":["have:image"],"params":{}}]}
    result=call_tool("fullseye_pipeline",dag,cat,store)
    assert result.get("isError") is False
    assert [r["stage"] for r in result["structuredContent"]["stages"]] == [2,1]
    assert result["structuredContent"]["out_sort"] == "image"

    attacks=[
      {"outputs":["stage:7"],"stages":[{"op":"gaussian","inputs":["have:image"]}]},
      {"stages":[{"op":"gaussian","inputs":["fullseye://img/0000000000000000"]}]},
      {"stages":[{"op":"gaussian","inputs":["have:image"],"params":{"x":{"ref":"stage:99"}}}]},
      {"stages":[{"op":"polarization_render","inputs":["have:image","have:image"],
                  "allow_reuse":True,"params":{"angles_deg":{"profile":"nope.x"}}}]},
    ]
    rejected=[]
    for attack in attacks:
        try: response=call_tool("fullseye_pipeline",{"handle":images,**attack},cat,store)
        except ValueError: rejected.append(True)
        else: rejected.append(response.get("isError") is True)
    assert rejected == [True,True,True,True]

    try: alias_response=call_tool("fullseye_pipeline",{"handle":images,"bindings":{"have:image":images},"stages":[
        {"op":"deflectometry_phase_to_slope","inputs":["have:image",images],"params":{}}]},cat,store)
    except ValueError: alias_rejected=True
    else: alias_rejected=alias_response.get("isError") is True
    assert alias_rejected

    image=store.put(np.zeros((8,8)),sort="image",provenance=[])["handle"]
    bad=validate_pipeline([{"op":"deflectometry_phase_to_slope",
                           "inputs":["have:image","have:image"],"params":{}}],None,cat,
                          bindings={"have:image":image},store=store)
    assert "distinct_role_reuses_reference" in {e["reason"] for e in bad["errors"]}

def test_parameter_refs_and_non_array_handles_share_the_pipeline_vocabulary():
    import numpy as np
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import validate_pipeline,call_tool
    cat=Catalog.load(); store=HandleStore(roots=[])
    stack=store.put(np.zeros((4,8,8)),sort="images",provenance=[])["handle"]
    ref=store.put(np.zeros((8,8)),sort="image",provenance=[])["handle"]
    checked=validate_pipeline([{"op":"decode_fringe","inputs":["have:images"],
        "params":{"ref_phase":{"ref":"have:image"}}}],None,cat,
        bindings={"have:images":stack,"have:image":ref},store=store)
    assert checked["valid"]
    table=store.put({"score":0.75,"label":"ok"},sort="table",provenance=[])
    inspected=call_tool("fullseye_inspect",{"handle":table["handle"]},cat,store)
    assert inspected["structuredContent"]["value"]["score"] == .75

def test_priority_queue_planner_replays_backward_derivations_forward():
    import random
    graph=load("OP_GRAPH.json")
    wants=sorted({e["output"] for e in graph["edges"] if e.get("verified_executable")
                  and e["output"] not in {"unknown","poly"}})
    random.Random(20261029).shuffle(wants)
    checked=0; failures=[]
    for want in wants[:40]:
        backward=opsearch.plan(None,want,direction="backward",constraints={"k":2,"max_depth":4})
        for candidate in backward.get("plans",[]):
            replay=opsearch.plan(candidate["consumed_have"],want,direction="forward",
                                 constraints={"k":3,"max_depth":4})
            if not replay["ok"]: failures.append((want,candidate["consumed_have"]))
            checked+=1
    assert failures == []
    assert checked >= 10

def test_round3_type_truth_uses_aliases_and_one_parameter_schema():
    graph=load("OP_GRAPH.json")
    assert [e["op"] for e in graph["edges"] if e["type_semantics"]=="poly"] == []
    assert {graph["sort_aliases"][x] for x in ("images","video")} == {"seq<image>"}
    python_edges=[e for e in graph["edges"] if e.get("executor",{}).get("kind")=="python"]
    registry_edges=[e for e in graph["edges"] if e.get("executor",{}).get("kind")=="registry"]
    assert python_edges and registry_edges
    assert [e["op"] for e in python_edges if "parameters" in e or "parameter_schema" not in e] == []
    assert [e["op"] for e in registry_edges if "parameter_schema" in e or "parameters" not in e] == []
    shapes=load("OP_SHAPES.json")
    forms={r["input_form"]:r["input_sort"] for r in shapes["shapes"]}
    assert len({forms[x] for x in ("same_view_bundle","different_views","reference_target","time_series")}) == 3

def test_physical_knob_midpoints_profiles_and_system_param_honesty():
    import numpy as np
    import ops
    from fssystem import save_profile,resolve_profile
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import call_tool,ArgError
    median=opsearch.param_space("median",{"width":32,"height":32})["parameters"]["a"]
    assert [ops._k(a) for a in median["enum"]] == median["physical_values"]
    small=opsearch.param_space("median",{"width":5,"height":5})["parameters"]["a"]
    assert small["allowed_physical_values"] == [3,5] and small["max"] == .5
    save_profile("product_a",{"decode_k":1.0}); save_profile("product_b",{"decode_k":2.0})
    assert resolve_profile("product_b.decode_k") == 2.0
    store=HandleStore(roots=[]); cat=Catalog.load()
    frames=np.stack([.5+.4*np.cos(2*np.pi*i/4)*np.ones((8,8)) for i in range(4)])
    handle=store.put(frames,sort="images",provenance=[])["handle"]
    base={"handle":handle,"bindings":{"have:images":handle},"stages":[
        {"op":"decode_fringe","inputs":["have:images"],"params":{"k":{"profile":"product_a.decode_k"}}}]}
    assert call_tool("fullseye_pipeline",base,cat,store)["isError"] is False
    base["stages"][0]["params"]["k"]={"profile":"product_b.decode_k"}
    assert call_tool("fullseye_pipeline",base,cat,store)["isError"] is False
    base["stages"][0]["params"]["k"]={"profile":"typo.decode_k"}
    try: call_tool("fullseye_pipeline",base,cat,store)
    except ArgError: rejected=True
    else: rejected=False
    assert rejected
    params=opsearch.system_params()["params"]
    unapplied=[r for r in params.values() if not r["applied_by"]]
    assert unapplied and {r["status"] for r in unapplied} == {"declared_not_applied"}
    assert params["border_policy"]["affects_numbers"] and params["numeric_floor"]["affects_numbers"]

def test_minimal_context_six_tasks_stay_under_four_thousand_tokens():
    from fullseye.mcp.catalog import Catalog
    from fullseye.mcp.handles import HandleStore
    from fullseye.mcp.server import call_tool
    found=call_tool("fullseye_find_ops",{"query":"remove noise"},Catalog.load(),HandleStore(roots=[]))
    assert len(found["structuredContent"]["ops"]) <= 3
    report=json.loads((ROOT/"docs/mcp_context_benchmark.json").read_text(encoding="utf-8"))
    assert len(report["tasks"]) == 6 and report["max_tokens"] <= 4000
    assert 16000 in opsearch.system_params()["params"]["mcp_response_budget"]["values"]
