//! `fs_apply` の中身 —— 経路の選択・native 経路・ハンドルの受け渡し。
//!
//! ヘッダの契約(`fullseye_abi.h` の GENERIC ENTRY POINT 節)をそのまま写す:
//!   * どの経路で走ったかを**必ず**返す(`FsApplyInfo.route`)。
//!   * パラメータの正本は Python 側。ここは JSON の構文(RFC 8259)と、契約 5 op が
//!     **必ず要る**キーの読み取りだけ(既定値は無いので解決も無い)。
//!   * ハンドルは不透明のまま(R-2)。画素の受け渡しは**コピー**(ゼロコピーは次段)。

use std::os::raw::{c_char, c_int, c_void};

use crate::{
    fs_connection, fs_gauss, fs_measure_all, fs_select_shape, fs_threshold, FsImage, FsObjectSet,
    FsRegion, FsTuple, FS_E_BAD_PARAMS, FS_E_INTERNAL, FS_E_INVALID_ARG, FS_E_TYPE,
    FS_E_UNSUPPORTED, FS_OK,
};

// --- fs_kind_t / route(ヘッダと同じ値) ----------------------------------------
#[allow(dead_code)] // 空のスロットの印。feature off のビルドでは参照されない
pub const FS_KIND_NONE: c_int = 0;
pub const FS_KIND_IMAGE: c_int = 1;
pub const FS_KIND_REGION: c_int = 2;
pub const FS_KIND_OBJECTSET: c_int = 3;
pub const FS_KIND_TUPLE: c_int = 4;

pub const FS_ROUTE_AUTO: c_int = 0;
pub const FS_ROUTE_NATIVE: c_int = 1;
pub const FS_ROUTE_PYTHON: c_int = 2;

/// `fs_handle_t`。
#[repr(C)]
#[derive(Clone, Copy)]
pub struct FsHandle {
    pub kind: c_int,
    pub ptr: *mut c_void,
}

/// `fs_apply_info_t`。
#[repr(C)]
pub struct FsApplyInfo {
    pub route: [c_char; 16],
    pub op: [c_char; 64],
    pub backend: [c_char; 32],
    pub degraded: c_int,
    pub message: [c_char; 512],
}

impl FsApplyInfo {
    pub fn blank() -> Self {
        FsApplyInfo {
            route: [0; 16],
            op: [0; 64],
            backend: [0; 32],
            degraded: 0,
            message: [0; 512],
        }
    }
}

/// NUL 終端で書き込む。溢れるなら UTF-8 の文字境界で切る(壊れた列を渡さない)。
pub fn put_str(buf: &mut [c_char], s: &str) {
    let cap = buf.len().saturating_sub(1);
    let mut n = s.len().min(cap);
    while n > 0 && !s.is_char_boundary(n) {
        n -= 1;
    }
    for (i, b) in s.as_bytes()[..n].iter().enumerate() {
        buf[i] = *b as c_char;
    }
    if !buf.is_empty() {
        buf[n] = 0;
    }
}

/// 状態コードつきの失敗。
pub struct Fail {
    pub code: c_int,
    pub msg: String,
}

pub fn fail(code: c_int, msg: impl Into<String>) -> Fail {
    Fail { code, msg: msg.into() }
}

/// 経路が作った値。呼び手の所有になる(R-5)。
pub enum Value {
    Image(Box<FsImage>),
    Region(Box<FsRegion>),
    ObjectSet(Box<FsObjectSet>),
    Tuple(Box<FsTuple>),
}

impl Value {
    pub fn into_handle(self) -> FsHandle {
        match self {
            Value::Image(b) => FsHandle { kind: FS_KIND_IMAGE, ptr: Box::into_raw(b) as *mut c_void },
            Value::Region(b) => FsHandle { kind: FS_KIND_REGION, ptr: Box::into_raw(b) as *mut c_void },
            Value::ObjectSet(b) => FsHandle { kind: FS_KIND_OBJECTSET, ptr: Box::into_raw(b) as *mut c_void },
            Value::Tuple(b) => FsHandle { kind: FS_KIND_TUPLE, ptr: Box::into_raw(b) as *mut c_void },
        }
    }
}

/// 1 回の apply の結果と来歴。
pub struct Outcome {
    pub values: Vec<Value>,
    pub backend: String,
    pub degraded: bool,
    pub note: String,
}

pub type ApplyResult = Result<Outcome, Fail>;

/// ネイティブ実装がある op(= ヘッダの `@fslib` タグの名前)。
pub const NATIVE_OPS: [&str; 5] = ["gauss", "threshold", "connection", "measure_all", "select_shape"];

pub fn has_native(op: &str) -> bool {
    NATIVE_OPS.contains(&op)
}

// --- params_json ----------------------------------------------------------------

pub type Params = serde_json::Map<String, serde_json::Value>;

/// RFC 8259 の構文検査。serde_json は NaN / Infinity を JSON として受けない。
/// オブジェクト以外は拒む。`5` と `5.0` はここでは区別せず**原文のまま** Python に渡す
/// (Python の json が int / float に分ける)。
pub fn parse_params(json: &str) -> Result<Params, Fail> {
    let v: serde_json::Value = serde_json::from_str(json)
        .map_err(|e| fail(FS_E_BAD_PARAMS, format!("params_json が JSON として読めない: {}", e)))?;
    match v {
        serde_json::Value::Object(m) => Ok(m),
        other => Err(fail(
            FS_E_BAD_PARAMS,
            format!("params_json はオブジェクト({{...}})でなければならない({})", kind_name(&other)),
        )),
    }
}

fn kind_name(v: &serde_json::Value) -> &'static str {
    match v {
        serde_json::Value::Null => "null",
        serde_json::Value::Bool(_) => "bool",
        serde_json::Value::Number(_) => "number",
        serde_json::Value::String(_) => "string",
        serde_json::Value::Array(_) => "array",
        serde_json::Value::Object(_) => "object",
    }
}

fn only_keys(op: &str, p: &Params, allowed: &[&str]) -> Result<(), Fail> {
    for k in p.keys() {
        if !allowed.contains(&k.as_str()) {
            return Err(fail(
                FS_E_BAD_PARAMS,
                format!("op '{}': 知らない引数: ['{}'](許すのは {:?})", op, k, allowed),
            ));
        }
    }
    Ok(())
}

fn num(op: &str, p: &Params, key: &str) -> Result<f64, Fail> {
    match p.get(key) {
        None => Err(fail(FS_E_BAD_PARAMS, format!("op '{}': 必須の引数が無い: {}", op, key))),
        Some(serde_json::Value::Number(n)) => n
            .as_f64()
            .ok_or_else(|| fail(FS_E_BAD_PARAMS, format!("op '{}': {} が数として読めない", op, key))),
        Some(other) => Err(fail(
            FS_E_BAD_PARAMS,
            format!("op '{}': {} は数でなければならない({})", op, key, kind_name(other)),
        )),
    }
}

fn string<'a>(op: &str, p: &'a Params, key: &str) -> Result<&'a str, Fail> {
    match p.get(key) {
        None => Err(fail(FS_E_BAD_PARAMS, format!("op '{}': 必須の引数が無い: {}", op, key))),
        Some(serde_json::Value::String(s)) => Ok(s.as_str()),
        Some(other) => Err(fail(
            FS_E_BAD_PARAMS,
            format!("op '{}': {} は文字列でなければならない({})", op, key, kind_name(other)),
        )),
    }
}

/// 成功時の note(python 経路の message と同じ形: 型つきのパラメータ)。
fn note(p: &Params) -> String {
    if p.is_empty() {
        return "params: (none)".to_string();
    }
    let parts: Vec<String> = p
        .iter()
        .map(|(k, v)| {
            let t = match v {
                serde_json::Value::Number(n) if n.is_f64() => "float",
                serde_json::Value::Number(_) => "int",
                serde_json::Value::String(_) => "str",
                serde_json::Value::Bool(_) => "bool",
                _ => "json",
            };
            format!("{}={}({})", k, v, t)
        })
        .collect();
    format!("params: {}", parts.join(", "))
}

// --- native 経路 ------------------------------------------------------------------

fn one_input(op: &str, inputs: &[FsHandle], kind: c_int, what: &str) -> Result<*mut c_void, Fail> {
    if inputs.len() != 1 {
        return Err(fail(
            FS_E_INVALID_ARG,
            format!("{} は入力ハンドル 1 つを取る({} 個)", op, inputs.len()),
        ));
    }
    let h = inputs[0];
    if h.kind != kind {
        return Err(fail(
            FS_E_TYPE,
            format!("型の不一致: {} は {} を受けるが、ハンドルの kind は {}", op, what, h.kind),
        ));
    }
    if h.ptr.is_null() {
        return Err(fail(FS_E_INVALID_ARG, format!("{}: 入力ハンドルが NULL", op)));
    }
    Ok(h.ptr)
}

fn status_fail(op: &str, st: c_int) -> Fail {
    fail(st, format!("native fs_{} が status {} を返した", op, st))
}

/// 契約 5 op を既存の extern 関数へ振り分ける。出力は Box に戻して `Value` にする。
pub fn native(op: &str, inputs: &[FsHandle], p: &Params) -> ApplyResult {
    let values: Vec<Value> = match op {
        "gauss" => {
            only_keys(op, p, &["sigma"])?;
            let sigma = num(op, p, "sigma")?;
            let img = one_input(op, inputs, FS_KIND_IMAGE, "image")? as *const FsImage;
            let mut out: *mut FsImage = std::ptr::null_mut();
            let st = fs_gauss(img, sigma, &mut out);
            if st != FS_OK {
                return Err(status_fail(op, st));
            }
            vec![Value::Image(unsafe { Box::from_raw(out) })]
        }
        "threshold" => {
            only_keys(op, p, &["lo", "hi"])?;
            let (lo, hi) = (num(op, p, "lo")?, num(op, p, "hi")?);
            let img = one_input(op, inputs, FS_KIND_IMAGE, "image")? as *const FsImage;
            let mut out: *mut FsRegion = std::ptr::null_mut();
            let st = fs_threshold(img, lo, hi, &mut out);
            if st != FS_OK {
                return Err(status_fail(op, st));
            }
            vec![Value::Region(unsafe { Box::from_raw(out) })]
        }
        "connection" => {
            only_keys(op, p, &[])?;
            let reg = one_input(op, inputs, FS_KIND_REGION, "region")? as *const FsRegion;
            let mut out: *mut FsObjectSet = std::ptr::null_mut();
            let st = fs_connection(reg, &mut out);
            if st != FS_OK {
                return Err(status_fail(op, st));
            }
            vec![Value::ObjectSet(unsafe { Box::from_raw(out) })]
        }
        "measure_all" => {
            only_keys(op, p, &[])?;
            let objs = one_input(op, inputs, FS_KIND_OBJECTSET, "objectset")? as *const FsObjectSet;
            let (mut a, mut r, mut c): (*mut FsTuple, *mut FsTuple, *mut FsTuple) =
                (std::ptr::null_mut(), std::ptr::null_mut(), std::ptr::null_mut());
            let st = fs_measure_all(objs, &mut a, &mut r, &mut c);
            if st != FS_OK {
                return Err(status_fail(op, st));
            }
            unsafe {
                vec![
                    Value::Tuple(Box::from_raw(a)),
                    Value::Tuple(Box::from_raw(r)),
                    Value::Tuple(Box::from_raw(c)),
                ]
            }
        }
        "select_shape" => {
            only_keys(op, p, &["feature", "vmin", "vmax"])?;
            let feature = string(op, p, "feature")?;
            let (vmin, vmax) = (num(op, p, "vmin")?, num(op, p, "vmax")?);
            let objs = one_input(op, inputs, FS_KIND_OBJECTSET, "objectset")? as *const FsObjectSet;
            let cfeat = std::ffi::CString::new(feature)
                .map_err(|_| fail(FS_E_BAD_PARAMS, "feature に NUL が含まれる"))?;
            let mut out: *mut FsObjectSet = std::ptr::null_mut();
            let st = fs_select_shape(objs, cfeat.as_ptr(), vmin, vmax, &mut out);
            if st != FS_OK {
                return Err(status_fail(op, st));
            }
            vec![Value::ObjectSet(unsafe { Box::from_raw(out) })]
        }
        _ => {
            return Err(fail(
                FS_E_UNSUPPORTED,
                format!("op '{}' にネイティブ実装は無い(あるのは {:?})", op, NATIVE_OPS),
            ))
        }
    };
    Ok(Outcome { values, backend: "rust".to_string(), degraded: false, note: note(p) })
}

// --- fs_apply の本体 ----------------------------------------------------------------

/// 引数の検査 → 経路の選択 → 実行 → 出力の書き込み。`info` は途中でも埋める。
#[allow(clippy::too_many_arguments)]
pub fn run(
    op: *const c_char,
    inputs: *const FsHandle,
    n_in: c_int,
    params_json: *const c_char,
    route_pref: c_int,
    outputs: *mut FsHandle,
    out_cap: c_int,
    n_out: *mut c_int,
    info: &mut FsApplyInfo,
) -> c_int {
    let r = run_inner(op, inputs, n_in, params_json, route_pref, outputs, out_cap, n_out, info);
    match r {
        Ok(()) => FS_OK,
        Err(f) => {
            put_str(&mut info.message, &f.msg);
            f.code
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn run_inner(
    op: *const c_char,
    inputs: *const FsHandle,
    n_in: c_int,
    params_json: *const c_char,
    route_pref: c_int,
    outputs: *mut FsHandle,
    out_cap: c_int,
    n_out: *mut c_int,
    info: &mut FsApplyInfo,
) -> Result<(), Fail> {
    if op.is_null() || n_out.is_null() {
        return Err(fail(FS_E_INVALID_ARG, "op と n_out は NULL にできない"));
    }
    if n_in < 0 || (n_in > 0 && inputs.is_null()) {
        return Err(fail(FS_E_INVALID_ARG, "inputs が NULL なのに n_in > 0"));
    }
    if out_cap < 0 || (out_cap > 0 && outputs.is_null()) {
        return Err(fail(FS_E_INVALID_ARG, "outputs が NULL なのに out_cap > 0"));
    }
    unsafe { *n_out = 0 };
    let op_s = unsafe { std::ffi::CStr::from_ptr(op) }
        .to_str()
        .map_err(|_| fail(FS_E_INVALID_ARG, "op 名が UTF-8 ではない"))?
        .to_string();
    put_str(&mut info.op, &op_s);
    let params_s: String = if params_json.is_null() {
        "{}".to_string()
    } else {
        unsafe { std::ffi::CStr::from_ptr(params_json) }
            .to_str()
            .map_err(|_| fail(FS_E_BAD_PARAMS, "params_json が UTF-8 ではない"))?
            .to_string()
    };
    let params = parse_params(&params_s)?;
    let ins: &[FsHandle] = if n_in == 0 {
        &[]
    } else {
        unsafe { std::slice::from_raw_parts(inputs, n_in as usize) }
    };

    let use_native = match route_pref {
        FS_ROUTE_AUTO => has_native(&op_s),
        FS_ROUTE_NATIVE => {
            if !has_native(&op_s) {
                return Err(fail(
                    FS_E_UNSUPPORTED,
                    format!("op '{}' にネイティブ実装は無い(あるのは {:?})。route_pref=0 か 2 で python 経路へ", op_s, NATIVE_OPS),
                ));
            }
            true
        }
        FS_ROUTE_PYTHON => false,
        other => {
            return Err(fail(FS_E_INVALID_ARG, format!("route_pref {} は 0 / 1 / 2 のどれか", other)))
        }
    };

    let outcome = if use_native {
        put_str(&mut info.route, "native");
        native(&op_s, ins, &params)?
    } else {
        put_str(&mut info.route, "python");
        crate::embed::apply(&op_s, ins, &params_s)?
    };
    put_str(&mut info.backend, &outcome.backend);
    info.degraded = if outcome.degraded { 1 } else { 0 };
    put_str(&mut info.message, &outcome.note);

    let n = outcome.values.len();
    if n > out_cap as usize {
        unsafe { *n_out = n as c_int }; // 必要な数を教えて、書かずに戻る(fs_region_runs と同じ)
        return Err(fail(
            FS_E_INVALID_ARG,
            format!("outputs の容量 {} では足りない(必要 {})", out_cap, n),
        ));
    }
    for (i, v) in outcome.values.into_iter().enumerate() {
        unsafe { *outputs.add(i) = v.into_handle() };
    }
    unsafe { *n_out = n as c_int };
    if n as c_int as usize != n {
        return Err(fail(FS_E_INTERNAL, "出力数が int を超えた"));
    }
    Ok(())
}
