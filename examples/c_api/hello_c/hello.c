#include <fullseye.h>

#include <stdio.h>

int main(void) {
    const double pixels[] = {0.0, 0.2, 0.0, 0.2, 1.0, 0.2, 0.0, 0.2, 0.0};
    fs_init_options_t options = FS_INIT_OPTIONS_INIT;
    fs_runtime_t *runtime = NULL;
    fs_result_id_t result = 0u;
    fs_input_n_t image = FS_INPUT_N_INIT;
    image.image.data = pixels;
    image.image.data_bytes = sizeof(pixels);
    image.image.width = 3;
    image.image.height = 3;
    image.image.row_stride_bytes = 3 * (int64_t)sizeof(double);

    if (fs_runtime_create(&options, &runtime) != FS_OK
        || fs_call_id_n(runtime, "registry:gaussian", sizeof("registry:gaussian") - 1u,
                        &image, 1, "{\"a\":0.5}", sizeof("{\"a\":0.5}") - 1u,
                        &result) != FS_OK) {
        char message[1024] = {0};
        fs_last_error(runtime, message, sizeof(message));
        fprintf(stderr, "Fullseye error: %s\n", message);
        fs_runtime_destroy(runtime);
        return 1;
    }
    {
        size_t count = 0u;
        const fs_status_t status = fs_result_count_n(result, &count);
        fs_image_view_t filtered = FS_IMAGE_VIEW_INIT;
        double sum = 0.0;
        if (status == FS_OK && fs_result_image_n(result, 0u, &filtered) == FS_OK) {
            const double *values = (const double *)filtered.data;
            for (int64_t row = 0; row < filtered.height; ++row)
                for (int64_t column = 0; column < filtered.width; ++column)
                    sum += values[row * (filtered.row_stride_bytes / (int64_t)sizeof(double)) + column];
        }
        printf("result_count=%zu output_sum=%.17g\n", count, sum);
        (void)fs_result_release_n(result);
        fs_runtime_destroy(runtime);
        return status == FS_OK && count == 1u ? 0 : 1;
    }
}
