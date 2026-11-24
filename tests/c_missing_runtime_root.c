/* Missing build-time runtime refusal gate / 消えた build-time runtime の拒否門。 */
#include "fullseye.h"

#include <string.h>

int main(int argc, char **argv) {
    const char *missing_root = argc > 1 ? argv[1] : "fullseye-runtime-root-does-not-exist";
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *runtime = (fs_runtime_t *)1;
    char message[512] = {0};

    options.runtime_root = missing_root;
    options.runtime_root_bytes = strlen(missing_root);
    if (fs_runtime_create(&options, &runtime) != FS_E_NO_PYTHON || runtime != NULL) return 1;
    (void)fs_last_error(NULL, message, sizeof(message));
    if (strstr(message, "no longer exists") == NULL || strstr(message, "Re-run CMake") == NULL) return 1;
    return 0;
}
