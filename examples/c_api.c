/* Fullseye C ABI lifecycle example / Fullseye C ABI の寿命を通す例。 */
#include "fullseye.h"

#include <stdio.h>
#include <string.h>

static int check(fs_runtime_t *runtime, fs_status_t status, const char *stage) {
    char message[1024];
    if (status == FS_OK) {
        return 1;
    }
    fs_last_error(runtime, message, sizeof(message));
    fprintf(stderr, "%s failed (%d): %s\n", stage, (int)status, message);
    return 0;
}

static fs_input_t image_input(const double *pixels, size_t count, int64_t height, int64_t width) {
    fs_input_t input = FS_INPUT_INIT;
    input.image.data = pixels;
    input.image.data_bytes = count * sizeof(double);
    input.image.width = width;
    input.image.height = height;
    input.image.row_stride_bytes = width * (int64_t)sizeof(double);
    return input;
}

static fs_input_n_t result_input(fs_value_kind_t kind, fs_result_id_t result, size_t index) {
    fs_input_n_t input = FS_INPUT_N_INIT;
    input.kind = kind;
    input.result_id = result;
    input.result_index = index;
    return input;
}

int main(int argc, char **argv) {
    const double pixels[30] = {
        0, 0, 0, 0, 0, 0,
        0, .8, .8, 0, .9, 0,
        0, .8, .8, 0, .9, 0,
        0, 0, 0, 0, 0, 0,
        .7, 0, 0, 0, 0, .7
    };
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *runtime = NULL;
    fs_result_id_t contract_region = 0u;
    fs_result_id_t objects = 0u;
    fs_result_id_t measures = 0u;
    fs_result_id_t registry_region = 0u;
    fs_result_id_t count = 0u;
    char *catalog = NULL;
    size_t catalog_bytes = 0;
    int ok = 0;

    if (argc > 1) {
        options.runtime_root = argv[1];
        options.runtime_root_bytes = strlen(argv[1]);
    }
    if (!check(NULL, fs_runtime_create(&options, &runtime), "initialize")) goto done;
    if (!check(runtime, fs_find_ops_json_n(runtime, "{\"query\":\"threshold\"}",
                                           sizeof("{\"query\":\"threshold\"}") - 1u,
                                           &catalog, &catalog_bytes), "search")) goto done;
    if (catalog_bytes == 0 || strstr(catalog, "contract:threshold") == NULL) goto done;

    fs_input_n_t image = FS_INPUT_N_INIT;
    image.image = image_input(pixels, 30, 5, 6).image;
    if (!check(runtime, fs_call_n(runtime, "contract:threshold", sizeof("contract:threshold") - 1u,
                                  &image, 1, "{\"lo\":0.6,\"hi\":1.0}",
                                  sizeof("{\"lo\":0.6,\"hi\":1.0}") - 1u, &contract_region),
               "contract threshold")) goto done;
    fs_input_n_t region = result_input(FS_VALUE_REGION, contract_region, 0);
    if (!check(runtime, fs_call_n(runtime, "contract:connection", sizeof("contract:connection") - 1u,
                                  &region, 1, "{}", sizeof("{}") - 1u, &objects),
               "connection")) goto done;
    fs_input_n_t object_input = result_input(FS_VALUE_OBJECTSET, objects, 0);
    if (!check(runtime, fs_call_n(runtime, "contract:measure_all", sizeof("contract:measure_all") - 1u,
                                  &object_input, 1, "{}", sizeof("{}") - 1u, &measures),
               "measure_all")) goto done;

    if (!check(runtime, fs_call_n(runtime, "registry:threshold", sizeof("registry:threshold") - 1u,
                                  &image, 1, "{\"a\":0.6,\"b\":0.5}",
                                  sizeof("{\"a\":0.6,\"b\":0.5}") - 1u, &registry_region),
               "registry threshold")) goto done;
    fs_input_n_t registry_input = result_input(FS_VALUE_REGION, registry_region, 0);
    if (!check(runtime, fs_call_n(runtime, "registry:blob_count", sizeof("registry:blob_count") - 1u,
                                  &registry_input, 1, "{}", sizeof("{}") - 1u, &count),
               "blob_count")) goto done;

    {
        double value = -1.0;
        size_t objects_count = 0;
        size_t tuple_count = 0;
        if (fs_result_object_count_n(objects, 0, &objects_count) != FS_OK || objects_count != 4) goto done;
        if (fs_result_tuple_size_n(measures, 0, &tuple_count) != FS_OK || tuple_count != 4) goto done;
        if (fs_result_real_n(count, 0, &value) != FS_OK || value != 4.0) goto done;
    }
    ok = 1;

done:
    fs_free(catalog);
    (void)fs_result_release_n(count);
    (void)fs_result_release_n(registry_region);
    (void)fs_result_release_n(measures);
    (void)fs_result_release_n(objects);
    (void)fs_result_release_n(contract_region);
    fs_runtime_destroy(runtime);
    return ok ? 0 : 1;
}
