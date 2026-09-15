#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Edge scale kappa is set based on parameter a
    double kappa = 0.02 + 0.2 * a;
    // Iteration count is set based on parameter b
    int iterations = 1 + (int)(15 * b);
    // Lambda is fixed at 0.2
    double lambda = 0.2;

    // Temporary storage for the next iteration
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        // Handle memory allocation failure
        memcpy(out, in, h * w * sizeof(double));
        return;
    }

    // Function to compute the gradient magnitude
    double gradient_magnitude(double center, double neighbor) {
        double diff = center - neighbor;
        return diff * diff;
    }

    // Function to compute the Perona-Malik conductance
    double conductance(double grad_mag, double kappa) {
        return 1.0 / (1.0 + (grad_mag / (kappa * kappa)));
    }

    // Main loop for the specified number of iterations
    for (int iter = 0; iter < iterations; ++iter) {
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double center = in[y * w + x];
                double grad_x = 0.0, grad_y = 0.0;

                // Compute gradient in x direction with periodic boundary conditions
                double left = in[y * w + ((x - 1 + w) % w)];
                double right = in[y * w + ((x + 1) % w)];
                grad_x = gradient_magnitude(center, left) + gradient_magnitude(center, right);

                // Compute gradient in y direction with periodic boundary conditions
                double top = in[((y - 1 + h) % h) * w + x];
                double bottom = in[((y + 1) % h) * w + x];
                grad_y = gradient_magnitude(center, top) + gradient_magnitude(center, bottom);

                // Compute the update term
                double update = 0.0;

                // Update in x direction
                double g_left = conductance(gradient_magnitude(center, left), kappa);
                double g_right = conductance(gradient_magnitude(center, right), kappa);
                update += g_left * (left - center) + g_right * (right - center);

                // Update in y direction
                double g_top = conductance(gradient_magnitude(center, top), kappa);
                double g_bottom = conductance(gradient_magnitude(center, bottom), kappa);
                update += g_top * (top - center) + g_bottom * (bottom - center);

                // Apply the update
                temp[y * w + x] = center + lambda * update;
            }
        }
        // Swap in and temp for the next iteration
        double* swap = in;
        in = temp;
        temp = swap;
    }

    // Copy the final result to out
    memcpy(out, in, h * w * sizeof(double));

    // Free the temporary storage
    if (in == temp) {
        free(temp);
    }
}
