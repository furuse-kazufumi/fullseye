#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Harris コーナー応答のシグマを計算
    double sigma_a = 0.5 + 2.0 * a;
    double sigma_b = 0.5 + 1.5 * b;

    // 画像の平滑化
    double* smoothed = (double*)malloc(h * w * sizeof(double));
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            int count = 0;
            for (int dy = -sigma_b; dy <= sigma_b; dy++) {
                for (int dx = -sigma_b; dx <= sigma_b; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        sum += in[ny * w + nx];
                        count++;
                    }
                }
            }
            smoothed[y * w + x] = sum / count;
        }
    }

    // Harris コーナー応答の計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double Ix = 0.0, Iy = 0.0, Ixx = 0.0, Iyy = 0.0, Ixy = 0.0;
            for (int dy = -sigma_a; dy <= sigma_a; dy++) {
                for (int dx = -sigma_a; dx <= sigma_a; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double I = smoothed[ny * w + nx];
                        Ix += dx * I;
                        Iy += dy * I;
                        Ixx += dx * dx * I;
                        Iyy += dy * dy * I;
                        Ixy += dx * dy * I;
                    }
                }
            }
            double det = Ixx * Iyy - Ixy * Ixy;
            double trace = Ixx + Iyy;
            out[y * w + x] = det - 0.04 * trace * trace;
        }
    }

    // 出力を最大値で正規化
    double max_response = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_response) {
            max_response = out[i];
        }
    }
    if (max_response > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_response;
        }
    }

    free(smoothed);
}
