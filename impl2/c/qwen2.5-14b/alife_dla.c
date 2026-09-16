#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const int generations = 1 + (int)(11 * a); // a パラメータに基づく成長世代数
    const double stickiness_threshold = b; // b パラメータに基づく接着しきい値
    const double max_brightness = 0.75; // 画像の最大輝度の75%を基準輝度とする
    const double gaussian_sigma = 1.0; // ガウシアン拡散のシグマ
    const double gaussian_coeff = 1.0 / (2.0 * M_PI * gaussian_sigma * gaussian_sigma); // ガウシアン係数

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // シードピクセルの選択
    double max_val = -1.0;
    int seed_x = -1, seed_y = -1;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            if (in[y * w + x] > max_val) {
                max_val = in[y * w + x];
                seed_x = x;
                seed_y = y;
            }
        }
    }

    // シードピクセルの設定
    out[seed_y * w + seed_x] = 1.0;

    // DLA の成長
    for (int gen = 0; gen < generations; gen++) {
        // 現在のクラスタの境界を計算
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                if (out[y * w + x] == 1.0) {
                    // 現在のピクセルがクラスタの一部である場合、その周囲のピクセルをチェック
                    for (int dy = -1; dy <= 1; dy++) {
                        for (int dx = -1; dx <= 1; dx++) {
                            int ny = y + dy, nx = x + dx;
                            if (ny >= 0 && ny < h && nx >= 0 && nx < w && out[ny * w + nx] == 0.0) {
                                // 現在のピクセルの周囲のピクセルがクラスタの一部でない場合、そのピクセルの濃度を計算
                                double concentration = 0.0;
                                for (int sy = -1; sy <= 1; sy++) {
                                    for (int sx = -1; sx <= 1; sx++) {
                                        int sy2 = sy + dy, sx2 = sx + dx;
                                        if (sy2 >= 0 && sy2 < h && sx2 >= 0 && sx2 < w) {
                                            double d = sqrt((sy2 - sy) * (sy2 - sy) + (sx2 - sx) * (sx2 - sx));
                                            concentration += exp(-d * d / (2.0 * gaussian_sigma * gaussian_sigma)) * in[sy2 * w + sx2];
                                        }
                                    }
                                }
                                concentration *= gaussian_coeff;
                                if (concentration > stickiness_threshold) {
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
