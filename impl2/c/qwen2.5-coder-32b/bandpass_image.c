#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // FFT and IFFT functions are not provided in standard C99, so we need to implement or use an external library.
    // For simplicity, we will use a naive implementation of FFT and IFFT here.
    // Note: This implementation is not optimized and is for educational purposes only.

    int n = h * w;
    double* real = (double*)malloc(n * sizeof(double));
    double* imag = (double*)malloc(n * sizeof(double));
    double* real_out = (double*)malloc(n * sizeof(double));
    double* imag_out = (double*)malloc(n * sizeof(double));

    // Copy input to real part and initialize imaginary part to zero
    memcpy(real, in, n * sizeof(double));
    memset(imag, 0, n * sizeof(double));

    // Perform 2D FFT
    for (int y = 0; y < h; y++) {
        fft(real + y * w, imag + y * w, w);
    }
    for (int x = 0; x < w; x++) {
        fft(real + x, imag + x, h, w);
    }

    // Apply bandpass filter in frequency domain
    double cutoff_a = a * (h / 2.0);
    double cutoff_b = b * (h / 2.0);
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double freq_x = x <= w / 2 ? x : x - w;
            double freq_y = y <= h / 2 ? y : y - h;
            double distance = sqrt(freq_x * freq_x + freq_y * freq_y);
            if (distance < cutoff_a || distance > cutoff_b) {
                real[y * w + x] = 0;
                imag[y * w + x] = 0;
            }
        }
    }

    // Perform 2D IFFT
    for (int y = 0; y < h; y++) {
        ifft(real + y * w, imag + y * w, w);
    }
    for (int x = 0; x < w; x++) {
        ifft(real + x, imag + x, h, w);
    }

    // Normalize and map to [0, 1]
    double max_val = 0;
    for (int i = 0; i < n; i++) {
        double val = real[i] / n;
        if (val > max_val) max_val = val;
        if (val < -max_val) max_val = -val;
    }
    for (int i = 0; i < n; i++) {
        double val = real[i] / n;
        out[i] = (val + max_val) / (2 * max_val);
    }

    // Free allocated memory
    free(real);
    free(imag);
    free(real_out);
    free(imag_out);
}

void fft(double* real, double* imag, int n, int stride = 1) {
    if (n <= 1) return;

    int m = n / 2;
    double* real_even = (double*)malloc(m * sizeof(double));
    double* imag_even = (double*)malloc(m * sizeof(double));
    double* real_odd = (double*)malloc(m * sizeof(double));
    double* imag_odd = (double*)malloc(m * sizeof(double));

    for (int i = 0; i < m; i++) {
        real_even[i] = real[i * stride * 2];
        imag_even[i] = imag[i * stride * 2];
        real_odd[i] = real[i * stride * 2 + stride];
        imag_odd[i] = imag[i * stride * 2 + stride];
    }

    fft(real_even, imag_even, m, stride * 2);
    fft(real_odd, imag_odd, m, stride * 2);

    for (int k = 0; k < m; k++) {
        double t_real = real_even[k * stride] * cos(2 * M_PI * k / n) - imag_even[k * stride] * sin(2 * M_PI * k / n);
        double t_imag = real_even[k * stride] * sin(2 * M_PI * k / n) + imag_even[k * stride] * cos(2 * M_PI * k / n);
        real[k * stride] = t_real + real_odd[k * stride] * cos(2 * M_PI * (k + m) / n) - imag_odd[k * stride] * sin(2 * M_PI * (k + m) / n);
        imag[k * stride] = t_imag + real_odd[k * stride] * sin(2 * M_PI * (k + m) / n) + imag_odd[k * stride] * cos(2 * M_PI * (k + m) / n);
        real[(k + m) * stride] = t_real - real_odd[k * stride] * cos(2 * M_PI * (k + m) / n) + imag_odd[k * stride] * sin(2 * M_PI * (k + m) / n);
        imag[(k + m) * stride] = t_imag - real_odd[k * stride] * sin(2 * M_PI * (k + m) / n) - imag_odd[k * stride] * cos(2 * M_PI * (k + m) / n);
    }

    free(real_even);
    free(imag_even);
    free(real_odd);
    free(imag_odd);
}

void ifft(double* real, double* imag, int n, int stride = 1) {
    for (int i = 0; i < n; i++) {
        imag[i * stride] = -imag[i * stride];
    }
    fft(real, imag, n, stride);
    for (int i = 0; i < n; i++) {
        imag[i * stride] = -imag[i * stride];
        real[i * stride] /= n;
        imag[i * stride] /= n;
    }
}
