// Copyright (c) 2026 Kazufumi Furuse. Apache-2.0.
// pybind11 embedded C ABI / pybind11 埋め込み C ABI。
#include "fullseye.h"

#include <pybind11/embed.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <chrono>
#include <condition_variable>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <mutex>
#include <new>
#include <memory>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#ifdef _WIN32
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  include <windows.h>
#elif defined(__APPLE__)
#  include <mach-o/dyld.h>
#else
#  include <unistd.h>
#endif

namespace py = pybind11;

#ifndef FULLSEYE_DEFAULT_RUNTIME_ROOT
#  define FULLSEYE_DEFAULT_RUNTIME_ROOT ""
#endif

#ifndef FULLSEYE_DEFAULT_PYTHON_HOME
#  define FULLSEYE_DEFAULT_PYTHON_HOME ""
#endif

static_assert(sizeof(fs_run_t) == 3u * sizeof(int32_t), "fs_run_t must contain three int32 values");

namespace {

constexpr uint32_t kRequiredInitSize =
    static_cast<uint32_t>(offsetof(fs_init_options_t, abi_minor) + sizeof(uint32_t));
constexpr uint32_t kRequiredInitNSize =
    static_cast<uint32_t>(offsetof(fs_init_options_t, python_home_bytes) + sizeof(size_t));
constexpr uint32_t kRequiredImageSize =
    static_cast<uint32_t>(offsetof(fs_image_view_t, range_hi) + sizeof(double));
constexpr uint32_t kRequiredInputSize =
    static_cast<uint32_t>(offsetof(fs_input_t, result_index) + sizeof(size_t));
constexpr uint32_t kRequiredInputNSize =
    static_cast<uint32_t>(offsetof(fs_input_n_t, result_index) + sizeof(size_t));
constexpr uint32_t kTypedInputNSize =
    static_cast<uint32_t>(offsetof(fs_input_n_t, feature) + sizeof(double));
constexpr uint32_t kRequiredArraySize =
    static_cast<uint32_t>(offsetof(fs_array_view_t, dtype) + sizeof(fs_dtype_t));
// Discovery reports retain every candidate and both repair command sets, so a
// short fixed error slot would hide the last remedy. / 全候補と二系統の修復手順を
// 保つため、短い固定バッファで末尾を切らない。
constexpr size_t kMaxErrorBytes = 16384u;
// Windows extended-length paths are limited to 32,767 UTF-16 code units.
// UTF-8 needs at most three bytes per UTF-16 code unit: a BMP scalar uses at
// most three bytes, and a supplementary scalar uses four bytes across its
// surrogate pair.  Use the resulting 98,301-byte bound for explicit ABI 0.2
// path spans on every platform so hostile lengths are rejected before a scan
// or allocation. / Windows の拡張長パスは UTF-16 で 32,767 code unit が上限。
// UTF-8 は UTF-16 code unit 当たり最大 3 B（BMP は最大 3 B、補助面は
// surrogate pair の 2 code unit で 4 B）なので、ABI 0.2 の明示長パスは
// 全プラットフォームで 98,301 B に制限し、走査・確保の前に拒否する。
constexpr size_t kWindowsExtendedPathUtf16CodeUnits = 32767u;
constexpr size_t kMaxRuntimePathBytes = 3u * kWindowsExtendedPathUtf16CodeUnits;
// Every generated C-callable operator ID is at most 41 UTF-8 bytes (952 rows,
// measured 2026-11-24).  Keep ample room for future scoped IDs while bounding
// an untrusted allocation request at the C boundary. / 現在の型台帳で最長の
// C-callable ID は 41 UTF-8 B (952 行、2026-11-24 実測)。将来の scoped ID
// の余裕を残しつつ、C 境界で信頼できない確保要求を上限化する。
constexpr size_t kMaxOperatorIdBytes = 256u;
// Query and parameter JSON are control-plane documents, not array payloads.
// One MiB is enough for closed operator schemas and prevents hostile span
// lengths from reaching std::string allocation. / query/params JSON は配列
// payload でなく制御用文書なので、1 MiB で閉じた schema には足り、悪意ある
// span 長を std::string の確保まで通さない。
constexpr size_t kMaxJsonBytes = 1024u * 1024u;
constexpr const char kSdkAbiVersion[] = "0.2";

struct Item {
    fs_value_kind_t kind = FS_VALUE_REAL;
    int64_t height = 0;
    int64_t width = 0;
    double range_lo = 0.0;
    double range_hi = 1.0;
    std::vector<double> image;
    std::vector<double> array;
    std::vector<int64_t> shape;
    std::vector<fs_run_t> runs;
    std::vector<std::vector<fs_run_t>> objects;
    double real = 0.0;
    std::vector<double> tuple;
};

struct ThreadError {
    const fs_runtime_t *runtime = nullptr;
    size_t length = 0u;
    char message[kMaxErrorBytes + 1u]{};
};

thread_local ThreadError g_error;
bool g_python_ready = false;
bool g_python_owned = false;
std::string g_python_root;
std::string g_python_home;
std::mutex g_python_mutex;
std::mutex g_runtime_mutex;
std::unordered_set<fs_runtime_t *> g_runtimes;

void set_error(const fs_runtime_t *runtime, std::string_view message) noexcept {
    g_error.runtime = runtime;
    g_error.length = std::min(message.size(), kMaxErrorBytes);
    if (g_error.length != 0u) {
        std::memcpy(g_error.message, message.data(), g_error.length);
    }
    g_error.message[g_error.length] = '\0';
}

void clear_error(const fs_runtime_t *runtime) {
    g_error.runtime = runtime;
    g_error.length = 0u;
    g_error.message[0] = '\0';
}

bool checked_mul(size_t left, size_t right, size_t *out) {
    if (left != 0u && right > std::numeric_limits<size_t>::max() / left) {
        return false;
    }
    *out = left * right;
    return true;
}

bool checked_add(size_t left, size_t right, size_t *out) {
    if (right > std::numeric_limits<size_t>::max() - left) {
        return false;
    }
    *out = left + right;
    return true;
}

size_t dtype_size(fs_dtype_t dtype) {
    switch (dtype) {
        case FS_DTYPE_U8: return sizeof(uint8_t);
        case FS_DTYPE_U16: return sizeof(uint16_t);
        case FS_DTYPE_F32: return sizeof(float);
        case FS_DTYPE_F64: return sizeof(double);
        default: return 0u;
    }
}

py::dtype numpy_dtype(fs_dtype_t dtype) {
    switch (dtype) {
        case FS_DTYPE_U8: return py::dtype::of<uint8_t>();
        case FS_DTYPE_U16: return py::dtype::of<uint16_t>();
        case FS_DTYPE_F32: return py::dtype::of<float>();
        case FS_DTYPE_F64: return py::dtype::of<double>();
        default: throw std::runtime_error("unknown image dtype");
    }
}

fs_status_t validate_image(const fs_runtime_t *runtime, const fs_image_view_t &view) {
    if (view.struct_size < kRequiredImageSize) {
        set_error(runtime, "fs_image_view_t.struct_size is too small");
        return FS_E_INVALID_ARG;
    }
    if (view.data == nullptr) {
        set_error(runtime, "image data must not be NULL");
        return FS_E_INVALID_ARG;
    }
    if (view.width <= 0 || view.height <= 0) {
        set_error(runtime, "image width and height must be positive");
        return FS_E_SHAPE;
    }
    const size_t element = dtype_size(view.dtype);
    if (element == 0u) {
        set_error(runtime, "image dtype is unknown");
        return FS_E_TYPE;
    }
    if (view.row_stride_bytes <= 0) {
        set_error(runtime, "row stride must be positive");
        return FS_E_SHAPE;
    }
    const auto width = static_cast<uint64_t>(view.width);
    const auto height = static_cast<uint64_t>(view.height);
    if (width > std::numeric_limits<size_t>::max() || height > std::numeric_limits<size_t>::max()
        || static_cast<uint64_t>(view.row_stride_bytes) > std::numeric_limits<size_t>::max()) {
        set_error(runtime, "image dimensions or stride overflow size_t");
        return FS_E_SHAPE;
    }
    size_t row_bytes = 0u;
    if (!checked_mul(static_cast<size_t>(width), element, &row_bytes)
        || static_cast<size_t>(view.row_stride_bytes) < row_bytes) {
        set_error(runtime, "row stride is smaller than one image row");
        return FS_E_SHAPE;
    }
    size_t row_offsets = 0u;
    size_t required = 0u;
    if (!checked_mul(static_cast<size_t>(height - 1u), static_cast<size_t>(view.row_stride_bytes), &row_offsets)
        || !checked_add(row_offsets, row_bytes, &required)) {
        set_error(runtime, "image byte extent overflows size_t");
        return FS_E_SHAPE;
    }
    if (view.data_bytes < required) {
        set_error(runtime, "image data_bytes is smaller than the strided image extent");
        return FS_E_SHAPE;
    }
    if (reinterpret_cast<uintptr_t>(view.data) % element != 0u
        || static_cast<size_t>(view.row_stride_bytes) % element != 0u) {
        set_error(runtime, "image data and stride must be aligned to the dtype size");
        return FS_E_SHAPE;
    }
    if (!std::isfinite(view.range_lo) || !std::isfinite(view.range_hi)
        || !(view.range_hi > view.range_lo)) {
        set_error(runtime, "image range must be finite and increasing");
        return FS_E_RANGE;
    }
    if (view.dtype == FS_DTYPE_F32 || view.dtype == FS_DTYPE_F64) {
        const auto *base = static_cast<const unsigned char *>(view.data);
        for (int64_t row = 0; row < view.height; ++row) {
            const auto *line = base + static_cast<size_t>(row) * static_cast<size_t>(view.row_stride_bytes);
            for (int64_t column = 0; column < view.width; ++column) {
                double value = 0.0;
                if (view.dtype == FS_DTYPE_F32) {
                    value = static_cast<double>(reinterpret_cast<const float *>(line)[column]);
                } else {
                    value = reinterpret_cast<const double *>(line)[column];
                }
                if (!std::isfinite(value)) {
                    set_error(runtime, "image contains NaN or infinity");
                    return FS_E_INVALID_ARG;
                }
            }
        }
    }
    return FS_OK;
}

fs_status_t validate_array(const fs_runtime_t *runtime, const fs_array_view_t &view,
                           fs_value_kind_t kind) {
    if (view.struct_size < kRequiredArraySize || view.data == nullptr) {
        set_error(runtime, "array view struct_size is too small or data is NULL");
        return FS_E_INVALID_ARG;
    }
    const uint32_t want_dims = kind == FS_VALUE_COLOR ? 3u : 0u;
    if ((want_dims != 0u && view.ndim != want_dims)
        || (kind == FS_VALUE_VOLUME && (view.ndim < 3u || view.ndim > 4u))) {
        set_error(runtime, "color requires three dimensions; volume requires three or four dimensions");
        return FS_E_SHAPE;
    }
    if (kind == FS_VALUE_COLOR && view.shape[2] != 3) {
        set_error(runtime, "color requires shape (height, width, 3)");
        return FS_E_SHAPE;
    }
    for (uint32_t i = view.ndim; i < 4u; ++i) {
        if (view.shape[i] != 0 || view.stride_bytes[i] != 0) {
            set_error(runtime, "array shape and stride entries after ndim must be zero");
            return FS_E_SHAPE;
        }
    }
    const size_t element = dtype_size(view.dtype);
    if (element == 0u) {
        set_error(runtime, "array dtype is unknown");
        return FS_E_TYPE;
    }
    size_t required = element;
    for (uint32_t i = 0u; i < view.ndim; ++i) {
        if (view.shape[i] <= 0 || view.stride_bytes[i] <= 0
            || static_cast<uint64_t>(view.shape[i]) > std::numeric_limits<size_t>::max()
            || static_cast<uint64_t>(view.stride_bytes[i]) > std::numeric_limits<size_t>::max()) {
            set_error(runtime, "array shape and stride must be positive and fit size_t");
            return FS_E_SHAPE;
        }
        size_t offset = 0u;
        if (!checked_mul(static_cast<size_t>(view.shape[i] - 1),
                         static_cast<size_t>(view.stride_bytes[i]), &offset)
            || !checked_add(required, offset, &required)) {
            set_error(runtime, "array byte extent overflows size_t");
            return FS_E_SHAPE;
        }
        if (static_cast<size_t>(view.stride_bytes[i]) % element != 0u) {
            set_error(runtime, "array stride must align to the dtype size");
            return FS_E_SHAPE;
        }
    }
    size_t contiguous_stride = element;
    for (uint32_t axis = view.ndim; axis-- > 1u;) {
        if (static_cast<size_t>(view.stride_bytes[axis]) != contiguous_stride) {
            set_error(runtime, "array must be contiguous after its first axis");
            return FS_E_SHAPE;
        }
        if (!checked_mul(contiguous_stride, static_cast<size_t>(view.shape[axis]),
                         &contiguous_stride)) {
            set_error(runtime, "array contiguous byte extent overflows size_t");
            return FS_E_SHAPE;
        }
    }
    if (static_cast<size_t>(view.stride_bytes[0]) < contiguous_stride) {
        set_error(runtime, "array first-axis stride is smaller than one contiguous trailing row");
        return FS_E_SHAPE;
    }
    if (view.data_bytes < required || reinterpret_cast<uintptr_t>(view.data) % element != 0u) {
        set_error(runtime, "array data_bytes is too small or data is misaligned");
        return FS_E_SHAPE;
    }
    if (view.dtype == FS_DTYPE_F32 || view.dtype == FS_DTYPE_F64) {
        const auto *base = static_cast<const unsigned char *>(view.data);
        const size_t rest = contiguous_stride / element;
        for (int64_t d0 = 0; d0 < view.shape[0]; ++d0) {
            const auto *row0 = base + static_cast<size_t>(d0) * static_cast<size_t>(view.stride_bytes[0]);
            for (size_t i = 0u; i < rest; ++i) {
                const double value = view.dtype == FS_DTYPE_F32
                    ? static_cast<double>(reinterpret_cast<const float *>(row0)[i])
                    : reinterpret_cast<const double *>(row0)[i];
                if (!std::isfinite(value)) {
                    set_error(runtime, "array contains NaN or infinity");
                    return FS_E_INVALID_ARG;
                }
            }
        }
    }
    return FS_OK;
}

void add_runtime_paths(const std::string &root) {
    if (root.empty()) {
        return;
    }
    py::list path = py::module_::import("sys").attr("path");
    const char separator =
#if defined(_WIN32)
        '\\';
#else
        '/';
#endif
    path.attr("insert")(0, root);
    path.attr("insert")(0, root + separator + "site-packages");
    path.attr("insert")(0, root + separator + "Lib" + separator + "site-packages");
    path.attr("insert")(0, root + separator + "runtime" + separator + "site-packages");
}

struct PythonInitResult {
    fs_status_t status = FS_OK;
    std::string error;
};

struct RuntimeAttempt {
    std::string source;
    std::string location;
    std::string outcome;
};

struct RuntimeDiscovery {
    bool found = false;
    std::string root;
    std::string home;
    std::string source;
    std::vector<RuntimeAttempt> attempts;
};

std::filesystem::path utf8_path(const std::string &value) {
#ifdef _WIN32
    if (value.size() > static_cast<size_t>(std::numeric_limits<int>::max())) {
        throw std::runtime_error("UTF-8 path exceeds the Windows API limit");
    }
    const int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
                                          static_cast<int>(value.size()), nullptr, 0);
    if (count <= 0) throw std::runtime_error("path is not valid UTF-8");
    std::wstring wide(static_cast<size_t>(count), L'\0');
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()),
                            wide.data(), count) != count) {
        throw std::runtime_error("path is not valid UTF-8");
    }
    return std::filesystem::path(wide);
#else
    return std::filesystem::path(value);
#endif
}

std::string path_utf8(const std::filesystem::path &value) {
    const auto bytes = value.u8string();
    return std::string(bytes.begin(), bytes.end());
}

std::string linked_python_home() {
#ifdef _WIN32
    char name[32]{};
    std::snprintf(name, sizeof(name), "python%d%d.dll", PY_MAJOR_VERSION, PY_MINOR_VERSION);
    const HMODULE module = GetModuleHandleA(name);
    if (module == nullptr) return "";
    std::vector<wchar_t> path(32768u, L'\0');
    const DWORD count = GetModuleFileNameW(module, path.data(), static_cast<DWORD>(path.size()));
    if (count == 0u || count >= path.size()) return "";
    return path_utf8(std::filesystem::path(std::wstring(path.data(), count)).parent_path());
#else
    return "";
#endif
}

std::string trim_ascii(std::string value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return "";
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1u);
}

bool compatible_runtime_root(const std::string &root, std::string *why) {
    try {
        if (root.empty()) {
            *why = "not specified";
            return false;
        }
        const std::filesystem::path base = utf8_path(root);
        std::error_code error;
        if (!std::filesystem::is_directory(base, error)) {
            *why = "directory does not exist";
            return false;
        }
        const std::filesystem::path package = base / "fullseye";
        if (!std::filesystem::is_regular_file(package / "__init__.py", error)) {
            *why = "fullseye is not installed (missing fullseye/__init__.py)";
            return false;
        }
        const std::filesystem::path abi_file = package / "sdk" / "ABI_VERSION";
        if (!std::filesystem::is_regular_file(abi_file, error)) {
            *why = "SDK ABI version file is missing (fullseye/sdk/ABI_VERSION)";
            return false;
        }
        std::ifstream input(abi_file, std::ios::binary);
        std::string version((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
        version = trim_ascii(version);
        if (version != kSdkAbiVersion) {
            *why = "SDK ABI version " + (version.empty() ? std::string("is empty") : version)
                + " does not match required " + kSdkAbiVersion;
            return false;
        }
        *why = "compatible fullseye SDK ABI " + std::string(kSdkAbiVersion);
        return true;
    } catch (const std::exception &exc) {
        *why = std::string("could not inspect the path: ") + exc.what();
        return false;
    }
}

void try_runtime_root(RuntimeDiscovery *discovery, const std::string &source,
                      const std::string &root, const std::string &home) {
    if (discovery->found) return;
    std::string why;
    const bool compatible = compatible_runtime_root(root, &why);
    discovery->attempts.push_back({source, root.empty() ? "(none)" : root,
                                   compatible ? "usable: " + why : why});
    if (compatible) {
        discovery->found = true;
        discovery->root = root;
        discovery->home = home.empty() ? linked_python_home() : home;
        discovery->source = source;
    }
}

void try_runtime_prefix(RuntimeDiscovery *discovery, const std::string &source,
                        const std::string &prefix) {
    if (discovery->found) return;
    if (prefix.empty()) {
        try_runtime_root(discovery, source, "", "");
        return;
    }
    const std::filesystem::path base = utf8_path(prefix);
    try_runtime_root(discovery, source + " (root)", path_utf8(base), prefix);
    if (discovery->found) return;
    try_runtime_root(discovery, source + " (Windows site-packages)",
                     path_utf8(base / "Lib" / "site-packages"), prefix);
    if (discovery->found) return;
    std::error_code error;
    const std::filesystem::path lib = base / "lib";
    if (!std::filesystem::is_directory(lib, error)) {
        discovery->attempts.push_back({source + " (POSIX site-packages)", path_utf8(lib),
                                       "directory does not exist"});
        return;
    }
    bool had_python_directory = false;
    for (const auto &entry : std::filesystem::directory_iterator(lib, error)) {
        if (error) break;
        const std::string name = entry.path().filename().string();
        if (name.rfind("python", 0u) != 0u) continue;
        had_python_directory = true;
        try_runtime_root(discovery, source + " (POSIX site-packages)",
                         path_utf8(entry.path() / "site-packages"), prefix);
        if (discovery->found) return;
    }
    if (!had_python_directory) {
        discovery->attempts.push_back({source + " (POSIX site-packages)", path_utf8(lib),
                                       "no lib/python*/site-packages directory"});
    }
}

std::optional<std::string> json_string_field(const std::string &text, const char *field) {
    const std::string key = std::string("\"") + field + "\"";
    const size_t key_at = text.find(key);
    if (key_at == std::string::npos) return std::nullopt;
    size_t at = text.find(':', key_at + key.size());
    if (at == std::string::npos) return std::nullopt;
    ++at;
    while (at < text.size() && (text[at] == ' ' || text[at] == '\t' || text[at] == '\r' || text[at] == '\n')) ++at;
    if (at >= text.size() || text[at++] != '\"') return std::nullopt;
    std::string value;
    while (at < text.size()) {
        const char character = text[at++];
        if (character == '\"') return value;
        if (character != '\\') {
            value.push_back(character);
            continue;
        }
        if (at >= text.size()) return std::nullopt;
        const char escaped = text[at++];
        switch (escaped) {
            case '\"': value.push_back('\"'); break;
            case '\\': value.push_back('\\'); break;
            case '/': value.push_back('/'); break;
            case 'b': value.push_back('\b'); break;
            case 'f': value.push_back('\f'); break;
            case 'n': value.push_back('\n'); break;
            case 'r': value.push_back('\r'); break;
            case 't': value.push_back('\t'); break;
            default: return std::nullopt;  // Manifests use UTF-8, never \u escapes.
        }
    }
    return std::nullopt;
}

std::string executable_directory() {
#ifdef _WIN32
    std::vector<wchar_t> path(32768u, L'\0');
    const DWORD count = GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
    if (count == 0u || count >= path.size()) return "";
    return path_utf8(std::filesystem::path(std::wstring(path.data(), count)).parent_path());
#elif defined(__APPLE__)
    uint32_t count = 0u;
    (void)_NSGetExecutablePath(nullptr, &count);
    std::vector<char> path(static_cast<size_t>(count) + 1u, '\0');
    if (_NSGetExecutablePath(path.data(), &count) != 0) return "";
    return path_utf8(std::filesystem::path(path.data()).parent_path());
#else
    std::vector<char> path(32768u, '\0');
    const ssize_t count = readlink("/proc/self/exe", path.data(), path.size() - 1u);
    if (count <= 0) return "";
    path[static_cast<size_t>(count)] = '\0';
    return path_utf8(std::filesystem::path(path.data()).parent_path());
#endif
}

std::string home_from_python_executable(const std::string &python) {
    if (python.empty()) return "";
    const std::filesystem::path directory = utf8_path(python).parent_path();
    const std::string leaf = directory.filename().string();
    return path_utf8((leaf == "Scripts" || leaf == "bin") ? directory.parent_path() : directory);
}

void try_runtime_manifest(RuntimeDiscovery *discovery) {
    if (discovery->found) return;
    const std::string directory = executable_directory();
    if (directory.empty()) {
        discovery->attempts.push_back({"adjacent fullseye_runtime.json", "(current executable)",
                                       "could not determine executable directory"});
        return;
    }
    const std::filesystem::path manifest = utf8_path(directory) / "fullseye_runtime.json";
    std::error_code error;
    if (!std::filesystem::is_regular_file(manifest, error)) {
        discovery->attempts.push_back({"adjacent fullseye_runtime.json", path_utf8(manifest), "file does not exist"});
        return;
    }
    std::ifstream input(manifest, std::ios::binary);
    const std::string text((std::istreambuf_iterator<char>(input)), std::istreambuf_iterator<char>());
    const auto root = json_string_field(text, "runtime_root");
    const auto version = json_string_field(text, "sdk_abi_version");
    if (!root || !version) {
        discovery->attempts.push_back({"adjacent fullseye_runtime.json", path_utf8(manifest),
                                       "invalid manifest: runtime_root or sdk_abi_version is missing"});
        return;
    }
    if (*version != kSdkAbiVersion) {
        discovery->attempts.push_back({"adjacent fullseye_runtime.json", path_utf8(manifest),
                                       "SDK ABI version " + *version + " does not match required " + kSdkAbiVersion});
        return;
    }
    const auto home = json_string_field(text, "python_home");
    const auto python = json_string_field(text, "python_executable");
    try_runtime_root(discovery, "adjacent fullseye_runtime.json", *root,
                     home ? *home : (python ? home_from_python_executable(*python) : ""));
}

#ifdef _WIN32
std::string utf8_from_wide(const std::wstring &value) {
    if (value.empty()) return "";
    const int count = WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(),
                                          static_cast<int>(value.size()), nullptr, 0, nullptr, nullptr);
    if (count <= 0) return "";
    std::string result(static_cast<size_t>(count), '\0');
    if (WideCharToMultiByte(CP_UTF8, WC_ERR_INVALID_CHARS, value.data(), static_cast<int>(value.size()),
                            result.data(), count, nullptr, nullptr) != count) return "";
    return result;
}

bool try_pep514_hive(RuntimeDiscovery *discovery, HKEY hive) {
    HKEY core = nullptr;
    if (RegOpenKeyExW(hive, L"Software\\Python\\PythonCore", 0u, KEY_READ, &core) != ERROR_SUCCESS) return false;
    bool found_installation = false;
    for (DWORD index = 0u; !discovery->found; ++index) {
        wchar_t name[256]{};
        DWORD length = static_cast<DWORD>(std::size(name) - 1u);
        if (RegEnumKeyExW(core, index, name, &length, nullptr, nullptr, nullptr, nullptr) != ERROR_SUCCESS) break;
        const std::wstring key_name = std::wstring(name, length) + L"\\InstallPath";
        HKEY install = nullptr;
        if (RegOpenKeyExW(core, key_name.c_str(), 0u, KEY_READ, &install) != ERROR_SUCCESS) continue;
        wchar_t value[32768]{};
        DWORD type = 0u;
        DWORD bytes = sizeof(value) - sizeof(wchar_t);
        const LONG result = RegQueryValueExW(install, nullptr, nullptr, &type,
                                             reinterpret_cast<LPBYTE>(value), &bytes);
        RegCloseKey(install);
        if (result != ERROR_SUCCESS || (type != REG_SZ && type != REG_EXPAND_SZ)) continue;
        found_installation = true;
        try_runtime_prefix(discovery, "PEP 514 registry", utf8_from_wide(value));
    }
    RegCloseKey(core);
    return found_installation;
}
#endif

void try_path_python3(RuntimeDiscovery *discovery) {
#ifndef _WIN32
    const char *path_value = std::getenv("PATH");
    if (path_value == nullptr || *path_value == '\0') {
        discovery->attempts.push_back({"PATH python3", "(PATH)", "PATH is empty"});
        return;
    }
    std::stringstream paths(path_value);
    std::string directory;
    bool found_executable = false;
    while (std::getline(paths, directory, ':') && !discovery->found) {
        const std::filesystem::path executable = (directory.empty() ? std::filesystem::path(".")
                                                                       : utf8_path(directory)) / "python3";
        std::error_code error;
        if (!std::filesystem::is_regular_file(executable, error)) continue;
        found_executable = true;
        try_runtime_prefix(discovery, "PATH python3", home_from_python_executable(path_utf8(executable)));
    }
    if (!discovery->found && !found_executable) {
        discovery->attempts.push_back({"PATH python3", "python3", "executable was not found"});
    }
#endif
}

RuntimeDiscovery discover_runtime(const std::string &explicit_root, const std::string &explicit_home) {
    RuntimeDiscovery discovery;
    if (!explicit_root.empty()) try_runtime_root(&discovery, "explicit runtime_root", explicit_root, explicit_home);
    if (!discovery.found) {
        const char *environment_root = std::getenv("FULLSEYE_PYTHON_ROOT");
        const char *venv_home = std::getenv("VIRTUAL_ENV");
        const char *conda_home = std::getenv("CONDA_PREFIX");
        const std::string environment_home = venv_home != nullptr && *venv_home != '\0' ? venv_home
            : (conda_home != nullptr && *conda_home != '\0' ? conda_home : linked_python_home());
        if (environment_root == nullptr || *environment_root == '\0') {
            discovery.attempts.push_back({"FULLSEYE_PYTHON_ROOT", "(not set)", "not specified"});
        } else {
            try_runtime_root(&discovery, "FULLSEYE_PYTHON_ROOT", environment_root, environment_home);
            if (!discovery.found) try_runtime_prefix(&discovery, "FULLSEYE_PYTHON_ROOT", environment_root);
        }
    }
    if (!discovery.found) try_runtime_manifest(&discovery);
    const char *venv = std::getenv("VIRTUAL_ENV");
    if (!discovery.found) try_runtime_prefix(&discovery, "VIRTUAL_ENV", venv == nullptr ? "" : venv);
    const char *conda = std::getenv("CONDA_PREFIX");
    if (!discovery.found) try_runtime_prefix(&discovery, "CONDA_PREFIX", conda == nullptr ? "" : conda);
#ifdef _WIN32
    if (!discovery.found) {
        const bool user_registry = try_pep514_hive(&discovery, HKEY_CURRENT_USER);
        const bool machine_registry = discovery.found ? false : try_pep514_hive(&discovery, HKEY_LOCAL_MACHINE);
        if (!discovery.found && !user_registry && !machine_registry) {
            discovery.attempts.push_back({"PEP 514 registry", "HKCU/HKLM Software\\Python\\PythonCore",
                                          "no registered Python installation"});
        }
    }
#else
    if (!discovery.found) try_path_python3(&discovery);
#endif
    if (!discovery.found && FULLSEYE_DEFAULT_RUNTIME_ROOT[0] != '\0') {
        try_runtime_root(&discovery, "embedded build-time fallback", FULLSEYE_DEFAULT_RUNTIME_ROOT,
                         FULLSEYE_DEFAULT_PYTHON_HOME);
    } else if (!discovery.found) {
        discovery.attempts.push_back({"embedded build-time fallback", "(not compiled in)", "not available"});
    }
    return discovery;
}

std::string discovery_report(const RuntimeDiscovery &discovery) {
    std::ostringstream output;
    if (discovery.found) {
        output << "Fullseye runtime discovery (CPython was not started).\n"
               << "Selected " << discovery.source << ": " << discovery.root << "\n";
    } else {
        output << "Fullseye could not find a compatible Python runtime.\n"
               << "Why: every candidate was absent, incomplete, or built for a different SDK ABI (expected "
               << kSdkAbiVersion << ").\n";
    }
    output << "Tried:\n";
    for (const RuntimeAttempt &attempt : discovery.attempts) {
        output << "- " << attempt.source << ": " << attempt.location << " -- " << attempt.outcome << "\n";
    }
    if (!discovery.found) {
        output << "Fix in PowerShell:\n"
               << "py -3.11 -m pip install fullseye\n"
               << "py -3.11 -m fullseye.sdk relink .\\build\n"
               << "Fix in bash:\n"
               << "python3 -m pip install fullseye\n"
               << "python3 -m fullseye.sdk relink ./build\n";
    }
    return output.str();
}

PythonInitResult initialize_python(const std::string &root, const std::string &home,
                                   bool allow_host) {
    std::lock_guard<std::mutex> lock(g_python_mutex);
    if (g_python_ready) {
        if (g_python_root != root || g_python_home != home) {
            return {FS_E_INVALID_ARG,
                    "the CPython runtime is already configured for a different runtime_root or python_home"};
        }
        if (!g_python_owned && !allow_host) {
            return {FS_E_INVALID_ARG,
                    "the existing CPython host requires FS_INIT_ALLOW_HOST_PYTHON_UNSAFE"};
        }
        return {};
    }
    std::string compatibility;
    if (!compatible_runtime_root(root, &compatibility)) {
        return {FS_E_NO_PYTHON,
                "the selected Fullseye Python runtime became unusable: " + compatibility
                + ". Run: python -m fullseye.sdk relink <executable-directory>."};
    }
    try {
        const bool was_running = Py_IsInitialized() != 0;
        if (was_running && g_python_owned) {
            if (g_python_root != root || g_python_home != home) {
                return {FS_E_INVALID_ARG,
                        "the CPython runtime is already configured for a different runtime_root or python_home"};
            }
            py::gil_scoped_acquire acquire;
            add_runtime_paths(root);
            py::module_::import("fullseye.c_api_bridge");
        } else if (was_running) {
            if (!allow_host) {
                return {FS_E_INVALID_ARG,
                        "FS_INIT_ISOLATED cannot use an existing CPython; set FS_INIT_ALLOW_HOST_PYTHON_UNSAFE to opt in to the host interpreter"};
            }
            py::gil_scoped_acquire acquire;
            add_runtime_paths(root);
            py::module_::import("fullseye.c_api_bridge");
            g_python_owned = false;
            g_python_root = root;
            g_python_home = home;
        } else {
            PyConfig config;
            PyConfig_InitIsolatedConfig(&config);
            config.install_signal_handlers = 0;
            config.parse_argv = 0;
            if (!home.empty()) {
                const PyStatus status = PyConfig_SetBytesString(&config, &config.home, home.c_str());
                if (PyStatus_Exception(status) != 0) {
                    const std::string message = status.err_msg == nullptr
                        ? "could not set Python home" : status.err_msg;
                    PyConfig_Clear(&config);
                    return {FS_E_NO_PYTHON, message};
                }
            }
            py::initialize_interpreter(&config, 0, nullptr, false);
            // Record ownership and the immutable configuration immediately. If
            // importing the bridge fails, this remains a library-owned Python.
            // 起動直後に所有者と設定を記録し、import 失敗後も library 所有と保つ。
            g_python_owned = true;
            g_python_root = root;
            g_python_home = home;
            try {
                add_runtime_paths(root);
                py::module_::import("fullseye.c_api_bridge");
            } catch (const std::exception &exc) {
                const std::string message = exc.what();
                PyEval_SaveThread();
                return {FS_E_NO_PYTHON, message};
            } catch (...) {
                PyEval_SaveThread();
                return {FS_E_NO_PYTHON, "unknown error while importing fullseye.c_api_bridge"};
            }
            // CPython remains alive until process exit; native callers acquire
            // the GIL for every later call. / 終了まで生かし、各呼出しで GIL を取る。
            PyEval_SaveThread();
        }
        g_python_ready = true;
        return {};
    } catch (const std::exception &exc) {
        return {FS_E_NO_PYTHON, exc.what()};
    } catch (...) {
        return {FS_E_NO_PYTHON, "unknown error while initializing CPython"};
    }
}

py::dict item_to_python(const Item &item) {
    py::dict value;
    if (item.kind == FS_VALUE_IMAGE) {
        value["kind"] = "image";
        value["h"] = item.height;
        value["w"] = item.width;
        value["lo"] = item.range_lo;
        value["hi"] = item.range_hi;
        value["array"] = py::array(py::dtype::of<double>(),
                                    {static_cast<py::ssize_t>(item.height), static_cast<py::ssize_t>(item.width)},
                                    {static_cast<py::ssize_t>(item.width * sizeof(double)),
                                     static_cast<py::ssize_t>(sizeof(double))}, item.image.data(), py::none());
    } else if (item.kind == FS_VALUE_COLOR || item.kind == FS_VALUE_VOLUME) {
        std::vector<py::ssize_t> shape;
        std::vector<py::ssize_t> strides;
        size_t stride = sizeof(double);
        for (auto it = item.shape.rbegin(); it != item.shape.rend(); ++it) {
            shape.insert(shape.begin(), static_cast<py::ssize_t>(*it));
            strides.insert(strides.begin(), static_cast<py::ssize_t>(stride));
            stride *= static_cast<size_t>(*it);
        }
        value["kind"] = item.kind == FS_VALUE_COLOR ? "color" : "volume";
        value["array"] = py::array(py::dtype::of<double>(), shape, strides, item.array.data(), py::none());
    } else if (item.kind == FS_VALUE_REGION) {
        value["kind"] = "region";
        value["h"] = item.height;
        value["w"] = item.width;
        value["runs"] = py::bytes(reinterpret_cast<const char *>(item.runs.data()),
                                   static_cast<py::ssize_t>(item.runs.size() * sizeof(fs_run_t)));
    } else if (item.kind == FS_VALUE_OBJECTSET) {
        value["kind"] = "objectset";
        value["h"] = item.height;
        value["w"] = item.width;
        py::list objects;
        for (const auto &runs : item.objects) {
            objects.append(py::bytes(reinterpret_cast<const char *>(runs.data()),
                                     static_cast<py::ssize_t>(runs.size() * sizeof(fs_run_t))));
        }
        value["objects"] = std::move(objects);
    } else if (item.kind == FS_VALUE_TUPLE) {
        value["kind"] = "tuple";
        value["values"] = py::cast(item.tuple);
    } else if (item.kind == FS_VALUE_FEATURE) {
        value["kind"] = "feature";
        value["value"] = item.real;
    } else {
        throw std::runtime_error("result kind cannot be used as an input");
    }
    return value;
}

py::dict image_to_python(const fs_image_view_t &view) {
    py::dict value;
    value["kind"] = "image";
    value["h"] = view.height;
    value["w"] = view.width;
    value["lo"] = view.range_lo;
    value["hi"] = view.range_hi;
    py::capsule borrowed(const_cast<void *>(view.data), [](void *) {});
    value["array"] = py::array(numpy_dtype(view.dtype),
                                {static_cast<py::ssize_t>(view.height), static_cast<py::ssize_t>(view.width)},
                                {static_cast<py::ssize_t>(view.row_stride_bytes),
                                 static_cast<py::ssize_t>(dtype_size(view.dtype))},
                                const_cast<void *>(view.data), borrowed);
    return value;
}

py::dict array_to_python(const fs_array_view_t &view, fs_value_kind_t kind) {
    py::dict value;
    py::capsule borrowed(const_cast<void *>(view.data), [](void *) {});
    std::vector<py::ssize_t> shape;
    std::vector<py::ssize_t> strides;
    for (uint32_t i = 0u; i < view.ndim; ++i) {
        shape.push_back(static_cast<py::ssize_t>(view.shape[i]));
        strides.push_back(static_cast<py::ssize_t>(view.stride_bytes[i]));
    }
    value["kind"] = kind == FS_VALUE_COLOR ? "color" : "volume";
    value["array"] = py::array(numpy_dtype(view.dtype), shape, strides,
                                 const_cast<void *>(view.data), borrowed);
    return value;
}

template <typename T>
std::vector<T> bytes_vector(const py::handle &value, const char *what) {
    const std::string bytes = py::cast<std::string>(value);
    if (bytes.size() % sizeof(T) != 0u) {
        throw std::runtime_error(std::string(what) + " byte length is invalid");
    }
    std::vector<T> out(bytes.size() / sizeof(T));
    if (!bytes.empty()) {
        std::memcpy(out.data(), bytes.data(), bytes.size());
    }
    return out;
}

Item python_to_item(const py::dict &value) {
    Item item;
    const std::string kind = py::cast<std::string>(value["kind"]);
    if (kind == "image") {
        item.kind = FS_VALUE_IMAGE;
        item.height = py::cast<int64_t>(value["h"]);
        item.width = py::cast<int64_t>(value["w"]);
        item.range_lo = py::cast<double>(value["lo"]);
        item.range_hi = py::cast<double>(value["hi"]);
        item.image = bytes_vector<double>(value["pixels"], "image");
        size_t expected = 0u;
        if (item.height <= 0 || item.width <= 0
            || !checked_mul(static_cast<size_t>(item.height), static_cast<size_t>(item.width), &expected)
            || item.image.size() != expected) {
            throw std::runtime_error("Python returned an invalid image shape or byte length");
        }
    } else if (kind == "color" || kind == "volume") {
        item.kind = kind == "color" ? FS_VALUE_COLOR : FS_VALUE_VOLUME;
        item.shape = py::cast<std::vector<int64_t>>(value["shape"]);
        item.array = bytes_vector<double>(value["pixels"], "array");
        if ((item.kind == FS_VALUE_COLOR && (item.shape.size() != 3u || item.shape[2] != 3))
            || (item.kind == FS_VALUE_VOLUME && (item.shape.size() < 3u || item.shape.size() > 4u))) {
            throw std::runtime_error("Python returned an invalid color or volume shape");
        }
        size_t expected = 1u;
        for (const int64_t dim : item.shape) {
            if (dim <= 0 || !checked_mul(expected, static_cast<size_t>(dim), &expected)) {
                throw std::runtime_error("Python returned an invalid color or volume shape");
            }
        }
        if (item.array.size() != expected) {
            throw std::runtime_error("Python returned an invalid color or volume byte length");
        }
    } else if (kind == "region") {
        item.kind = FS_VALUE_REGION;
        item.height = py::cast<int64_t>(value["h"]);
        item.width = py::cast<int64_t>(value["w"]);
        item.runs = bytes_vector<fs_run_t>(value["runs"], "region runs");
    } else if (kind == "objectset") {
        item.kind = FS_VALUE_OBJECTSET;
        item.height = py::cast<int64_t>(value["h"]);
        item.width = py::cast<int64_t>(value["w"]);
        for (const py::handle object : py::cast<py::list>(value["objects"])) {
            item.objects.push_back(bytes_vector<fs_run_t>(object, "object runs"));
        }
    } else if (kind == "real" || kind == "feature") {
        item.kind = FS_VALUE_REAL;
        item.real = py::cast<double>(value["value"]);
    } else if (kind == "tuple") {
        item.kind = FS_VALUE_TUPLE;
        item.tuple = bytes_vector<double>(value["values"], "tuple");
        if (value.contains("count") && item.tuple.size() != py::cast<size_t>(value["count"])) {
            throw std::runtime_error("Python returned an invalid tuple byte length");
        }
    } else {
        throw std::runtime_error("Python returned an unknown result kind");
    }
    return item;
}

}  // namespace

struct fs_runtime {
    std::atomic<size_t> active{0u};
    std::atomic<bool> closing{false};
};

struct ResultPayload {
    std::vector<Item> items;
};

struct fs_result {
    ResultPayload payload;
};

namespace {

std::mutex g_result_mutex;
struct ResultSlot {
    uint32_t generation = 1u;
    bool retired = false;
    std::shared_ptr<const ResultPayload> payload;
};
std::vector<ResultSlot> g_result_slots;
std::vector<uint32_t> g_free_result_slots;

#if defined(FULLSEYE_C_API_TESTING)
std::mutex g_test_lease_mutex;
std::condition_variable g_test_lease_cv;
bool g_test_pause_after_id_lease = false;
bool g_test_id_lease_acquired = false;
bool g_test_id_lease_resume = false;

void pause_after_id_lease_for_test() {
    std::unique_lock<std::mutex> lock(g_test_lease_mutex);
    if (!g_test_pause_after_id_lease) return;
    g_test_id_lease_acquired = true;
    g_test_lease_cv.notify_all();
    g_test_lease_cv.wait(lock, [] { return g_test_id_lease_resume; });
}
#endif

fs_result_id_t make_result_id(uint32_t index, uint32_t generation) {
    return (static_cast<fs_result_id_t>(generation) << 32u)
        | static_cast<fs_result_id_t>(index + 1u);
}

bool split_result_id(fs_result_id_t id, uint32_t *index, uint32_t *generation) {
    const uint64_t raw_index = id & UINT64_C(0xffffffff);
    const uint64_t raw_generation = id >> 32u;
    if (raw_index == 0u || raw_generation == 0u
        || raw_index > static_cast<uint64_t>(std::numeric_limits<uint32_t>::max())) {
        return false;
    }
    *index = static_cast<uint32_t>(raw_index - 1u);
    *generation = static_cast<uint32_t>(raw_generation);
    return true;
}

class ResultIdLease {
public:
    explicit ResultIdLease(fs_result_id_t result) noexcept {
        try {
            uint32_t index = 0u;
            uint32_t generation = 0u;
            if (!split_result_id(result, &index, &generation)) {
                return;
            }
            {
                std::lock_guard<std::mutex> lock(g_result_mutex);
                if (index < g_result_slots.size()) {
                    const ResultSlot &slot = g_result_slots[index];
                    if (slot.generation == generation) {
                        payload_ = slot.payload;
                    }
                }
            }
#if defined(FULLSEYE_C_API_TESTING)
            if (payload_) pause_after_id_lease_for_test();
#endif
        } catch (const std::bad_alloc &) {
            status_ = FS_E_OUT_OF_MEMORY;
        } catch (...) {
            status_ = FS_E_INTERNAL;
        }
    }
    const ResultPayload *get() const noexcept { return payload_.get(); }
    explicit operator bool() const noexcept { return static_cast<bool>(payload_); }
    fs_status_t status() const noexcept { return status_; }

private:
    std::shared_ptr<const ResultPayload> payload_;
    fs_status_t status_ = FS_OK;
};

class RuntimeCall {
public:
    explicit RuntimeCall(fs_runtime_t *runtime) noexcept : runtime_(runtime) {
        try {
            std::lock_guard<std::mutex> lock(g_runtime_mutex);
            if (runtime_ == nullptr || g_runtimes.count(runtime_) == 0u
                || runtime_->closing.load(std::memory_order_acquire)) {
                return;
            }
            runtime_->active.fetch_add(1u, std::memory_order_acq_rel);
            entered_ = true;
        } catch (const std::bad_alloc &) {
            status_ = FS_E_OUT_OF_MEMORY;
        } catch (...) {
            status_ = FS_E_INTERNAL;
        }
    }
    ~RuntimeCall() noexcept { finish(); }
    bool entered() const noexcept { return entered_; }
    fs_status_t status() const noexcept { return status_; }

private:
    void finish() noexcept {
        try {
            if (runtime_ == nullptr || finished_ || !entered_) {
                finished_ = true;
                return;
            }
            finished_ = true;
            std::lock_guard<std::mutex> lock(g_runtime_mutex);
            const size_t remaining = runtime_->active.fetch_sub(1u, std::memory_order_acq_rel) - 1u;
            if (remaining == 0u && runtime_->closing.load(std::memory_order_acquire)) {
                g_runtimes.erase(runtime_);
                delete runtime_;
            }
        } catch (...) {
            // C ABI cleanup must not throw during stack unwinding. A mutex
            // failure leaves the runtime alive rather than crossing C. /
            // C ABI の後始末は巻き戻し中に例外を出さない。mutex 失敗時は C 境界を
            // 越えず runtime を残す。
        }
    }
    fs_runtime_t *runtime_ = nullptr;
    bool entered_ = false;
    bool finished_ = false;
    fs_status_t status_ = FS_OK;
};

fs_status_t access_item(const ResultPayload *result, size_t index, fs_value_kind_t expected,
                        const Item **out) {
    if (result == nullptr || out == nullptr || index >= result->items.size()) {
        return FS_E_INVALID_ARG;
    }
    const Item &item = result->items[index];
    if (item.kind != expected) {
        return FS_E_TYPE;
    }
    *out = &item;
    return FS_OK;
}

bool copy_text_span(const char *text, size_t bytes, bool optional, std::string *out) {
    if (text == nullptr) {
        return optional && bytes == 0u;
    }
    out->assign(text, bytes);
    return true;
}

fs_result_id_t register_result(std::shared_ptr<const ResultPayload> payload) {
    std::lock_guard<std::mutex> lock(g_result_mutex);
    uint32_t index = 0u;
    if (!g_free_result_slots.empty()) {
        index = g_free_result_slots.back();
        g_free_result_slots.pop_back();
        if (g_result_slots[index].retired) {
            return 0u;
        }
        g_result_slots[index].payload = std::move(payload);
    } else {
        if (g_result_slots.size() >= std::numeric_limits<uint32_t>::max()) {
            return 0u;
        }
        index = static_cast<uint32_t>(g_result_slots.size());
        g_result_slots.push_back(ResultSlot{});
        g_result_slots.back().payload = std::move(payload);
    }
    return make_result_id(index, g_result_slots[index].generation);
}

fs_status_t release_result_id(fs_result_id_t result) {
    uint32_t index = 0u;
    uint32_t generation = 0u;
    if (!split_result_id(result, &index, &generation)) {
        return FS_E_INVALID_ARG;
    }
    std::lock_guard<std::mutex> lock(g_result_mutex);
    if (index >= g_result_slots.size() || g_result_slots[index].generation != generation
        || !g_result_slots[index].payload) {
        return FS_E_INVALID_ARG;
    }
    ResultSlot &slot = g_result_slots[index];
    slot.payload.reset();
    if (slot.generation == std::numeric_limits<uint32_t>::max()) {
        // Never wrap a generation: an ID that was once invalid must never
        // become valid again. / 世代は一周させず、失効 ID を再有効化しない。
        slot.retired = true;
    } else {
        ++slot.generation;
        g_free_result_slots.push_back(index);
    }
    return FS_OK;
}

}  // namespace

extern "C" {

#if defined(FULLSEYE_C_API_TESTING)
FS_API fs_status_t FS_CALL fs_test_result_id_seed_next_generation(uint32_t generation) {
    try {
        if (generation == 0u) return FS_E_INVALID_ARG;
        std::lock_guard<std::mutex> lock(g_result_mutex);
        if (g_free_result_slots.empty()) return FS_E_INVALID_ARG;
        const uint32_t index = g_free_result_slots.back();
        ResultSlot &slot = g_result_slots[index];
        if (slot.payload || slot.retired) return FS_E_INVALID_ARG;
        slot.generation = generation;
        return FS_OK;
    } catch (const std::bad_alloc &) {
        return FS_E_OUT_OF_MEMORY;
    } catch (...) {
        return FS_E_INTERNAL;
    }
}

FS_API fs_status_t FS_CALL fs_test_result_id_pause_after_lease(int enabled) {
    try {
        std::lock_guard<std::mutex> lock(g_test_lease_mutex);
        g_test_pause_after_id_lease = enabled != 0;
        g_test_id_lease_acquired = false;
        g_test_id_lease_resume = !g_test_pause_after_id_lease;
        return FS_OK;
    } catch (const std::bad_alloc &) {
        return FS_E_OUT_OF_MEMORY;
    } catch (...) {
        return FS_E_INTERNAL;
    }
}

FS_API fs_status_t FS_CALL fs_test_result_id_wait_for_lease(uint32_t timeout_ms) {
    try {
        std::unique_lock<std::mutex> lock(g_test_lease_mutex);
        const bool acquired = g_test_lease_cv.wait_for(lock, std::chrono::milliseconds(timeout_ms), [] {
            return g_test_id_lease_acquired;
        });
        return acquired ? FS_OK : FS_E_BUSY;
    } catch (const std::bad_alloc &) {
        return FS_E_OUT_OF_MEMORY;
    } catch (...) {
        return FS_E_INTERNAL;
    }
}

FS_API fs_status_t FS_CALL fs_test_result_id_resume_lease(void) {
    try {
        std::lock_guard<std::mutex> lock(g_test_lease_mutex);
        g_test_id_lease_resume = true;
        g_test_lease_cv.notify_all();
        return FS_OK;
    } catch (const std::bad_alloc &) {
        return FS_E_OUT_OF_MEMORY;
    } catch (...) {
        return FS_E_INTERNAL;
    }
}
#endif

FS_API size_t FS_CALL fs_runtime_diagnose(char *buf, size_t capacity) {
    try {
        const std::string message = discovery_report(discover_runtime("", ""));
        const size_t needed = message.size() + 1u;
        if (buf != nullptr && capacity != 0u) {
            const size_t copied = std::min(message.size(), capacity - 1u);
            if (copied != 0u) std::memcpy(buf, message.data(), copied);
            buf[copied] = '\0';
        }
        return needed;
    } catch (...) {
        static constexpr char fallback[] = "Fullseye runtime discovery could not inspect this process.";
        if (buf != nullptr && capacity != 0u) {
            const size_t copied = std::min(sizeof(fallback) - 1u, capacity - 1u);
            std::memcpy(buf, fallback, copied);
            buf[copied] = '\0';
        }
        return sizeof(fallback);
    }
}

FS_API fs_status_t FS_CALL fs_runtime_create(const fs_init_options_t *options, fs_runtime_t **out) {
    if (out != nullptr) {
        *out = nullptr;
    }
    try {
        if (options == nullptr || out == nullptr) {
            set_error(nullptr, "options and out must not be NULL");
            return FS_E_INVALID_ARG;
        }
        if (options->struct_size < kRequiredInitSize) {
            set_error(nullptr, "fs_init_options_t.struct_size is too small");
            return FS_E_INVALID_ARG;
        }
        if (options->abi_major != FULLSEYE_ABI_VERSION_MAJOR
            || options->abi_minor > FULLSEYE_ABI_VERSION_MINOR) {
            set_error(nullptr, "requested ABI version is not compatible with this runtime");
            return FS_E_UNSUPPORTED;
        }
        if ((options->flags & FS_INIT_ISOLATED) == 0u) {
            set_error(nullptr, "FS_INIT_ISOLATED is mandatory");
            return FS_E_INVALID_ARG;
        }
        const bool bounded_options = options->abi_minor >= 2u;
        if (bounded_options && options->struct_size < kRequiredInitNSize) {
            set_error(nullptr, "ABI 0.2 fs_init_options_t.struct_size is too small");
            return FS_E_INVALID_ARG;
        }
        std::string root;
        std::string home;
        if (bounded_options) {
            if ((options->runtime_root == nullptr && options->runtime_root_bytes != 0u)
                || (options->runtime_root != nullptr && options->runtime_root_bytes == 0u)
                || (options->python_home == nullptr && options->python_home_bytes != 0u)
                || (options->python_home != nullptr && options->python_home_bytes == 0u)) {
                set_error(nullptr, "ABI 0.2 runtime_root and python_home pointers must match their byte lengths");
                return FS_E_INVALID_ARG;
            }
            if (options->runtime_root_bytes > kMaxRuntimePathBytes
                || options->python_home_bytes > kMaxRuntimePathBytes) {
                set_error(nullptr, "ABI 0.2 runtime_root and python_home exceed the 98301-byte path limit");
                return FS_E_INVALID_ARG;
            }
            if (options->runtime_root != nullptr) {
                if (std::memchr(options->runtime_root, '\0', options->runtime_root_bytes) != nullptr) {
                    set_error(nullptr, "ABI 0.2 runtime_root must not contain NUL bytes");
                    return FS_E_INVALID_ARG;
                }
                root.assign(options->runtime_root, options->runtime_root_bytes);
            }
            if (options->python_home != nullptr) {
                if (std::memchr(options->python_home, '\0', options->python_home_bytes) != nullptr) {
                    set_error(nullptr, "ABI 0.2 python_home must not contain NUL bytes");
                    return FS_E_INVALID_ARG;
                }
                home.assign(options->python_home, options->python_home_bytes);
            }
        } else {
            root = options->runtime_root == nullptr ? "" : options->runtime_root;
            home = options->python_home == nullptr ? "" : options->python_home;
        }
        // Preserve the one-interpreter-per-process contract before automatic
        // recovery can consider a different environment. / 同一 process の
        // Python 設定が固定済みなら、自動探索より先に明示指定の食い違いを拒否する。
        if (!root.empty()) {
            std::lock_guard<std::mutex> lock(g_python_mutex);
            if (g_python_ready && root != g_python_root) {
                set_error(nullptr, "the CPython runtime is already configured for a different runtime_root or python_home");
                return FS_E_INVALID_ARG;
            }
        }
        const RuntimeDiscovery discovery = discover_runtime(root, home);
        if (!discovery.found) {
            set_error(nullptr, discovery_report(discovery));
            return FS_E_NO_PYTHON;
        }
        const PythonInitResult init = initialize_python(
            discovery.root, discovery.home,
            (options->flags & FS_INIT_ALLOW_HOST_PYTHON_UNSAFE) != 0u);
        if (init.status != FS_OK) {
            set_error(nullptr, init.error);
            return init.status;
        }
        std::clog << "Fullseye runtime: using " << discovery.source << ": " << discovery.root << '\n';
        auto *runtime = new fs_runtime_t();
        {
            std::lock_guard<std::mutex> lock(g_runtime_mutex);
            g_runtimes.insert(runtime);
        }
        *out = runtime;
        clear_error(runtime);
        return FS_OK;
    } catch (const std::bad_alloc &) {
        set_error(nullptr, "out of memory while creating the runtime");
        return FS_E_OUT_OF_MEMORY;
    } catch (const std::exception &exc) {
        set_error(nullptr, exc.what());
        return FS_E_INTERNAL;
    } catch (...) {
        set_error(nullptr, "unknown error while creating the runtime");
        return FS_E_INTERNAL;
    }
}

FS_API void FS_CALL fs_runtime_destroy(fs_runtime_t *runtime) {
    try {
        if (runtime == nullptr) {
            return;
        }
        std::lock_guard<std::mutex> lock(g_runtime_mutex);
        if (g_runtimes.count(runtime) == 0u) {
            return;
        }
        runtime->closing.store(true, std::memory_order_release);
        if (runtime->active.load(std::memory_order_acquire) == 0u) {
            g_runtimes.erase(runtime);
            delete runtime;
        }
    } catch (...) {
        // Void C API functions cannot return a status. Never allow a C++
        // exception to cross the ABI boundary. / void の C API は状態を返せないので、
        // C++ 例外を ABI 境界の外へ出さない。
    }
}

FS_API fs_status_t FS_CALL fs_find_ops_json(fs_runtime_t *runtime, const char *query_json,
                                             char **out_utf8, size_t *out_bytes) {
    if (query_json == nullptr) {
        if (out_utf8 != nullptr) *out_utf8 = nullptr;
        if (out_bytes != nullptr) *out_bytes = 0u;
        set_error(runtime, "query_json must not be NULL");
        return FS_E_INVALID_ARG;
    }
    return fs_find_ops_json_n(runtime, query_json, std::strlen(query_json), out_utf8, out_bytes);
}

FS_API fs_status_t FS_CALL fs_find_ops_json_n(fs_runtime_t *runtime, const char *query_json,
                                               size_t query_json_bytes, char **out_utf8,
                                               size_t *out_bytes) {
    if (out_utf8 != nullptr) {
        *out_utf8 = nullptr;
    }
    if (out_bytes != nullptr) {
        *out_bytes = 0u;
    }
    if (runtime == nullptr || out_utf8 == nullptr || out_bytes == nullptr) {
        set_error(runtime, "runtime, out_utf8, and out_bytes must not be NULL");
        return FS_E_INVALID_ARG;
    }
    if (query_json_bytes > kMaxJsonBytes) {
        set_error(runtime, "query_json exceeds the 1 MiB C API byte limit");
        return FS_E_INVALID_ARG;
    }
    try {
        std::string query;
        if (!copy_text_span(query_json, query_json_bytes, true, &query)) {
            set_error(runtime, "query_json is NULL with a non-zero byte length");
            return FS_E_INVALID_ARG;
        }
        RuntimeCall call(runtime);
        if (call.status() != FS_OK) {
            set_error(runtime, "could not enter the runtime call");
            return call.status();
        }
        if (!call.entered()) {
            set_error(runtime, "runtime is closing");
            return FS_E_BUSY;
        }
        py::gil_scoped_acquire acquire;
        const py::object bridge = py::module_::import("fullseye.c_api_bridge");
        const std::string text = py::cast<std::string>(bridge.attr("find_ops")(
            query_json == nullptr ? py::none() : py::cast(query)));
        char *copy = static_cast<char *>(std::malloc(text.size() + 1u));
        if (copy == nullptr) {
            set_error(runtime, "out of memory while copying search results");
            return FS_E_OUT_OF_MEMORY;
        }
        std::memcpy(copy, text.c_str(), text.size() + 1u);
        *out_utf8 = copy;
        *out_bytes = text.size() + 1u;
        clear_error(runtime);
        return FS_OK;
    } catch (const py::error_already_set &exc) {
        set_error(runtime, exc.what());
        return FS_E_BAD_PARAMS;
    } catch (const std::bad_alloc &) {
        set_error(runtime, "out of memory while searching operators");
        return FS_E_OUT_OF_MEMORY;
    } catch (const std::exception &exc) {
        set_error(runtime, exc.what());
        return FS_E_INTERNAL;
    } catch (...) {
        set_error(runtime, "unknown error while searching operators");
        return FS_E_INTERNAL;
    }
}

FS_API fs_status_t FS_CALL fs_call(fs_runtime_t *runtime, const char *op_id,
                                    const fs_input_t *inputs, size_t input_count,
                                    const char *params_json, fs_result_t **out) {
    if (out != nullptr) {
        *out = nullptr;
    }
    if (runtime == nullptr || op_id == nullptr || params_json == nullptr || out == nullptr
        || (input_count != 0u && inputs == nullptr)) {
        set_error(runtime, "runtime, C strings, inputs, and out must satisfy the ABI 0.1 contract");
        return FS_E_INVALID_ARG;
    }
    try {
        RuntimeCall call(runtime);
        if (call.status() != FS_OK) {
            set_error(runtime, "could not enter the runtime call");
            return call.status();
        }
        if (!call.entered()) {
            set_error(runtime, "runtime is closing");
            return FS_E_BUSY;
        }
        py::gil_scoped_acquire acquire;
        py::list values;
        for (size_t index = 0; index < input_count; ++index) {
            const fs_input_t &input = inputs[index];
            if (input.struct_size < kRequiredInputSize) {
                set_error(runtime, "fs_input_t.struct_size is too small");
                return FS_E_INVALID_ARG;
            }
            if (input.result != nullptr) {
                if (input.result_index >= input.result->payload.items.size()) {
                    set_error(runtime, "result_index is out of range");
                    return FS_E_INVALID_ARG;
                }
                const Item &item = input.result->payload.items[input.result_index];
                if (input.kind != item.kind) {
                    set_error(runtime, "fs_input_t.kind does not match the borrowed result");
                    return FS_E_TYPE;
                }
                values.append(item_to_python(item));
            } else {
                if (input.kind != FS_VALUE_IMAGE) {
                    set_error(runtime, "non-image inputs must borrow an earlier result");
                    return FS_E_INVALID_ARG;
                }
                const fs_status_t status = validate_image(runtime, input.image);
                if (status != FS_OK) return status;
                values.append(image_to_python(input.image));
            }
        }
        const py::object bridge = py::module_::import("fullseye.c_api_bridge");
        const py::dict answer = py::cast<py::dict>(bridge.attr("call")(op_id, values, params_json));
        const auto status = static_cast<fs_status_t>(py::cast<int>(answer["status"]));
        if (status != FS_OK) {
            set_error(runtime, py::cast<std::string>(answer["message"]));
            return status;
        }
        auto result = std::make_unique<fs_result_t>();
        for (const py::handle value : py::cast<py::list>(answer["outputs"])) {
            result->payload.items.push_back(python_to_item(py::cast<py::dict>(value)));
        }
        *out = result.release();
        clear_error(runtime);
        return FS_OK;
    } catch (const py::error_already_set &exc) {
        set_error(runtime, exc.what()); return FS_E_PY_EXCEPTION;
    } catch (const std::bad_alloc &) {
        set_error(runtime, "out of memory while running the operator"); return FS_E_OUT_OF_MEMORY;
    } catch (const std::exception &exc) {
        set_error(runtime, exc.what()); return FS_E_INTERNAL;
    } catch (...) {
        set_error(runtime, "unknown error while running the operator"); return FS_E_INTERNAL;
    }
}

FS_API fs_status_t FS_CALL fs_call_id_n(fs_runtime_t *runtime, const char *op_id,
                                         size_t op_id_bytes, const fs_input_n_t *inputs,
                                         size_t input_count, const char *params_json,
                                         size_t params_json_bytes, fs_result_id_t *out) {
    if (out != nullptr) {
        *out = 0u;
    }
    if (runtime == nullptr || op_id == nullptr || out == nullptr
        || (input_count != 0u && inputs == nullptr)) {
        set_error(runtime, "runtime, op_id, inputs, and out must satisfy the C API contract");
        return FS_E_INVALID_ARG;
    }
    if (op_id_bytes > kMaxOperatorIdBytes) {
        set_error(runtime, "op_id exceeds the 256 B C API byte limit");
        return FS_E_INVALID_ARG;
    }
    if (params_json_bytes > kMaxJsonBytes) {
        set_error(runtime, "params_json exceeds the 1 MiB C API byte limit");
        return FS_E_INVALID_ARG;
    }
    try {
        std::string op;
        std::string params;
        if (!copy_text_span(op_id, op_id_bytes, false, &op)
            || !copy_text_span(params_json, params_json_bytes, true, &params)) {
            set_error(runtime, "a string pointer is NULL with a non-zero byte length");
            return FS_E_INVALID_ARG;
        }
        RuntimeCall call(runtime);
        if (call.status() != FS_OK) {
            set_error(runtime, "could not enter the runtime call");
            return call.status();
        }
        if (!call.entered()) {
            set_error(runtime, "runtime is closing");
            return FS_E_BUSY;
        }
        py::gil_scoped_acquire acquire;
        py::list values;
        std::vector<ResultIdLease> borrowed_results;
        for (size_t index = 0; index < input_count; ++index) {
            const fs_input_n_t &input = inputs[index];
            if (input.struct_size < kRequiredInputNSize) {
                set_error(runtime, "fs_input_n_t.struct_size is too small");
                return FS_E_INVALID_ARG;
            }
            if (input.result_id != 0u) {
                borrowed_results.emplace_back(input.result_id);
                const ResultPayload *borrowed = borrowed_results.back().get();
                if (borrowed == nullptr || input.result_index >= borrowed->items.size()) {
                    set_error(runtime, "result_index is out of range");
                    return FS_E_INVALID_ARG;
                }
                const Item &item = borrowed->items[input.result_index];
                if (input.kind != item.kind) {
                    set_error(runtime, "fs_input_n_t.kind does not match the borrowed result");
                    return FS_E_TYPE;
                }
                values.append(item_to_python(item));
            } else {
                if (input.kind == FS_VALUE_IMAGE) {
                    const fs_status_t status = validate_image(runtime, input.image);
                    if (status != FS_OK) return status;
                    values.append(image_to_python(input.image));
                } else if (input.kind == FS_VALUE_COLOR || input.kind == FS_VALUE_VOLUME) {
                    if (input.struct_size < kTypedInputNSize) {
                        set_error(runtime, "typed array input requires the extended fs_input_n_t");
                        return FS_E_UNSUPPORTED;
                    }
                    const fs_status_t status = validate_array(runtime, input.array, input.kind);
                    if (status != FS_OK) return status;
                    values.append(array_to_python(input.array, input.kind));
                } else if (input.kind == FS_VALUE_FEATURE) {
                    if (input.struct_size < kTypedInputNSize || !std::isfinite(input.feature)) {
                        set_error(runtime, "feature input requires a finite value in the extended fs_input_n_t");
                        return input.struct_size < kTypedInputNSize ? FS_E_UNSUPPORTED : FS_E_INVALID_ARG;
                    }
                    py::dict value;
                    value["kind"] = "feature";
                    value["value"] = input.feature;
                    values.append(std::move(value));
                } else {
                    set_error(runtime, "non-image inputs must borrow an earlier result or use a typed C ABI kind");
                    return FS_E_INVALID_ARG;
                }
            }
        }
        const py::object bridge = py::module_::import("fullseye.c_api_bridge");
        const py::dict answer = py::cast<py::dict>(bridge.attr("call")(
            op, values, params_json == nullptr ? py::none() : py::cast(params)));
        const int status_value = py::cast<int>(answer["status"]);
        const auto status = static_cast<fs_status_t>(status_value);
        if (status != FS_OK) {
            set_error(runtime, py::cast<std::string>(answer["message"]));
            return status;
        }
        auto payload = std::make_shared<ResultPayload>();
        for (const py::handle value : py::cast<py::list>(answer["outputs"])) {
            payload->items.push_back(python_to_item(py::cast<py::dict>(value)));
        }
        const fs_result_id_t id = register_result(std::move(payload));
        if (id == 0u) {
            set_error(runtime, "result handle table is exhausted");
            return FS_E_OUT_OF_MEMORY;
        }
        *out = id;
        clear_error(runtime);
        return FS_OK;
    } catch (const py::error_already_set &exc) {
        set_error(runtime, exc.what());
        return FS_E_PY_EXCEPTION;
    } catch (const std::bad_alloc &) {
        set_error(runtime, "out of memory while running the operator");
        return FS_E_OUT_OF_MEMORY;
    } catch (const std::exception &exc) {
        set_error(runtime, exc.what());
        return FS_E_INTERNAL;
    } catch (...) {
        set_error(runtime, "unknown error while running the operator");
        return FS_E_INTERNAL;
    }
}

FS_API size_t FS_CALL fs_result_count(const fs_result_t *result) {
    return result == nullptr ? 0u : result->payload.items.size();
}

FS_API fs_status_t FS_CALL fs_result_kind(const fs_result_t *result, size_t index,
                                           fs_value_kind_t *out) {
    if (result == nullptr || out == nullptr || index >= result->payload.items.size()) {
        return FS_E_INVALID_ARG;
    }
    *out = result->payload.items[index].kind;
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_image(const fs_result_t *result, size_t index,
                                            fs_image_view_t *out_borrowed) {
    const Item *item = nullptr;
    const fs_status_t status = result == nullptr ? FS_E_INVALID_ARG
        : access_item(&result->payload, index, FS_VALUE_IMAGE, &item);
    if (status != FS_OK || out_borrowed == nullptr) {
        return out_borrowed == nullptr ? FS_E_INVALID_ARG : status;
    }
    if (out_borrowed->struct_size < kRequiredImageSize) {
        return FS_E_INVALID_ARG;
    }
    out_borrowed->data = item->image.data();
    out_borrowed->data_bytes = item->image.size() * sizeof(double);
    out_borrowed->width = item->width;
    out_borrowed->height = item->height;
    out_borrowed->row_stride_bytes = item->width * static_cast<int64_t>(sizeof(double));
    out_borrowed->dtype = FS_DTYPE_F64;
    out_borrowed->range_lo = item->range_lo;
    out_borrowed->range_hi = item->range_hi;
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_region_runs(const fs_result_t *result, size_t index,
                                                  const fs_run_t **out_borrowed,
                                                  size_t *out_count) {
    const Item *item = nullptr;
    const fs_status_t status = result == nullptr ? FS_E_INVALID_ARG
        : access_item(&result->payload, index, FS_VALUE_REGION, &item);
    if (status != FS_OK || out_borrowed == nullptr || out_count == nullptr) {
        return status != FS_OK ? status : FS_E_INVALID_ARG;
    }
    *out_borrowed = item->runs.data();
    *out_count = item->runs.size();
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_object_count(const fs_result_t *result, size_t index,
                                                   size_t *out_count) {
    const Item *item = nullptr;
    const fs_status_t status = result == nullptr ? FS_E_INVALID_ARG
        : access_item(&result->payload, index, FS_VALUE_OBJECTSET, &item);
    if (status != FS_OK || out_count == nullptr) {
        return status != FS_OK ? status : FS_E_INVALID_ARG;
    }
    *out_count = item->objects.size();
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_object_runs(const fs_result_t *result, size_t index,
                                                  size_t object_index,
                                                  const fs_run_t **out_borrowed,
                                                  size_t *out_count) {
    const Item *item = nullptr;
    const fs_status_t status = result == nullptr ? FS_E_INVALID_ARG
        : access_item(&result->payload, index, FS_VALUE_OBJECTSET, &item);
    if (status != FS_OK || out_borrowed == nullptr || out_count == nullptr
        || object_index >= item->objects.size()) {
        return status != FS_OK ? status : FS_E_INVALID_ARG;
    }
    *out_borrowed = item->objects[object_index].data();
    *out_count = item->objects[object_index].size();
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_real(const fs_result_t *result, size_t index, double *out) {
    const Item *item = nullptr;
    const fs_status_t status = result == nullptr ? FS_E_INVALID_ARG
        : access_item(&result->payload, index, FS_VALUE_REAL, &item);
    if (status != FS_OK || out == nullptr) {
        return status != FS_OK ? status : FS_E_INVALID_ARG;
    }
    *out = item->real;
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_tuple_size(const fs_result_t *result, size_t index,
                                                 size_t *out_count) {
    const Item *item = nullptr;
    const fs_status_t status = result == nullptr ? FS_E_INVALID_ARG
        : access_item(&result->payload, index, FS_VALUE_TUPLE, &item);
    if (status != FS_OK || out_count == nullptr) {
        return status != FS_OK ? status : FS_E_INVALID_ARG;
    }
    *out_count = item->tuple.size();
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_tuple_real(const fs_result_t *result, size_t index,
                                                 size_t element_index, double *out) {
    const Item *item = nullptr;
    const fs_status_t status = result == nullptr ? FS_E_INVALID_ARG
        : access_item(&result->payload, index, FS_VALUE_TUPLE, &item);
    if (status != FS_OK || out == nullptr || element_index >= item->tuple.size()) {
        return status != FS_OK ? status : FS_E_INVALID_ARG;
    }
    *out = item->tuple[element_index];
    return FS_OK;
}

FS_API void FS_CALL fs_result_release(fs_result_t *result) {
    delete result;
}

FS_API fs_status_t FS_CALL fs_result_count_n(fs_result_id_t result, size_t *out_count) {
    ResultIdLease lease(result);
    if (lease.status() != FS_OK) return lease.status();
    if (!lease || out_count == nullptr) return FS_E_INVALID_ARG;
    *out_count = lease.get()->items.size();
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_kind_n(fs_result_id_t result, size_t index,
    fs_value_kind_t *out) {
    ResultIdLease lease(result);
    if (lease.status() != FS_OK) return lease.status();
    if (!lease || out == nullptr || index >= lease.get()->items.size()) return FS_E_INVALID_ARG;
    *out = lease.get()->items[index].kind;
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_image_n(fs_result_id_t result, size_t index,
                                               fs_image_view_t *out_borrowed) {
    ResultIdLease lease(result);
    if (lease.status() != FS_OK) return lease.status();
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_IMAGE, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out_borrowed == nullptr) return status != FS_OK ? status : FS_E_INVALID_ARG;
    if (out_borrowed->struct_size < kRequiredImageSize) return FS_E_INVALID_ARG;
    out_borrowed->data = item->image.data();
    out_borrowed->data_bytes = item->image.size() * sizeof(double);
    out_borrowed->width = item->width;
    out_borrowed->height = item->height;
    out_borrowed->row_stride_bytes = item->width * static_cast<int64_t>(sizeof(double));
    out_borrowed->dtype = FS_DTYPE_F64;
    out_borrowed->range_lo = item->range_lo;
    out_borrowed->range_hi = item->range_hi;
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_array_n(fs_result_id_t result, size_t index,
                                               fs_array_view_t *out_borrowed) {
    ResultIdLease lease(result);
    if (lease.status() != FS_OK) return lease.status();
    if (!lease || out_borrowed == nullptr || out_borrowed->struct_size < kRequiredArraySize
        || index >= lease.get()->items.size()) return FS_E_INVALID_ARG;
    const Item &item = lease.get()->items[index];
    if (item.kind != FS_VALUE_COLOR && item.kind != FS_VALUE_VOLUME) return FS_E_TYPE;
    out_borrowed->data = item.array.data();
    out_borrowed->data_bytes = item.array.size() * sizeof(double);
    out_borrowed->ndim = static_cast<uint32_t>(item.shape.size());
    for (uint32_t i = 0u; i < 4u; ++i) {
        out_borrowed->shape[i] = i < item.shape.size() ? item.shape[i] : 0;
        size_t stride = sizeof(double);
        for (size_t j = item.shape.size(); j > static_cast<size_t>(i + 1u); --j) {
            stride *= static_cast<size_t>(item.shape[j - 1u]);
        }
        out_borrowed->stride_bytes[i] = i < item.shape.size() ? static_cast<int64_t>(stride) : 0;
    }
    out_borrowed->dtype = FS_DTYPE_F64;
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_region_runs_n(fs_result_id_t result, size_t index,
                                                     const fs_run_t **out_borrowed, size_t *out_count) {
    ResultIdLease lease(result);
    if (lease.status() != FS_OK) return lease.status();
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_REGION, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out_borrowed == nullptr || out_count == nullptr) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out_borrowed = item->runs.data(); *out_count = item->runs.size(); return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_object_count_n(fs_result_id_t result, size_t index,
                                                      size_t *out_count) {
    ResultIdLease lease(result);
    if (lease.status() != FS_OK) return lease.status();
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_OBJECTSET, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out_count == nullptr) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out_count = item->objects.size(); return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_object_runs_n(fs_result_id_t result, size_t index,
                                                     size_t object_index, const fs_run_t **out_borrowed,
                                                     size_t *out_count) {
    ResultIdLease lease(result);
    if (lease.status() != FS_OK) return lease.status();
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_OBJECTSET, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out_borrowed == nullptr || out_count == nullptr || object_index >= item->objects.size()) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out_borrowed = item->objects[object_index].data(); *out_count = item->objects[object_index].size(); return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_real_n(fs_result_id_t result, size_t index, double *out) {
    ResultIdLease lease(result);
    if (lease.status() != FS_OK) return lease.status();
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_REAL, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out == nullptr) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out = item->real; return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_tuple_size_n(fs_result_id_t result, size_t index,
                                                    size_t *out_count) {
    ResultIdLease lease(result);
    if (lease.status() != FS_OK) return lease.status();
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_TUPLE, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out_count == nullptr) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out_count = item->tuple.size(); return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_tuple_real_n(fs_result_id_t result, size_t index,
                                                    size_t element_index, double *out) {
    ResultIdLease lease(result);
    if (lease.status() != FS_OK) return lease.status();
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_TUPLE, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out == nullptr || element_index >= item->tuple.size()) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out = item->tuple[element_index]; return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_release_n(fs_result_id_t result) {
    try {
        const fs_status_t status = release_result_id(result);
        if (status != FS_OK) set_error(nullptr, "result ID is unknown or has already been released");
        else clear_error(nullptr);
        return status;
    } catch (const std::bad_alloc &) {
        set_error(nullptr, "out of memory while releasing the result ID");
        return FS_E_OUT_OF_MEMORY;
    } catch (const std::exception &exc) {
        set_error(nullptr, exc.what());
        return FS_E_INTERNAL;
    } catch (...) {
        set_error(nullptr, "unknown error while releasing the result ID");
        return FS_E_INTERNAL;
    }
}

FS_API void FS_CALL fs_free(void *library_allocated) {
    std::free(library_allocated);
}

FS_API size_t FS_CALL fs_last_error(fs_runtime_t *runtime, char *buf, size_t capacity) {
    const bool matches = g_error.runtime == runtime || runtime == nullptr;
    const size_t length = matches ? g_error.length : 0u;
    const size_t required = length + 1u;
    if (buf != nullptr && capacity != 0u) {
        const size_t copied = std::min(length, capacity - 1u);
        std::memcpy(buf, g_error.message, copied);
        buf[copied] = '\0';
    }
    return required;
}

FS_API fs_status_t FS_CALL fs_abi_version(int32_t *major, int32_t *minor) {
    if (major == nullptr || minor == nullptr) {
        return FS_E_INVALID_ARG;
    }
    *major = FULLSEYE_ABI_VERSION_MAJOR;
    *minor = FULLSEYE_ABI_VERSION_MINOR;
    return FS_OK;
}

FS_API size_t FS_CALL fs_runtime_version(fs_runtime_t *runtime, char *buf, size_t capacity) {
    if (runtime == nullptr) {
        return 0u;
    }
    try {
        RuntimeCall call(runtime);
        if (call.status() != FS_OK) {
            set_error(runtime, "could not enter the runtime call");
            return 0u;
        }
        if (!call.entered()) {
            set_error(runtime, "runtime is closing");
            return 0u;
        }
        py::gil_scoped_acquire acquire;
        const std::string version = py::cast<std::string>(py::module_::import("fullseye").attr("version")());
        const size_t required = version.size() + 1u;
        if (buf != nullptr && capacity != 0u) {
            const size_t copied = std::min(version.size(), capacity - 1u);
            std::memcpy(buf, version.data(), copied);
            buf[copied] = '\0';
        }
        clear_error(runtime);
        return required;
    } catch (const std::exception &exc) {
        set_error(runtime, exc.what());
        return 0u;
    } catch (...) {
        set_error(runtime, "unknown error while reading the runtime version");
        return 0u;
    }
}

}  // extern "C"
