/* Runtime discovery is inspectable without starting CPython / CPython を起動せず探索を報告する門。 */
#include "fullseye.h"

#include <string.h>

int main(void) {
    char report[8192] = {0};
    const size_t needed = fs_runtime_diagnose(report, sizeof(report));
    if (needed < 2u || report[0] == '\0') return 1;
    if (strstr(report, "Tried:") == NULL) return 2;
    if (strstr(report, "FULLSEYE_PYTHON_ROOT") == NULL) return 3;
    /* This call is diagnostic only: creating a runtime would log/select one
     * candidate, whereas this gate must work even when none is installed. */
    return 0;
}
