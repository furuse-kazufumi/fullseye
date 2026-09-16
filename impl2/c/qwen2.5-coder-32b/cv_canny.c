#include <math.h>
#include <stdlib.h>
#include <string.h>

#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define MIN(a, b) ((a) < (b) ? (a) : (b))

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    if (h < 1 || w < 1) return;

    // Convert input image to 8-bit grayscale
    unsigned char* gray = (unsigned char*)malloc(h * w * sizeof(unsigned char));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            gray[index] = (unsigned char)(CLAMP(in[index] * 255.0, 0, 255));
        }
    }

    // Calculate thresholds
    int threshold1 = (int)(50.0 + 100.0 * a);
    int threshold2 = (int)(100.0 + 150.0 * b);

    // Allocate memory for intermediate results
    unsigned char* edges = (unsigned char*)calloc(h * w, sizeof(unsigned char));
    unsigned char* weak = (unsigned char*)calloc(h * w, sizeof(unsigned char));
    unsigned char* strong = (unsigned char*)calloc(h * w, sizeof(unsigned char));

    // Gaussian blur (simple 3x3 averaging filter for demonstration)
    unsigned char* blurred = (unsigned char*)malloc(h * w * sizeof(unsigned char));
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            int index = y * w + x;
            blurred[index] = (gray[index - w - 1] + gray[index - w] + gray[index - w + 1] +
                              gray[index - 1] + gray[index] + gray[index + 1] +
                              gray[index + w - 1] + gray[index + w] + gray[index + w + 1]) / 9;
        }
    }
    // Copy border pixels
    for (int x = 0; x < w; x++) {
        blurred[x] = gray[x];
        blurred[(h - 1) * w + x] = gray[(h - 1) * w + x];
    }
    for (int y = 0; y < h; y++) {
        blurred[y * w] = gray[y * w];
        blurred[y * w + w - 1] = gray[y * w + w - 1];
    }

    // Sobel edge detection
    int* grad_x = (int*)malloc(h * w * sizeof(int));
    int* grad_y = (int*)malloc(h * w * sizeof(int));
    int* grad_mag = (int*)malloc(h * w * sizeof(int));
    double* grad_dir = (double*)malloc(h * w * sizeof(double));
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            int index = y * w + x;
            int gx = (blurred[index - w - 1] + 2 * blurred[index - 1] + blurred[index + w - 1]) -
                     (blurred[index - w + 1] + 2 * blurred[index + 1] + blurred[index + w + 1]);
            int gy = (blurred[index - w - 1] + 2 * blurred[index - w] + blurred[index - w + 1]) -
                     (blurred[index + w - 1] + 2 * blurred[index + w] + blurred[index + w + 1]);
            grad_x[index] = gx;
            grad_y[index] = gy;
            grad_mag[index] = (int)sqrt(gx * gx + gy * gy);
            grad_dir[index] = atan2((double)gy, (double)gx) * 180.0 / M_PI;
        }
    }
    // Copy border pixels
    for (int x = 0; x < w; x++) {
        grad_x[x] = grad_x[w + x];
        grad_x[(h - 1) * w + x] = grad_x[(h - 2) * w + x];
        grad_y[x] = grad_y[w + x];
        grad_y[(h - 1) * w + x] = grad_y[(h - 2) * w + x];
        grad_mag[x] = grad_mag[w + x];
        grad_mag[(h - 1) * w + x] = grad_mag[(h - 2) * w + x];
        grad_dir[x] = grad_dir[w + x];
        grad_dir[(h - 1) * w + x] = grad_dir[(h - 2) * w + x];
    }
    for (int y = 0; y < h; y++) {
        grad_x[y * w] = grad_x[y * w + 1];
        grad_x[y * w + w - 1] = grad_x[y * w + w - 2];
        grad_y[y * w] = grad_y[y * w + 1];
        grad_y[y * w + w - 1] = grad_y[y * w + w - 2];
        grad_mag[y * w] = grad_mag[y * w + 1];
        grad_mag[y * w + w - 1] = grad_mag[y * w + w - 2];
        grad_dir[y * w] = grad_dir[y * w + 1];
        grad_dir[y * w + w - 1] = grad_dir[y * w + w - 2];
    }

    // Non-maximum suppression
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            int index = y * w + x;
            double angle = grad_dir[index];
            int q = 255;
            int r = 255;

            // angle 0
            if ((angle >= -22.5 && angle < 22.5) || (angle >= 157.5 && angle <= 180) || (angle >= -180 && angle < -157.5)) {
                q = grad_mag[index + 1];
                r = grad_mag[index - 1];
            }
            // angle 45
            else if ((angle >= 22.5 && angle < 67.5) || (angle >= -157.5 && angle < -112.5)) {
                q = grad_mag[index + w + 1];
                r = grad_mag[index - w - 1];
            }
            // angle 90
            else if ((angle >= 67.5 && angle < 112.5) || (angle >= -112.5 && angle < -67.5)) {
                q = grad_mag[index + w];
                r = grad_mag[index - w];
            }
            // angle 135
            else if ((angle >= 112.5 && angle < 157.5) || (angle >= -67.5 && angle < -22.5)) {
                q = grad_mag[index + w - 1];
                r = grad_mag[index - w + 1];
            }

            if (grad_mag[index] >= q && grad_mag[index] >= r) {
                edges[index] = grad_mag[index];
            } else {
                edges[index] = 0;
            }
        }
    }

    // Double thresholding
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            if (edges[index] >= threshold2) {
                strong[index] = 255;
            } else if (edges[index] >= threshold1) {
                weak[index] = 255;
            } else {
                edges[index] = 0;
            }
        }
    }

    // Edge tracking by hysteresis
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            int index = y * w + x;
            if (weak[index] == 255) {
                if (strong[index - w - 1] || strong[index - w] || strong[index - w + 1] ||
                    strong[index - 1] || strong[index + 1] ||
                    strong[index + w - 1] || strong[index + w] || strong[index + w + 1]) {
                    strong[index] = 255;
                } else {
                    strong[index] = 0;
                }
            }
        }
    }

    // Copy strong edges to output
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            out[index] = strong[index] > 0 ? 1.0 : 0.0;
        }
    }

    // Free allocated memory
    free(gray);
    free(edges);
    free(weak);
    free(strong);
    free(blurred);
    free(grad_x);
    free(grad_y);
    free(grad_mag);
    free(grad_dir);
}
