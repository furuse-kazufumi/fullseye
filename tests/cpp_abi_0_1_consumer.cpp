// ABI 0.1 C++ binary-consumer gate / ABI 0.1 C++ バイナリ利用者の門。
// This source intentionally carries the old pointer-result wrapper declarations
// instead of including fullseye.h. / 現行ヘッダでなく旧ポインタ API の宣言で組む。
#include "fullseye_abi.h"

#include <cstddef>
#include <cstdint>
#include <utility>

extern "C" {
struct fs_runtime;
struct fs_result;
typedef struct fs_runtime fs_runtime_t;
typedef struct fs_result fs_result_t;
typedef enum fs_value_kind_0_1 { FS_VALUE_IMAGE_0_1 = 1 } fs_value_kind_0_1_t;
typedef struct fs_init_options_0_1 {
    uint32_t struct_size;
    const char *runtime_root;
    const char *python_home;
    uint32_t flags;
    uint32_t abi_major;
    uint32_t abi_minor;
} fs_init_options_0_1_t;
typedef struct fs_image_view_0_1 {
    uint32_t struct_size;
    const void *data;
    size_t data_bytes;
    int64_t width;
    int64_t height;
    int64_t row_stride_bytes;
    fs_dtype_t dtype;
    double range_lo;
    double range_hi;
} fs_image_view_0_1_t;
typedef struct fs_input_0_1 {
    uint32_t struct_size;
    fs_value_kind_0_1_t kind;
    fs_image_view_0_1_t image;
    const fs_result_t *result;
    size_t result_index;
} fs_input_0_1_t;
fs_status_t fs_runtime_create(const fs_init_options_0_1_t *, fs_runtime_t **);
void fs_runtime_destroy(fs_runtime_t *);
fs_status_t fs_call(fs_runtime_t *, const char *, const fs_input_0_1_t *, size_t,
                    const char *, fs_result_t **);
size_t fs_result_count(const fs_result_t *);
void fs_result_release(fs_result_t *);
}

class Result {
public:
    explicit Result(fs_result_t *value = nullptr) : value_(value) {}
    ~Result() { fs_result_release(value_); }
    Result(const Result &) = delete;
    Result &operator=(const Result &) = delete;
    Result(Result &&other) noexcept : value_(std::exchange(other.value_, nullptr)) {}
    size_t size() const { return fs_result_count(value_); }
private:
    fs_result_t *value_;
};

int main(int argc, char **argv) {
    const double pixels[] = {0.0, 1.0, 1.0, 0.0};
    fs_init_options_0_1_t options = {sizeof(options), nullptr, nullptr, 1u, 0u, 1u};
    fs_image_view_0_1_t image = {sizeof(image), pixels, sizeof(pixels), 2, 2,
                                  2 * static_cast<int64_t>(sizeof(double)), FS_DTYPE_F64, 0.0, 1.0};
    fs_input_0_1_t input = {sizeof(input), FS_VALUE_IMAGE_0_1, image, nullptr, 0u};
    fs_runtime_t *runtime = nullptr;
    fs_result_t *raw = nullptr;
    if (argc > 1) options.runtime_root = argv[1];
    if (fs_runtime_create(&options, &runtime) != FS_OK) return 1;
    const fs_status_t status = fs_call(runtime, "contract:threshold", &input, 1u,
                                       "{\"lo\":0.5,\"hi\":1.0}", &raw);
    Result result(raw);
    fs_runtime_destroy(runtime);
    return status == FS_OK && result.size() == 1u ? 0 : 1;
}
