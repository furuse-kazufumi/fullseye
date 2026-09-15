//! `fullseye_abi.h` の契約を Rust で実装したスパイク。
//!
//! **目的は性能ではない。** 同じ仕様を 2 回実装して、結果が食い違う場所を探すこと
//! (repo の決定 = 「先回りして Rust コアを書き始めない」「差分テストで等価性を
//! 証明したものだけ有効」)。ここで実装するのは契約のごく一部:
//!
//!   fs_image_create / fs_image_shape / fs_image_range / fs_image_absolute
//!   fs_threshold / fs_region_area / fs_region_run_count / fs_region_runs
//!   fs_connection / fs_objectset_count / fs_objectset_region
//!   ...と、それぞれの release
//!
//! **Region は run-length で持つ**(契約 R-2 が想定している表現)。Python 側が
//! dense mask なら、ここで差分が出る —— それが探しているもの。
//!
//! 規約(ヘッダの R-1〜R-5):
//!   R-1 すべての関数が fs_status_t を返し、結果は out-param で渡す。黙った代替値は返さない。
//!   R-2 Region の記憶形式は外から見えない(runs でしか取り出せない)。
//!   R-3 画像は自分の値域を持ち、しきい値は 0..1 の相対値としてそこへ写される。
//!   R-4 境界を越えるのはスカラ・型つき配列・不透明ハンドル・状態コードだけ。
//!   R-5 out-param のハンドルは呼び手の所有。対応する release で返す。

use std::os::raw::{c_char, c_double, c_int, c_void};

mod apply;
mod embed;
pub use apply::{FsApplyInfo, FsHandle};

// --- R-1: 状態コード(ヘッダの fs_status と同じ値) -------------------------
//
// ★2026-09-15: ここは長らく `FS_E_ALLOC = 3` / `FS_E_UNSUPPORTED = 4` だった。ヘッダは
//   3 = FS_E_SHAPE / 4 = FS_E_RANGE / 6 = FS_E_UNSUPPORTED と宣言しているので、
//   `fs_image_create` が f64 以外の dtype に返していた 4 は **FS_E_RANGE の番号**だった。
//   差分テストは「非ゼロを返した」までしか見ていなかったので素通り —— 2026-09-14 に
//   `fslib` 側で見つけた「状態コードの取り違え」と同じ型が、こちら側にも在った。
//   `fs_apply` を足すときにヘッダの番号を機械で照合して発覚(tests/test_abi_apply.py)。
pub const FS_OK: c_int = 0;
pub const FS_E_INVALID_ARG: c_int = 1;
pub const FS_E_TYPE: c_int = 2;
pub const FS_E_SHAPE: c_int = 3;
pub const FS_E_RANGE: c_int = 4;
pub const FS_E_NO_BACKEND: c_int = 5;
pub const FS_E_UNSUPPORTED: c_int = 6;
pub const FS_E_OUT_OF_MEMORY: c_int = 7;
pub const FS_E_DEADLINE: c_int = 8;
pub const FS_E_INTERNAL: c_int = 9;
pub const FS_E_NO_PYTHON: c_int = 10;
pub const FS_E_UNKNOWN_OP: c_int = 11;
pub const FS_E_BAD_PARAMS: c_int = 12;
pub const FS_E_PY_EXCEPTION: c_int = 13;

// --- 不透明ハンドルの中身(外からは見えない) ------------------------------
pub struct FsImage {
    h: i32,
    w: i32,
    px: Vec<f64>, // 行優先。画素は f64 に正規化して持つ(このスパイクの範囲)
    dtype: c_int, // ★呼び手が**名乗った** dtype。読み返せる(契約 fs_image_dtype)
    lo: f64,
    hi: f64,
}

// --- R-4: 境界を越える要素型(ヘッダの fs_dtype と同じ値)-------------------
pub const FS_DTYPE_U8: c_int = 1;
pub const FS_DTYPE_U16: c_int = 2;
pub const FS_DTYPE_F32: c_int = 3;
pub const FS_DTYPE_F64: c_int = 4;

#[repr(C)]
#[derive(Clone, Copy)]
pub struct FsRun {
    row: i32,
    col_begin: i32, // 含む
    col_end: i32,   // 含まない
}

pub struct FsRegion {
    runs: Vec<FsRun>, // ★ run-length。dense mask は持たない(R-2)
    h: i32,
    w: i32,
}

pub struct FsObjectSet {
    objs: Vec<FsRegion>,
}

/// 制御値のタプル。ヘッダは「int / real / string が混ざりうる」と言っているので
/// 要素ごとに型を持つ。このスパイクが作るのは real だけ(measure_all の 3 本)。
pub struct FsTuple {
    vals: Vec<f64>,
    elem: Vec<c_int>, // FS_ELEM_*
}

pub const FS_ELEM_INT: c_int = 1;
pub const FS_ELEM_REAL: c_int = 2;
#[allow(dead_code)]
pub const FS_ELEM_STRING: c_int = 3;

// --- 画像 -------------------------------------------------------------------

/// 画素を借りて画像を作る。`pixels` は行優先、`row_stride_bytes` は行の間隔。
///
/// ★2026-09-14: **`dtype` 引数がここに無かった。** ヘッダは 8 引数で宣言しているのに
/// Rust も ctypes 3 箇所も 7 引数で書いており、**C ABI の引数がずれたまま**
/// 差分ファジング 60,000 ケース × 3 シードも変異解析 10/10 も全部通っていた。
/// 見つかったのは **C から `#include` して呼ぶ経路を初めて作ったとき** ——
/// Python / C# / Lua はどれも FFI で宣言を**書き写して**おり、3 つとも同じ写し
/// 間違いをしていたので、**互いに一致していることが検証にならなかった**。
/// (このスパイクは画素を f64 として読む。`dtype` は呼び手の申告として保持し、
///  `fs_image_dtype` で読み返せる —— 契約がそう宣言している。)
#[no_mangle]
pub extern "C" fn fs_image_create(
    pixels: *const c_void,
    height: i32,
    width: i32,
    row_stride_bytes: i64,
    dtype: c_int,
    range_lo: c_double,
    range_hi: c_double,
    out: *mut *mut FsImage,
) -> c_int {
    if pixels.is_null() || out.is_null() || height <= 0 || width <= 0 {
        return FS_E_INVALID_ARG;
    }
    if !(FS_DTYPE_U8..=FS_DTYPE_F64).contains(&dtype) {
        return FS_E_INVALID_ARG; // 宣言された 4 種の外は受けない
    }
    if dtype != FS_DTYPE_F64 {
        // 正直に: このスパイクは f64 の画素しか読まない。黙って誤読しない。
        return FS_E_UNSUPPORTED;
    }
    if !(range_hi > range_lo) {
        return FS_E_INVALID_ARG; // 値域が潰れている画像は受けない(R-3)
    }
    let stride = if row_stride_bytes > 0 {
        row_stride_bytes as usize
    } else {
        (width as usize) * std::mem::size_of::<f64>()
    };
    let mut px = Vec::with_capacity((height as usize) * (width as usize));
    unsafe {
        let base = pixels as *const u8;
        for r in 0..height as usize {
            let row = base.add(r * stride) as *const f64;
            for c in 0..width as usize {
                px.push(*row.add(c));
            }
        }
        *out = Box::into_raw(Box::new(FsImage {
            h: height,
            w: width,
            px,
            dtype,
            lo: range_lo,
            hi: range_hi,
        }));
    }
    FS_OK
}

/// 呼び手が名乗った dtype を読み返す(契約 `fs_image_dtype`)。
#[no_mangle]
pub extern "C" fn fs_image_dtype(img: *const FsImage, out: *mut c_int) -> c_int {
    if img.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    unsafe { *out = (*img).dtype };
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_image_shape(img: *const FsImage, height: *mut i32, width: *mut i32) -> c_int {
    if img.is_null() || height.is_null() || width.is_null() {
        return FS_E_INVALID_ARG;
    }
    unsafe {
        *height = (*img).h;
        *width = (*img).w;
    }
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_image_range(img: *const FsImage, lo: *mut c_double, hi: *mut c_double) -> c_int {
    if img.is_null() || lo.is_null() || hi.is_null() {
        return FS_E_INVALID_ARG;
    }
    unsafe {
        *lo = (*img).lo;
        *hi = (*img).hi;
    }
    FS_OK
}

/// R-3: 0..1 の相対値をこの画像の値域へ写す。
#[no_mangle]
pub extern "C" fn fs_image_absolute(
    img: *const FsImage,
    relative: c_double,
    out: *mut c_double,
) -> c_int {
    if img.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    if !relative.is_finite() {
        return FS_E_INVALID_ARG;
    }
    unsafe {
        *out = (*img).lo + relative * ((*img).hi - (*img).lo);
    }
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_image_release(img: *mut FsImage) {
    if !img.is_null() {
        unsafe { drop(Box::from_raw(img)) };
    }
}

// --- 演算子 -----------------------------------------------------------------

/// `@fslib threshold` —— lo/hi は **相対値(0..1)**。画像の値域を通して解決する。
///
/// ★仕様で決めきれていない点(差分が出るならここ): 境界は閉区間か半開区間か。
/// ここでは **両端を含む**(lo <= v <= hi)。ヘッダは「relative」としか書いていない。
#[no_mangle]
pub extern "C" fn fs_threshold(
    img: *const FsImage,
    lo: c_double,
    hi: c_double,
    out: *mut *mut FsRegion,
) -> c_int {
    if img.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    if !lo.is_finite() || !hi.is_finite() || hi < lo {
        return FS_E_INVALID_ARG;
    }
    let im = unsafe { &*img };
    let alo = im.lo + lo * (im.hi - im.lo);
    let ahi = im.lo + hi * (im.hi - im.lo);
    let mut runs: Vec<FsRun> = Vec::new();
    for r in 0..im.h as usize {
        let mut c = 0usize;
        let w = im.w as usize;
        while c < w {
            let v = im.px[r * w + c];
            if v >= alo && v <= ahi {
                let begin = c;
                while c < w {
                    let v2 = im.px[r * w + c];
                    if !(v2 >= alo && v2 <= ahi) {
                        break;
                    }
                    c += 1;
                }
                runs.push(FsRun {
                    row: r as i32,
                    col_begin: begin as i32,
                    col_end: c as i32,
                });
            } else {
                c += 1;
            }
        }
    }
    unsafe {
        *out = Box::into_raw(Box::new(FsRegion {
            runs,
            h: im.h,
            w: im.w,
        }));
    }
    FS_OK
}

// --- 領域 -------------------------------------------------------------------

#[no_mangle]
pub extern "C" fn fs_region_area(reg: *const FsRegion, out: *mut i64) -> c_int {
    if reg.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    let r = unsafe { &*reg };
    let a: i64 = r
        .runs
        .iter()
        .map(|x| (x.col_end - x.col_begin) as i64)
        .sum();
    unsafe { *out = a };
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_region_run_count(reg: *const FsRegion, out: *mut i64) -> c_int {
    if reg.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    unsafe { *out = (*reg).runs.len() as i64 };
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_region_runs(
    reg: *const FsRegion,
    buf: *mut FsRun,
    buf_len: i64,
    written: *mut i64,
) -> c_int {
    if reg.is_null() || written.is_null() {
        return FS_E_INVALID_ARG;
    }
    let r = unsafe { &*reg };
    let n = r.runs.len() as i64;
    if buf.is_null() || buf_len < n {
        unsafe { *written = n }; // 必要な長さを教えて、書かずに戻る
        return FS_E_INVALID_ARG;
    }
    unsafe {
        std::ptr::copy_nonoverlapping(r.runs.as_ptr(), buf, r.runs.len());
        *written = n;
    }
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_region_release(reg: *mut FsRegion) {
    if !reg.is_null() {
        unsafe { drop(Box::from_raw(reg)) };
    }
}

// --- 連結成分 ---------------------------------------------------------------

/// `@fslib connection` —— run どうしの隣接で連結成分に分ける。
///
/// ★仕様で決めきれていない点: **4 連結か 8 連結か**。ヘッダは何も言っていない。
/// ここでは **8 連結**(斜めもつながる)。Python 側が 4 連結なら差分が出る ——
/// それがこのスパイクで探しているもの。
#[no_mangle]
pub extern "C" fn fs_connection(reg: *const FsRegion, out: *mut *mut FsObjectSet) -> c_int {
    if reg.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    let r = unsafe { &*reg };
    let n = r.runs.len();
    let mut parent: Vec<usize> = (0..n).collect();

    fn find(p: &mut Vec<usize>, mut x: usize) -> usize {
        while p[x] != x {
            p[x] = p[p[x]];
            x = p[x];
        }
        x
    }

    for i in 0..n {
        for j in (i + 1)..n {
            let a = r.runs[i];
            let b = r.runs[j];
            if (a.row - b.row).abs() != 1 {
                continue;
            }
            // 8 連結: 列の区間が 1 画素ぶん広げて重なれば隣接
            let overlap = a.col_begin < b.col_end + 1 && b.col_begin < a.col_end + 1;
            if overlap {
                let (ra, rb) = (find(&mut parent, i), find(&mut parent, j));
                if ra != rb {
                    parent[ra] = rb;
                }
            }
        }
    }
    // 同じ根の run をまとめる
    let mut groups: std::collections::HashMap<usize, Vec<FsRun>> = std::collections::HashMap::new();
    for i in 0..n {
        let root = find(&mut parent, i);
        groups.entry(root).or_default().push(r.runs[i]);
    }
    let mut objs: Vec<FsRegion> = groups
        .into_values()
        .map(|runs| FsRegion {
            runs,
            h: r.h,
            w: r.w,
        })
        .collect();
    // 並びを決める(実装依存にしない): 最初の run の (row, col) 順
    objs.sort_by_key(|o| {
        let f = o.runs.iter().min_by_key(|x| (x.row, x.col_begin)).unwrap();
        (f.row, f.col_begin)
    });
    unsafe { *out = Box::into_raw(Box::new(FsObjectSet { objs })) };
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_objectset_count(objs: *const FsObjectSet, out: *mut i64) -> c_int {
    if objs.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    unsafe { *out = (*objs).objs.len() as i64 };
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_objectset_region(
    objs: *const FsObjectSet,
    index: i64,
    out: *mut *mut FsRegion,
) -> c_int {
    if objs.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    let s = unsafe { &*objs };
    if index < 0 || index as usize >= s.objs.len() {
        return FS_E_INVALID_ARG;
    }
    let src = &s.objs[index as usize];
    unsafe {
        *out = Box::into_raw(Box::new(FsRegion {
            runs: src.runs.clone(),
            h: src.h,
            w: src.w,
        }))
    };
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_objectset_release(objs: *mut FsObjectSet) {
    if !objs.is_null() {
        unsafe { drop(Box::from_raw(objs)) };
    }
}

// --- タプル(制御値) --------------------------------------------------------

#[no_mangle]
pub extern "C" fn fs_tuple_length(t: *const FsTuple, out: *mut i64) -> c_int {
    if t.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    unsafe { *out = (*t).vals.len() as i64 };
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_tuple_elem_type(t: *const FsTuple, i: i64, out: *mut c_int) -> c_int {
    if t.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    let tp = unsafe { &*t };
    if i < 0 || i as usize >= tp.elem.len() {
        return FS_E_INVALID_ARG;
    }
    unsafe { *out = tp.elem[i as usize] };
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_tuple_get_real(t: *const FsTuple, i: i64, out: *mut c_double) -> c_int {
    if t.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    let tp = unsafe { &*t };
    if i < 0 || i as usize >= tp.vals.len() {
        return FS_E_INVALID_ARG;
    }
    unsafe { *out = tp.vals[i as usize] };
    FS_OK
}

/// ★契約が黙っている点: **real の要素を int として引けるか**。
/// ここでは **引けない**(`FS_E_TYPE`)。種別は型が運ぶのであって、呼び手の
/// 期待で決まるものではない —— `fslib` の `_require` と同じ立場を取った。
#[no_mangle]
pub extern "C" fn fs_tuple_get_int(t: *const FsTuple, i: i64, out: *mut i64) -> c_int {
    if t.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    let tp = unsafe { &*t };
    if i < 0 || i as usize >= tp.vals.len() {
        return FS_E_INVALID_ARG;
    }
    if tp.elem[i as usize] != FS_ELEM_INT {
        return FS_E_TYPE;
    }
    unsafe { *out = tp.vals[i as usize] as i64 };
    FS_OK
}

#[no_mangle]
pub extern "C" fn fs_tuple_release(t: *mut FsTuple) {
    if !t.is_null() {
        unsafe { drop(Box::from_raw(t)) };
    }
}

fn real_tuple(vals: Vec<f64>) -> *mut FsTuple {
    let n = vals.len();
    Box::into_raw(Box::new(FsTuple {
        vals,
        elem: vec![FS_ELEM_REAL; n],
    }))
}

// --- gauss ------------------------------------------------------------------

/// scipy の `gaussian_filter1d` と同じ半径の取り方: `lw = int(truncate*sigma + 0.5)`、
/// truncate は既定の 4.0。**ヘッダは半径も端の扱いも決めていない** —— だからここは
/// 「片方の実装がたまたま選んだ値」であり、差が出たらそれは仕様の穴の場所。
fn gauss_kernel(sigma: f64) -> Vec<f64> {
    let lw = (4.0 * sigma + 0.5) as i64;
    let s2 = sigma * sigma;
    let mut w: Vec<f64> = (-lw..=lw)
        .map(|x| (-0.5 * (x as f64) * (x as f64) / s2).exp())
        .collect();
    let s: f64 = w.iter().sum();
    for v in w.iter_mut() {
        *v /= s;
    }
    w
}

/// scipy の `mode='reflect'` = `(d c b a | a b c d)`。境界の**上**で折り返す。
///
/// ★ OpenCV の既定は `BORDER_REFLECT_101` = `(d c b | a b c d)` で、折り返しの
/// 軸が半画素ずれる。同じ「reflect」という語で別物を指すので、端の画素だけ
/// 静かに違う —— 内部だけ見る検査では絶対に出ない種類の食い違い。
fn reflect(mut i: i64, n: i64) -> usize {
    let n2 = 2 * n;
    loop {
        if i < 0 {
            i = -i - 1;
        } else if i >= n {
            i = n2 - i - 1;
        } else {
            return i as usize;
        }
    }
}

/// `@fslib gauss` —— 分離可能な 1 次元たたみ込みを行 → 列の順に適用する。
///
/// ★契約が黙っている点: `sigma <= 0`。ここでは **無効引数**として拒む
/// (`threshold` の `lo > hi` と同じ立場 —— R-1 は「失敗」と「何も無い」を分ける)。
#[no_mangle]
pub extern "C" fn fs_gauss(img: *const FsImage, sigma: c_double, out: *mut *mut FsImage) -> c_int {
    if img.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    if !sigma.is_finite() || sigma <= 0.0 {
        return FS_E_INVALID_ARG;
    }
    let im = unsafe { &*img };
    let (h, w) = (im.h as i64, im.w as i64);
    let k = gauss_kernel(sigma);
    let lw = (k.len() as i64 - 1) / 2;

    // 行方向(列インデックスに沿って)
    let mut tmp = vec![0.0f64; (h * w) as usize];
    for r in 0..h {
        for c in 0..w {
            let mut acc = 0.0;
            for (t, kv) in k.iter().enumerate() {
                let cc = reflect(c + t as i64 - lw, w) as i64;
                acc += kv * im.px[(r * w + cc) as usize];
            }
            tmp[(r * w + c) as usize] = acc;
        }
    }
    // 列方向(行インデックスに沿って)
    let mut px = vec![0.0f64; (h * w) as usize];
    for r in 0..h {
        for c in 0..w {
            let mut acc = 0.0;
            for (t, kv) in k.iter().enumerate() {
                let rr = reflect(r + t as i64 - lw, h) as i64;
                acc += kv * tmp[(rr * w + c) as usize];
            }
            px[(r * w + c) as usize] = acc;
        }
    }
    unsafe {
        *out = Box::into_raw(Box::new(FsImage {
            h: im.h,
            w: im.w,
            px,
            dtype: im.dtype,
            lo: im.lo,
            hi: im.hi,
        }))
    };
    FS_OK
}

// --- measure_all ------------------------------------------------------------

/// `@fslib measure_all` —— 生きている物体を 1 度で測る。`row` / `column` は
/// 画素インデックスの重心(画素の中心が整数)。
#[no_mangle]
pub extern "C" fn fs_measure_all(
    objs: *const FsObjectSet,
    area: *mut *mut FsTuple,
    row: *mut *mut FsTuple,
    column: *mut *mut FsTuple,
) -> c_int {
    if objs.is_null() || area.is_null() || row.is_null() || column.is_null() {
        return FS_E_INVALID_ARG;
    }
    let s = unsafe { &*objs };
    let (mut a, mut rr, mut cc) = (Vec::new(), Vec::new(), Vec::new());
    for o in &s.objs {
        let mut n = 0.0f64;
        let (mut sr, mut sc) = (0.0f64, 0.0f64);
        for run in &o.runs {
            let len = (run.col_end - run.col_begin) as f64;
            n += len;
            sr += (run.row as f64) * len;
            // cb..ce-1 の総和 = (cb + ce - 1) * len / 2
            sc += ((run.col_begin + run.col_end - 1) as f64) * len / 2.0;
        }
        a.push(n);
        // 面積 0 の物体は `connection` からは出ない。出たなら重心は決められない。
        rr.push(if n > 0.0 { sr / n } else { 0.0 });
        cc.push(if n > 0.0 { sc / n } else { 0.0 });
    }
    unsafe {
        *area = real_tuple(a);
        *row = real_tuple(rr);
        *column = real_tuple(cc);
    }
    FS_OK
}

// --- select_shape -----------------------------------------------------------

/// `@fslib select_shape` —— 測った特徴で絞る。区間は **両端を含む**
/// (`threshold` と揃える)。並びは入力の並びを保つ。
///
/// ★契約が黙っている点 2 つ:
///   1. 知らない `feature` —— ここでは `FS_E_INVALID_ARG`。
///   2. `vmin > vmax` —— ここでは `FS_E_INVALID_ARG`。ヘッダが `threshold` について
///      「逆さの区間は呼び手の間違いであって、空を寄こせという指定ではない」と
///      書いた以上、**同じ理屈は select_shape にも効くはず**。効いていないなら
///      直すのは実装ではなくヘッダのほう。
#[no_mangle]
pub extern "C" fn fs_select_shape(
    objs: *const FsObjectSet,
    feature: *const c_char,
    vmin: c_double,
    vmax: c_double,
    out: *mut *mut FsObjectSet,
) -> c_int {
    if objs.is_null() || feature.is_null() || out.is_null() {
        return FS_E_INVALID_ARG;
    }
    if !vmin.is_finite() || !vmax.is_finite() || vmax < vmin {
        return FS_E_INVALID_ARG;
    }
    let name = match unsafe { std::ffi::CStr::from_ptr(feature) }.to_str() {
        Ok(s) => s,
        Err(_) => return FS_E_INVALID_ARG,
    };
    let s = unsafe { &*objs };
    let (mut ta, mut tr, mut tc) = (
        std::ptr::null_mut(),
        std::ptr::null_mut(),
        std::ptr::null_mut(),
    );
    let st = fs_measure_all(objs, &mut ta, &mut tr, &mut tc);
    if st != FS_OK {
        return st;
    }
    let pick: &Vec<f64> = unsafe {
        match name {
            "area" => &(*ta).vals,
            "row" => &(*tr).vals,
            "column" => &(*tc).vals,
            _ => {
                fs_tuple_release(ta);
                fs_tuple_release(tr);
                fs_tuple_release(tc);
                return FS_E_INVALID_ARG;
            }
        }
    };
    let kept: Vec<FsRegion> = s
        .objs
        .iter()
        .zip(pick.iter())
        .filter(|(_, v)| **v >= vmin && **v <= vmax)
        .map(|(o, _)| FsRegion {
            runs: o.runs.clone(),
            h: o.h,
            w: o.w,
        })
        .collect();
    fs_tuple_release(ta);
    fs_tuple_release(tr);
    fs_tuple_release(tc);
    unsafe { *out = Box::into_raw(Box::new(FsObjectSet { objs: kept })) };
    FS_OK
}

// --- 契約の外(テスト専用) --------------------------------------------------

/// ★これは **`fullseye_abi.h` の一部ではない**。
///
/// ヘッダには **画素を読み返す関数が無い**(`fs_image_shape` / `_dtype` / `_range` /
/// `_absolute` / `_domain` / `_reduce_domain` / `_release` だけ)。つまり
/// `fs_gauss` の出力は、契約の中では `fs_threshold` を通してしか観測できない。
/// 差分テストで画素そのものを突き合わせるために置いた抜け道であり、
/// **契約に足すべきかどうかは別に決めること**(ここで足すと仕様になってしまう)。
#[no_mangle]
pub extern "C" fn fs_debug_copy_pixels(img: *const FsImage, buf: *mut c_double, buf_len: i64) -> c_int {
    if img.is_null() || buf.is_null() {
        return FS_E_INVALID_ARG;
    }
    let im = unsafe { &*img };
    if buf_len < im.px.len() as i64 {
        return FS_E_INVALID_ARG;
    }
    unsafe { std::ptr::copy_nonoverlapping(im.px.as_ptr(), buf, im.px.len()) };
    FS_OK
}

/// ABI の版(ヘッダの FULLSEYE_ABI_VERSION_*)。呼び手が食い違いを検出できるように。
#[no_mangle]
pub extern "C" fn fs_abi_version(major: *mut i32, minor: *mut i32) -> c_int {
    if major.is_null() || minor.is_null() {
        return FS_E_INVALID_ARG;
    }
    unsafe {
        *major = 0;
        *minor = 1;
    }
    FS_OK
}

// --- 汎用入口(ヘッダの GENERIC ENTRY POINT 節) -------------------------------
//
// 契約の 5 op は上の typed な関数が正本。`fs_apply` は **op 名 + JSON** で同じ 5 op
// (native 経路)と、Python レジストリの ~900 op(python 経路、feature `embed`)を
// 1 つの関数から呼ぶ。どの経路で走ったかは `info.route` に必ず書く。中身は
// `apply.rs`(経路の選択・native)と `embed.rs`(CPython の埋め込み)。

/// `fs_apply` —— op 名で任意の演算子を呼ぶ。`params_json` は JSON オブジェクト
/// (NULL = "{}")。`outputs` に書いたハンドルは呼び手の所有(R-5)。
#[no_mangle]
pub extern "C" fn fs_apply(
    op: *const c_char,
    inputs: *const FsHandle,
    n_in: c_int,
    params_json: *const c_char,
    route_pref: c_int,
    outputs: *mut FsHandle,
    out_cap: c_int,
    n_out: *mut c_int,
    info: *mut FsApplyInfo,
) -> c_int {
    let mut inf = FsApplyInfo::blank();
    let st = apply::run(op, inputs, n_in, params_json, route_pref, outputs, out_cap, n_out, &mut inf);
    if !info.is_null() {
        unsafe { std::ptr::write(info, inf) };
    }
    st
}

/// 埋め込み CPython を起動する(プロセスで 1 回)。NULL なら探索(env → PEP 514 → 失敗)。
#[no_mangle]
pub extern "C" fn fs_python_init(python_home_or_null: *const c_char) -> c_int {
    let home: Option<String> = if python_home_or_null.is_null() {
        None
    } else {
        match unsafe { std::ffi::CStr::from_ptr(python_home_or_null) }.to_str() {
            Ok(s) => Some(s.to_string()),
            Err(_) => return FS_E_INVALID_ARG,
        }
    };
    match embed::ensure(home.as_deref()) {
        Ok(()) => FS_OK,
        Err(_) => FS_E_NO_PYTHON,
    }
}

/// python 経路が今使えるか。使えなければ理由を `why` に書いて FS_E_NO_PYTHON。
#[no_mangle]
pub extern "C" fn fs_python_available(why: *mut c_char, why_len: c_int) -> c_int {
    let r = embed::ensure(None);
    if !why.is_null() && why_len > 0 {
        let buf = unsafe { std::slice::from_raw_parts_mut(why, why_len as usize) };
        apply::put_str(buf, r.as_ref().err().map(|s| s.as_str()).unwrap_or(""));
    }
    match r {
        Ok(()) => FS_OK,
        Err(_) => FS_E_NO_PYTHON,
    }
}

static CATALOG: std::sync::Mutex<Option<std::ffi::CString>> = std::sync::Mutex::new(None);

/// op のカタログ(JSON)。文字列はライブラリの所有で、次の呼び出しまで有効。
#[no_mangle]
pub extern "C" fn fs_catalog_json(out: *mut *const c_char) -> c_int {
    if out.is_null() {
        return FS_E_INVALID_ARG;
    }
    unsafe { *out = std::ptr::null() };
    let s = match embed::catalog() {
        Ok(s) => s,
        Err(f) => return f.code,
    };
    let c = match std::ffi::CString::new(s) {
        Ok(c) => c,
        Err(_) => return FS_E_INTERNAL,
    };
    let mut g = CATALOG.lock().unwrap_or_else(|e| e.into_inner());
    *g = Some(c);
    unsafe { *out = g.as_ref().map(|c| c.as_ptr()).unwrap_or(std::ptr::null()) };
    FS_OK
}
