#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int max_iterations = 6;
    const int initial_radius = 2;
    const double initial_seed_multiplier = 1.0;
    const double std_dev_multiplier = 3.0;

    // 入力画像の中心座標
    int center_x = w / 2;
    int center_y = h / 2;

    // 初期種子の選択
    double seed_value = in[center_y * w + center_x];
    int iterations = 1 + (int)(a * 5);
    double multiplier = 1.0 + (std_dev_multiplier * b);

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 初期種子の追加
    out[center_y * w + center_x] = 1.0;

    // 信頼区間連結の反復処理
    for (int iter = 0; iter < iterations; ++iter) {
        // 新しい領域の追加
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                if (out[y * w + x] == 1.0) {
                    // 現在のピクセルの平均と標準偏差の計算
                    double sum = 0.0;
                    int count = 0;
                    for (int dy = -initial_radius; dy <= initial_radius; ++dy) {
                        for (int dx = -initial_radius; dx <= initial_radius; ++dx) {
                            int ny = y + dy;
                            int nx = x + dx;
                            if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                                sum += in[ny * w + nx];
                                ++count;
                            }
                        }
                    }
                    double mean = sum / count;
                    double variance = 0.0;
                    for (int dy = -initial_radius; dy <= initial_radius; ++dy) {
                        for (int dx = -initial_radius; dx <= initial_radius; ++dx) {
                            int ny = y + dy;
                            int nx = x + dx;
                            if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                                double diff = in[ny * w + nx] - mean;
                                variance += diff * diff;
                            }
                        }
                    }
                    variance /= count;
                    double std_dev = sqrt(variance);

                    // 信頼区間の計算
                    double lower_bound = mean - multiplier * std_dev;
                    double upper_bound = mean + multiplier * std_dev;

                    // 信頼区間内のピクセルの追加
                    for (int dy = -initial_radius; dy <= initial_radius; ++dy) {
                        for (int dx = -initial_radius; dx <= initial_radius; ++dx) {
                            int ny = y + dy;
                            int nx = x + dx;
                            if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                                if (in[ny * w + nx] >= lower_bound && in[ny * w + nx] <= upper_bound) {
                                    out[ny * w + nx] = 1.0;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
