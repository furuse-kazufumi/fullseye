//! `embed` feature のときだけ意味を持つ: 建てた相手の CPython の版を crate へ渡す。
//!
//! ★試して駄目だった案(2026-09-15、記録): Windows で `python3XY.dll` を `/DELAYLOAD`
//!   にして「DLL が見つからない時点で `fullseye_core.dll` のロードごと失敗する」のを
//!   避けようとしたが、**リンクできない**(LNK1194)。pyo3 は `PyBytes_Type` のような
//!   **データシンボル**を import しており、遅延ロードは関数しか扱えない。
//!   → python3XY.dll は**静的 import** のまま。実行時は OS の DLL 探索(exe と同じ dir /
//!   PATH)で解決される必要があり、見つからなければ `fullseye_core.dll` 自体が
//!   ロードできない(理由は OS のエラー 126 で出る)。自前の探索(`FULLSEYE_PYTHON_HOME`
//!   → PEP 514)が決めるのは `PyConfig.home`(標準ライブラリの所在)のほう。
//!   同梱(python-build-standalone を cdylib の隣に置く)が次段の解。
//!
//! feature off のときは Python を一切リンクしないので、ここは何もしない。
fn main() {
    println!("cargo:rerun-if-changed=build.rs");
    #[cfg(feature = "embed")]
    {
        let ver = pyo3_build_config::get().version();
        // 実行時の照合に使う名前(例: "python311.dll")と版("3.11")。
        println!("cargo:rustc-env=FULLSEYE_PYTHON_DLL=python{}{}.dll", ver.major, ver.minor);
        println!("cargo:rustc-env=FULLSEYE_PYTHON_VERSION={}.{}", ver.major, ver.minor);
    }
}
