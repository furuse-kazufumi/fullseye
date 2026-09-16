#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Number of iterations is determined by parameter 'a' scaled to an integer value
    int iterations = (int)(a * 10.0); // Assuming 'a' in [0,1] scales to 0 to 10 iterations
    double K = b; // Conductance parameter

    // Temporary storage for intermediate results
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // Handle memory allocation failure
        memcpy(out, in, h * w * sizeof(double));
        return;
    }

    // Copy initial input to output
    memcpy(out, in, h * w * sizeof(double));

    // Anisotropic diffusion loop
    for (int iter = 0; iter < iterations; ++iter) {
        // Swap roles of out and temp
        double* current = out;
        out = temp;
        temp = current;

        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                // Calculate indices with periodic boundary conditions
                int left = (x - 1 + w) % w;
                int right = (x + 1) % w;
                int top = (y - 1 + h) % h;
                int bottom = (y + 1) % h;

                // Calculate differences
                double dx = current[y * w + right] - current[y * w + left];
                double dy = current[bottom * w + x] - current[top * w + x];

                // Calculate conductance terms
                double g_x = exp(-dx * dx / (K * K));
                double g_y = exp(-dy * dy / (K * K));

                // Update pixel value
                out[y * w + x] = current[y * w + x] + 0.25 * (
                    g_x * (current[y * w + right] - current[y * w + left]) +
                    g_y * (current[bottom * w + x] - current[top * w + x])
                );
            }
        }
    }

    // Copy final result to output if necessary
    if (out != temp) {
        memcpy(out, temp, h * w * sizeof(double));
    }

    // Free temporary storage
    free(temp);
}
