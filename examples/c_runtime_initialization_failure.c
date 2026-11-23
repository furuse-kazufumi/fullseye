/* Library-owned Python failure retry gate / library 所有 Python の失敗再試行門。 */
#include "fullseye.h"

int main(void) {
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *runtime = NULL;
    static const char missing_root[] = "fullseye-c-api-missing-root";
    options.runtime_root = missing_root;
    options.runtime_root_bytes = sizeof(missing_root) - 1u;
    /* Both calls enter the library-owned interpreter path. The second must not
     * be rejected as an unsafe host interpreter. / 2 回目を host 扱いしない。 */
    if (fs_runtime_create(&options, &runtime) != FS_E_NO_PYTHON || runtime != NULL) return 1;
    if (fs_runtime_create(&options, &runtime) != FS_E_NO_PYTHON || runtime != NULL) return 1;
    return 0;
}
