/* Missing explicit runtime fails closed before ambient discovery / 明示 runtime の不在は環境探索前に拒否する門。 */
#include "fullseye.h"

#include <string.h>

int main(int argc, char **argv) {
    const char *missing_root = argc > 1 ? argv[1] : "fullseye-runtime-root-does-not-exist";
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *runtime = (fs_runtime_t *)1;
    char message[16385] = {0};

    options.runtime_root = missing_root;
    options.runtime_root_bytes = strlen(missing_root);
    if (fs_runtime_create(&options, &runtime) != FS_E_NO_PYTHON || runtime != NULL) return 1;
    (void)fs_last_error(NULL, message, sizeof(message));
    if (strstr(message, missing_root) == NULL
        || strstr(message, "does not contain fullseye/c_api_bridge.py") == NULL
        || strstr(message, "対応する配置の fullseye/c_api_bridge.py がありません") == NULL
        || strstr(message, "Set runtime_root") == NULL
        || strstr(message, "runtime_root に指定してください") == NULL
        || strstr(message, "fullseye doctor") == NULL) return 1;
    return 0;
}
