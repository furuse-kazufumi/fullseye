//! `fs_apply` の python 経路 —— CPython を埋め込み、`fullseye.abi_bridge` を呼ぶ。
//!
//! feature `embed` が off のときは、この経路は **FS_E_NO_PYTHON を理由つきで返す**だけ
//! (Python を一切リンクしない。軽い C ABI をそのまま保つ)。
//!
//! 先行調査で決めた作法(memory `project_fullseye_multilang_abi_program` 第 3 期):
//!   * `auto-initialize` は使わず、`PyConfig` を自前で組んで `Py_InitializeFromConfig`
//!     (home を指定できるようにする)。初期化はプロセス寿命で **1 回だけ**
//!     (`Py_FinalizeEx` 後の再初期化は拡張モジュールが壊れうるので、終了処理はしない)。
//!   * ホストが既に CPython なら(ctypes から呼ばれた場合)何も起動せず、その解釈系を使う。
//!   * 非 Python スレッドからは毎回 `Python::attach`。Python オブジェクトを static に
//!     キャッシュしない(`OnceLock` の中で import しない —— deadlock の温床)。
//!   * 実行時に python3XY.dll が要る。**同梱はしない**: 探索順は
//!     `FULLSEYE_PYTHON_HOME` → PEP 514 レジストリ(HKCU / HKLM `Software\Python\PythonCore\
//!     3.XY\InstallPath`)→ 見つからなければ fail-closed。Windows では DLL を `/DELAYLOAD`
//!     しているので(build.rs)、ここで `LoadLibraryW` してから初めて Python API に触れる。
//!   * numpy との受け渡しは **コピー**(bytes)。numpy の crate には依存しない。

use crate::apply::{ApplyResult, Fail, FsHandle};

#[cfg(not(feature = "embed"))]
mod imp {
    use super::*;
    use crate::apply::fail;
    use crate::FS_E_NO_PYTHON;

    pub const WHY: &str =
        "python 経路はこのビルドに入っていない(`cargo build --features embed` で有効になる)";

    pub fn ensure(_home: Option<&str>) -> Result<(), String> {
        Err(WHY.to_string())
    }

    pub fn apply(_op: &str, _inputs: &[FsHandle], _params_json: &str) -> ApplyResult {
        Err(fail(FS_E_NO_PYTHON, WHY))
    }

    pub fn catalog() -> Result<String, Fail> {
        Err(fail(FS_E_NO_PYTHON, WHY))
    }
}

#[cfg(feature = "embed")]
mod imp {
    use super::*;
    use crate::apply::{
        fail, Outcome, Value, FS_KIND_IMAGE, FS_KIND_OBJECTSET, FS_KIND_REGION, FS_KIND_TUPLE,
    };
    use crate::{
        FsImage, FsObjectSet, FsRegion, FsRun, FsTuple, FS_DTYPE_F64, FS_E_NO_PYTHON,
        FS_E_PY_EXCEPTION, FS_E_UNSUPPORTED, FS_ELEM_INT, FS_ELEM_REAL,
    };
    use pyo3::prelude::*;
    use pyo3::types::{PyBytes, PyDict, PyList};
    use std::sync::Mutex;

    /// ビルド時に build.rs が決めた名前(例 "python311.dll")と版("3.11")。
    pub const PYTHON_DLL: &str = env!("FULLSEYE_PYTHON_DLL");
    pub const PYTHON_VERSION: &str = env!("FULLSEYE_PYTHON_VERSION");

    /// プロセスで 1 回だけ決まる状態。`Some(Ok)` = 使える / `Some(Err(理由))` = 使えない。
    static STATE: Mutex<Option<Result<(), String>>> = Mutex::new(None);

    pub fn ensure(home: Option<&str>) -> Result<(), String> {
        let mut g = STATE.lock().unwrap_or_else(|e| e.into_inner());
        if let Some(r) = g.as_ref() {
            return r.clone();
        }
        let r = init(home);
        *g = Some(r.clone());
        r
    }

    // ---- Windows: DLL の所在と PEP 514 ------------------------------------------------
    #[cfg(windows)]
    mod win {
        use std::ffi::OsStr;
        use std::os::windows::ffi::{OsStrExt, OsStringExt};

        #[link(name = "kernel32")]
        extern "system" {
            fn GetModuleHandleW(name: *const u16) -> *mut core::ffi::c_void;
            fn GetModuleHandleExW(flags: u32, addr: *const core::ffi::c_void,
                                  out: *mut *mut core::ffi::c_void) -> i32;
            fn GetModuleFileNameW(module: *mut core::ffi::c_void, buf: *mut u16, len: u32) -> u32;
        }
        #[link(name = "advapi32")]
        extern "system" {
            fn RegOpenKeyExW(root: *mut core::ffi::c_void, sub: *const u16, opts: u32, sam: u32,
                             out: *mut *mut core::ffi::c_void) -> i32;
            fn RegQueryValueExW(key: *mut core::ffi::c_void, name: *const u16, reserved: *mut u32,
                                ty: *mut u32, data: *mut u8, len: *mut u32) -> i32;
            fn RegCloseKey(key: *mut core::ffi::c_void) -> i32;
        }
        const HKCU: usize = 0x8000_0001;
        const HKLM: usize = 0x8000_0002;
        const KEY_READ: u32 = 0x2_0019;
        const KEY_WOW64_64KEY: u32 = 0x0100;

        pub fn wide(s: &str) -> Vec<u16> {
            OsStr::new(s).encode_wide().chain(std::iter::once(0)).collect()
        }

        pub fn module_loaded(name: &str) -> bool {
            !unsafe { GetModuleHandleW(wide(name).as_ptr()) }.is_null()
        }

        fn module_file(h: *mut core::ffi::c_void) -> Option<std::path::PathBuf> {
            let mut buf = vec![0u16; 32768];
            let n = unsafe { GetModuleFileNameW(h, buf.as_mut_ptr(), buf.len() as u32) };
            if n == 0 {
                return None;
            }
            Some(std::path::PathBuf::from(std::ffi::OsString::from_wide(&buf[..n as usize])))
        }

        /// 既にプロセスにロードされている `name` の在りか(そのディレクトリ)。
        pub fn loaded_module_dir(name: &str) -> Option<std::path::PathBuf> {
            let h = unsafe { GetModuleHandleW(wide(name).as_ptr()) };
            if h.is_null() {
                return None;
            }
            module_file(h).and_then(|p| p.parent().map(|d| d.to_path_buf()))
        }

        /// PEP 514: `Software\Python\PythonCore\<ver>\InstallPath` の既定値。HKCU → HKLM。
        pub fn registry_install_path(version: &str) -> Option<String> {
            let sub = wide(&format!("Software\\Python\\PythonCore\\{}\\InstallPath", version));
            for root in [HKCU, HKLM] {
                let mut key: *mut core::ffi::c_void = std::ptr::null_mut();
                let rc = unsafe {
                    RegOpenKeyExW(root as *mut _, sub.as_ptr(), 0, KEY_READ | KEY_WOW64_64KEY, &mut key)
                };
                if rc != 0 {
                    continue;
                }
                let mut ty = 0u32;
                let mut len = 0u32;
                let rc = unsafe {
                    RegQueryValueExW(key, wide("").as_ptr(), std::ptr::null_mut(), &mut ty,
                                     std::ptr::null_mut(), &mut len)
                };
                if rc == 0 && len > 0 {
                    let mut buf = vec![0u8; len as usize];
                    let rc = unsafe {
                        RegQueryValueExW(key, wide("").as_ptr(), std::ptr::null_mut(), &mut ty,
                                         buf.as_mut_ptr(), &mut len)
                    };
                    unsafe { RegCloseKey(key) };
                    if rc == 0 {
                        let u: Vec<u16> = buf
                            .chunks_exact(2)
                            .map(|c| u16::from_le_bytes([c[0], c[1]]))
                            .take_while(|&x| x != 0)
                            .collect();
                        let s = std::ffi::OsString::from_wide(&u).to_string_lossy().to_string();
                        let s = s.trim_end_matches(['\\', '/']).to_string();
                        if !s.is_empty() {
                            return Some(s);
                        }
                    }
                } else {
                    unsafe { RegCloseKey(key) };
                }
            }
            None
        }

        /// この DLL 自身のパス(`FULLSEYE_ROOT` が無いときの checkout 探索に使う)。
        pub fn this_module_path() -> Option<std::path::PathBuf> {
            const FROM_ADDRESS: u32 = 0x4;
            const UNCHANGED_REFCOUNT: u32 = 0x2;
            let mut h: *mut core::ffi::c_void = std::ptr::null_mut();
            let ok = unsafe {
                GetModuleHandleExW(FROM_ADDRESS | UNCHANGED_REFCOUNT,
                                   this_module_path as *const core::ffi::c_void, &mut h)
            };
            if ok == 0 || h.is_null() {
                return None;
            }
            module_file(h)
        }
    }

    /// `PyConfig.home`(標準ライブラリの所在)の探索順:
    /// 引数 → `FULLSEYE_PYTHON_HOME` → PEP 514 レジストリ(Windows)→
    /// 既にプロセスにロードされている python3XY.dll のディレクトリ(Windows。静的 import
    /// なのでここに来た時点で必ずロード済み = 実際にリンクされた runtime そのもの)→
    /// それも無ければ fail-closed。
    fn resolve_home(explicit: Option<&str>) -> Result<Option<String>, String> {
        if let Some(h) = explicit {
            if h.trim().is_empty() {
                return Err("python_home が空文字列".to_string());
            }
            return Ok(Some(h.to_string()));
        }
        if let Ok(h) = std::env::var("FULLSEYE_PYTHON_HOME") {
            if !h.trim().is_empty() {
                return Ok(Some(h));
            }
        }
        #[cfg(windows)]
        {
            if let Some(p) = win::registry_install_path(PYTHON_VERSION) {
                return Ok(Some(p));
            }
            if let Some(d) = win::loaded_module_dir(PYTHON_DLL) {
                return Ok(Some(d.to_string_lossy().to_string()));
            }
            return Err(format!(
                "CPython {} の home が決まらない: FULLSEYE_PYTHON_HOME も、PEP 514 レジストリ \
                 (HKCU/HKLM\\Software\\Python\\PythonCore\\{}\\InstallPath)も、ロード済みの {} も無い。\
                 同梱はしていない(fail-closed)",
                PYTHON_VERSION, PYTHON_VERSION, PYTHON_DLL
            ));
        }
        #[cfg(not(windows))]
        {
            Ok(None) // 共有ライブラリの動的リンクが libpython を解決する。home は Python 任せ
        }
    }

    fn init(explicit_home: Option<&str>) -> Result<(), String> {
        #[cfg(windows)]
        {
            // 別の版の CPython がホストなら(例: py -3.14 の ctypes からこの 3.11 向け DLL を
            // 読んだ)、2 つ目の解釈系を起こさない(fail-closed)。
            for minor in 8..=20 {
                let other = format!("python3{}.dll", minor);
                if other != PYTHON_DLL && win::module_loaded(&other) {
                    return Err(format!(
                        "ホストは {} で動いているが、このライブラリは {} 向けに建ててある \
                         (PYO3_PYTHON を合わせて建て直すこと)",
                        other, PYTHON_DLL
                    ));
                }
            }
        }
        if unsafe { pyo3::ffi::Py_IsInitialized() } == 0 {
            // ホストは Python ではない(C / C# / Lua)。home を決めて起動する。
            let home = resolve_home(explicit_home)?;
            #[cfg(windows)]
            if let Some(h) = home.as_deref() {
                if !std::path::Path::new(h).join(PYTHON_DLL).exists() {
                    return Err(format!("{} が python home {} に無い", PYTHON_DLL, h));
                }
            }
            start_interpreter(home.as_deref())?;
        }
        // 既に初期化済み = ホストが CPython(ctypes / pytest)。何も起動せず、その解釈系を使う。
        Python::attach(|py| make_bridge_importable(py))
    }

    #[cfg(windows)]
    type WChar = u16;
    #[cfg(not(windows))]
    type WChar = i32;

    fn to_wide(s: &str) -> Vec<WChar> {
        #[cfg(windows)]
        {
            win::wide(s)
        }
        #[cfg(not(windows))]
        {
            s.chars().map(|c| c as i32).chain(std::iter::once(0)).collect()
        }
    }

    fn status_text(st: &pyo3::ffi::PyStatus) -> String {
        if st.err_msg.is_null() {
            "(理由なし)".to_string()
        } else {
            unsafe { std::ffi::CStr::from_ptr(st.err_msg) }.to_string_lossy().to_string()
        }
    }

    /// `Py_InitializeFromConfig`。シグナルハンドラは奪わない(ホストのもの)。
    fn start_interpreter(home: Option<&str>) -> Result<(), String> {
        use pyo3::ffi;
        unsafe {
            let mut cfg: ffi::PyConfig = std::mem::zeroed();
            ffi::PyConfig_InitPythonConfig(&mut cfg);
            let p = &mut cfg as *mut ffi::PyConfig;
            (*p).install_signal_handlers = 0;
            (*p).parse_argv = 0;
            if let Some(h) = home {
                let w = to_wide(h);
                let st = ffi::PyConfig_SetString(p, std::ptr::addr_of_mut!((*p).home), w.as_ptr() as *const _);
                if ffi::PyStatus_Exception(st) != 0 {
                    let msg = status_text(&st);
                    ffi::PyConfig_Clear(p);
                    return Err(format!("PyConfig_SetString(home) が失敗: {}", msg));
                }
            }
            let st = ffi::Py_InitializeFromConfig(p);
            ffi::PyConfig_Clear(p);
            if ffi::PyStatus_Exception(st) != 0 {
                return Err(format!("Py_InitializeFromConfig が失敗(home={:?}): {}", home, status_text(&st)));
            }
            // 主スレッドが GIL を握ったままだと他スレッドの attach が永久に待つ。手放す。
            ffi::PyEval_SaveThread();
        }
        Ok(())
    }

    /// `sys.path` の先頭に dir を足し、**既に import 済みの `fullseye` を捨てる**。
    ///
    /// ★2026-09-15 実測: C の見本から起動したとき `FULLSEYE_ROOT` を指しているのに
    ///   `No module named 'fullseye.abi_bridge'` になった。site-packages に **PyPI の
    ///   `fullseye` 0.1.11(wheel、abi_bridge.py は無い)** が入っていて、最初の import で
    ///   そちらが `sys.modules` に載り、後から sys.path を足しても差し替わらなかった。
    ///   名前が同じ別物が先に居るときは、捨ててから入れ直す。
    fn prepend_path(py: Python<'_>, dir: &std::path::Path) -> PyResult<()> {
        let sys = py.import("sys")?;
        sys.getattr("path")?.call_method1("insert", (0, dir.to_string_lossy().to_string()))?;
        let modules = sys.getattr("modules")?;
        let keys: Vec<String> = modules.call_method0("keys")?.extract()?;
        for k in keys {
            if k == "fullseye" || k.starts_with("fullseye.") {
                modules.call_method1("pop", (k, py.None()))?;
            }
        }
        Ok(())
    }

    /// `fullseye.abi_bridge` を import できる状態にする。順に試す:
    /// `FULLSEYE_ROOT`(指定があれば**最初に**入れる)→ そのまま → この DLL の祖先で
    /// `fullseye/abi_bridge.py` を持つ dir(開発 checkout の `rust/fullseye_core/target/...`)。
    fn make_bridge_importable(py: Python<'_>) -> Result<(), String> {
        let mut last = String::new();
        if let Ok(r) = std::env::var("FULLSEYE_ROOT") {
            if let Err(e) = prepend_path(py, std::path::Path::new(&r)) {
                last = e.to_string();
            }
        }
        match py.import("fullseye.abi_bridge") {
            Ok(_) => return Ok(()),
            Err(e) => last = e.to_string(),
        }
        let mut candidates: Vec<std::path::PathBuf> = Vec::new();
        #[cfg(windows)]
        {
            if let Some(p) = win::this_module_path() {
                let mut d = p.parent().map(|x| x.to_path_buf());
                while let Some(dir) = d {
                    if dir.join("fullseye").join("abi_bridge.py").exists() {
                        candidates.push(dir.clone());
                    }
                    d = dir.parent().map(|x| x.to_path_buf());
                }
            }
        }
        for c in candidates {
            if let Err(e) = prepend_path(py, &c) {
                last = e.to_string();
                continue;
            }
            match py.import("fullseye.abi_bridge") {
                Ok(_) => return Ok(()),
                Err(e) => last = e.to_string(),
            }
        }
        // どの `fullseye` が見えていたかを添える(PyPI の wheel が先に居る事故を読めるように)
        let seen = py
            .import("fullseye")
            .ok()
            .and_then(|m| m.getattr("__file__").ok())
            .and_then(|f| f.extract::<String>().ok())
            .unwrap_or_else(|| "(fullseye 自体が無い)".to_string());
        Err(format!(
            "fullseye.abi_bridge を import できない({}; 見えている fullseye = {})。\
             FULLSEYE_ROOT に checkout を指すこと",
            last, seen
        ))
    }

    // ---- ハンドル ↔ 辞書(bytes) ----------------------------------------------------
    fn f64_bytes(v: &[f64]) -> &[u8] {
        unsafe { std::slice::from_raw_parts(v.as_ptr() as *const u8, v.len() * 8) }
    }

    fn runs_bytes(v: &[FsRun]) -> &[u8] {
        unsafe { std::slice::from_raw_parts(v.as_ptr() as *const u8, v.len() * std::mem::size_of::<FsRun>()) }
    }

    fn handle_to_py<'py>(py: Python<'py>, h: &FsHandle) -> Result<Bound<'py, PyDict>, Fail> {
        let d = PyDict::new(py);
        let r: PyResult<()> = (|| {
            match h.kind {
                FS_KIND_IMAGE => {
                    let im = unsafe { &*(h.ptr as *const FsImage) };
                    d.set_item("kind", "image")?;
                    d.set_item("h", im.h)?;
                    d.set_item("w", im.w)?;
                    d.set_item("lo", im.lo)?;
                    d.set_item("hi", im.hi)?;
                    d.set_item("dtype", im.dtype)?;
                    d.set_item("pixels", PyBytes::new(py, f64_bytes(&im.px)))?;
                }
                FS_KIND_REGION => {
                    let rg = unsafe { &*(h.ptr as *const FsRegion) };
                    d.set_item("kind", "region")?;
                    d.set_item("h", rg.h)?;
                    d.set_item("w", rg.w)?;
                    d.set_item("runs", PyBytes::new(py, runs_bytes(&rg.runs)))?;
                }
                FS_KIND_OBJECTSET => {
                    let os = unsafe { &*(h.ptr as *const FsObjectSet) };
                    d.set_item("kind", "objectset")?;
                    let (hh, ww) = os.objs.first().map(|o| (o.h, o.w)).unwrap_or((0, 0));
                    d.set_item("h", hh)?;
                    d.set_item("w", ww)?;
                    let list = PyList::empty(py);
                    for o in &os.objs {
                        list.append(PyBytes::new(py, runs_bytes(&o.runs)))?;
                    }
                    d.set_item("objects", list)?;
                }
                FS_KIND_TUPLE => {
                    let t = unsafe { &*(h.ptr as *const FsTuple) };
                    d.set_item("kind", "tuple")?;
                    d.set_item("values", t.vals.clone())?;
                    d.set_item("elem", t.elem.clone())?;
                }
                _ => {
                    d.set_item("kind", format!("unknown:{}", h.kind))?;
                }
            }
            Ok(())
        })();
        r.map_err(|e| pyfail(&e))?;
        if h.ptr.is_null() && h.kind != crate::apply::FS_KIND_NONE {
            return Err(fail(crate::FS_E_INVALID_ARG, "入力ハンドルが NULL"));
        }
        Ok(d)
    }

    fn pyfail(e: &PyErr) -> Fail {
        fail(FS_E_PY_EXCEPTION, e.to_string())
    }

    fn bytes_of<'a>(item: &'a Bound<'a, PyAny>, key: &str) -> Result<Vec<u8>, Fail> {
        let b = item.get_item(key).map_err(|e| pyfail(&e))?;
        let b = b
            .cast::<PyBytes>()
            .map_err(|_| fail(FS_E_PY_EXCEPTION, format!("bridge の '{}' が bytes ではない", key)))?;
        Ok(b.as_bytes().to_vec())
    }

    fn int_of(item: &Bound<'_, PyAny>, key: &str) -> Result<i64, Fail> {
        item.get_item(key).and_then(|v| v.extract::<i64>()).map_err(|e| pyfail(&e))
    }

    fn f64_of(item: &Bound<'_, PyAny>, key: &str) -> Result<f64, Fail> {
        item.get_item(key).and_then(|v| v.extract::<f64>()).map_err(|e| pyfail(&e))
    }

    fn runs_of(bytes: &[u8]) -> Vec<FsRun> {
        bytes
            .chunks_exact(12)
            .map(|c| FsRun {
                row: i32::from_ne_bytes([c[0], c[1], c[2], c[3]]),
                col_begin: i32::from_ne_bytes([c[4], c[5], c[6], c[7]]),
                col_end: i32::from_ne_bytes([c[8], c[9], c[10], c[11]]),
            })
            .collect()
    }

    fn py_to_value(item: &Bound<'_, PyAny>) -> Result<Value, Fail> {
        let kind: String = item.get_item("kind").and_then(|v| v.extract()).map_err(|e| pyfail(&e))?;
        match kind.as_str() {
            "image" => {
                let (h, w) = (int_of(item, "h")? as i32, int_of(item, "w")? as i32);
                let bytes = bytes_of(item, "pixels")?;
                if bytes.len() != (h as usize) * (w as usize) * 8 {
                    return Err(fail(FS_E_PY_EXCEPTION, "bridge の画素バイト数が h*w*8 と合わない"));
                }
                let px: Vec<f64> = bytes
                    .chunks_exact(8)
                    .map(|c| f64::from_ne_bytes([c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7]]))
                    .collect();
                Ok(Value::Image(Box::new(FsImage {
                    h,
                    w,
                    px,
                    dtype: FS_DTYPE_F64,
                    lo: f64_of(item, "lo")?,
                    hi: f64_of(item, "hi")?,
                })))
            }
            "region" => {
                let (h, w) = (int_of(item, "h")? as i32, int_of(item, "w")? as i32);
                let runs = runs_of(&bytes_of(item, "runs")?);
                Ok(Value::Region(Box::new(FsRegion { runs, h, w })))
            }
            "objectset" => {
                let (h, w) = (int_of(item, "h")? as i32, int_of(item, "w")? as i32);
                let objs_py = item.get_item("objects").map_err(|e| pyfail(&e))?;
                let mut objs = Vec::new();
                for o in objs_py.try_iter().map_err(|e| pyfail(&e))? {
                    let o = o.map_err(|e| pyfail(&e))?;
                    let b = o
                        .cast::<PyBytes>()
                        .map_err(|_| fail(FS_E_PY_EXCEPTION, "objects の要素が bytes ではない"))?;
                    objs.push(FsRegion { runs: runs_of(b.as_bytes()), h, w });
                }
                Ok(Value::ObjectSet(Box::new(FsObjectSet { objs })))
            }
            "tuple" => {
                let vals: Vec<f64> = item.get_item("values").and_then(|v| v.extract()).map_err(|e| pyfail(&e))?;
                let elem: Vec<i32> = item.get_item("elem").and_then(|v| v.extract()).map_err(|e| pyfail(&e))?;
                if elem.iter().any(|&e| e != FS_ELEM_REAL && e != FS_ELEM_INT) {
                    return Err(fail(FS_E_UNSUPPORTED, "文字列要素のタプルはこの実装では運べない"));
                }
                if vals.len() != elem.len() {
                    return Err(fail(FS_E_PY_EXCEPTION, "tuple の values と elem の長さが違う"));
                }
                Ok(Value::Tuple(Box::new(FsTuple { vals, elem })))
            }
            other => Err(fail(FS_E_UNSUPPORTED, format!("bridge が返した kind '{}' は運べない", other))),
        }
    }

    // ---- 公開 -------------------------------------------------------------------------
    pub fn apply(op: &str, inputs: &[FsHandle], params_json: &str) -> ApplyResult {
        ensure(None).map_err(|m| fail(FS_E_NO_PYTHON, m))?;
        Python::attach(|py| -> ApplyResult {
            let bridge = py.import("fullseye.abi_bridge").map_err(|e| pyfail(&e))?;
            let list = PyList::empty(py);
            for h in inputs {
                list.append(handle_to_py(py, h)?).map_err(|e| pyfail(&e))?;
            }
            let res = bridge
                .getattr("apply")
                .and_then(|f| f.call1((op, list, params_json)))
                .map_err(|e| pyfail(&e))?;
            let status = int_of(&res, "status")? as i32;
            let message: String = res.get_item("message").and_then(|v| v.extract()).map_err(|e| pyfail(&e))?;
            if status != crate::FS_OK {
                return Err(fail(status, message));
            }
            let backend: String = res.get_item("backend").and_then(|v| v.extract()).map_err(|e| pyfail(&e))?;
            let degraded: Vec<String> = res.get_item("degraded").and_then(|v| v.extract()).map_err(|e| pyfail(&e))?;
            let mut values = Vec::new();
            let outs = res.get_item("outputs").map_err(|e| pyfail(&e))?;
            for o in outs.try_iter().map_err(|e| pyfail(&e))? {
                values.push(py_to_value(&o.map_err(|e| pyfail(&e))?)?);
            }
            let note = if degraded.is_empty() {
                message
            } else {
                format!("{} | 劣化 {} 件: {}", message, degraded.len(), degraded.join("; "))
            };
            Ok(Outcome { values, backend, degraded: !degraded.is_empty(), note })
        })
    }

    pub fn catalog() -> Result<String, Fail> {
        ensure(None).map_err(|m| fail(FS_E_NO_PYTHON, m))?;
        Python::attach(|py| -> Result<String, Fail> {
            let bridge = py.import("fullseye.abi_bridge").map_err(|e| pyfail(&e))?;
            bridge
                .getattr("catalog_json")
                .and_then(|f| f.call0())
                .and_then(|s| s.extract::<String>())
                .map_err(|e| pyfail(&e))
        })
    }
}

pub use imp::{apply, catalog, ensure};
