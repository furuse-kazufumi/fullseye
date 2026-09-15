#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate the shift amount based on parameter a
    int s = 1 + (int)(4 * a);
    
    // Calculate the amplitude based on parameter b
    double amplitude = 0.1 + 0.9 * b;
    
    // Temporary storage for the high-pass filtered image
    double* high_pass = (double*)malloc(h * w * sizeof(double));
    if (high_pass == NULL) {
        // Handle memory allocation failure
        memcpy(out, in, h * w * sizeof(double));
        return;
    }
    
    // Apply Gaussian blur with sigma = 1 to create the low-pass version
    double* low_pass = (double*)malloc(h * w * sizeof(double));
    if (low_pass == NULL) {
        // Handle memory allocation failure
        free(high_pass);
        memcpy(out, in, h * w * sizeof(double));
        return;
    }
    
    // Simple 3x3 Gaussian kernel with sigma = 1
    double kernel[9] = {1.0, 2.0, 1.0, 2.0, 4.0, 2.0, 1.0, 2.0, 1.0};
    double kernel_sum = 16.0;
    
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    // Clamp to edge for boundary handling
                    if (ny < 0) ny = 0;
                    if (ny >= h) ny = h - 1;
                    if (nx < 0) nx = 0;
                    if (nx >= w) nx = w - 1;
                    sum += in[ny * w + nx] * kernel[(ky + 1) * 3 + (kx + 1)];
                }
            }
            low_pass[y * w + x] = sum / kernel_sum;
        }
    }
    
    // Compute the high-pass version
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            high_pass[y * w + x] = in[y * w + x] - low_pass[y * w + x];
        }
    }
    
    // Shift the high-pass image horizontally by s pixels
    double* shifted_high_pass = (double*)malloc(h * w * sizeof(double));
    if (shifted_high_pass == NULL) {
        // Handle memory allocation failure
        free(high_pass);
        free(low_pass);
        memcpy(out, in, h * w * sizeof(double));
        return;
    }
    
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int nx = x + s;
            if (nx >= w) nx = w - 1; // Clamp to edge for boundary handling
            shifted_high_pass[y * w + x] = high_pass[y * w + nx];
        }
    }
    
    // Combine the original image with the shifted high-pass image
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x] + amplitude * shifted_high_pass[y * w + x];
            // Clamp the output to [0, 1]
            if (out[y * w + x] < 0.0) out[y * w + x] = 0.0;
            if (out[y * w + x] > 1.0) out[y * w + x] = 1.0;
        }
    }
    
    // Free allocated memory
    free(high_pass);
    free(low_pass);
    free(shifted_high_pass);
}
