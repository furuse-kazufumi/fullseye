/* CPython ownership/configuration gate / CPython 所有者と設定の門。 */
#include "fullseye.h"

#include <string.h>

int main(int argc, char **argv) {
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *first = NULL;
    fs_runtime_t *second = NULL;
    fs_runtime_t *different = NULL;
    char other_root[] = "different-root";
    int ok = 0;
    if (argc < 2) return 1;
    options.runtime_root = argv[1];
    options.runtime_root_bytes = strlen(argv[1]);
    if (fs_runtime_create(&options, &first) != FS_OK) goto done;
    /* The library owns this isolated CPython: the same configuration may make
     * another runtime. / ライブラリ起動の隔離 CPython は同じ設定なら再利用できる。 */
    if (fs_runtime_create(&options, &second) != FS_OK) goto done;
    options.runtime_root = other_root;
    options.runtime_root_bytes = sizeof(other_root) - 1u;
    if (fs_runtime_create(&options, &different) != FS_E_INVALID_ARG) goto done;
    ok = 1;
done:
    fs_runtime_destroy(different);
    fs_runtime_destroy(second);
    fs_runtime_destroy(first);
    return ok ? 0 : 1;
}
