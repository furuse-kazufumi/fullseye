/* ABI 0.1 binary-consumer gate / ABI 0.1 バイナリ利用者の門。
 * This deliberately carries the 0.1 declarations rather than including the
 * current fullseye.h, so it catches ABI-compatible additions that accidentally
 * change an old entry point. / 現行ヘッダを使わず 0.1 宣言で組み、足すだけ版が
 * 旧入口を壊さないことを確かめる。 */
#include "fullseye_abi.h"

#include <stddef.h>
#include <stdint.h>

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

extern fs_status_t fs_runtime_create(const fs_init_options_0_1_t *, fs_runtime_t **);
extern void fs_runtime_destroy(fs_runtime_t *);
extern fs_status_t fs_find_ops_json(fs_runtime_t *, const char *, char **, size_t *);
extern fs_status_t fs_call(fs_runtime_t *, const char *, const fs_input_0_1_t *, size_t,
                           const char *, fs_result_t **);
extern size_t fs_result_count(const fs_result_t *);
extern void fs_result_release(fs_result_t *);
extern void fs_free(void *);

int main(int argc, char **argv) {
    const double pixels[] = {0.0, 1.0, 1.0, 0.0};
    fs_init_options_0_1_t options = {
        (uint32_t)sizeof(fs_init_options_0_1_t), NULL, NULL, 1u, 0u, 1u
    };
    fs_image_view_0_1_t image = {
        (uint32_t)sizeof(fs_image_view_0_1_t), pixels, sizeof(pixels), 2, 2,
        2 * (int64_t)sizeof(double), FS_DTYPE_F64, 0.0, 1.0
    };
    fs_input_0_1_t input = {
        (uint32_t)sizeof(fs_input_0_1_t), FS_VALUE_IMAGE_0_1, image, NULL, 0u
    };
    fs_runtime_t *runtime = NULL;
    fs_result_t *result = NULL;
    char *catalog = NULL;
    size_t catalog_bytes = 0u;
    int ok = 0;
    if (argc > 1) options.runtime_root = argv[1];
    if (fs_runtime_create(&options, &runtime) != FS_OK) goto done;
    if (fs_find_ops_json(runtime, "{\"limit\":1}", &catalog, &catalog_bytes) != FS_OK
        || catalog_bytes == 0u) goto done;
    if (fs_call(runtime, "contract:threshold", &input, 1u,
                "{\"lo\":0.5,\"hi\":1.0}", &result) != FS_OK) goto done;
    if (fs_result_count(result) != 1u) goto done;
    ok = 1;
done:
    fs_result_release(result);
    fs_free(catalog);
    fs_runtime_destroy(runtime);
    return ok ? 0 : 1;
}
