#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 欠損領域のしきい値
    const double threshold_high = 235.0 / 255.0;
    const double threshold_low = 20.0 / 255.0;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // 画像の各画素を処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double pixel_value = in[y * w + x];
            // 欠損領域の判定
            if (pixel_value > threshold_high || pixel_value < threshold_low) {
                // 欠損領域の場合、周囲の画素値を平均して埋める
                double sum = 0.0;
                int count = 0;
                for (int dy = -3; dy <= 3; ++dy) {
                    for (int dx = -3; dx <= 3; ++dx) {
                        int ny = y + dy;
                        int nx = x + dx;
                        // 画像の範囲内に収まるかチェック
                        if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                            double neighbor_value = in[ny * w + nx];
                            if (neighbor_value >= threshold_low && neighbor_value <= threshold_high) {
                                sum += neighbor_value;
                                ++count;
                            }
                        }
                    }
                }
                // 周囲の画素値の平均を計算
                if (count > 0) {
                    out[y * w + x] = sum / count;
                } else {
                    // 周囲に適切な画素がない場合、元の値を保持
                    out[y * w + x] = pixel_value;
                }
            } else {
                // 欠損でない場合、元の値を保持
                out[y * w + x] = pixel_value;
            }
        }
    }
}
