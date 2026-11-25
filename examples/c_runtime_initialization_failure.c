/* Library-owned Python failure retry gate / library 所有 Python の失敗再試行門。 */
#include "fullseye.h"

#include <stdio.h>
#include <string.h>

static int expect_missing_runtime_root(fs_init_options_t *options, fs_runtime_t **runtime,
                                       const char *missing_root) {
    char message[4096];
    const fs_status_t status = fs_runtime_create(options, runtime);
    const size_t message_bytes = fs_last_error(NULL, message, sizeof(message));
    if (status == FS_E_NO_PYTHON && *runtime == NULL && message_bytes > 1u
        && message_bytes <= sizeof(message) && strstr(message, missing_root) != NULL
        && strstr(message, "does not contain fullseye/c_api_bridge.py") != NULL
        && strstr(message, "対応する配置の fullseye/c_api_bridge.py がありません") != NULL
        && strstr(message, "Set runtime_root") != NULL
        && strstr(message, "runtime_root に指定してください") != NULL
        && strstr(message, "fullseye doctor") != NULL) {
        return 1;
    }
    fprintf(stderr, "missing runtime_root: expected FS_E_NO_PYTHON and the bilingual repair "
                    "message; got status=%d runtime=%p message=%s\n",
            (int)status, (void *)*runtime, message);
    return 0;
}

int main(void) {
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *runtime = NULL;
    static const char missing_root[] = "fullseye-c-api-missing-root";
    options.runtime_root = missing_root;
    options.runtime_root_bytes = sizeof(missing_root) - 1u;
    /* Both calls fail before CPython initialization rather than resolving an
     * unrelated ambient package. / 無関係な環境を解決せず、CPython 起動前に失敗する。 */
    if (!expect_missing_runtime_root(&options, &runtime, missing_root)) return 1;
    if (!expect_missing_runtime_root(&options, &runtime, missing_root)) return 1;
    return 0;
}
