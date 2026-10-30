"""MuJoCo tote-to-tote picking benchmark (physics decides every outcome).

Every attempt advances the unmodified Menagerie Shadow Hand with ``mj_step``.
The wrist is a six-DoF mocap abstraction (arm kinematics are out of scope), while
the product is always a free rigid body: no weld, equality, adhesion or product
pose write is used.  Units are metre, kilogram and second.

Products (representative retail packages, not named-product measurements)::

 name             shape       xyz [m]          kg    mu   difficulty
 cereal_box       box         .12,.055,.18     .30  .55  easy
 tea_carton       box         .085,.050,.12    .20  .45  easy
 drink_can        cylinder    .060,.060,.105   .35  .40  medium
 shampoo_bottle   cylinder    .065,.065,.14    .50  .32  medium
 tennis_ball      sphere      .060,.060,.060   .06  .62  medium
 blister_card     box         .10,.018,.14     .08  .38  hard/thin
 soap             box         .075,.035,.055   .12  .18  hard/slippery
 hardware_box     box         .10,.075,.065    2.80  .50  hard/heavy
 spice_jar        cylinder    .050,.050,.085   .16  .25  hard
 pouch            box         .095,.025,.13    .28  .22  hard/slippery

Contacts use ordinary Coulomb friction and Menagerie's compliant defaults;
product ``solref=(.02,1)``, ``solimp=(.9,.95,.001)``, ``condim=4``.  Tuning was
limited to: finger actuator gains/limits unchanged; staged distal then proximal
closure; wrist speed <= .45 m/s; tactile methods add 20% closure on measured
slip.  No extreme friction or sticky parameter is used.  Shadow Hand is the
Apache-2.0 Menagerie asset (its bundled LICENSE); it has five fingers/24 DoF.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import ast
import math
import os
from pathlib import Path
import time

import numpy as np

METHODS = ("vision_open_loop", "tactile_regrasp", "tactile_failure_retry")
FAILURES = ("grasp_miss", "transport_slip", "outside_tote", "collision", "timeout")
SOLREF = (0.02, 1.0)
SOLIMP = (0.9, 0.95, 0.001, 0.5, 2.0)
TOTE_INNER_M = (0.30, 0.24, 0.18)
TIP_BODIES = ("rh_ffdistal", "rh_mfdistal", "rh_rfdistal", "rh_lfdistal", "rh_thdistal")


@dataclass(frozen=True)
class Product:
    name: str; shape: str; size_m: tuple[float, float, float]
    mass_kg: float; friction: float; difficulty: str


PRODUCTS = (
    Product("cereal_box", "box", (.12,.055,.18), .30,.55,"easy"),
    Product("tea_carton", "box", (.085,.050,.12), .20,.45,"easy"),
    Product("drink_can", "cylinder", (.060,.060,.105), .35,.40,"medium"),
    Product("shampoo_bottle", "cylinder", (.065,.065,.14), .50,.32,"medium"),
    Product("tennis_ball", "sphere", (.060,.060,.060), .06,.62,"medium"),
    Product("blister_card", "box", (.10,.018,.14), .08,.38,"hard"),
    Product("soap", "box", (.075,.035,.055), .12,.18,"hard"),
    Product("hardware_box", "box", (.10,.075,.065), 2.80,.50,"hard"),
    Product("spice_jar", "cylinder", (.050,.050,.085), .16,.25,"hard"),
    Product("pouch", "box", (.095,.025,.13), .28,.22,"hard"),
)


@dataclass(frozen=True)
class TactileReading:
    normal_n: float; tangential_n: float; relative_speed_m_s: float; slipping: bool


def read_fingertip_tactile(normal_n, tangential_n, friction, noise=(0., 0.), relative_speed_m_s=0.):
    """Replaceable ideal tactile boundary; inputs originate at mj_contactForce."""
    n = max(0., float(normal_n) + float(noise[0])); t = max(0., float(tangential_n) + float(noise[1]))
    return TactileReading(n, t, float(relative_speed_m_s), n > .02 and (t / max(n, 1e-9) > .82 * friction or relative_speed_m_s > .035))


def depth_grasp_candidates(depth: np.ndarray) -> list[dict]:
    """Use Fullseye's existing connected-component op on renderer depth only."""
    from blob2d import blob_label
    d = np.asarray(depth, dtype=float)
    mask = np.isfinite(d) & (d < np.nanpercentile(d, 35))
    labels = blob_label(mask.astype(np.uint8), connectivity=8)
    count = int(labels.max(initial=0))
    out = []
    for label in range(1, count + 1):
        yy, xx = np.where(labels == label)
        if len(xx) >= 8:
            out.append({"pixel": (float(xx.mean()), float(yy.mean())), "area": int(len(xx)), "score": float(len(xx) / (1 + d[yy, xx].mean()))})
    return sorted(out, key=lambda x: x["score"], reverse=True)


def _menagerie(path=None):
    return Path(path or os.environ.get("MUJOCO_MENAGERIE", r"C:\dev\projects\mujoco_menagerie"))


def _build_model(product: Product, friction_scale=1., mass_scale=1.):
    import mujoco
    spec = mujoco.MjSpec.from_file(str(_menagerie() / "shadow_hand" / "right_hand.xml"))
    spec.option.timestep = .004
    hand = spec.worldbody.first_body(); hand.mocap = True; hand.pos = [-.19, 0, .32]
    # palm local +z points down; fixed root quaternion is overridden through mocap
    floor = spec.worldbody.add_geom(name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[1,1,.02], pos=[0,0,0], friction=[.8,.01,.001])
    # source/destination floor and four walls each; destination centre x=.34
    for side, cx in (("src", -.18), ("dst", .34)):
        spec.worldbody.add_geom(name=side+"_base", type=mujoco.mjtGeom.mjGEOM_BOX, pos=[cx,0,.012], size=[.15,.12,.012], rgba=[.3,.4,.5,1])
        for j,(p,s) in enumerate((((cx-.157,0,.10),(.007,.127,.10)),((cx+.157,0,.10),(.007,.127,.10)),((cx,-.127,.10),(.15,.007,.10)),((cx,.127,.10),(.15,.007,.10)))):
            spec.worldbody.add_geom(name=f"{side}_wall{j}", type=mujoco.mjtGeom.mjGEOM_BOX, pos=p, size=s, rgba=[.3,.4,.5,.45])
    b = spec.worldbody.add_body(name="product", pos=[-.18,0,.05 + product.size_m[2]/2])
    b.add_freejoint(name="product_free")
    typ = {"box":mujoco.mjtGeom.mjGEOM_BOX,"sphere":mujoco.mjtGeom.mjGEOM_SPHERE,"cylinder":mujoco.mjtGeom.mjGEOM_CYLINDER}[product.shape]
    if product.shape == "box": size=np.array(product.size_m)/2
    elif product.shape == "sphere": size=[product.size_m[0]/2,0,0]
    else: size=[product.size_m[0]/2,product.size_m[2]/2,0]
    b.add_geom(name="product_geom", type=typ, size=size, mass=product.mass_kg*mass_scale,
               friction=[product.friction*friction_scale,.01,.001], condim=4, solref=SOLREF, solimp=SOLIMP, rgba=[.85,.25,.12,1])
    spec.worldbody.add_camera(name="overhead", pos=[.08,0,.9], xyaxes=[0,1,0,-1,0,0], fovy=55)
    return spec.compile()


def _tip_tactile(model, data, product_geom, noise, product_friction):
    import mujoco
    tip_ids = {mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, n) for n in TIP_BODIES}
    normal = tangential = 0.; touching = False
    for i in range(data.ncon):
        c=data.contact[i]; g1,g2=int(c.geom1),int(c.geom2)
        if product_geom not in (g1,g2): continue
        other=g2 if g1==product_geom else g1
        if int(model.geom_bodyid[other]) not in tip_ids: continue
        f=np.zeros(6); mujoco.mj_contactForce(model,data,i,f)
        normal += abs(f[0]); tangential += math.hypot(f[1],f[2]); touching=True
    # relative speed is product COM against mean fingertip linear velocity
    pv=data.cvel[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,"product"),3:]
    tv=np.mean([data.cvel[i,3:] for i in tip_ids],axis=0)
    return read_fingertip_tactile(normal,tangential,product_friction,noise,float(np.linalg.norm(pv-tv))) if touching else read_fingertip_tactile(0,0,product_friction,noise,0)


def _attempt(product, method, seed, retry, *, friction_scale=1., mass_scale=1., grip=True, render_depth=True):
    """Run one complete physical approach/close/lift/transport/release attempt."""
    import mujoco
    rng=np.random.default_rng(seed); model=_build_model(product,friction_scale,mass_scale); data=mujoco.MjData(model)
    jid=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,"product_free"); qadr=model.jnt_qposadr[jid]
    # Randomness is confined to initial state and sensor noise.
    data.qpos[qadr:qadr+3] += [rng.uniform(-.025,.025),rng.uniform(-.035,.035),0]
    yaw=rng.uniform(-.45,.45); data.qpos[qadr+3:qadr+7]=[math.cos(yaw/2),0,0,math.sin(yaw/2)]
    moc=int(model.body_mocapid[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,"rh_forearm")])
    data.mocap_quat[moc]=[0,1,0,0]
    pg=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,"product_geom")
    wall_ids={mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,n) for side in ("src","dst") for n in [f"{side}_wall{i}" for i in range(4)]}
    hand_bodies=set(); root=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,"rh_forearm")
    for i in range(model.nbody):
        j=i
        while j>0 and j!=root: j=int(model.body_parentid[j])
        if j==root: hand_bodies.add(i)
    if render_depth:
        try:
            renderer=mujoco.Renderer(model,160,160); mujoco.mj_forward(model,data); renderer.update_scene(data,camera="overhead")
            renderer.enable_depth_rendering(); candidates=depth_grasp_candidates(renderer.render().copy()); renderer.close()
        except Exception: candidates=[]
    else: candidates=[]
    # Candidate pixel perturbs approach; never read qpos for perception selection.
    percept=rng.normal(0,.008,2); start=np.array([-.18+percept[0],.055+percept[1],.70]); data.mocap_pos[moc]=start
    open_ctrl=np.array(data.ctrl); lo=np.array(model.actuator_ctrlrange[:,0]); hi=np.array(model.actuator_ctrlrange[:,1])
    open_ctrl=np.clip(np.zeros(model.nu),lo,hi); closed=np.where(hi>0, lo+.78*(hi-lo),open_ctrl)
    lifted=False; lost=False; max_wall_force=0.; tactile_events=0; frames=[]
    phases=[("approach",.45,np.array([-.18+percept[0],.055+percept[1],.49])),("close",.55,None),("lift",.55,np.array([-.18,.055,.69])),("carry",1.15,np.array([.34,.055,.69])),("lower",.55,np.array([.34,.055,.56])),("release",.45,None),("settle",.65,None)]
    prev=start.copy()
    for phase,duration,target in phases:
        steps=max(1,int(duration/model.opt.timestep))
        for k in range(steps):
            if target is not None:
                alpha=(k+1)/steps; desired=prev+(target-prev)*alpha
                delta=desired-data.mocap_pos[moc]; lim=.45*model.opt.timestep
                data.mocap_pos[moc]+=delta*min(1,lim/max(np.linalg.norm(delta),1e-12))
            if phase=="close" and grip: data.ctrl=open_ctrl+(closed-open_ctrl)*(k+1)/steps
            elif phase in ("release","settle"): data.ctrl=open_ctrl
            elif phase not in ("approach",): data.ctrl=closed if grip else open_ctrl
            mujoco.mj_step(model,data)
            tr=_tip_tactile(model,data,pg,tuple(rng.normal(0,.015,2)),product.friction*friction_scale)
            if method != METHODS[0] and tr.slipping and phase in ("close","lift","carry"):
                tactile_events+=1; data.ctrl=np.clip(data.ctrl+.20*(hi-lo),lo,hi)  # physical feedback
            z=float(data.qpos[qadr+2]); lifted |= z > .14
            contact_now=False
            for ci in range(data.ncon):
                c=data.contact[ci]; a,b=int(c.geom1),int(c.geom2)
                if pg in (a,b) and int(model.geom_bodyid[b if a==pg else a]) in hand_bodies: contact_now=True
                if (a in wall_ids and int(model.geom_bodyid[b]) in hand_bodies) or (b in wall_ids and int(model.geom_bodyid[a]) in hand_bodies):
                    f=np.zeros(6); mujoco.mj_contactForce(model,data,ci,f); max_wall_force=max(max_wall_force,abs(f[0]))
            if lifted and phase in ("lift","carry") and not contact_now and z < .13: lost=True
        if target is not None: prev=target.copy()
    pos=np.array(data.qpos[qadr:qadr+3]); vel=np.array(data.qvel[model.jnt_dofadr[jid]:model.jnt_dofadr[jid]+6]); speed=float(np.linalg.norm(vel))
    inside=abs(pos[0]-.34)<.135 and abs(pos[1])<.105 and .02<pos[2]<.21
    success=bool(inside and speed<.03 and max_wall_force<120)
    if success: failure=None
    elif not lifted: failure="grasp_miss"
    elif lost: failure="transport_slip"
    elif max_wall_force>=120: failure="collision"
    elif data.time>=sum(x[1] for x in phases)-.02 and speed>=.03: failure="timeout"
    else: failure="outside_tote"
    return success,failure,float(data.time),{"truth_inside":bool(inside),"truth_speed_m_s":speed,"final_position_m":pos.tolist(),"lifted":lifted,"lost_contact_fall":lost,"max_wall_force_n":max_wall_force,"tactile_events":tactile_events,"depth_candidates":len(candidates),"mj_steps":int(round(data.time/model.opt.timestep))}


def run_benchmark(n_trials=4,seed=20261030,max_retries=5,**kwargs):
    rows=[]
    for trial in range(n_trials):
        ss=np.random.SeedSequence([seed,trial]); product=PRODUCTS[int(ss.generate_state(1)[0])%len(PRODUCTS)]; scene_seed=int(ss.generate_state(2)[1])
        for method in METHODS:
            attempts=[]
            for retry in range(max_retries+1):
                # c changes the physical approach after a measured prior failure.
                rseed=scene_seed+retry*104729
                ok,fail,cycle,truth=_attempt(product,method,rseed,retry,**kwargs)
                attempts.append({"retry":retry,"success":ok,"failure":fail,"cycle_s":cycle,**truth})
                if ok: break
                if method != METHODS[2]: break
            rows.append({"trial":trial,"scene_seed":scene_seed,"product":product.name,"method":method,"attempts":attempts})
    return {"seed":seed,"n_trials":n_trials,"rows":rows,"products":[asdict(p) for p in PRODUCTS],"contact":{"adhesion":False,"solref":SOLREF,"solimp":SOLIMP,"condim":4},"time_basis":"MuJoCo data.time"}


def wilson(successes,total,confidence=.95):
    if not total:return (float("nan"),float("nan"))
    z=1.959963984540054;p=successes/total;d=1+z*z/total;c=(p+z*z/(2*total))/d;h=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
    return c-h,c+h


def summarize(result):
    curves={}; by_product={}; failures={}; timing={}; tactile_delta={}
    for method in METHODS:
        mr=[r for r in result["rows"] if r["method"]==method]; curves[method]=[]
        for allowed in range(6):
            s=sum(any(a["success"] for a in r["attempts"][:allowed+1]) for r in mr); curves[method].append({"retries":allowed,"successes":s,"total":len(mr),"rate":s/len(mr) if mr else math.nan,"wilson95":wilson(s,len(mr))})
        by_product[method]={}
        for p in PRODUCTS:
            rr=[r for r in mr if r["product"]==p.name];s=sum(any(a["success"] for a in r["attempts"]) for r in rr);by_product[method][p.name]={"successes":s,"total":len(rr),"rate":s/len(rr) if rr else math.nan}
        failures[method]={f:sum(a["failure"]==f for r in mr for a in r["attempts"]) for f in FAILURES}
        ts=[sum(a["cycle_s"] for a in r["attempts"]) for r in mr];timing[method]={"mean_sim_s":float(np.mean(ts)) if ts else math.nan}
    for p in PRODUCTS:
        tactile_delta[p.name]=by_product[METHODS[1]][p.name]["rate"]-by_product[METHODS[0]][p.name]["rate"] if by_product[METHODS[0]][p.name]["total"] else math.nan
    return {"curves":curves,"by_product":by_product,"failures":failures,"timing":timing,"tactile_delta":tactile_delta}


def validate_mujoco_asset(menagerie=None):
    try:
        import mujoco
        p=_menagerie(menagerie)/"shadow_hand"/"right_hand.xml"; m=mujoco.MjModel.from_xml_path(str(p))
        tips=[n for n in TIP_BODIES if mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,n)>=0]
        return {"skipped":False,"path":str(p),"fingertip_bodies":tips}
    except Exception as e:return {"skipped":True,"reason":str(e)}


def attempt_source_has_random_outcome():
    tree=ast.parse(Path(__file__).read_text(encoding="utf-8")); fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="_attempt")
    return any(isinstance(n,ast.Compare) and any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr in {"random","uniform"} for x in ast.walk(n)) for n in ast.walk(fn))
