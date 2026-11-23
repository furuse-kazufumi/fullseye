/* Result-handle lifetime gate / 結果ハンドルの寿命を確かめる C の門。 */
#include "fullseye.h"

#include <stdatomic.h>
#include <string.h>

#ifdef _WIN32
#include <process.h>
#include <windows.h>
#else
#include <pthread.h>
#endif

enum { ACCESS_ITERATIONS = 1000 };

typedef struct race_arg {
    fs_result_t *result;
    atomic_int start;
    int ok;
} race_arg_t;

static fs_input_t image_input(const double *pixels, size_t count) {
    fs_input_t input = FS_INPUT_INIT;
    input.image.data = pixels;
    input.image.data_bytes = count * sizeof(double);
    input.image.width = 2;
    input.image.height = 2;
    input.image.row_stride_bytes = 2 * (int64_t)sizeof(double);
    return input;
}

static void read_during_release(race_arg_t *arg) {
    int index;
    while (atomic_load_explicit(&arg->start, memory_order_acquire) == 0) {}
    arg->ok = 1;
    for (index = 0; index < ACCESS_ITERATIONS; ++index) {
        fs_value_kind_t kind = FS_VALUE_IMAGE;
        fs_status_t status = fs_result_kind(arg->result, 0, &kind);
        if (status != FS_OK && status != FS_E_INVALID_ARG) arg->ok = 0;
    }
}

#ifdef _WIN32
static unsigned __stdcall race_main(void *value) {
    read_during_release((race_arg_t *)value);
    return 0;
}
#else
static void *race_main(void *value) {
    read_during_release((race_arg_t *)value);
    return NULL;
}
#endif

static fs_status_t threshold(fs_runtime_t *runtime, fs_result_t **out) {
    const double pixels[] = {0.0, 1.0, 1.0, 0.0};
    fs_input_t input = image_input(pixels, 4);
    static const char op[] = "contract:threshold";
    static const char params[] = "{\"lo\":0.5,\"hi\":1.0}";
    return fs_call_n(runtime, op, sizeof(op) - 1u, &input, 1, params, sizeof(params) - 1u, out);
}

int main(int argc, char **argv) {
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *runtime = NULL;
    fs_result_t *result = NULL;
    fs_value_kind_t kind = FS_VALUE_IMAGE;
    race_arg_t race = {NULL, ATOMIC_VAR_INIT(0), 0};
    int ok = 0;
    if (argc > 1) options.runtime_root = argv[1];
    if (fs_runtime_create(&options, &runtime) != FS_OK) goto done;
    if (threshold(runtime, &result) != FS_OK) goto done;
    if (fs_result_release(result) != FS_OK) goto done;
    if (fs_result_kind(result, 0, &kind) != FS_E_INVALID_ARG) goto done;
    if (fs_result_release(result) != FS_E_INVALID_ARG) goto done;
    if (fs_result_kind((fs_result_t *)0x1234, 0, &kind) != FS_E_INVALID_ARG) goto done;

    result = NULL;
    if (threshold(runtime, &result) != FS_OK) goto done;
    race.result = result;
#ifdef _WIN32
    HANDLE thread = (HANDLE)_beginthreadex(NULL, 0, race_main, &race, 0, NULL);
    if (thread == NULL) goto done;
    atomic_store_explicit(&race.start, 1, memory_order_release);
    if (fs_result_release(result) != FS_OK) { CloseHandle(thread); goto done; }
    WaitForSingleObject(thread, INFINITE);
    CloseHandle(thread);
#else
    pthread_t thread;
    if (pthread_create(&thread, NULL, race_main, &race) != 0) goto done;
    atomic_store_explicit(&race.start, 1, memory_order_release);
    if (fs_result_release(result) != FS_OK) { pthread_join(thread, NULL); goto done; }
    pthread_join(thread, NULL);
#endif
    result = NULL;
    if (!race.ok) goto done;
    ok = 1;
done:
    if (result != NULL) fs_result_release(result);
    fs_runtime_destroy(runtime);
    return ok ? 0 : 1;
}
