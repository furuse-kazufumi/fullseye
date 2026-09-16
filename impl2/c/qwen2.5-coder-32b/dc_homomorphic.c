#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Allocate memory for the frequency domain representation
    double* real = (double*)malloc(h * w * sizeof(double));
    double* imag = (double*)malloc(h * w * sizeof(double));
    double* mag = (double*)malloc(h * w * sizeof(double));
    double* phase = (double*)malloc(h * w * sizeof(double));
    double* filtered_real = (double*)malloc(h * w * sizeof(double));
    double* filtered_imag = (double*)malloc(h * w * sizeof(double));

    // Forward FFT
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            real[y * w + x] = in[y * w + x];
            imag[y * w + x] = 0.0;
        }
    }

    // Perform 2D FFT using a simple implementation (not optimized)
    for (int u = 0; u < h; u++) {
        for (int v = 0; v < w; v++) {
            double sum_real = 0.0;
            double sum_imag = 0.0;
            for (int y = 0; y < h; y++) {
                for (int x = 0; x < w; x++) {
                    double angle = -2.0 * M_PI * ((u * y / (double)h) + (v * x / (double)w));
                    sum_real += real[y * w + x] * cos(angle) - imag[y * w + x] * sin(angle);
                    sum_imag += real[y * w + x] * sin(angle) + imag[y * w + x] * cos(angle);
                }
            }
            real[u * w + v] = sum_real / (h * w);
            imag[u * w + v] = sum_imag / (h * w);
        }
    }

    // Calculate magnitude and phase
    for (int u = 0; u < h; u++) {
        for (int v = 0; v < w; v++) {
            mag[u * w + v] = sqrt(real[u * w + v] * real[u * w + v] + imag[u * w + v] * imag[u * w + v]);
            phase[u * w + v] = atan2(imag[u * w + v], real[u * w + v]);
        }
    }

    // Apply homomorphic filter
    for (int u = 0; u < h; u++) {
        for (int v = 0; v < w; v++) {
            double Duv = sqrt((u - h / 2.0) * (u - h / 2.0) + (v - w / 2.0) * (v - w / 2.0));
            double Huv = a + (1.0 - a) * (1.0 - exp(-b * Duv * Duv));
            filtered_real[u * w + v] = Huv * mag[u * w + v] * cos(phase[u * w + v]);
            filtered_imag[u * w + v] = Huv * mag[u * w + v] * sin(phase[u * w + v]);
        }
    }

    // Inverse FFT
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum_real = 0.0;
            double sum_imag = 0.0;
            for (int u = 0; u < h; u++) {
                for (int v = 0; v < w; v++) {
                    double angle = 2.0 * M_PI * ((u * y / (double)h) + (v * x / (double)w));
                    sum_real += filtered_real[u * w + v] * cos(angle) - filtered_imag[u * w + v] * sin(angle);
                    sum_imag += filtered_real[u * w + v] * sin(angle) + filtered_imag[u * w + v] * cos(angle);
                }
            }
            out[y * w + x] = sum_real;
        }
    }

    // Free allocated memory
    free(real);
    free(imag);
    free(mag);
    free(phase);
    free(filtered_real);
    free(filtered_imag);
}
