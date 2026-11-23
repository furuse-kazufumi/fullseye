/* Copyright (c) 2026 Kazufumi Furuse. Apache-2.0.
 * Fullseye embedded C API / Fullseye 埋め込み C API.
 *
 * The existing fullseye_abi.h remains the semantic L1 contract.  This header
 * adds the initial C SDK API (ABI 0.2) implemented by the pybind11 bridge.
 * 既存の fullseye_abi.h を意味論上の L1 契約として保ち、このヘッダは pybind11
 * ブリッジが実装する、最初の C SDK API (ABI 0.2) を追加する。
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
/* A generation-tagged, opaque result handle for the ABI 0.2 C SDK API.
 * ABI 0.2 の長さ付き API が返す世代付き不透明結果ハンドル。 */
typedef uint64_t fs_result_id_t;

typedef enum fs_value_kind {
    FS_VALUE_IMAGE = 1,
    FS_VALUE_REGION = 2,
    FS_VALUE_OBJECTSET = 3,
    FS_VALUE_REAL = 4,
    FS_VALUE_TUPLE = 5
} fs_value_kind_t;

enum {
    FS_INIT_ISOLATED = 1u,
    /* Deliberately opt in when this DLL is loaded by an existing CPython host.
     * 既存 CPython ホストを使う場合だけ、明示的に危険な許可を与える。 */
    FS_INIT_ALLOW_HOST_PYTHON_UNSAFE = 2u
};

typedef struct fs_init_options {
    uint32_t struct_size;
    const char *runtime_root;
    const char *python_home;
    uint32_t flags;
    uint32_t abi_major;
    uint32_t abi_minor;
    /* ABI 0.2: explicit byte spans.  A non-NULL pointer needs a non-zero
     * length; NULL with zero means unspecified. ABI 0.1 uses C strings.
     * ABI 0.2: 明示長。非 NULL なら長さは正、NULL と 0 は未指定。ABI 0.1 は C 文字列。 */
    size_t runtime_root_bytes;
    size_t python_home_bytes;
} fs_init_options_t;

#define FS_INIT_OPTIONS_INIT \
    { (uint32_t)sizeof(fs_init_options_t), NULL, NULL, FS_INIT_ISOLATED, \
      FULLSEYE_ABI_VERSION_MAJOR, FULLSEYE_ABI_VERSION_MINOR, 0u, 0u }

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

/* Compatibility map / 互換性表:
 *
 *   Surface                              Version       Result ownership
 *   fullseye_abi.h public L1 contract    published 0.1  its declared handles
 *   fs_runtime_create, fs_call, and      C SDK 0.2     fs_result_t* pointer
 *     fs_find_ops_json below
 *   fs_find_ops_json_n and fs_call_id_n  C SDK 0.2     fs_result_id_t
 *
 * The C SDK is first published as 0.2. Its generation-ID call entry is named
 * fs_call_id_n so it cannot be mistaken for a pointer-result function.
 * C SDK は 0.2 として最初に公開する。世代付き ID を返す入口は
 * fs_call_id_n とし、ポインタ結果の関数名と混同しない。
 *
 * Pointer entry points accept valid NUL-terminated C strings. Result
 * pointers must not be used after fs_result_release(); that is undefined.
 * ABI 0.1 旧入口は有効な NUL 終端 C 文字列を受ける。fs_result_release() 後の
 * 結果ポインタ利用は未定義で、呼出し側の責任。 */
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
/* ABI 0.2 bounded API. Byte spans need not have a trailing NUL and must
 * contain UTF-8 text. Results are generation-tagged IDs; unknown or released
 * IDs return FS_E_INVALID_ARG. / ABI 0.2 の長さ付き API。文字列は終端 NUL
 * 不要で UTF-8。結果は世代付き ID で、未知・解放済み ID は FS_E_INVALID_ARG。 */
typedef struct fs_input_n {
    uint32_t struct_size;
    fs_value_kind_t kind;
    fs_image_view_t image;
    fs_result_id_t result_id;
    size_t result_index;
} fs_input_n_t;

#define FS_INPUT_N_INIT \
    { (uint32_t)sizeof(fs_input_n_t), FS_VALUE_IMAGE, FS_IMAGE_VIEW_INIT, 0u, 0u }

FS_API fs_status_t FS_CALL fs_find_ops_json_n(fs_runtime_t *runtime,
                                               const char *query_json,
                                               size_t query_json_bytes,
                                               char **out_utf8,
                                               size_t *out_bytes);
FS_API fs_status_t FS_CALL fs_call_id_n(fs_runtime_t *runtime,
                                         const char *op_id,
                                         size_t op_id_bytes,
                                         const fs_input_n_t *inputs,
                                         size_t input_count,
                                         const char *params_json,
                                         size_t params_json_bytes,
                                         fs_result_id_t *out);

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
/* ABI 0.1 pointer results. Borrowed views are valid through release.
 * ABI 0.1 ポインタ結果。借用 view は release まで有効。 */
FS_API void FS_CALL fs_result_release(fs_result_t *result);
/* ABI 0.2 generation-ID results. Borrowed views are valid until the matching
 * release_n; callers must not retain a borrowed pointer past it.
 * ABI 0.2 世代 ID 結果。借用 view は release_n まで有効。 */
FS_API fs_status_t FS_CALL fs_result_count_n(fs_result_id_t result, size_t *out_count);
FS_API fs_status_t FS_CALL fs_result_kind_n(fs_result_id_t result, size_t index,
                                             fs_value_kind_t *out);
FS_API fs_status_t FS_CALL fs_result_image_n(fs_result_id_t result, size_t index,
                                              fs_image_view_t *out_borrowed);
FS_API fs_status_t FS_CALL fs_result_region_runs_n(fs_result_id_t result, size_t index,
                                                    const fs_run_t **out_borrowed,
                                                    size_t *out_count);
FS_API fs_status_t FS_CALL fs_result_object_count_n(fs_result_id_t result, size_t index,
                                                     size_t *out_count);
FS_API fs_status_t FS_CALL fs_result_object_runs_n(fs_result_id_t result, size_t index,
                                                    size_t object_index,
                                                    const fs_run_t **out_borrowed,
                                                    size_t *out_count);
FS_API fs_status_t FS_CALL fs_result_real_n(fs_result_id_t result, size_t index, double *out);
FS_API fs_status_t FS_CALL fs_result_tuple_size_n(fs_result_id_t result, size_t index,
                                                   size_t *out_count);
FS_API fs_status_t FS_CALL fs_result_tuple_real_n(fs_result_id_t result, size_t index,
                                                   size_t element_index, double *out);
FS_API fs_status_t FS_CALL fs_result_release_n(fs_result_id_t result);
FS_API void FS_CALL fs_free(void *library_allocated);

/* The returned size includes the trailing NUL byte / 返す長さは終端 NUL を含む。 */
FS_API size_t FS_CALL fs_last_error(fs_runtime_t *runtime, char *buf, size_t capacity);
FS_API fs_status_t FS_CALL fs_abi_version(int32_t *major, int32_t *minor);
FS_API size_t FS_CALL fs_runtime_version(fs_runtime_t *runtime, char *buf, size_t capacity);

#ifdef __cplusplus
}
#endif
#endif /* FULLSEYE_H */
