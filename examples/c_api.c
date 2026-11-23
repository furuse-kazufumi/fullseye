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

static fs_input_t result_input(fs_value_kind_t kind, const fs_result_t *result, size_t index) {
    fs_input_t input = FS_INPUT_INIT;
    input.kind = kind;
    input.result = result;
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
    fs_result_t *contract_region = NULL;
    fs_result_t *objects = NULL;
    fs_result_t *measures = NULL;
    fs_result_t *registry_region = NULL;
    fs_result_t *count = NULL;
    char *catalog = NULL;
    size_t catalog_bytes = 0;
    int ok = 0;

    if (argc > 1) {
        options.runtime_root = argv[1];
    }
    if (!check(NULL, fs_runtime_create(&options, &runtime), "initialize")) goto done;
    if (!check(runtime, fs_find_ops_json(runtime, "{\"query\":\"threshold\"}",
                                         &catalog, &catalog_bytes), "search")) goto done;
    if (catalog_bytes == 0 || strstr(catalog, "contract:threshold") == NULL) goto done;

    fs_input_t image = image_input(pixels, 30, 5, 6);
    if (!check(runtime, fs_call(runtime, "contract:threshold", &image, 1,
                                "{\"lo\":0.6,\"hi\":1.0}", &contract_region),
               "contract threshold")) goto done;
    fs_input_t region = result_input(FS_VALUE_REGION, contract_region, 0);
    if (!check(runtime, fs_call(runtime, "contract:connection", &region, 1, "{}", &objects),
               "connection")) goto done;
    fs_input_t object_input = result_input(FS_VALUE_OBJECTSET, objects, 0);
    if (!check(runtime, fs_call(runtime, "contract:measure_all", &object_input, 1, "{}", &measures),
               "measure_all")) goto done;

    if (!check(runtime, fs_call(runtime, "registry:threshold", &image, 1,
                                "{\"a\":0.6,\"b\":0.5}", &registry_region),
               "registry threshold")) goto done;
    fs_input_t registry_input = result_input(FS_VALUE_REGION, registry_region, 0);
    if (!check(runtime, fs_call(runtime, "registry:blob_count", &registry_input, 1, "{}", &count),
               "blob_count")) goto done;

    {
        double value = -1.0;
        size_t objects_count = 0;
        size_t tuple_count = 0;
        if (fs_result_object_count(objects, 0, &objects_count) != FS_OK || objects_count != 4) goto done;
        if (fs_result_tuple_size(measures, 0, &tuple_count) != FS_OK || tuple_count != 4) goto done;
        if (fs_result_real(count, 0, &value) != FS_OK || value != 4.0) goto done;
    }
    ok = 1;

done:
    fs_free(catalog);
    fs_result_release(count);
    fs_result_release(registry_region);
    fs_result_release(measures);
    fs_result_release(objects);
    fs_result_release(contract_region);
    fs_runtime_destroy(runtime);
    return ok ? 0 : 1;
}
