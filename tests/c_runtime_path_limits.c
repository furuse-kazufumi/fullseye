/* Runtime-path span refusal gate / runtime path の span 拒否ゲート。 */
#include "fullseye.h"

#include <stdint.h>

int main(void) {
    static const char path[] = "x";
    const size_t hostile_bytes = SIZE_MAX / 2u;
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *runtime = (fs_runtime_t *)UINTPTR_MAX;

    options.runtime_root = path;
    options.runtime_root_bytes = hostile_bytes;
    if (fs_runtime_create(&options, &runtime) != FS_E_INVALID_ARG || runtime != NULL) return 1;

    runtime = (fs_runtime_t *)UINTPTR_MAX;
    options.runtime_root = NULL;
    options.runtime_root_bytes = 0u;
    options.python_home = path;
    options.python_home_bytes = hostile_bytes;
    if (fs_runtime_create(&options, &runtime) != FS_E_INVALID_ARG || runtime != NULL) return 1;

    return 0;
}
