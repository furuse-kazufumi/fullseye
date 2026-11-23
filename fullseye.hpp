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
        check(fs_result_count_n(value_, &count));
        return count;
    }

private:
    void check(fs_status_t status) const {
        if (status != FS_OK) throw Error(status, "Fullseye result access failed");
    }
    fs_result_id_t value_;
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

    Result call(const std::string &op_id, const std::vector<fs_input_n_t> &inputs,
                const std::string &params = "{}") {
        fs_result_id_t out = 0u;
        check(fs_call_id_n(value_, op_id.data(), op_id.size(),
                           inputs.empty() ? nullptr : inputs.data(), inputs.size(),
                           params.data(), params.size(), &out));
        return Result(out);
    }

    std::string find_ops(const std::string &query = "{}") {
        char *text = nullptr;
        size_t bytes = 0;
        check(fs_find_ops_json_n(value_, query.data(), query.size(), &text, &bytes));
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
