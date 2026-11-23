/* Copyright (c) 2026 Kazufumi Furuse. Apache-2.0.
 * Fullseye embedded C API / Fullseye 埋め込み C API.
 *
 * The existing fullseye_abi.h remains the semantic L1 contract.  This header
 * adds an owned runtime/result API implemented by the pybind11 bridge.
 * 既存の fullseye_abi.h を意味論上の L1 契約として保ち、このヘッダは pybind11
 * ブリッジが実装する所有権つき runtime/result API を追加する。
 */
#ifndef FULLSEYE_H
#define FULLSEYE_H

#include <stddef.h>
#include <stdint.h>
#include "fullseye_abi.h"

#if defined(_WIN32)
#  if defined(FULLSEYE_BUILD)
#    define FS_API __declspec(dllexport)
#  else
#    define FS_API __declspec(dllimport)
#  endif
#  define FS_CALL __cdecl
#elif defined(__GNUC__) || defined(__clang__)
#  define FS_API __attribute__((visibility("default")))
#  define FS_CALL
#else
#  define FS_API
#  define FS_CALL
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* Appended status: old numeric values in fullseye_abi.h are unchanged.
 * 追加状態: fullseye_abi.h の既存番号は変更しない。 */
#define FS_E_BUSY ((fs_status_t)14)

typedef struct fs_runtime fs_runtime_t;
typedef struct fs_result fs_result_t;

typedef enum fs_value_kind {
    FS_VALUE_IMAGE = 1,
    FS_VALUE_REGION = 2,
    FS_VALUE_OBJECTSET = 3,
    FS_VALUE_REAL = 4,
    FS_VALUE_TUPLE = 5
} fs_value_kind_t;

enum {
    FS_INIT_ISOLATED = 1u
};

typedef struct fs_init_options {
    uint32_t struct_size;
    const char *runtime_root;
    const char *python_home;
    uint32_t flags;
    uint32_t abi_major;
    uint32_t abi_minor;
} fs_init_options_t;

#define FS_INIT_OPTIONS_INIT \
    { (uint32_t)sizeof(fs_init_options_t), NULL, NULL, FS_INIT_ISOLATED, \
      FULLSEYE_ABI_VERSION_MAJOR, FULLSEYE_ABI_VERSION_MINOR }

typedef struct fs_image_view {
    uint32_t struct_size;
    const void *data;
    size_t data_bytes;
    int64_t width;
    int64_t height;
    int64_t row_stride_bytes;
    fs_dtype_t dtype;
    double range_lo;
    double range_hi;
} fs_image_view_t;

#define FS_IMAGE_VIEW_INIT \
    { (uint32_t)sizeof(fs_image_view_t), NULL, 0u, 0, 0, 0, FS_DTYPE_F64, 0.0, 1.0 }

typedef struct fs_input {
    uint32_t struct_size;
    fs_value_kind_t kind;
    fs_image_view_t image;
    const fs_result_t *result;
    size_t result_index;
} fs_input_t;

#define FS_INPUT_INIT \
    { (uint32_t)sizeof(fs_input_t), FS_VALUE_IMAGE, FS_IMAGE_VIEW_INIT, NULL, 0u }

/* Runtime lifecycle / runtime の寿命。CPython はプロセス終了まで finalize しない。 */
FS_API fs_status_t FS_CALL fs_runtime_create(const fs_init_options_t *options,
                                              fs_runtime_t **out);
FS_API void FS_CALL fs_runtime_destroy(fs_runtime_t *runtime);

/* Discovery and execution / 検索と実行。IDs are always scoped / ID は必ず層付き。 */
FS_API fs_status_t FS_CALL fs_find_ops_json(fs_runtime_t *runtime,
                                             const char *query_json,
                                             char **out_utf8,
                                             size_t *out_bytes);
FS_API fs_status_t FS_CALL fs_call(fs_runtime_t *runtime,
                                    const char *op_id,
                                    const fs_input_t *inputs,
                                    size_t input_count,
                                    const char *params_json,
                                    fs_result_t **out);

/* Borrowed result views remain valid through fs_result_release().
 * 借用結果は fs_result_release() まで有効。 */
FS_API size_t FS_CALL fs_result_count(const fs_result_t *result);
FS_API fs_status_t FS_CALL fs_result_kind(const fs_result_t *result,
                                           size_t index,
                                           fs_value_kind_t *out);
FS_API fs_status_t FS_CALL fs_result_image(const fs_result_t *result,
                                            size_t index,
                                            fs_image_view_t *out_borrowed);
FS_API fs_status_t FS_CALL fs_result_region_runs(const fs_result_t *result,
                                                  size_t index,
                                                  const fs_run_t **out_borrowed,
                                                  size_t *out_count);
FS_API fs_status_t FS_CALL fs_result_object_count(const fs_result_t *result,
                                                   size_t index,
                                                   size_t *out_count);
FS_API fs_status_t FS_CALL fs_result_object_runs(const fs_result_t *result,
                                                  size_t index,
                                                  size_t object_index,
                                                  const fs_run_t **out_borrowed,
                                                  size_t *out_count);
FS_API fs_status_t FS_CALL fs_result_real(const fs_result_t *result,
                                           size_t index,
                                           double *out);
FS_API fs_status_t FS_CALL fs_result_tuple_size(const fs_result_t *result,
                                                 size_t index,
                                                 size_t *out_count);
FS_API fs_status_t FS_CALL fs_result_tuple_real(const fs_result_t *result,
                                                 size_t index,
                                                 size_t element_index,
                                                 double *out);
FS_API void FS_CALL fs_result_release(fs_result_t *result);
FS_API void FS_CALL fs_free(void *library_allocated);

/* The returned size includes the trailing NUL byte / 返す長さは終端 NUL を含む。 */
FS_API size_t FS_CALL fs_last_error(fs_runtime_t *runtime, char *buf, size_t capacity);
FS_API fs_status_t FS_CALL fs_abi_version(int32_t *major, int32_t *minor);
FS_API size_t FS_CALL fs_runtime_version(fs_runtime_t *runtime, char *buf, size_t capacity);

#ifdef __cplusplus
}
#endif
#endif /* FULLSEYE_H */
