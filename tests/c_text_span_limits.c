/* Bounded-text refusal gate / 長さ付きテキストの拒否を確かめる C の門。 */
#include "fullseye.h"

#include <stdint.h>
#include <string.h>

int main(int argc, char **argv) {
    static const char query[] = "{}";
    static const char op[] = "contract:threshold";
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *runtime = NULL;
    fs_result_id_t result = UINT64_C(1);
    char *catalog = (char *)UINTPTR_MAX;
    size_t catalog_bytes = SIZE_MAX;
    const size_t hostile_bytes = SIZE_MAX / 2u;
    int ok = 0;

    if (argc > 1) {
        options.runtime_root = argv[1];
        options.runtime_root_bytes = strlen(argv[1]);
    }
    if (fs_runtime_create(&options, &runtime) != FS_OK) goto done;

    if (fs_find_ops_json_n(runtime, query, hostile_bytes, &catalog, &catalog_bytes) != FS_E_INVALID_ARG
        || catalog != NULL || catalog_bytes != 0u) goto done;
    if (fs_call_id_n(runtime, op, hostile_bytes, NULL, 0, query, sizeof(query) - 1u, &result)
            != FS_E_INVALID_ARG || result != 0u) goto done;
    result = UINT64_C(1);
    if (fs_call_id_n(runtime, op, sizeof(op) - 1u, NULL, 0, query, hostile_bytes, &result)
            != FS_E_INVALID_ARG || result != 0u) goto done;
    ok = 1;

done:
    fs_runtime_destroy(runtime);
    return ok ? 0 : 1;
}
