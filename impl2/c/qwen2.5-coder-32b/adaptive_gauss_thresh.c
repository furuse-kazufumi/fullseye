#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Calculate sigma and offset based on the parameters a and b
    double sigma = 1.0 + 3.0 * a; // sigma ranges from 1.0 to 4.0
    double offset = (b - 0.5) * 0.3; // offset ranges from -0.15 to 0.15

    // Calculate the size of the Gaussian kernel
    int kernel_size = (int)(6 * sigma + 1); // 6-sigma rule for kernel size
    int half_kernel = kernel_size / 2;

    // Allocate memory for the Gaussian kernel
    double* kernel = (double*)malloc(kernel_size * sizeof(double));
    double sum = 0.0;

    // Create the Gaussian kernel
    for (int i = 0; i < kernel_size; i++) {
        int x = i - half_kernel;
        kernel[i] = exp(-(x * x) / (2 * sigma * sigma)) / (sqrt(2 * M_PI) * sigma);
        sum += kernel[i];
    }

    // Normalize the kernel
    for (int i = 0; i < kernel_size; i++) {
        kernel[i] /= sum;
    }

    // Allocate memory for the temporary image to store the Gaussian filtered values
    double* temp = (double*)malloc(h * w * sizeof(double));

    // Apply Gaussian filter along the rows
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int k = 0; k < kernel_size; k++) {
                int nx = x + k - half_kernel;
                if (nx < 0) nx = 0; // Boundary handling: clamp to edge
                if (nx >= w) nx = w - 1;
                sum += in[y * w + nx] * kernel[k];
            }
            temp[y * w + x] = sum;
        }
    }

    // Apply Gaussian filter along the columns
    for (int x = 0; x < w; x++) {
        for (int y = 0; y < h; y++) {
            double sum = 0.0;
            for (int k = 0; k < kernel_size; k++) {
                int ny = y + k - half_kernel;
                if (ny < 0) ny = 0; // Boundary handling: clamp to edge
                if (ny >= h) ny = h - 1;
                sum += temp[ny * w + x] * kernel[k];
            }
            double threshold = sum + offset;
            out[y * w + x] = (in[y * w + x] > threshold) ? 1.0 : 0.0;
        }
    }

    // Free allocated memory
    free(kernel);
    free(temp);
}
