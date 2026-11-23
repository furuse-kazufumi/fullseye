/* Thread-local error gate using native OS threads / OS ネイティブスレッドによるエラー分離の門。 */
#include "fullseye.h"

#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#include <process.h>
#else
#include <pthread.h>
#endif

enum { THREAD_COUNT = 8, ERROR_CAPACITY = 1024 };

typedef struct thread_arg {
    fs_runtime_t *runtime;
    int index;
    int ok;
} thread_arg_t;

static void run_one(thread_arg_t *arg) {
    char op[64];
    char error[ERROR_CAPACITY];
    fs_result_t *result = NULL;
    snprintf(op, sizeof(op), "registry:missing_%d", arg->index);
    fs_status_t status = fs_call_n(arg->runtime, op, strlen(op), NULL, 0,
                                   "{}", sizeof("{}") - 1u, &result);
    fs_last_error(arg->runtime, error, sizeof(error));
    arg->ok = status == FS_E_UNKNOWN_OP && result == NULL && strstr(error, op) != NULL;
}

#ifdef _WIN32
static unsigned __stdcall thread_main(void *value) {
    run_one((thread_arg_t *)value);
    return 0;
}
#else
static void *thread_main(void *value) {
    run_one((thread_arg_t *)value);
    return NULL;
}
#endif

int main(int argc, char **argv) {
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *runtime = NULL;
    thread_arg_t args[THREAD_COUNT];
    int ok = 1;
    int index;
    if (argc > 1) options.runtime_root = argv[1];
    if (fs_runtime_create(&options, &runtime) != FS_OK) return 1;

#ifdef _WIN32
    HANDLE threads[THREAD_COUNT];
    for (index = 0; index < THREAD_COUNT; ++index) {
        args[index] = (thread_arg_t){runtime, index, 0};
        threads[index] = (HANDLE)_beginthreadex(NULL, 0, thread_main, &args[index], 0, NULL);
        if (threads[index] == NULL) ok = 0;
    }
    if (ok) WaitForMultipleObjects(THREAD_COUNT, threads, TRUE, INFINITE);
    for (index = 0; index < THREAD_COUNT; ++index) {
        if (threads[index] != NULL) CloseHandle(threads[index]);
    }
#else
    pthread_t threads[THREAD_COUNT];
    for (index = 0; index < THREAD_COUNT; ++index) {
        args[index] = (thread_arg_t){runtime, index, 0};
        if (pthread_create(&threads[index], NULL, thread_main, &args[index]) != 0) ok = 0;
    }
    if (ok) {
        for (index = 0; index < THREAD_COUNT; ++index) pthread_join(threads[index], NULL);
    }
#endif
    for (index = 0; index < THREAD_COUNT; ++index) ok = ok && args[index].ok;
    fs_runtime_destroy(runtime);
    return ok ? 0 : 1;
}
