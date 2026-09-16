#include <math.h>
#include <stdlib.h>
#include <string.h>

#define GRID_SIZE 5
#define EPSILON 1e-6

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    double amp = 0.12 * a * fmin(h, w);
    double alpha = 0.5 + 1.5 * b;
    double grid_step_x = 1.0 / (GRID_SIZE - 1);
    double grid_step_y = 1.0 / (GRID_SIZE - 1);

    // Control points p_i and displaced points q_i
    double p[GRID_SIZE * GRID_SIZE][2];
    double q[GRID_SIZE * GRID_SIZE][2];

    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            double gx = j * grid_step_x;
            double gy = i * grid_step_y;
            p[i * GRID_SIZE + j][0] = gx;
            p[i * GRID_SIZE + j][1] = gy;
            q[i * GRID_SIZE + j][0] = gx + amp * sin(2 * M_PI * gx);
            q[i * GRID_SIZE + j][1] = gy + amp * cos(2 * M_PI * gy);
        }
    }

    // For each pixel in the output image, compute the weighted least-squares affine map
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double v[2] = {(double)x / (w - 1), (double)y / (h - 1)};
            double weights[GRID_SIZE * GRID_SIZE];
            double sum_weights = 0.0;

            // Compute weights
            for (int i = 0; i < GRID_SIZE * GRID_SIZE; ++i) {
                double dist = sqrt(pow(p[i][0] - v[0], 2) + pow(p[i][1] - v[1], 2));
                weights[i] = dist < EPSILON ? 1.0 : pow(1.0 / (dist + EPSILON), 2 * alpha);
                sum_weights += weights[i];
            }

            // Normalize weights
            for (int i = 0; i < GRID_SIZE * GRID_SIZE; ++i) {
                weights[i] /= sum_weights;
            }

            // Compute weighted sums for the affine transformation
            double sum_p[2] = {0.0, 0.0};
            double sum_q[2] = {0.0, 0.0};
            double sum_pq[2][2] = {{0.0, 0.0}, {0.0, 0.0}};
            double sum_pp[2][2] = {{0.0, 0.0}, {0.0, 0.0}};

            for (int i = 0; i < GRID_SIZE * GRID_SIZE; ++i) {
                sum_p[0] += weights[i] * p[i][0];
                sum_p[1] += weights[i] * p[i][1];
                sum_q[0] += weights[i] * q[i][0];
                sum_q[1] += weights[i] * q[i][1];
                sum_pq[0][0] += weights[i] * p[i][0] * q[i][0];
                sum_pq[0][1] += weights[i] * p[i][0] * q[i][1];
                sum_pq[1][0] += weights[i] * p[i][1] * q[i][0];
                sum_pq[1][1] += weights[i] * p[i][1] * q[i][1];
                sum_pp[0][0] += weights[i] * p[i][0] * p[i][0];
                sum_pp[0][1] += weights[i] * p[i][0] * p[i][1];
                sum_pp[1][0] += weights[i] * p[i][1] * p[i][0];
                sum_pp[1][1] += weights[i] * p[i][1] * p[i][1];
            }

            // Solve for the affine transformation matrix A
            double det = sum_pp[0][0] * sum_pp[1][1] - sum_pp[0][1] * sum_pp[1][0];
            if (fabs(det) < EPSILON) {
                det = EPSILON; // Avoid division by zero
            }
            double A[2][2] = {
                {(sum_pp[1][1] * sum_pq[0][0] - sum_pp[0][1] * sum_pq[1][0]) / det,
                 (sum_pp[0][0] * sum_pq[1][0] - sum_pp[1][0] * sum_pq[0][0]) / det},
                {(sum_pp[1][1] * sum_pq[0][1] - sum_pp[0][1] * sum_pq[1][1]) / det,
                 (sum_pp[0][0] * sum_pq[1][1] - sum_pp[1][0] * sum_pq[0][1]) / det}
            };

            // Compute the translation vector t
            double t[2] = {
                sum_q[0] - A[0][0] * sum_p[0] - A[0][1] * sum_p[1],
                sum_q[1] - A[1][0] * sum_p[0] - A[1][1] * sum_p[1]
            };

            // Apply the affine transformation to the pixel coordinates
            double u[2] = {
                A[0][0] * v[0] + A[0][1] * v[1] + t[0],
                A[1][0] * v[0] + A[1][1] * v[1] + t[1]
            };

            // Bilinear interpolation to get the pixel value
            int x0 = (int)(u[0] * (w - 1));
            int y0 = (int)(u[1] * (h - 1));
            int x1 = x0 + 1;
            int y1 = y0 + 1;
            double wx = u[0] * (w - 1) - x0;
            double wy = u[1] * (h - 1) - y0;

            // Clamp to image boundaries
            x0 = x0 < 0 ? 0 : (x0 >= w ? w - 1 : x0);
            y0 = y0 < 0 ? 0 : (y0 >= h ? h - 1 : y0);
            x1 = x1 < 0 ? 0 : (x1 >= w ? w - 1 : x1);
            y1 = y1 < 0 ? 0 : (y1 >= h ? h - 1 : y1);

            double pixel00 = in[y0 * w + x0];
            double pixel01 = in[y0 * w + x1];
            double pixel10 = in[y1 * w + x0];
            double pixel11 = in[y1 * w + x1];

            double interpolated_value = (1 - wx) * (1 - wy) * pixel00 +
                                        wx * (1 - wy) * pixel01 +
                                        (1 - wx) * wy * pixel10 +
                                        wx * wy * pixel11;

            // Clamp the interpolated value to [0, 1]
            interpolated_value = interpolated_value < 0.0 ? 0.0 : (interpolated_value > 1.0 ? 1.0 : interpolated_value);

            out[y * w + x] = interpolated_value;
        }
    }
}
