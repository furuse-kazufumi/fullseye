#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Initialize output to 0
    memset(out, 0, h * w * sizeof(double));

    // Parameters for edge detection and segmentation
    double threshold = a * 0.3;
    double min_ratio = 3 + b * 12;

    // Temporary storage for gradient magnitude and direction
    double* magnitude = (double*)malloc(h * w * sizeof(double));
    double* direction = (double*)malloc(h * w * sizeof(double));

    // Compute gradient magnitude and direction using Sobel operator
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double gx = (in[(y-1)*w + (x+1)] + 2*in[y*w + (x+1)] + in[(y+1)*w + (x+1)]) -
                       (in[(y-1)*w + (x-1)] + 2*in[y*w + (x-1)] + in[(y+1)*w + (x-1)]);
            double gy = (in[(y+1)*w + (x-1)] + 2*in[(y+1)*w + x] + in[(y+1)*w + (x+1)]) -
                       (in[(y-1)*w + (x-1)] + 2*in[(y-1)*w + x] + in[(y-1)*w + (x+1)]);
            magnitude[y*w + x] = sqrt(gx * gx + gy * gy);
            direction[y*w + x] = atan2(gy, gx);
        }
    }

    // Non-maximum suppression
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            double angle = direction[y*w + x] * 180 / M_PI;
            if (angle < 0) angle += 180;

            int q = 255, r = 255;

            // angle 0
            if ((angle >= 0 && angle < 22.5) || (angle >= 157.5 && angle <= 180)) {
                q = magnitude[y*w + (x+1)];
                r = magnitude[y*w + (x-1)];
            }
            // angle 45
            else if (angle >= 22.5 && angle < 67.5) {
                q = magnitude[(y+1)*w + (x+1)];
                r = magnitude[(y-1)*w + (x-1)];
            }
            // angle 90
            else if (angle >= 67.5 && angle < 112.5) {
                q = magnitude[(y+1)*w + x];
                r = magnitude[(y-1)*w + x];
            }
            // angle 135
            else if (angle >= 112.5 && angle < 157.5) {
                q = magnitude[(y-1)*w + (x+1)];
                r = magnitude[(y+1)*w + (x-1)];
            }

            if (magnitude[y*w + x] >= q && magnitude[y*w + x] >= r && magnitude[y*w + x] >= threshold) {
                out[y*w + x] = magnitude[y*w + x];
            } else {
                out[y*w + x] = 0;
            }
        }
    }

    // Label connected components
    int* labels = (int*)malloc(h * w * sizeof(int));
    memset(labels, 0, h * w * sizeof(int));
    int label_count = 1;

    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            if (out[y*w + x] > 0) {
                int neighbors[8] = {
                    labels[(y-1)*w + (x-1)], labels[(y-1)*w + x], labels[(y-1)*w + (x+1)],
                    labels[y*w + (x-1)], labels[y*w + (x+1)],
                    labels[(y+1)*w + (x-1)], labels[(y+1)*w + x], labels[(y+1)*w + (x+1)]
                };
                int min_label = 0;
                for (int i = 0; i < 8; i++) {
                    if (neighbors[i] > 0 && (min_label == 0 || neighbors[i] < min_label)) {
                        min_label = neighbors[i];
                    }
                }
                if (min_label == 0) {
                    labels[y*w + x] = label_count++;
                } else {
                    labels[y*w + x] = min_label;
                    for (int i = 0; i < 8; i++) {
                        if (neighbors[i] > min_label) {
                            for (int j = 1; j < h - 1; j++) {
                                for (int k = 1; k < w - 1; k++) {
                                    if (labels[j*w + k] == neighbors[i]) {
                                        labels[j*w + k] = min_label;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Calculate PCA for each component and filter based on min_ratio
    for (int label = 1; label < label_count; label++) {
        int count = 0;
        double sum_x = 0, sum_y = 0;
        double sum_xx = 0, sum_yy = 0, sum_xy = 0;

        for (int y = 1; y < h - 1; y++) {
            for (int x = 1; x < w - 1; x++) {
                if (labels[y*w + x] == label) {
                    count++;
                    sum_x += x;
                    sum_y += y;
                    sum_xx += x * x;
                    sum_yy += y * y;
                    sum_xy += x * y;
                }
            }
        }

        if (count >= 5) {
            double mean_x = sum_x / count;
            double mean_y = sum_y / count;
            double cov_xx = sum_xx / count - mean_x * mean_x;
            double cov_yy = sum_yy / count - mean_y * mean_y;
            double cov_xy = sum_xy / count - mean_x * mean_y;

            double lambda1, lambda2;
            double discriminant = sqrt((cov_xx - cov_yy) * (cov_xx - cov_yy) + 4 * cov_xy * cov_xy);
            lambda1 = (cov_xx + cov_yy + discriminant) / 2;
            lambda2 = (cov_xx + cov_yy - discriminant) / 2;

            if (lambda2 == 0 || (lambda1 / lambda2 >= min_ratio)) {
                for (int y = 1; y < h - 1; y++) {
                    for (int x = 1; x < w - 1; x++) {
                        if (labels[y*w + x] == label) {
                            out[y*w + x] = 1.0;
                        }
                    }
                }
            } else {
                for (int y = 1; y < h - 1; y++) {
                    for (int x = 1; x < w - 1; x++) {
                        if (labels[y*w + x] == label) {
                            out[y*w + x] = 0.0;
                        }
                    }
                }
            }
        } else {
            for (int y = 1; y < h - 1; y++) {
                for (int x = 1; x < w - 1; x++) {
                    if (labels[y*w + x] == label) {
                        out[y*w + x] = 0.0;
                    }
                }
            }
        }
    }

    // Clean up
    free(magnitude);
    free(direction);
    free(labels);
}
