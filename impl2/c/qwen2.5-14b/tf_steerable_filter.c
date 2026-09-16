#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を 0 に設定する
    // これは境界外アクセスを避けるための簡単な方法であり、仕様書では明示的に定義されていないため、この選択を明記します。

    // 2D ガウシアンフィルタのパラメータ
    double sigma = b; // b はガウシアンの標準偏差を設定
    double theta = a * M_PI; // a は角度を設定 (0 から pi の範囲)

    // ガウシアンフィルタの係数を計算
    double gaussian_filter[3][3];
    double sum = 0.0;
    for (int i = -1; i <= 1; ++i) {
        for (int j = -1; j <= 1; ++j) {
            double coefficient = exp(-(i*i + j*j) / (2 * sigma * sigma)) / (2 * M_PI * sigma * sigma);
            gaussian_filter[i + 1][j + 1] = coefficient;
            sum += coefficient;
        }
    }
    for (int i = -1; i <= 1; ++i) {
        for (int j = -1; j <= 1; ++j) {
            gaussian_filter[i + 1][j + 1] /= sum; // 正規化
        }
    }

    // 画像のガウシアンフィルタリング
    double gaussian_image[h][w];
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double value = 0.0;
            for (int i = -1; i <= 1; ++i) {
                for (int j = -1; j <= 1; ++j) {
                    int ny = y + i;
                    int nx = x + j;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        value += in[ny * w + nx] * gaussian_filter[i + 1][j + 1];
                    }
                }
            }
            gaussian_image[y][x] = value;
        }
    }

    // x 方向と y 方向の微分
    double dx[h][w];
    double dy[h][w];
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            dx[y][x] = (x == 0) ? 0 : (gaussian_image[y][x] - gaussian_image[y][x - 1]);
            dy[y][x] = (y == 0) ? 0 : (gaussian_image[y][x] - gaussian_image[y - 1][x]);
        }
    }

    // 方向付き微分
    double response[h][w];
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            response[y][x] = cos(theta) * dx[y][x] + sin(theta) * dy[y][x];
        }
    }

    // 答えを [0,1] の範囲にマッピング
    double min_response = 1.0;
    double max_response = -1.0;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (response[y][x] < min_response) min_response = response[y][x];
            if (response[y][x] > max_response) max_response = response[y][x];
        }
    }
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = (response[y][x] - min_response) / (max_response - min_response + 1e-6);
        }
    }
}
