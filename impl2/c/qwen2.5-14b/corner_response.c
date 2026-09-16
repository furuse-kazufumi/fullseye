#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。つまみ a はガウシアンの σ を 0.5 から 2.5 に変更する。
    // ここでは a の値を 0.5 から 2.5 にスケーリングして使用する。
    double sigma = a * 2.0 + 0.5;

    // ガウシアンカーネルのサイズを計算。σ の 3 倍のサイズを取る。
    int kernel_size = (int)(3 * sigma + 0.5);
    if (kernel_size % 2 == 0) {
        kernel_size++;
    }

    // ガウシアンカーネルを計算
    double* kernel = (double*)malloc(kernel_size * kernel_size * sizeof(double));
    double sum = 0.0;
    for (int i = -kernel_size / 2; i <= kernel_size / 2; i++) {
        for (int j = -kernel_size / 2; j <= kernel_size / 2; j++) {
            double x = i, y = j;
            kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)] = exp(-(x * x + y * y) / (2 * sigma * sigma));
            sum += kernel[(i + kernel_size / 2) * kernel_size + (j + kernel_size / 2)];
        }
    }
    for (int i = 0; i < kernel_size * kernel_size; i++) {
        kernel[i] /= sum;
    }

    // ガウシアンフィルタリングを適用
    double* Ix = (double*)malloc(h * w * sizeof(double));
    double* Iy = (double*)malloc(h * w * sizeof(double));
    double* Ixx = (double*)malloc(h * w * sizeof(double));
    double* Iyy = (double*)malloc(h * w * sizeof(double));
    double* Ixy = (double*)malloc(h * w * sizeof(double));

    // x 方向の微分
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int nx = x + kx;
                    int ny = y + ky;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        sum += kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)] * (in[ny * w + nx + 1] - in[ny * w + nx - 1]);
                    }
                }
            }
            Ix[y * w + x] = sum;
        }
    }

    // y 方向の微分
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int nx = x + kx;
                    int ny = y + ky;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        sum += kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)] * (in[ny * w + nx + w] - in[ny * w + nx - w]);
                    }
                }
            }
            Iy[y * w + x] = sum;
        }
    }

    // Ixx, Iyy, Ixy の計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int nx = x + kx;
                    int ny = y + ky;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        sum += kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)] * (Ix[ny * w + nx] * Ix[ny * w + nx]);
                    }
                }
            }
            Ixx[y * w + x] = sum;
        }
    }

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int nx = x + kx;
                    int ny = y + ky;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        sum += kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)] * (Iy[ny * w + nx] * Iy[ny * w + nx]);
                    }
                }
            }
            Iyy[y * w + x] = sum;
        }
    }

    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int ky = -kernel_size / 2; ky <= kernel_size / 2; ky++) {
                for (int kx = -kernel_size / 2; kx <= kernel_size / 2; kx++) {
                    int nx = x + kx;
                    int ny = y + ky;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        sum += kernel[(ky + kernel_size / 2) * kernel_size + (kx + kernel_size / 2)] * (Ix[ny * w + nx] * Iy[ny * w + nx]);
                    }
                }
            }
            Ixy[y * w + x] = sum;
        }
    }

    // Harris コーナー検出の応答値を計算
    double k = 0.04;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double det = Ixx[y * w + x] * Iyy[y * w + x] - Ixy[y * w + x] * Ixy[y * w + x];
            double trace = Ixx[y * w + x] + Iyy[y * w + x];
            double response = det - k * trace * trace;
            out[y * w + x] = (response + 1.0) / 2.0; // [0,1] に正規化
        }
    }

    // メモリの解放
    free(kernel);
    free(Ix);
    free(Iy);
    free(Ixx);
    free(Iyy);
    free(Ixy);
}
