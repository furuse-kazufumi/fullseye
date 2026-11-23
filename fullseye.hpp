// Copyright (c) 2026 Kazufumi Furuse. Apache-2.0.
// C++17 RAII wrapper / C++17 RAII ラッパー。
#pragma once

#include <cstring>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

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

class Result {
public:
    explicit Result(fs_result_t *value = nullptr) noexcept : value_(value) {}
    ~Result() { fs_result_release(value_); }
    Result(Result &&other) noexcept : value_(std::exchange(other.value_, nullptr)) {}
    Result &operator=(Result &&other) noexcept {
        if (this != &other) {
            fs_result_release(value_);
            value_ = std::exchange(other.value_, nullptr);
        }
        return *this;
    }
    Result(const Result &) = delete;
    Result &operator=(const Result &) = delete;
    fs_result_t *get() const noexcept { return value_; }
    size_t size() const noexcept { return fs_result_count(value_); }

private:
    fs_result_t *value_;
};

class Runtime {
public:
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

    Result call(const std::string &op_id, const std::vector<fs_input_t> &inputs,
                const std::string &params = "{}") {
        fs_result_t *out = nullptr;
        check(fs_call(value_, op_id.c_str(), inputs.empty() ? nullptr : inputs.data(),
                      inputs.size(), params.c_str(), &out));
        return Result(out);
    }

    std::string find_ops(const std::string &query = "{}") {
        char *text = nullptr;
        size_t bytes = 0;
        check(fs_find_ops_json(value_, query.c_str(), &text, &bytes));
        std::string result(text, bytes ? bytes - 1 : 0);
        fs_free(text);
        return result;
    }

    fs_runtime_t *get() const noexcept { return value_; }

private:
    void create(const fs_init_options_t &options) {
        const fs_status_t status = fs_runtime_create(&options, &value_);
        if (status != FS_OK) {
            throw Error(status, "Fullseye runtime initialization failed");
        }
    }
    void check(fs_status_t status) const {
        if (status == FS_OK) {
            return;
        }
        const size_t needed = fs_last_error(value_, nullptr, 0);
        std::vector<char> message(needed ? needed : 1, '\0');
        fs_last_error(value_, message.data(), message.size());
        throw Error(status, std::string(message.data()));
    }

    fs_runtime_t *value_ = nullptr;
};

}  // namespace fullseye
