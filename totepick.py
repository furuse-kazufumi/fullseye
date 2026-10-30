"""Panda parallel-gripper tote-picking benchmark (physics decides outcomes).

Every attempt advances a genuine Menagerie Franka Panda with ``mj_step``.  The
seven arm joints and the parallel gripper are position controlled; products are
free bodies and are never welded, attached, moved by mocap, or pose-written after
initialisation.  Randomness is limited to initial scenes and sensor noise.

Retail-sized products (all dimensions fit the Panda's 80 mm opening)::

 name             shape       xyz [m]          kg    mu   difficulty
 tea_carton       box         .060,.040,.105   .20  .55  easy
 drink_can        cylinder    .040,.040,.105   .12 1.05  easy
 vitamin_box      box         .048,.032,.085   .12  .50  easy
 spice_jar        cylinder    .045,.045,.080   .16  .38  medium
 shampoo_bottle   cylinder    .065,.065,.135   .50  .34  medium/tall
 refill_pouch     box         .060,.025,.110   .28  .25  hard/slippery
 blister_card     box         .070,.014,.105   .08  .36  hard/thin
 slick_soap       box         .068,.035,.050   .12  .16  hard/slippery
 metal_tin        box         .070,.050,.090  1.50  .42  hard/heavy

Products use ordinary Coulomb contact: ``condim=3``, ``solref=(.02,1)``,
``solimp=(.9,.95,.001)``, and the listed sliding coefficient (torsional .01,
rolling .001).  No extreme friction or adhesion is used.  The Panda model is the
Apache-2.0 MuJoCo Menagerie asset.  Its gripper actuator uses [0,255] (255=open).

The three calibrations inherited from :mod:`bin_pick` are essential: command the
real gripper range, target the measured midpoint of the collision pads rather than
the finger-body origin, and rotate quaternion error into world coordinates in the
6-DoF IK.  ``PandaPlant`` is deliberately separate from perception and tactile
adapters so a five-finger plant or FingerVision reader can replace either later.
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
GRIP_OPEN, GRIP_SHUT = 255.0, 0.0
HOME = np.array([0.0, 0.3, 0.0, -1.57079, 0.0, 2.0, -0.7853])
TABLE_TOP, WALL_H = .13, .055
SRC = np.array([.48, .20]); DST = np.array([.48, -.20])
TOTE_HALF = np.array([.13, .09])


@dataclass(frozen=True)
class Product:
    name: str; shape: str; size_m: tuple[float, float, float]
    mass_kg: float; friction: float; difficulty: str


PRODUCTS = (
    Product("tea_carton", "box", (.060,.040,.105), .20,.55,"easy"),
    Product("drink_can", "cylinder", (.040,.040,.105), .12,1.05,"easy"),
    Product("vitamin_box", "box", (.048,.032,.085), .12,.50,"easy"),
    Product("spice_jar", "cylinder", (.045,.045,.080), .16,.38,"medium"),
    Product("shampoo_bottle", "cylinder", (.065,.065,.135), .50,.34,"medium"),
    Product("refill_pouch", "box", (.060,.025,.110), .28,.25,"hard"),
    Product("blister_card", "box", (.070,.014,.105), .08,.36,"hard"),
    Product("slick_soap", "box", (.068,.035,.050), .12,.16,"hard"),
    Product("metal_tin", "box", (.070,.050,.090), 1.50,.42,"hard"),
)


@dataclass(frozen=True)
class TactileReading:
    normal_n: float; tangential_n: float; relative_speed_m_s: float; slipping: bool


def read_fingertip_tactile(normal_n, tangential_n, friction, noise=(0., 0.), relative_speed_m_s=0.):
    """Replaceable ideal tactile boundary; force inputs come from mj_contactForce."""
    n=max(0.,float(normal_n)+float(noise[0])); t=max(0.,float(tangential_n)+float(noise[1]))
    return TactileReading(n,t,float(relative_speed_m_s),n>.02 and (t/max(n,1e-9)>.82*friction or relative_speed_m_s>.03))


def depth_grasp_candidates(depth: np.ndarray, *, camera_z=.90, fovy_deg=52., wall_mask=None,
                           table_z=TABLE_TOP, wall_top=TABLE_TOP+WALL_H) -> list[dict]:
    """Extract object blobs from renderer depth only and reject tote-wall pixels.

    ``wall_mask`` is geometry known from the tote design, not simulator truth.  The
    height guard also removes blobs whose median height lies at the wall top (within
    8 mm), which catches wall edges left by rasterisation.
    """
    from blob2d import blob_label
    d=np.asarray(depth,float); h,w=d.shape
    z=camera_z-d
    fg=np.isfinite(d)&(z>table_z+.012)
    if wall_mask is not None: fg &= ~np.asarray(wall_mask,bool)
    labels=blob_label(fg.astype(np.uint8),connectivity=8); out=[]
    focal=.5*h/math.tan(math.radians(fovy_deg)/2)
    for lab in range(1,int(labels.max(initial=0))+1):
        yy,xx=np.where(labels==lab)
        if len(xx)<10: continue
        medz=float(np.median(z[yy,xx]))
        if medz > table_z+.20: continue  # robot arm/hand above the merchandise
        if abs(medz-wall_top)<.008: continue
        u=float(xx.mean()); v=float(yy.mean()); dep=float(np.median(d[yy,xx]))
        # camera xyaxes=[0,1,0,-1,0,0]: image right=world +y, down=world +x
        world=(float(SRC[0]+(v-h/2)*dep/focal),float(SRC[1]+(u-w/2)*dep/focal),medz)
        out.append({"pixel":(u,v),"world":world,"area":len(xx),"height_m":medz,
                    "score":float(medz+min(len(xx),1000)/100000.)})
    return sorted(out,key=lambda x:x["score"],reverse=True)


def _menagerie(path=None):
    return Path(path or os.environ.get("MUJOCO_MENAGERIE", r"C:\dev\projects\mujoco_menagerie"))


def _add_tote(spec, mujoco, name, centre):
    cx,cy=centre; t=.006
    spec.worldbody.add_geom(name=name+"_base",type=mujoco.mjtGeom.mjGEOM_BOX,pos=[cx,cy,TABLE_TOP/2],size=[TOTE_HALF[0],TOTE_HALF[1],TABLE_TOP/2],rgba=[.28,.36,.45,1])
    for i,(p,s) in enumerate((((cx,cy+TOTE_HALF[1]),(TOTE_HALF[0]+t,t)),((cx,cy-TOTE_HALF[1]),(TOTE_HALF[0]+t,t)),((cx+TOTE_HALF[0],cy),(t,TOTE_HALF[1])),((cx-TOTE_HALF[0],cy),(t,TOTE_HALF[1])))):
        spec.worldbody.add_geom(name=f"{name}_wall{i}",type=mujoco.mjtGeom.mjGEOM_BOX,pos=[p[0],p[1],TABLE_TOP+WALL_H/2],size=[s[0],s[1],WALL_H/2],rgba=[.5,.55,.62,.45])


def _build_model(product: Product, seed=0, friction_scale=1., mass_scale=1., clutter=True):
    import mujoco
    spec=mujoco.MjSpec.from_file(str(_menagerie()/"franka_emika_panda"/"scene.xml")); spec.option.timestep=.004
    _add_tote(spec,mujoco,"src",SRC); _add_tote(spec,mujoco,"dst",DST)
    rng=np.random.default_rng(seed)
    x=float(SRC[0]+rng.uniform(-.018,.018)); y=float(SRC[1]+rng.uniform(-.020,.020))
    b=spec.worldbody.add_body(name="product",pos=[x,y,TABLE_TOP+product.size_m[2]/2+.002]); b.add_freejoint(name="product_free")
    typ={"box":mujoco.mjtGeom.mjGEOM_BOX,"cylinder":mujoco.mjtGeom.mjGEOM_CYLINDER}[product.shape]
    size=np.array(product.size_m)/2 if product.shape=="box" else [product.size_m[0]/2,product.size_m[2]/2,0]
    b.add_geom(name="product_geom",type=typ,size=size,mass=product.mass_kg*mass_scale,friction=[product.friction*friction_scale,.01,.001],condim=3,solref=SOLREF,solimp=SOLIMP,rgba=[.88,.28,.13,1])
    # Two neighbouring free packages make this a real pile.  They touch the target
    # after settling but are lower, so the depth planner still selects the target.
    if clutter:
        for i,dy in enumerate((-.046,.046)):
            q=spec.worldbody.add_body(name=f"neighbour{i}",pos=[x+.012,y+dy,TABLE_TOP+.027]); q.add_freejoint()
            q.add_geom(name=f"neighbour_geom{i}",type=mujoco.mjtGeom.mjGEOM_BOX,size=[.024,.018,.025],mass=.11,friction=[.48,.01,.001],condim=3,rgba=[.25,.62,.42,1])
    spec.worldbody.add_camera(name="overhead",pos=[SRC[0],SRC[1],.90],xyaxes=[0,1,0,-1,0,0],fovy=52)
    return spec.compile()


def _ik_solve(mujoco,m,dk,hand_id,goal,quat_t,seed,iters=180):
    q=np.asarray(seed,float).copy()
    for _ in range(iters):
        dk.qpos[:7]=q; mujoco.mj_kinematics(m,dk); mujoco.mj_comPos(m,dk)
        pe=np.asarray(goal)-dk.xpos[hand_id]; oe=np.zeros(3); mujoco.mju_subQuat(oe,np.asarray(quat_t),dk.xquat[hand_id]); oe=dk.xmat[hand_id].reshape(3,3)@oe
        if np.linalg.norm(pe)<1e-3 and np.linalg.norm(oe)<1e-2: break
        jp=np.zeros((3,m.nv)); jr=np.zeros((3,m.nv)); mujoco.mj_jacBody(m,dk,jp,jr,hand_id); J=np.vstack([jp[:,:7],jr[:,:7]])
        dq=J.T@np.linalg.solve(J@J.T+.1*np.eye(6),np.r_[pe,oe]); q=np.clip(q+np.clip(dq,-.1,.1),m.jnt_range[:7,0],m.jnt_range[:7,1])
    return q


def _pad_state(mujoco,m,d):
    bids=[mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,n) for n in ("left_finger","right_finger")]
    gids=[i for i in range(m.ngeom) if int(m.geom_bodyid[i]) in bids and i>=0]
    return np.mean([d.geom_xpos[i] for i in gids],axis=0),set(gids)


def _tip_tactile(model,data,product_geom,pad_geoms,noise,friction):
    import mujoco
    normal=tangent=0.; rel=0.
    pb=int(model.geom_bodyid[product_geom])
    for i in range(data.ncon):
        c=data.contact[i]; a,b=int(c.geom1),int(c.geom2)
        if product_geom not in (a,b) or (b if a==product_geom else a) not in pad_geoms: continue
        f=np.zeros(6); mujoco.mj_contactForce(model,data,i,f); normal+=abs(f[0]); tangent+=math.hypot(f[1],f[2])
        other=b if a==product_geom else a; rel=max(rel,float(np.linalg.norm(data.cvel[pb,3:]-data.cvel[int(model.geom_bodyid[other]),3:])))
    return read_fingertip_tactile(normal,tangent,friction,noise,rel)


def _wall_mask(h,w):
    """Known image-space exclusion band for the source tote's four walls."""
    mask=np.zeros((h,w),bool); focal=.5*h/math.tan(math.radians(52.)/2); depth=.90-(TABLE_TOP+WALL_H)
    du=int(round(TOTE_HALF[1]*focal/depth)); dv=int(round(TOTE_HALF[0]*focal/depth)); band=4
    u0,u1=w//2-du,w//2+du; v0,v1=h//2-dv,h//2+dv
    mask[max(0,v0-band):min(h,v0+band+1),max(0,u0-band):min(w,u1+band+1)]=True
    mask[max(0,v1-band):min(h,v1+band+1),max(0,u0-band):min(w,u1+band+1)]=True
    mask[max(0,v0-band):min(h,v1+band+1),max(0,u0-band):min(w,u0+band+1)]=True
    mask[max(0,v0-band):min(h,v1+band+1),max(0,u1-band):min(w,u1+band+1)]=True
    return mask


def _attempt(product,method,seed,retry,*,friction_scale=1.,mass_scale=1.,grip=True,render_depth=True,clutter=True,diagnostics=False):
    """Run approach, close, lift, carry, release; all outcomes use physical state."""
    import mujoco
    rng=np.random.default_rng(seed); m=_build_model(product,seed,friction_scale,mass_scale,clutter); d=mujoco.MjData(m); dk=mujoco.MjData(m)
    d.ctrl[:7]=HOME; d.ctrl[7]=GRIP_OPEN; d.qpos[:7]=HOME
    mujoco.mj_forward(m,d); settle_steps=int(.8/m.opt.timestep)
    for _ in range(settle_steps): mujoco.mj_step(m,d)
    hand=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,"hand"); pad_c,pads=_pad_state(mujoco,m,d); offset=pad_c-d.xpos[hand]; quat=d.xquat[hand].copy()
    candidates=[]
    if render_depth:
        ren=mujoco.Renderer(m,height=180,width=180); ren.enable_depth_rendering(); ren.update_scene(d,camera="overhead"); dep=ren.render().copy(); ren.close()
        candidates=depth_grasp_candidates(dep,wall_mask=_wall_mask(*dep.shape))
    # Fallback is a fixed tote-centre scan pose, never product truth. Retry offsets
    # depend only on the previous failure index and are the method-(c) policy.
    if candidates: gx,gy,_=candidates[0]["world"]
    else: gx,gy=SRC
    if method==METHODS[2] and retry: gx+=(-1 if retry%2 else 1)*.009*((retry+1)//2)
    # bounded camera noise is an initial sensor condition
    gx+=rng.normal(0,.0025); gy+=rng.normal(0,.0025)
    pg=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,"product_geom"); jid=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,"product_free"); qa=int(m.jnt_qposadr[jid]); da=int(m.jnt_dofadr[jid])
    walls={mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_GEOM,f"{s}_wall{i}") for s in ("src","dst") for i in range(4)}
    hand_bodies=set(); root=hand
    for bi in range(m.nbody):
        j=bi
        while j>0 and j!=root: j=int(m.body_parentid[j])
        if j==root: hand_bodies.add(bi)
    def solve(point): return _ik_solve(mujoco,m,dk,hand,np.asarray(point)-offset,quat,d.qpos[:7])
    max_force=0.; lifted=False; lost=False; tactile_events=0; log=[]; ever_contact=False; tactile_boost=False
    def step_to(qtarget,gripcmd,seconds,phase):
        nonlocal max_force,lifted,lost,tactile_events,ever_contact,tactile_boost
        n=max(1,int(seconds/m.opt.timestep)); q0=d.ctrl[:7].copy()
        for k in range(n):
            d.ctrl[:7]=q0+(qtarget-q0)*(k+1)/n; cmd=gripcmd(k,n) if callable(gripcmd) else gripcmd
            if tactile_boost and cmd<GRIP_OPEN: cmd=GRIP_SHUT
            d.ctrl[7]=cmd; mujoco.mj_step(m,d)
            touching=False
            for ci in range(d.ncon):
                c=d.contact[ci]; a,b=int(c.geom1),int(c.geom2); other=b if a==pg else a
                if pg in (a,b) and int(m.geom_bodyid[other]) in hand_bodies: touching=True; ever_contact=True
                if (a in walls and int(m.geom_bodyid[b]) in hand_bodies) or (b in walls and int(m.geom_bodyid[a]) in hand_bodies):
                    f=np.zeros(6); mujoco.mj_contactForce(m,d,ci,f); max_force=max(max_force,abs(float(f[0])))
            tr=_tip_tactile(m,d,pg,pads,tuple(rng.normal(0,.01,2)),product.friction*friction_scale)
            if method!=METHODS[0] and tr.slipping and phase in ("close","lift","carry"):
                tactile_events+=1; tactile_boost=True; d.ctrl[7]=GRIP_SHUT
            z=float(d.qpos[qa+2]); lifted|=z>TABLE_TOP+product.size_m[2]/2+.045
            if lifted and phase in ("lift","carry") and ever_contact and not touching and z<TABLE_TOP+product.size_m[2]/2+.025: lost=True
            if diagnostics and k%25==0: log.append({"time_s":float(d.time),"phase":phase,"product_z":z,"normal_n":tr.normal_n,"tangent_n":tr.tangential_n,"joint_target":d.ctrl[:7].tolist(),"joint_actual":d.qpos[:7].tolist(),"actuator_force":d.actuator_force.tolist(),"pad_position":_pad_state(mujoco,m,d)[0].tolist()})
    zc=TABLE_TOP+product.size_m[2]/2
    hover=(gx,gy,max(.34,zc+.14)); grasp=(gx,gy,zc); lift=(gx,gy,.36); carry=(DST[0],DST[1],.36); lower=(DST[0],DST[1],TABLE_TOP+product.size_m[2]/2+.025)
    step_to(solve(hover),GRIP_OPEN,.8,"approach"); step_to(solve(grasp),GRIP_OPEN,.7,"descend")
    base_shut=30.0
    close=lambda k,n: GRIP_OPEN+(base_shut-GRIP_OPEN)*(k+1)/n if grip else GRIP_OPEN
    step_to(d.ctrl[:7].copy(),close,.45,"close"); step_to(solve(lift),base_shut if grip else GRIP_OPEN,.75,"lift")
    step_to(solve(carry),base_shut if grip else GRIP_OPEN,1.0,"carry"); step_to(solve(lower),base_shut if grip else GRIP_OPEN,.55,"lower")
    step_to(d.ctrl[:7].copy(),GRIP_OPEN,.35,"release"); step_to(d.ctrl[:7].copy(),GRIP_OPEN,.8,"settle")
    pos=np.array(d.qpos[qa:qa+3]); speed=float(np.linalg.norm(d.qvel[da:da+6])); inside=bool(np.all(np.abs(pos[:2]-DST)<TOTE_HALF-[.012,.012]) and TABLE_TOP<pos[2]<TABLE_TOP+.20)
    success=bool(inside and speed<.04 and max_force<140.)
    if success: failure=None
    elif not lifted: failure="grasp_miss"
    elif lost: failure="transport_slip"
    elif max_force>=140: failure="collision"
    elif speed>=.04: failure="timeout"
    else: failure="outside_tote"
    truth={"truth_inside":inside,"truth_speed_m_s":speed,"final_position_m":pos.tolist(),"lifted":lifted,"lost_contact_fall":lost,"max_wall_force_n":max_force,"tactile_events":tactile_events,"depth_candidates":len(candidates),"grasp_world_m":[gx,gy,zc],"pad_offset_m":offset.tolist(),"mj_steps":int(round(d.time/m.opt.timestep)),"diagnostics":log}
    return success,failure,float(d.time),truth


def run_benchmark(n_trials=4,seed=20261030,max_retries=5,**kwargs):
    rows=[]
    for trial in range(n_trials):
        ss=np.random.SeedSequence([seed,trial]); product=PRODUCTS[int(ss.generate_state(1)[0])%len(PRODUCTS)]; scene_seed=int(ss.generate_state(2)[1])
        for method in METHODS:
            attempts=[]
            for retry in range(max_retries+1):
                ok,fail,cycle,truth=_attempt(product,method,scene_seed,retry,**kwargs); attempts.append({"retry":retry,"success":ok,"failure":fail,"cycle_s":cycle,**truth})
                if ok or method!=METHODS[2]: break
            rows.append({"trial":trial,"scene_seed":scene_seed,"product":product.name,"difficulty":product.difficulty,"method":method,"attempts":attempts})
    return {"seed":seed,"n_trials":n_trials,"rows":rows,"products":[asdict(p) for p in PRODUCTS],"contact":{"adhesion":False,"solref":SOLREF,"solimp":SOLIMP,"condim":3},"time_basis":"MuJoCo data.time"}


def wilson(successes,total,confidence=.95):
    if not total:return (float("nan"),float("nan"))
    z=1.959963984540054;p=successes/total;d=1+z*z/total;c=(p+z*z/(2*total))/d;h=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
    return c-h,c+h


def _mcnemar(rows):
    a={r["trial"]:any(x["success"] for x in r["attempts"]) for r in rows if r["method"]==METHODS[0]}; b={r["trial"]:any(x["success"] for x in r["attempts"]) for r in rows if r["method"]==METHODS[1]}
    n01=sum(not a[k] and b[k] for k in a); n10=sum(a[k] and not b[k] for k in a); n=n01+n10
    p=1.0 if n==0 else min(1.,2*sum(math.comb(n,i) for i in range(min(n01,n10)+1))*.5**n)
    return {"b_wins":n01,"a_wins":n10,"exact_two_sided_p":p}


def summarize(result):
    curves={};by_product={};failures={};timing={};delta={}
    for method in METHODS:
        rr=[r for r in result["rows"] if r["method"]==method];curves[method]=[]
        for allowed in range(6):
            s=sum(any(a["success"] for a in r["attempts"][:allowed+1]) for r in rr);curves[method].append({"retries":allowed,"successes":s,"total":len(rr),"rate":s/len(rr) if rr else math.nan,"wilson95":wilson(s,len(rr))})
        by_product[method]={}
        for p in PRODUCTS:
            pr=[r for r in rr if r["product"]==p.name];s=sum(any(a["success"] for a in r["attempts"]) for r in pr);by_product[method][p.name]={"successes":s,"total":len(pr),"rate":s/len(pr) if pr else math.nan}
        failures[method]={f:sum(a["failure"]==f for r in rr for a in r["attempts"]) for f in FAILURES}; ts=[sum(a["cycle_s"] for a in r["attempts"]) for r in rr];timing[method]={"mean_sim_s":float(np.mean(ts)) if ts else math.nan}
    for p in PRODUCTS:
        x=by_product[METHODS[0]][p.name]; y=by_product[METHODS[1]][p.name]; delta[p.name]=y["rate"]-x["rate"] if x["total"] else math.nan
    return {"curves":curves,"by_product":by_product,"failures":failures,"timing":timing,"tactile_delta":delta,"mcnemar_b_minus_a":_mcnemar(result["rows"])}


def validate_mujoco_asset(menagerie=None):
    try:
        import mujoco
        p=_menagerie(menagerie)/"franka_emika_panda"/"scene.xml";m=mujoco.MjModel.from_xml_path(str(p));return {"skipped":False,"path":str(p),"arm_actuators":m.nu-1,"gripper_ctrlrange":m.actuator_ctrlrange[-1].tolist()}
    except Exception as e:return {"skipped":True,"reason":str(e)}


def attempt_source_has_random_outcome():
    tree=ast.parse(Path(__file__).read_text(encoding="utf-8"));fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="_attempt")
    return any(isinstance(n,ast.Compare) and any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr in {"random","uniform"} for x in ast.walk(n)) for n in ast.walk(fn))
