// Copyright (c) 2026 Kazufumi Furuse. Apache-2.0.
// pybind11 embedded C ABI / pybind11 埋め込み C ABI。
#include "fullseye.h"

#include <pybind11/embed.h>
#include <pybind11/numpy.h>

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <limits>
#include <mutex>
#include <new>
#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace py = pybind11;

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
constexpr size_t kMaxErrorBytes = 4096u;

struct Item {
    fs_value_kind_t kind = FS_VALUE_REAL;
    int64_t height = 0;
    int64_t width = 0;
    double range_lo = 0.0;
    double range_hi = 1.0;
    std::vector<double> image;
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
std::string g_python_error;
bool g_python_owned = false;
std::string g_python_root;
std::string g_python_home;
std::mutex g_python_mutex;
std::mutex g_runtime_mutex;
std::unordered_set<fs_runtime_t *> g_runtimes;

void set_error(const fs_runtime_t *runtime, std::string message) {
    g_error.runtime = runtime;
    g_error.length = std::min(message.size(), kMaxErrorBytes);
    std::memcpy(g_error.message, message.data(), g_error.length);
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

fs_status_t initialize_python(const std::string &root, const std::string &home,
                              bool allow_host) {
    std::lock_guard<std::mutex> lock(g_python_mutex);
    if (g_python_ready) {
        if (g_python_root != root || g_python_home != home) {
            g_python_error = "the CPython runtime is already configured for a different runtime_root or python_home";
            return FS_E_INVALID_ARG;
        }
        if (!g_python_owned && !allow_host) {
            g_python_error = "the existing CPython host requires FS_INIT_ALLOW_HOST_PYTHON_UNSAFE";
            return FS_E_INVALID_ARG;
        }
        return FS_OK;
    }
    try {
        const bool was_running = Py_IsInitialized() != 0;
        if (was_running && !allow_host) {
            g_python_error = "FS_INIT_ISOLATED cannot use an existing CPython; set FS_INIT_ALLOW_HOST_PYTHON_UNSAFE to opt in to the host interpreter";
            return FS_E_INVALID_ARG;
        }
        if (!was_running) {
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
                    throw std::runtime_error(message);
                }
            }
            py::initialize_interpreter(&config, 0, nullptr, false);
            add_runtime_paths(root);
            py::module_::import("fullseye.c_api_bridge");
            g_python_owned = true;
            // CPython remains alive until process exit; native callers acquire
            // the GIL for every later call. / 終了まで生かし、各呼出しで GIL を取る。
            PyEval_SaveThread();
        } else {
            py::gil_scoped_acquire acquire;
            add_runtime_paths(root);
            py::module_::import("fullseye.c_api_bridge");
            g_python_owned = false;
        }
        g_python_root = root;
        g_python_home = home;
        g_python_ready = true;
        g_python_error.clear();
        return FS_OK;
    } catch (const std::exception &exc) {
        g_python_error = exc.what();
    } catch (...) {
        g_python_error = "unknown error while initializing CPython";
    }
    return FS_E_NO_PYTHON;
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
    } else if (kind == "real") {
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
    std::shared_ptr<const ResultPayload> payload;
};
std::vector<ResultSlot> g_result_slots;
std::vector<uint32_t> g_free_result_slots;

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
    explicit ResultIdLease(fs_result_id_t result) {
        uint32_t index = 0u;
        uint32_t generation = 0u;
        if (!split_result_id(result, &index, &generation)) {
            return;
        }
        std::lock_guard<std::mutex> lock(g_result_mutex);
        if (index < g_result_slots.size()) {
            const ResultSlot &slot = g_result_slots[index];
            if (slot.generation == generation) {
                payload_ = slot.payload;
            }
        }
    }
    const ResultPayload *get() const noexcept { return payload_.get(); }
    explicit operator bool() const noexcept { return static_cast<bool>(payload_); }

private:
    std::shared_ptr<const ResultPayload> payload_;
};

class RuntimeCall {
public:
    explicit RuntimeCall(fs_runtime_t *runtime) : runtime_(runtime) {
        std::lock_guard<std::mutex> lock(g_runtime_mutex);
        if (runtime_ == nullptr || g_runtimes.count(runtime_) == 0u
            || runtime_->closing.load(std::memory_order_acquire)) {
            return;
        }
        runtime_->active.fetch_add(1u, std::memory_order_acq_rel);
        entered_ = true;
    }
    ~RuntimeCall() { finish(); }
    bool entered() const noexcept { return entered_; }

private:
    void finish() {
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
    }
    fs_runtime_t *runtime_ = nullptr;
    bool entered_ = false;
    bool finished_ = false;
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
    ++slot.generation;
    if (slot.generation == 0u) {
        ++slot.generation;
    }
    g_free_result_slots.push_back(index);
    return FS_OK;
}

}  // namespace

extern "C" {

FS_API fs_status_t FS_CALL fs_runtime_create(const fs_init_options_t *options, fs_runtime_t **out) {
    if (out != nullptr) {
        *out = nullptr;
    }
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
    const char *environment_root = std::getenv("FULLSEYE_PYTHON_ROOT");
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
        if (options->runtime_root != nullptr) {
            root.assign(options->runtime_root, options->runtime_root_bytes);
        }
        if (options->python_home != nullptr) {
            home.assign(options->python_home, options->python_home_bytes);
        }
    } else {
        root = options->runtime_root == nullptr ? "" : options->runtime_root;
        home = options->python_home == nullptr ? "" : options->python_home;
    }
    if (root.empty() && environment_root != nullptr && *environment_root != '\0') {
        root = environment_root;
    }
    if (root.empty()) {
        set_error(nullptr, "no Fullseye Python environment was specified; set runtime_root or "
                           "FULLSEYE_PYTHON_ROOT to an environment containing the fullseye package");
        return FS_E_NO_PYTHON;
    }
    try {
        const fs_status_t init_status = initialize_python(
            root, home, (options->flags & FS_INIT_ALLOW_HOST_PYTHON_UNSAFE) != 0u);
        if (init_status != FS_OK) {
            set_error(nullptr, "CPython initialization failed: " + g_python_error);
            return init_status;
        }
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
    std::string query;
    if (!copy_text_span(query_json, query_json_bytes, true, &query)) {
        set_error(runtime, "query_json is NULL with a non-zero byte length");
        return FS_E_INVALID_ARG;
    }
    RuntimeCall call(runtime);
    if (!call.entered()) {
        set_error(runtime, "runtime is closing");
        return FS_E_BUSY;
    }
    try {
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
    RuntimeCall call(runtime);
    if (!call.entered()) {
        set_error(runtime, "runtime is closing");
        return FS_E_BUSY;
    }
    try {
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

FS_API fs_status_t FS_CALL fs_call_n(fs_runtime_t *runtime, const char *op_id,
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
    std::string op;
    std::string params;
    if (!copy_text_span(op_id, op_id_bytes, false, &op)
        || !copy_text_span(params_json, params_json_bytes, true, &params)) {
        set_error(runtime, "a string pointer is NULL with a non-zero byte length");
        return FS_E_INVALID_ARG;
    }
    RuntimeCall call(runtime);
    if (!call.entered()) {
        set_error(runtime, "runtime is closing");
        return FS_E_BUSY;
    }
    try {
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
                if (input.kind != FS_VALUE_IMAGE) {
                    set_error(runtime, "non-image inputs must borrow an earlier result");
                    return FS_E_INVALID_ARG;
                }
                const fs_status_t status = validate_image(runtime, input.image);
                if (status != FS_OK) {
                    return status;
                }
                values.append(image_to_python(input.image));
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
    if (!lease || out_count == nullptr) return FS_E_INVALID_ARG;
    *out_count = lease.get()->items.size();
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_kind_n(fs_result_id_t result, size_t index,
                                             fs_value_kind_t *out) {
    ResultIdLease lease(result);
    if (!lease || out == nullptr || index >= lease.get()->items.size()) return FS_E_INVALID_ARG;
    *out = lease.get()->items[index].kind;
    return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_image_n(fs_result_id_t result, size_t index,
                                              fs_image_view_t *out_borrowed) {
    ResultIdLease lease(result);
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

FS_API fs_status_t FS_CALL fs_result_region_runs_n(fs_result_id_t result, size_t index,
                                                    const fs_run_t **out_borrowed, size_t *out_count) {
    ResultIdLease lease(result);
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_REGION, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out_borrowed == nullptr || out_count == nullptr) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out_borrowed = item->runs.data(); *out_count = item->runs.size(); return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_object_count_n(fs_result_id_t result, size_t index,
                                                     size_t *out_count) {
    ResultIdLease lease(result);
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
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_OBJECTSET, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out_borrowed == nullptr || out_count == nullptr || object_index >= item->objects.size()) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out_borrowed = item->objects[object_index].data(); *out_count = item->objects[object_index].size(); return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_real_n(fs_result_id_t result, size_t index, double *out) {
    ResultIdLease lease(result);
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_REAL, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out == nullptr) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out = item->real; return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_tuple_size_n(fs_result_id_t result, size_t index,
                                                   size_t *out_count) {
    ResultIdLease lease(result);
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_TUPLE, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out_count == nullptr) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out_count = item->tuple.size(); return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_tuple_real_n(fs_result_id_t result, size_t index,
                                                   size_t element_index, double *out) {
    ResultIdLease lease(result);
    const Item *item = nullptr;
    const fs_status_t status = lease ? access_item(lease.get(), index, FS_VALUE_TUPLE, &item)
                                     : FS_E_INVALID_ARG;
    if (status != FS_OK || out == nullptr || element_index >= item->tuple.size()) return status != FS_OK ? status : FS_E_INVALID_ARG;
    *out = item->tuple[element_index]; return FS_OK;
}

FS_API fs_status_t FS_CALL fs_result_release_n(fs_result_id_t result) {
    const fs_status_t status = release_result_id(result);
    if (status != FS_OK) set_error(nullptr, "result ID is unknown or has already been released");
    else clear_error(nullptr);
    return status;
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
    RuntimeCall call(runtime);
    if (!call.entered()) {
        set_error(runtime, "runtime is closing");
        return 0u;
    }
    try {
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
