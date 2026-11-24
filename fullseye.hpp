// Copyright (c) 2026 Kazufumi Furuse. Apache-2.0.
// C++ RAII convenience layer / C++ RAII の使いやすい層。
#pragma once

#include <cmath>
#include <cstddef>
#include <cstring>
#include <initializer_list>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#if __cplusplus >= 202002L
#  include <span>
#endif

#include "fullseye.h"

namespace fullseye {

class Error : public std::runtime_error {
public:
    Error(fs_status_t status, std::string message)
        : std::runtime_error(std::move(message)), status_(status) {}
    fs_status_t status() const noexcept { return status_; }

private:
    fs_status_t status_;
};

enum class BufferOwnership {
    borrow,
    copy,
};

class Image {
public:
    Image() = default;
    Image(const Image &) = delete;
    Image &operator=(const Image &) = delete;
    Image(Image &&other) noexcept
        : data_(other.data_), height_(other.height_), width_(other.width_), count_(other.count_),
          owned_(std::move(other.owned_)) {
        if (!owned_.empty()) data_ = owned_.data();
        other.data_ = nullptr;
        other.height_ = other.width_ = 0;
        other.count_ = 0;
    }
    Image &operator=(Image &&other) noexcept {
        if (this != &other) {
            data_ = other.data_;
            height_ = other.height_;
            width_ = other.width_;
            count_ = other.count_;
            owned_ = std::move(other.owned_);
            if (!owned_.empty()) data_ = owned_.data();
            other.data_ = nullptr;
            other.height_ = other.width_ = 0;
            other.count_ = 0;
        }
        return *this;
    }

    static Image from_buffer(const double *data, int64_t height, int64_t width,
                             BufferOwnership ownership = BufferOwnership::borrow) {
        if (data == nullptr || height <= 0 || width <= 0) {
            throw std::invalid_argument("Image::from_buffer needs a non-null, non-empty float64 buffer");
        }
        const auto h = static_cast<size_t>(height);
        const auto w = static_cast<size_t>(width);
        if (h > std::numeric_limits<size_t>::max() / w
            || h * w > std::numeric_limits<size_t>::max() / sizeof(double)) {
            throw std::overflow_error("Image::from_buffer dimensions overflow size_t");
        }
        Image image;
        image.height_ = height;
        image.width_ = width;
        image.count_ = h * w;
        if (ownership == BufferOwnership::copy) {
            image.owned_.assign(data, data + image.count_);
            image.data_ = image.owned_.data();
        } else {
            image.data_ = data;
        }
        return image;
    }

#if __cplusplus >= 202002L
    static Image from_buffer(std::span<const double> data, int64_t height, int64_t width,
                             BufferOwnership ownership = BufferOwnership::borrow) {
        auto image = from_buffer(data.data(), height, width, ownership);
        if (data.size() != image.count_) {
            throw std::invalid_argument("Image::from_buffer span size does not match height * width");
        }
        return image;
    }
#endif

    fs_input_n_t input() const noexcept {
        fs_input_n_t value = FS_INPUT_N_INIT;
        value.image.data = data_;
        value.image.data_bytes = count_ * sizeof(double);
        value.image.width = width_;
        value.image.height = height_;
        value.image.row_stride_bytes = width_ * static_cast<int64_t>(sizeof(double));
        value.image.dtype = FS_DTYPE_F64;
        value.image.range_lo = 0.0;
        value.image.range_hi = 1.0;
        return value;
    }

private:
    const double *data_ = nullptr;
    int64_t height_ = 0;
    int64_t width_ = 0;
    size_t count_ = 0;
    std::vector<double> owned_;
};

inline const char *status_name(fs_status_t status) noexcept {
    switch (status) {
        case FS_OK: return "FS_OK";
        case FS_E_INVALID_ARG: return "FS_E_INVALID_ARG";
        case FS_E_TYPE: return "FS_E_TYPE";
        case FS_E_SHAPE: return "FS_E_SHAPE";
        case FS_E_RANGE: return "FS_E_RANGE";
        case FS_E_NO_BACKEND: return "FS_E_NO_BACKEND";
        case FS_E_UNSUPPORTED: return "FS_E_UNSUPPORTED";
        case FS_E_OUT_OF_MEMORY: return "FS_E_OUT_OF_MEMORY";
        case FS_E_NO_PYTHON: return "FS_E_NO_PYTHON";
        case FS_E_UNKNOWN_OP: return "FS_E_UNKNOWN_OP";
        case FS_E_BAD_PARAMS: return "FS_E_BAD_PARAMS";
        case FS_E_PY_EXCEPTION: return "FS_E_PY_EXCEPTION";
        case FS_E_BUSY: return "FS_E_BUSY";
        default: return "FS_E_INTERNAL";
    }
}

class ImageView {
public:
    const double *data() const noexcept { return data_; }
    int64_t height() const noexcept { return height_; }
    int64_t width() const noexcept { return width_; }
    double at(int64_t row, int64_t column) const {
        if (row < 0 || column < 0 || row >= height_ || column >= width_) {
            throw std::out_of_range("Fullseye ImageView index is outside the result image");
        }
        const auto *bytes = reinterpret_cast<const unsigned char *>(data_)
            + static_cast<size_t>(row) * static_cast<size_t>(stride_bytes_);
        return reinterpret_cast<const double *>(bytes)[column];
    }

private:
    friend class Result;
    ImageView(const double *data, int64_t height, int64_t width, int64_t stride_bytes)
        : data_(data), height_(height), width_(width), stride_bytes_(stride_bytes) {}

    const double *data_ = nullptr;
    int64_t height_ = 0;
    int64_t width_ = 0;
    int64_t stride_bytes_ = 0;
};

class Result {
public:
    explicit Result(fs_result_id_t value = 0u) noexcept : value_(value) {}
    ~Result() { if (value_ != 0u) (void)fs_result_release_n(value_); }
    Result(Result &&other) noexcept : value_(std::exchange(other.value_, 0u)) {}
    Result &operator=(Result &&other) noexcept {
        if (this != &other) {
            if (value_ != 0u) (void)fs_result_release_n(value_);
            value_ = std::exchange(other.value_, 0u);
        }
        return *this;
    }
    Result(const Result &) = delete;
    Result &operator=(const Result &) = delete;
    fs_result_id_t get() const noexcept { return value_; }
    size_t size() const {
        size_t count = 0u;
        const fs_status_t status = fs_result_count_n(value_, &count);
        if (status != FS_OK) {
            throw Error(status, std::string("Fullseye result.size failed (") + status_name(status) + ")");
        }
        return count;
    }
    // The returned pixels are borrowed and remain valid while *this remains
    // alive. / 返す画素は借用で、この Result の寿命まで有効。
    ImageView image(size_t index = 0u) const {
        fs_image_view_t value = FS_IMAGE_VIEW_INIT;
        const fs_status_t status = fs_result_image_n(value_, index, &value);
        if (status != FS_OK || value.dtype != FS_DTYPE_F64) {
            throw Error(status == FS_OK ? FS_E_TYPE : status,
                        std::string("Fullseye result.image failed (") +
                        status_name(status == FS_OK ? FS_E_TYPE : status) + ")");
        }
        return ImageView(static_cast<const double *>(value.data), value.height, value.width,
                         value.row_stride_bytes);
    }

private:
    fs_result_id_t value_;
};

class Runtime {
public:
    using Parameter = std::pair<std::string, double>;

    Runtime() {
        fs_init_options_t options = FS_INIT_OPTIONS_INIT;
        create(options);
    }
    explicit Runtime(const fs_init_options_t &options) { create(options); }
    ~Runtime() { fs_runtime_destroy(value_); }
    Runtime(const Runtime &) = delete;
    Runtime &operator=(const Runtime &) = delete;
    Runtime(Runtime &&other) noexcept : value_(std::exchange(other.value_, nullptr)) {}
    Runtime &operator=(Runtime &&other) noexcept {
        if (this != &other) {
            fs_runtime_destroy(value_);
            value_ = std::exchange(other.value_, nullptr);
        }
        return *this;
    }

    Result call(const std::string &op_id, const std::vector<fs_input_n_t> &inputs,
                const std::string &params = "{}") {
        fs_result_id_t out = 0u;
        check(fs_call_id_n(value_, op_id.data(), op_id.size(),
                           inputs.empty() ? nullptr : inputs.data(), inputs.size(),
                           params.data(), params.size(), &out), "op " + op_id);
        return Result(out);
    }

    Result call(std::string_view op_name, const Image &image,
                std::initializer_list<Parameter> parameters = {}) {
        const std::string op_id = scoped_op(op_name);
        return call(op_id, std::vector<fs_input_n_t>{image.input()}, params_json(parameters));
    }

    std::string find(std::string_view query = "") {
        return find_ops(query.empty() ? "{}" : "{\"query\":" + json_string(query) + "}");
    }

    std::string find_ops(const std::string &query = "{}") {
        char *text = nullptr;
        size_t bytes = 0;
        check(fs_find_ops_json_n(value_, query.data(), query.size(), &text, &bytes), "operator search");
        std::string result(text, bytes ? bytes - 1 : 0);
        fs_free(text);
        return result;
    }

    fs_runtime_t *get() const noexcept { return value_; }

private:
    static std::string json_string(std::string_view value) {
        std::string result{"\""};
        for (const unsigned char ch : value) {
            if (ch < 0x20u) throw std::invalid_argument("Fullseye parameter names and queries cannot contain control characters");
            if (ch == '\\' || ch == '\"') result += '\\';
            result += static_cast<char>(ch);
        }
        return result + "\"";
    }

    static std::string params_json(std::initializer_list<Parameter> parameters) {
        std::string result{"{"};
        bool first = true;
        for (const auto &parameter : parameters) {
            if (!std::isfinite(parameter.second)) {
                throw std::invalid_argument("Fullseye parameters must be finite JSON numbers");
            }
            if (!first) result += ',';
            first = false;
            result += json_string(parameter.first);
            result += ':';
            result += std::to_string(parameter.second);
        }
        return result + "}";
    }

    static std::string scoped_op(std::string_view op_name) {
        if (op_name.empty()) throw std::invalid_argument("Fullseye op name must not be empty");
        const std::string name(op_name);
        return name.find(':') == std::string::npos ? "registry:" + name : name;
    }

    void create(const fs_init_options_t &options) {
        const fs_status_t status = fs_runtime_create(&options, &value_);
        if (status != FS_OK) {
            throw Error(status, "Fullseye runtime initialization failed (" +
                                std::string(status_name(status)) + "): " + last_error());
        }
    }
    std::string last_error() const {
        const size_t needed = fs_last_error(value_, nullptr, 0);
        std::vector<char> message(needed ? needed : 1, '\0');
        fs_last_error(value_, message.data(), message.size());
        return std::string(message.data());
    }
    void check(fs_status_t status, const std::string &context) const {
        if (status != FS_OK) {
            throw Error(status, "Fullseye " + context + " failed (" + status_name(status) + "): " + last_error());
        }
    }

    fs_runtime_t *value_ = nullptr;
};

}  // namespace fullseye
