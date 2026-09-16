#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Edge handling: wrap around (periodic boundary conditions)
    // This is chosen based on the specification which states that the edges wrap around.

    // Constants
    const double lambda = 0.2;
    const double kappa = 0.02 + 0.2 * a;
    const int iterations = 1 + (int)(15 * b);

    // Helper function to get the value at a given coordinate with periodic boundary conditions
    double get_value(const double* img, int y, int x, int height, int width) {
        return img[(y % height + height) % height * width + (x % width + width) % width];
    }

    // Helper function to compute the gradient in a given direction
    double compute_gradient(const double* img, int y, int x, int height, int width, int dir) {
        int dy = (dir == 0) ? 1 : 0;
        int dx = (dir == 0) ? 0 : 1;
        return get_value(img, y + dy, x + dx, height, width) - get_value(img, y, x, height, width);
    }

    // Helper function to compute the conductance function g(s)
    double conductance(double s, double kappa) {
        return 1.0 / (1.0 + pow(s / kappa, 2));
    }

    // Apply the Perona-Malik diffusion
    for (int iter = 0; iter < iterations; iter++) {
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double sum = 0.0;
                for (int dir = 0; dir < 4; dir++) {
                    double grad = compute_gradient(in, y, x, h, w, dir);
                    double g = conductance(fabs(grad), kappa);
                    sum += g * grad;
                }
                out[y * w + x] = in[y * w + x] + lambda * sum;
            }
        }
        // Copy the output back to the input for the next iteration
        for (int i = 0; i < h * w; i++) {
            in[i] = out[i];
        }
    }
}
