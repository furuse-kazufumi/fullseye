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

// --- R-1: 状態コード(ヘッダの fs_status と同じ値) -------------------------
pub const FS_OK: c_int = 0;
pub const FS_E_INVALID_ARG: c_int = 1;
pub const FS_E_TYPE: c_int = 2;
pub const FS_E_ALLOC: c_int = 3;
pub const FS_E_UNSUPPORTED: c_int = 4;

// --- 不透明ハンドルの中身(外からは見えない) ------------------------------
pub struct FsImage {
    h: i32,
    w: i32,
    px: Vec<f64>, // 行優先。dtype は f64 に正規化して持つ(このスパイクの範囲)
    lo: f64,
    hi: f64,
}

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

// --- 画像 -------------------------------------------------------------------

/// 画素を借りて画像を作る。`pixels` は f64 の行優先、`row_stride_bytes` は行の間隔。
#[no_mangle]
pub extern "C" fn fs_image_create(
    pixels: *const c_void,
    height: i32,
    width: i32,
    row_stride_bytes: i64,
    range_lo: c_double,
    range_hi: c_double,
    out: *mut *mut FsImage,
) -> c_int {
    if pixels.is_null() || out.is_null() || height <= 0 || width <= 0 {
        return FS_E_INVALID_ARG;
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
            lo: range_lo,
            hi: range_hi,
        }));
    }
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

// 使わない型を参照して警告を消す(c_char は将来 select_shape の feature 名で使う)
#[allow(dead_code)]
fn _unused(_: *const c_char) {}
